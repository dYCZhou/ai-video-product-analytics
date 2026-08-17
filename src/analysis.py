"""Run the end-to-end product, model and A/B analysis and export reproducible results."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, norm, ttest_ind


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def load_data() -> dict[str, pd.DataFrame]:
    tables = {
        name: pd.read_csv(RAW / f"{name}.csv", encoding="utf-8-sig")
        for name in [
            "user_info",
            "prompt_pool",
            "generation_tasks",
            "user_actions",
            "payment_orders",
            "ab_experiment",
            "model_scores",
        ]
    }
    for table, cols in {
        "user_info": ["register_date", "first_visit_date"],
        "generation_tasks": ["submit_time", "finish_time"],
        "user_actions": ["event_time"],
        "payment_orders": ["order_time"],
        "ab_experiment": ["enter_time"],
    }.items():
        for col in cols:
            tables[table][col] = pd.to_datetime(tables[table][col])
    return tables


def safe_rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def two_proportion_test(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (x2 / n2 - x1 / n1) / se if se else 0.0
    return float(z), float(2 * norm.sf(abs(z)))


def action_task_sets(actions: pd.DataFrame) -> dict[str, set[str]]:
    return {
        action: set(group["task_id"])
        for action, group in actions.groupby("action_type")
    }


def build_funnel(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    users, tasks, actions, orders = (
        t["user_info"],
        t["generation_tasks"],
        t["user_actions"],
        t["payment_orders"],
    )
    stages = [
        ("注册用户", set(users["user_id"])),
        ("提交生成", set(tasks["user_id"])),
        ("生成成功", set(tasks.loc[tasks["status"].eq("success"), "user_id"])),
        ("预览视频", set(actions.loc[actions["action_type"].eq("preview"), "user_id"])),
        ("下载视频", set(actions.loc[actions["action_type"].eq("download"), "user_id"])),
        ("付费点击", set(actions.loc[actions["action_type"].eq("pay_click"), "user_id"])),
        ("支付成功", set(orders.loc[orders["pay_status"].eq("success"), "user_id"])),
    ]
    rows = []
    previous = None
    base = len(stages[0][1])
    for stage, ids in stages:
        count = len(ids)
        rows.append(
            {
                "stage": stage,
                "users": count,
                "overall_conversion": safe_rate(count, base),
                "step_conversion": 1.0 if previous is None else safe_rate(count, previous),
            }
        )
        previous = count
    return pd.DataFrame(rows)


def build_model_metrics(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tasks = t["generation_tasks"]
    actions = t["user_actions"]
    orders = t["payment_orders"]
    scores = t["model_scores"]
    action_sets = action_task_sets(actions)
    paid_tasks = set(orders.loc[orders["pay_status"].eq("success"), "task_id"])
    rows = []
    for model, group in tasks.groupby("model_version"):
        successful = group.loc[group["status"].eq("success")]
        successful_ids = set(successful["task_id"])
        model_scores = scores.loc[scores["model_version"].eq(model)]
        rows.append(
            {
                "model_version": model,
                "tasks": len(group),
                "success_rate": group["status"].eq("success").mean(),
                "avg_duration_sec": group["generation_duration"].mean(),
                "p90_duration_sec": group["generation_duration"].quantile(0.9),
                "human_score": model_scores["human_score"].mean(),
                "style_score": model_scores["style_score"].mean(),
                "download_rate": safe_rate(
                    len(successful_ids & action_sets.get("download", set())),
                    len(successful_ids),
                ),
                "edit_rate": safe_rate(
                    len(successful_ids & action_sets.get("edit_again", set())),
                    len(successful_ids),
                ),
                "task_pay_rate": safe_rate(
                    len(successful_ids & paid_tasks), len(successful_ids)
                ),
                "complaint_rate": model_scores["complaint_flag"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("model_version")


def build_prompt_metrics(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tasks = t["generation_tasks"].merge(
        t["prompt_pool"][["prompt_id", "prompt_type", "commercial_intent"]],
        on="prompt_id",
        how="left",
        validate="many_to_one",
    )
    actions = t["user_actions"]
    orders = t["payment_orders"]
    action_sets = action_task_sets(actions)
    paid_orders = orders.loc[orders["pay_status"].eq("success")]
    paid_tasks = set(paid_orders["task_id"])
    revenue_map = paid_orders.groupby("task_id")["amount"].sum().to_dict()
    rows = []
    for prompt_type, group in tasks.groupby("prompt_type"):
        successful_ids = set(group.loc[group["status"].eq("success"), "task_id"])
        all_ids = set(group["task_id"])
        rows.append(
            {
                "prompt_type": prompt_type,
                "tasks": len(group),
                "success_rate": group["status"].eq("success").mean(),
                "download_rate": safe_rate(
                    len(successful_ids & action_sets.get("download", set())),
                    len(successful_ids),
                ),
                "pay_click_rate": safe_rate(
                    len(successful_ids & action_sets.get("pay_click", set())),
                    len(successful_ids),
                ),
                "task_pay_rate": safe_rate(
                    len(successful_ids & paid_tasks), len(successful_ids)
                ),
                "revenue": sum(revenue_map.get(task_id, 0) for task_id in all_ids),
                "revenue_per_task": safe_rate(
                    sum(revenue_map.get(task_id, 0) for task_id in all_ids),
                    len(group),
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("revenue_per_task", ascending=False)


def build_channel_metrics(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    users = t["user_info"]
    tasks = t["generation_tasks"]
    orders = t["payment_orders"]
    success_users = set(tasks.loc[tasks["status"].eq("success"), "user_id"])
    paid = orders.loc[orders["pay_status"].eq("success")]
    revenue_by_user = paid.groupby("user_id")["amount"].sum()
    rows = []
    for channel, group in users.groupby("channel"):
        ids = set(group["user_id"])
        revenue = revenue_by_user.reindex(list(ids)).fillna(0).sum()
        paid_users = len(ids & set(paid["user_id"]))
        rows.append(
            {
                "channel": channel,
                "users": len(ids),
                "success_user_rate": safe_rate(len(ids & success_users), len(ids)),
                "payer_rate": safe_rate(paid_users, len(ids)),
                "arpu": safe_rate(revenue, len(ids)),
                "arppu": safe_rate(revenue, paid_users),
                "revenue": revenue,
            }
        )
    return pd.DataFrame(rows).sort_values("payer_rate", ascending=False)


def build_duration_metrics(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    successful = t["generation_tasks"].loc[
        t["generation_tasks"]["status"].eq("success")
    ].copy()
    successful["duration_bucket"] = pd.cut(
        successful["generation_duration"],
        bins=[0, 45, 75, 120, np.inf],
        labels=["≤45s", "46–75s", "76–120s", ">120s"],
        right=True,
    )
    sets = action_task_sets(t["user_actions"])
    rows = []
    for bucket, group in successful.groupby("duration_bucket", observed=True):
        ids = set(group["task_id"])
        rows.append(
            {
                "duration_bucket": str(bucket),
                "successful_tasks": len(ids),
                "preview_rate": safe_rate(
                    len(ids & sets.get("preview", set())), len(ids)
                ),
                "download_rate": safe_rate(
                    len(ids & sets.get("download", set())), len(ids)
                ),
                "exit_rate": safe_rate(len(ids & sets.get("exit", set())), len(ids)),
            }
        )
    return pd.DataFrame(rows)


def build_retention(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    users = t["user_info"][["user_id", "register_date"]].copy()
    users["register_day"] = users["register_date"].dt.normalize()
    activity = t["generation_tasks"][["user_id", "submit_time"]].copy()
    activity["active_day"] = activity["submit_time"].dt.normalize()
    activity = activity.drop_duplicates(["user_id", "active_day"]).merge(
        users[["user_id", "register_day"]], on="user_id", how="left"
    )
    activity["day_gap"] = (activity["active_day"] - activity["register_day"]).dt.days
    d0_users = set(activity.loc[activity["day_gap"].eq(0), "user_id"])
    data_end = t["generation_tasks"]["submit_time"].max().normalize()
    register_day_by_user = users.set_index("user_id")["register_day"]
    cohorts = []
    for gap in [0, 1, 7, 14]:
        # Only users with a complete observation window are eligible for Dn.
        mature_users = set(
            register_day_by_user.loc[
                register_day_by_user.le(data_end - pd.Timedelta(days=gap))
            ].index
        )
        eligible_d0_users = d0_users & mature_users
        active_users = set(activity.loc[activity["day_gap"].eq(gap), "user_id"])
        retained = len(eligible_d0_users & active_users)
        cohorts.append(
            {
                "retention_day": f"D{gap}",
                "retained_users": retained,
                "eligible_d0_users": len(eligible_d0_users),
                "retention_rate": safe_rate(retained, len(eligible_d0_users)),
            }
        )
    return pd.DataFrame(cohorts)


def build_ab_metrics(t: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict]:
    experiment = t["ab_experiment"]
    tasks = t["generation_tasks"].merge(
        experiment[["user_id", "group", "enter_time"]],
        on="user_id",
        validate="many_to_one",
    )
    tasks = tasks.loc[tasks["submit_time"].ge(tasks["enter_time"])].copy()
    post_task_ids = set(tasks["task_id"])
    actions = t["user_actions"].loc[
        t["user_actions"]["task_id"].isin(post_task_ids)
    ].copy()
    orders = t["payment_orders"].loc[
        t["payment_orders"]["task_id"].isin(post_task_ids)
    ].copy()
    scores = t["model_scores"].loc[
        t["model_scores"]["task_id"].isin(post_task_ids)
    ].copy()

    eligible_users = set(tasks["user_id"])
    success_users = set(tasks.loc[tasks["status"].eq("success"), "user_id"])
    click_users = set(actions.loc[actions["action_type"].eq("pay_click"), "user_id"])
    action_sets = action_task_sets(actions)
    paid = orders.loc[orders["pay_status"].eq("success")]
    paid_users = set(paid["user_id"])
    revenue_by_user = paid.groupby("user_id")["amount"].sum()
    complained_tasks = set(scores.loc[scores["complaint_flag"].eq(1), "task_id"])

    rows = []
    for group_name, assignment in experiment.groupby("group"):
        assigned = set(assignment["user_id"]) & eligible_users
        success = assigned & success_users
        clicks = assigned & click_users
        payers = assigned & paid_users
        group_tasks = tasks.loc[tasks["user_id"].isin(assigned)]
        task_ids = set(group_tasks["task_id"])
        successful_task_ids = set(
            group_tasks.loc[group_tasks["status"].eq("success"), "task_id"]
        )
        revenue = revenue_by_user.reindex(list(assigned)).fillna(0).sum()
        rows.append(
            {
                "group": group_name,
                "eligible_users": len(assigned),
                "successful_users": len(success),
                "click_users": len(clicks),
                "payer_users": len(payers),
                "tasks": len(task_ids),
                "successful_tasks": len(successful_task_ids),
                "pay_click_rate": safe_rate(len(clicks), len(success)),
                "click_to_pay_rate": safe_rate(len(payers), len(clicks)),
                "user_pay_rate": safe_rate(len(payers), len(assigned)),
                "task_download_rate": safe_rate(
                    len(successful_task_ids & action_sets.get("download", set())),
                    len(successful_task_ids),
                ),
                "task_exit_rate": safe_rate(
                    len(task_ids & action_sets.get("exit", set())), len(task_ids)
                ),
                "task_regenerate_rate": safe_rate(
                    len(successful_task_ids & action_sets.get("regenerate", set())),
                    len(successful_task_ids),
                ),
                "task_complaint_rate": safe_rate(
                    len(successful_task_ids & complained_tasks),
                    len(successful_task_ids),
                ),
                "revenue": revenue,
                "arpu": safe_rate(revenue, len(assigned)),
            }
        )
    result = pd.DataFrame(rows).sort_values("group").reset_index(drop=True)
    c = result.set_index("group").loc["control"]
    e = result.set_index("group").loc["treatment"]
    z_click, p_click = two_proportion_test(
        int(c["click_users"]),
        int(c["successful_users"]),
        int(e["click_users"]),
        int(e["successful_users"]),
    )
    z_pay, p_pay = two_proportion_test(
        int(c["payer_users"]),
        int(c["eligible_users"]),
        int(e["payer_users"]),
        int(e["eligible_users"]),
    )
    observed = (
        experiment["group"].value_counts().reindex(["control", "treatment"]).to_numpy()
    )
    _, srm_p = chi2_contingency(
        np.vstack([observed, np.array([len(experiment) / 2] * 2)])
    )[:2]

    control_revenue = revenue_by_user.reindex(
        experiment.loc[experiment["group"].eq("control"), "user_id"]
    ).fillna(0)
    treatment_revenue = revenue_by_user.reindex(
        experiment.loc[experiment["group"].eq("treatment"), "user_id"]
    ).fillna(0)
    _, revenue_p = ttest_ind(
        control_revenue, treatment_revenue, equal_var=False
    )
    stats = {
        "pay_click_absolute_lift_pp": float(
            (e["pay_click_rate"] - c["pay_click_rate"]) * 100
        ),
        "pay_click_relative_lift": float(
            e["pay_click_rate"] / c["pay_click_rate"] - 1
        ),
        "pay_click_z": z_click,
        "pay_click_p_value": p_click,
        "user_pay_absolute_lift_pp": float(
            (e["user_pay_rate"] - c["user_pay_rate"]) * 100
        ),
        "user_pay_relative_lift": float(
            e["user_pay_rate"] / c["user_pay_rate"] - 1
        ),
        "user_pay_z": z_pay,
        "user_pay_p_value": p_pay,
        "arpu_relative_lift": float(e["arpu"] / c["arpu"] - 1),
        "revenue_ttest_p_value": float(revenue_p),
        "srm_p_value": float(srm_p),
    }
    return result, stats


def build_summary(
    t: dict[str, pd.DataFrame],
    funnel: pd.DataFrame,
    models: pd.DataFrame,
    prompts: pd.DataFrame,
    channels: pd.DataFrame,
    duration: pd.DataFrame,
    retention: pd.DataFrame,
    ab: pd.DataFrame,
    ab_stats: dict,
) -> dict:
    tasks, actions, orders = (
        t["generation_tasks"],
        t["user_actions"],
        t["payment_orders"],
    )
    successful = tasks.loc[tasks["status"].eq("success")]
    successful_ids = set(successful["task_id"])
    action_sets = action_task_sets(actions)
    paid = orders.loc[orders["pay_status"].eq("success")]
    effective_actions = {"download", "share", "favorite", "edit_again", "regenerate"}
    effective_users = actions.loc[
        actions["action_type"].isin(effective_actions), "user_id"
    ].nunique()
    return {
        "data_scope": {
            "users": len(t["user_info"]),
            "prompts": len(t["prompt_pool"]),
            "tasks": len(tasks),
            "actions": len(actions),
            "orders": len(orders),
            "successful_orders": len(paid),
            "start_date": str(tasks["submit_time"].min().date()),
            "end_date": str(tasks["submit_time"].max().date()),
        },
        "overall": {
            "success_rate": float(tasks["status"].eq("success").mean()),
            "avg_duration_sec": float(tasks["generation_duration"].mean()),
            "p90_duration_sec": float(tasks["generation_duration"].quantile(0.9)),
            "download_rate": safe_rate(
                len(successful_ids & action_sets.get("download", set())),
                len(successful_ids),
            ),
            "edit_rate": safe_rate(
                len(successful_ids & action_sets.get("edit_again", set())),
                len(successful_ids),
            ),
            "pay_click_rate": safe_rate(
                len(successful_ids & action_sets.get("pay_click", set())),
                len(successful_ids),
            ),
            "payer_rate": safe_rate(paid["user_id"].nunique(), len(t["user_info"])),
            "revenue": float(paid["amount"].sum()),
            "arpu": safe_rate(paid["amount"].sum(), len(t["user_info"])),
            "arppu": safe_rate(paid["amount"].sum(), paid["user_id"].nunique()),
            "effective_video_users": int(effective_users),
        },
        "key_findings": {
            "best_success_model": models.loc[
                models["success_rate"].idxmax(), "model_version"
            ],
            "highest_quality_model": models.loc[
                models["human_score"].idxmax(), "model_version"
            ],
            "highest_style_model": models.loc[
                models["style_score"].idxmax(), "model_version"
            ],
            "highest_value_prompt": prompts.iloc[0]["prompt_type"],
            "highest_payer_channel": channels.iloc[0]["channel"],
            "d1_retention_rate": float(
                retention.loc[retention["retention_day"].eq("D1"), "retention_rate"].iloc[0]
            ),
            "fast_bucket_download_rate": float(duration.iloc[0]["download_rate"]),
            "slow_bucket_download_rate": float(duration.iloc[-1]["download_rate"]),
        },
        "ab_test": ab_stats,
    }


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    t = load_data()
    funnel = build_funnel(t)
    models = build_model_metrics(t)
    prompts = build_prompt_metrics(t)
    channels = build_channel_metrics(t)
    duration = build_duration_metrics(t)
    retention = build_retention(t)
    ab, ab_stats = build_ab_metrics(t)
    outputs = {
        "funnel_metrics": funnel,
        "model_metrics": models,
        "prompt_metrics": prompts,
        "channel_metrics": channels,
        "duration_metrics": duration,
        "retention_metrics": retention,
        "ab_metrics": ab,
    }
    for name, frame in outputs.items():
        frame.to_csv(PROCESSED / f"{name}.csv", index=False, encoding="utf-8-sig")
    summary = build_summary(
        t, funnel, models, prompts, channels, duration, retention, ab, ab_stats
    )
    (PROCESSED / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
