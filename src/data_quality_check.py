"""Validate referential, temporal and business consistency of generated data."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"


def load_tables() -> dict[str, pd.DataFrame]:
    names = [
        "user_info",
        "prompt_pool",
        "generation_tasks",
        "user_actions",
        "payment_orders",
        "ab_experiment",
        "model_scores",
    ]
    missing = [name for name in names if not (DATA_DIR / f"{name}.csv").exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing CSV files: {missing}. Run src/generate_mock_data.py first."
        )
    tables = {
        name: pd.read_csv(DATA_DIR / f"{name}.csv", encoding="utf-8-sig")
        for name in names
    }
    for table_name, columns in {
        "user_info": ["register_date", "first_visit_date"],
        "generation_tasks": ["submit_time", "finish_time"],
        "user_actions": ["event_time"],
        "payment_orders": ["order_time"],
        "ab_experiment": ["enter_time"],
    }.items():
        for column in columns:
            tables[table_name][column] = pd.to_datetime(
                tables[table_name][column], errors="coerce"
            )
    return tables


class CheckRunner:
    def __init__(self):
        self.failures = []

    def check(self, condition: bool, label: str, detail: str = ""):
        marker = "PASS" if condition else "FAIL"
        print(f"[{marker}] {label}" + (f" — {detail}" if detail else ""))
        if not condition:
            self.failures.append(label)


def main() -> None:
    t = load_tables()
    users = t["user_info"]
    prompts = t["prompt_pool"]
    tasks = t["generation_tasks"]
    actions = t["user_actions"]
    orders = t["payment_orders"]
    experiment = t["ab_experiment"]
    scores = t["model_scores"]
    check = CheckRunner()

    print("=== Structural checks ===")
    for frame, key, name in [
        (users, "user_id", "user_info"),
        (prompts, "prompt_id", "prompt_pool"),
        (tasks, "task_id", "generation_tasks"),
        (actions, "event_id", "user_actions"),
        (orders, "order_id", "payment_orders"),
        (experiment, "user_id", "ab_experiment"),
        (scores, "task_id", "model_scores"),
    ]:
        check.check(frame[key].notna().all() and frame[key].is_unique, f"{name} primary key")

    check.check(tasks["user_id"].isin(users["user_id"]).all(), "task user foreign keys")
    check.check(tasks["prompt_id"].isin(prompts["prompt_id"]).all(), "task prompt foreign keys")
    check.check(actions["user_id"].isin(users["user_id"]).all(), "action user foreign keys")
    check.check(actions["task_id"].isin(tasks["task_id"]).all(), "action task foreign keys")
    check.check(orders["user_id"].isin(users["user_id"]).all(), "order user foreign keys")
    check.check(orders["task_id"].isin(tasks["task_id"]).all(), "order task foreign keys")
    check.check(experiment["user_id"].isin(users["user_id"]).all(), "experiment user foreign keys")
    check.check(scores["task_id"].isin(tasks["task_id"]).all(), "score task foreign keys")

    print("\n=== Time and business logic checks ===")
    check.check((tasks["finish_time"] > tasks["submit_time"]).all(), "finish after submit")
    task_finish = tasks.set_index("task_id")["finish_time"]
    check.check(
        (actions["event_time"] >= actions["task_id"].map(task_finish)).all(),
        "actions occur after task finish",
    )
    check.check(
        (orders["order_time"] >= orders["task_id"].map(task_finish)).all(),
        "orders occur after task finish",
    )
    check.check((orders["amount"] > 0).all(), "all order amounts positive")
    check.check(
        set(orders["pay_status"].unique()).issubset({"success", "failed"}),
        "valid payment statuses",
    )

    task_status = tasks.set_index("task_id")["status"]
    success_only_actions = {"preview", "download", "share", "favorite", "edit_again", "regenerate", "pay_click"}
    illegal_action_count = actions.loc[
        actions["action_type"].isin(success_only_actions)
        & actions["task_id"].map(task_status).ne("success")
    ].shape[0]
    check.check(illegal_action_count == 0, "failed tasks have no success-only actions", f"{illegal_action_count} illegal rows")

    score_status = scores["task_id"].map(task_status)
    check.check(score_status.eq("success").all(), "scores only exist for successful tasks")
    success_ids = set(tasks.loc[tasks["status"] == "success", "task_id"])
    check.check(set(scores["task_id"]) == success_ids, "every successful task has one score")
    score_cols = ["clarity_score", "motion_score", "style_score", "human_score"]
    check.check(scores[score_cols].apply(lambda col: col.between(1, 5).all()).all(), "scores within 1 to 5")
    check.check(
        (tasks.loc[tasks["status"] == "success", "fail_reason"] == "none").all()
        and (tasks.loc[tasks["status"] != "success", "fail_reason"] != "none").all(),
        "status and fail_reason agree",
    )

    action_pairs = set(zip(actions["task_id"], actions["action_type"]))
    orders_have_click = orders["task_id"].map(lambda task_id: (task_id, "pay_click") in action_pairs)
    check.check(orders_have_click.all(), "every order follows a pay_click")
    check.check(orders["task_id"].is_unique, "at most one payment attempt per task")

    successful_payers = set(orders.loc[orders["pay_status"] == "success", "user_id"])
    flagged_payers = set(users.loc[users["is_paid"] == 1, "user_id"])
    check.check(successful_payers == flagged_payers, "user payment flag matches successful orders")
    check.check(
        ((users["is_paid"] == 1) == (users["user_type"] == "payer")).all(),
        "user_type matches is_paid",
    )

    print("\n=== Experiment and signal checks ===")
    group_share = experiment["group"].value_counts(normalize=True)
    balance_ok = group_share.between(0.48, 0.52).all()
    check.check(balance_ok, "experiment groups are balanced", group_share.round(4).to_dict().__str__())
    check.check(experiment["user_id"].is_unique, "one experiment group per user")

    task_summary = tasks.groupby("model_version").agg(
        tasks=("task_id", "size"),
        success_rate=("status", lambda x: x.eq("success").mean()),
        avg_duration=("generation_duration", "mean"),
    )
    score_summary = scores.groupby("model_version").agg(
        human_score=("human_score", "mean"),
        style_score=("style_score", "mean"),
        complaint_rate=("complaint_flag", "mean"),
    )
    summary = task_summary.join(score_summary)
    print("\nModel diagnostic summary:")
    print(summary.round(4).to_string())
    check.check(
        summary.loc["Model_A", "avg_duration"] < summary.loc["Model_C", "avg_duration"] < summary.loc["Model_B", "avg_duration"],
        "model duration ordering A < C < B",
    )
    check.check(
        summary.loc["Model_A", "success_rate"] > summary.loc["Model_B", "success_rate"] > summary.loc["Model_C", "success_rate"],
        "model success ordering A > B > C",
    )
    check.check(
        summary.loc["Model_B", "human_score"] > summary.loc["Model_A", "human_score"],
        "Model_B has higher human score than Model_A",
    )
    check.check(
        summary.loc["Model_C", "style_score"] > summary.loc["Model_A", "style_score"],
        "Model_C has stronger style score than Model_A",
    )

    user_group = experiment.set_index("user_id")["group"]
    successful_task_ids = set(tasks.loc[tasks["status"] == "success", "task_id"])
    successful_users = set(tasks.loc[tasks["task_id"].isin(successful_task_ids), "user_id"])
    click_users = actions.loc[actions["action_type"] == "pay_click"].groupby("user_id").size().index
    experiment_metrics = []
    for group in ["control", "treatment"]:
        group_users = set(user_group[user_group == group].index) & successful_users
        clicked = len(group_users & set(click_users))
        experiment_metrics.append(
            {"group": group, "successful_users": len(group_users), "click_users": clicked, "click_rate": clicked / len(group_users)}
        )
    experiment_metrics = pd.DataFrame(experiment_metrics).set_index("group")
    print("\nExperiment diagnostic summary:")
    print(experiment_metrics.round(4).to_string())
    check.check(
        experiment_metrics.loc["treatment", "click_rate"] > experiment_metrics.loc["control", "click_rate"],
        "treatment pay-click rate exceeds control",
    )

    print("\n=== Result ===")
    if check.failures:
        print(f"QUALITY CHECK FAILED: {len(check.failures)} issue(s): {check.failures}")
        raise SystemExit(1)
    print(
        f"ALL CHECKS PASSED | users={len(users):,}, tasks={len(tasks):,}, "
        f"actions={len(actions):,}, orders={len(orders):,}"
    )


if __name__ == "__main__":
    main()

