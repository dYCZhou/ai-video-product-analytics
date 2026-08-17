"""Generate logically consistent mock data for an AI-video analytics project."""

from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 20260724
N_USERS = 5_000
N_PROMPTS = 320
DATA_START = pd.Timestamp("2026-05-01")
DATA_END = pd.Timestamp("2026-06-29 23:59:59")
EXPERIMENT_START = pd.Timestamp("2026-05-15 00:00:00")

# 面试前请亲自修改一次 Model_B，例如从 92 改为 110，再观察结果。
MODEL_DURATION_SECONDS = {"Model_A": 42, "Model_B": 92, "Model_C": 68}
MODEL_SUCCESS_RATE = {"Model_A": 0.925, "Model_B": 0.875, "Model_C": 0.815}

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "raw"

PROMPT_TYPES = [
    "商品广告",
    "人物写真",
    "风景旅行",
    "短剧剧情",
    "二次元",
    "教育科普",
    "社交娱乐",
    "品牌宣传",
]
PROMPT_INTENT = {
    "商品广告": "high",
    "品牌宣传": "high",
    "教育科普": "medium",
    "短剧剧情": "medium",
    "人物写真": "medium",
    "二次元": "low",
    "风景旅行": "low",
    "社交娱乐": "low",
}
PROMPT_TEMPLATES = {
    "商品广告": "为一款轻量运动鞋制作电影感产品广告，展示材质细节与动态镜头",
    "人物写真": "生成一段自然光下的人物写真视频，镜头缓慢推进，肤色真实",
    "风景旅行": "航拍山谷与湖泊的旅行短片，清晨薄雾，画面宁静",
    "短剧剧情": "两位朋友在雨夜车站重逢，情绪克制，使用电影叙事镜头",
    "二次元": "动漫少年站在霓虹城市天台，风吹动衣角，强烈风格化光影",
    "教育科普": "用清晰动画解释太阳能电池的工作原理，适合一分钟科普视频",
    "社交娱乐": "生成适合社交平台发布的轻松搞笑短片，节奏明快",
    "品牌宣传": "为科技品牌制作简洁高端的品牌宣传片，突出可靠与创新",
}


def clipped_score(rng: np.random.Generator, mean: float, size: int, sd: float = 0.48):
    return np.round(np.clip(rng.normal(mean, sd, size), 1, 5), 2)


def random_timestamp(
    rng: np.random.Generator, start: pd.Timestamp, end: pd.Timestamp
) -> pd.Timestamp:
    seconds = max(int((end - start).total_seconds()), 0)
    return start + pd.to_timedelta(int(rng.integers(0, seconds + 1)), unit="s")


def build_prompt_pool(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for idx in range(1, N_PROMPTS + 1):
        prompt_type = rng.choice(
            PROMPT_TYPES, p=[0.15, 0.14, 0.11, 0.13, 0.13, 0.10, 0.12, 0.12]
        )
        language = rng.choice(["zh", "en"], p=[0.86, 0.14])
        base = PROMPT_TEMPLATES[prompt_type]
        text = f"{base}，编号{idx:03d}"
        if language == "en":
            text = (
                f"Create a cinematic {prompt_type} video with coherent motion, "
                f"natural lighting and clear subject details, sample {idx:03d}"
            )
        rows.append(
            {
                "prompt_id": f"P{idx:04d}",
                "prompt_text": text,
                "prompt_type": prompt_type,
                "language": language,
                "prompt_length": len(text),
                "commercial_intent": PROMPT_INTENT[prompt_type],
            }
        )
    return pd.DataFrame(rows)


def build_users(rng: np.random.Generator) -> pd.DataFrame:
    user_ids = [f"U{i:06d}" for i in range(1, N_USERS + 1)]
    channels = rng.choice(
        ["organic", "app_store", "short_video_ads", "search_ads", "kol", "referral"],
        size=N_USERS,
        p=[0.25, 0.17, 0.20, 0.14, 0.12, 0.12],
    )
    devices = rng.choice(["iOS", "Android", "Web"], size=N_USERS, p=[0.36, 0.39, 0.25])
    regions = rng.choice(
        ["一线城市", "新一线城市", "二线城市", "海外"],
        size=N_USERS,
        p=[0.30, 0.31, 0.25, 0.14],
    )
    days = rng.integers(0, (DATA_END.normalize() - DATA_START).days + 1, N_USERS)
    register_dates = DATA_START + pd.to_timedelta(days, unit="D")
    first_visit_dates = register_dates - pd.to_timedelta(
        rng.choice([0, 1, 2], N_USERS, p=[0.92, 0.06, 0.02]), unit="D"
    )
    return pd.DataFrame(
        {
            "user_id": user_ids,
            "register_date": register_dates,
            "first_visit_date": first_visit_dates,
            "channel": channels,
            "device": devices,
            "region": regions,
            "user_type": "free",
            "is_paid": 0,
        }
    )


def build_experiment(
    rng: np.random.Generator, users: pd.DataFrame
) -> pd.DataFrame:
    # 固定 50/50 随机分桶，用户只能进入一个组。
    groups = np.array(["control"] * (len(users) // 2) + ["treatment"] * (len(users) - len(users) // 2))
    rng.shuffle(groups)
    register_time = pd.to_datetime(users["register_date"]) + pd.to_timedelta(
        rng.integers(8, 22, len(users)), unit="h"
    )
    enter_time = register_time.where(register_time >= EXPERIMENT_START, EXPERIMENT_START)
    return pd.DataFrame(
        {
            "user_id": users["user_id"],
            "experiment_id": "EXP_FINISH_PAGE_001",
            "group": groups,
            "enter_time": enter_time,
            "experiment_version": "v1",
        }
    )


def choose_model(rng: np.random.Generator, prompt_type: str) -> str:
    if prompt_type in {"商品广告", "品牌宣传", "教育科普"}:
        probs = [0.25, 0.60, 0.15]
    elif prompt_type in {"二次元", "短剧剧情"}:
        probs = [0.25, 0.25, 0.50]
    else:
        probs = [0.55, 0.28, 0.17]
    return rng.choice(["Model_A", "Model_B", "Model_C"], p=probs)


def build_tasks(
    rng: np.random.Generator, users: pd.DataFrame, prompts: pd.DataFrame
) -> pd.DataFrame:
    prompt_lookup = prompts.set_index("prompt_id")["prompt_type"].to_dict()
    prompt_ids = prompts["prompt_id"].to_numpy()
    channel_factor = {
        "organic": 1.15,
        "app_store": 1.00,
        "short_video_ads": 0.78,
        "search_ads": 0.94,
        "kol": 0.90,
        "referral": 1.18,
    }
    rows = []
    task_number = 1
    for user in users.itertuples(index=False):
        active_days = max((DATA_END.normalize() - user.register_date).days + 1, 1)
        expected = (2.1 + 4.3 * active_days / 60) * channel_factor[user.channel]
        n_tasks = max(1, int(rng.poisson(expected)))
        submit_times = sorted(
            random_timestamp(
                rng,
                pd.Timestamp(user.register_date) + pd.Timedelta(hours=8),
                DATA_END,
            )
            for _ in range(n_tasks)
        )
        for user_task_index, submit_time in enumerate(submit_times):
            prompt_id = str(rng.choice(prompt_ids))
            prompt_type = prompt_lookup[prompt_id]
            model = choose_model(rng, prompt_type)
            generation_type = rng.choice(
                ["text_to_video", "image_to_video", "template_video"],
                p=[0.59, 0.25, 0.16],
            )
            duration = max(
                8,
                int(
                    rng.lognormal(
                        mean=np.log(MODEL_DURATION_SECONDS[model]),
                        sigma={"Model_A": 0.30, "Model_B": 0.34, "Model_C": 0.44}[model],
                    )
                ),
            )
            success_rate = MODEL_SUCCESS_RATE[model]
            success_rate += 0.018 if generation_type == "template_video" else 0
            success_rate -= 0.018 if generation_type == "image_to_video" else 0
            draw = rng.random()
            timeout_cut = {"Model_A": 0.025, "Model_B": 0.050, "Model_C": 0.075}[model]
            if draw < success_rate:
                status, fail_reason = "success", "none"
            elif draw < success_rate + timeout_cut:
                status, fail_reason = "timeout", "timeout"
                duration = max(duration, {"Model_A": 115, "Model_B": 185, "Model_C": 165}[model])
            else:
                status = "failed"
                fail_reason = rng.choice(
                    ["sensitive_content", "resource_limit", "model_error", "unknown"],
                    p=[0.15, 0.28, 0.43, 0.14],
                )
            finish_time = submit_time + pd.to_timedelta(duration, unit="s")
            rows.append(
                {
                    "task_id": f"T{task_number:08d}",
                    "user_id": user.user_id,
                    "prompt_id": prompt_id,
                    "submit_time": submit_time,
                    "finish_time": finish_time,
                    "model_version": model,
                    "generation_type": generation_type,
                    "status": status,
                    "fail_reason": fail_reason,
                    "generation_duration": duration,
                    "is_first_generation": int(user_task_index == 0),
                }
            )
            task_number += 1
    return pd.DataFrame(rows)


def build_scores(
    rng: np.random.Generator, successful_tasks: pd.DataFrame
) -> pd.DataFrame:
    means = {
        "Model_A": (3.62, 3.55, 3.48),
        "Model_B": (4.38, 4.20, 4.12),
        "Model_C": (3.88, 3.78, 4.48),
    }
    score_frames = []
    for model, subset in successful_tasks.groupby("model_version"):
        clarity_mean, motion_mean, style_mean = means[model]
        n = len(subset)
        clarity = clipped_score(rng, clarity_mean, n)
        motion = clipped_score(rng, motion_mean, n)
        style = clipped_score(rng, style_mean, n)
        human = np.round(np.clip(0.38 * clarity + 0.34 * motion + 0.28 * style + rng.normal(0, 0.16, n), 1, 5), 2)
        complaint_prob = {"Model_A": 0.018, "Model_B": 0.013, "Model_C": 0.047}[model]
        complaint = rng.binomial(1, complaint_prob + np.maximum(3.0 - human, 0) * 0.018)
        score_frames.append(
            pd.DataFrame(
                {
                    "task_id": subset["task_id"].to_numpy(),
                    "model_version": model,
                    "clarity_score": clarity,
                    "motion_score": motion,
                    "style_score": style,
                    "human_score": human,
                    "complaint_flag": complaint,
                }
            )
        )
    return pd.concat(score_frames, ignore_index=True)


def build_actions_and_orders(
    rng: np.random.Generator,
    tasks: pd.DataFrame,
    prompts: pd.DataFrame,
    experiment: pd.DataFrame,
    scores: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prompt_meta = prompts.set_index("prompt_id")[["prompt_type", "commercial_intent"]].to_dict("index")
    group_map = experiment.set_index("user_id")["group"].to_dict()
    enter_map = pd.to_datetime(experiment.set_index("user_id")["enter_time"]).to_dict()
    score_map = scores.set_index("task_id")["human_score"].to_dict()
    actions = []
    orders = []
    event_number = 1
    order_number = 1

    def add_action(task, action_type: str, minute_low: int, minute_high: int):
        nonlocal event_number
        event_time = task.finish_time + pd.to_timedelta(
            int(rng.integers(minute_low * 60, minute_high * 60 + 1)), unit="s"
        )
        actions.append(
            {
                "event_id": f"E{event_number:09d}",
                "user_id": task.user_id,
                "task_id": task.task_id,
                "event_time": event_time,
                "action_type": action_type,
                "session_id": f"S{task.task_id[1:]}",
            }
        )
        event_number += 1
        return event_time

    for task in tasks.itertuples(index=False):
        if task.status != "success":
            if rng.random() < (0.38 if task.status == "failed" else 0.29):
                add_action(task, "retry", 1, 9)
            else:
                add_action(task, "exit", 0, 3)
            continue

        meta = prompt_meta[task.prompt_id]
        human_score = score_map[task.task_id]
        duration_penalty = min(max((task.generation_duration - 55) / 180, 0), 0.34)
        quality_boost = (human_score - 3.5) * 0.105
        commercial_boost = {"high": 0.09, "medium": 0.035, "low": 0.0}[meta["commercial_intent"]]
        treatment_active = (
            group_map[task.user_id] == "treatment"
            and task.submit_time >= enter_map[task.user_id]
        )

        preview_prob = np.clip(0.93 - duration_penalty * 0.65, 0.55, 0.96)
        if rng.random() < preview_prob:
            add_action(task, "preview", 0, 2)
        else:
            add_action(task, "exit", 0, 2)
            continue

        download_prob = np.clip(0.49 + quality_boost - duration_penalty, 0.15, 0.76)
        downloaded = rng.random() < download_prob
        if downloaded:
            add_action(task, "download", 1, 6)
        if rng.random() < np.clip(0.105 + quality_boost * 0.45, 0.03, 0.24):
            add_action(task, "share", 2, 10)
        if rng.random() < np.clip(0.13 + quality_boost * 0.30, 0.04, 0.25):
            add_action(task, "favorite", 1, 8)
        if rng.random() < np.clip(0.14 + quality_boost * 0.38, 0.04, 0.29):
            add_action(task, "edit_again", 3, 18)
        if rng.random() < np.clip(0.18 + quality_boost * 0.32 - duration_penalty * 0.25, 0.05, 0.32):
            add_action(task, "regenerate", 2, 15)

        click_prob = 0.055 + commercial_boost + (0.052 if treatment_active else 0)
        click_prob += 0.025 if downloaded else 0
        if rng.random() < np.clip(click_prob, 0.02, 0.30):
            click_time = add_action(task, "pay_click", 2, 14)
            pay_success_prob = (
                0.24
                + {"high": 0.13, "medium": 0.055, "low": 0.0}[meta["commercial_intent"]]
                + (0.025 if treatment_active else 0)
                + max(human_score - 3.7, 0) * 0.035
            )
            pay_status = "success" if rng.random() < min(pay_success_prob, 0.62) else "failed"
            plan_type = rng.choice(
                ["hd_export", "remove_watermark", "fast_generation", "monthly_member", "credit_pack"],
                p=[0.27, 0.24, 0.13, 0.21, 0.15],
            )
            amount_map = {
                "hd_export": 6.9,
                "remove_watermark": 9.9,
                "fast_generation": 4.9,
                "monthly_member": 39.0,
                "credit_pack": 29.0,
            }
            entrance = rng.choice(
                ["finish_page", "download_page", "member_center", "popup", "template_page"],
                p=([0.48, 0.22, 0.10, 0.12, 0.08] if treatment_active else [0.32, 0.30, 0.16, 0.16, 0.06]),
            )
            orders.append(
                {
                    "order_id": f"O{order_number:07d}",
                    "user_id": task.user_id,
                    "task_id": task.task_id,
                    "order_time": click_time + pd.to_timedelta(int(rng.integers(15, 240)), unit="s"),
                    "plan_type": plan_type,
                    "amount": amount_map[plan_type],
                    "pay_status": pay_status,
                    "pay_entrance": entrance,
                }
            )
            order_number += 1
        elif rng.random() < np.clip(0.20 + duration_penalty, 0.15, 0.52):
            add_action(task, "exit", 1, 10)

    return pd.DataFrame(actions), pd.DataFrame(orders)


def finalize_users(users: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    paid_users = set(orders.loc[orders["pay_status"] == "success", "user_id"])
    result = users.copy()
    result["is_paid"] = result["user_id"].isin(paid_users).astype(int)
    result["user_type"] = np.where(result["is_paid"].eq(1), "payer", "free")
    return result


def save_tables(tables: dict[str, pd.DataFrame]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_columns = {
        "user_info": ["register_date", "first_visit_date"],
        "generation_tasks": ["submit_time", "finish_time"],
        "user_actions": ["event_time"],
        "payment_orders": ["order_time"],
        "ab_experiment": ["enter_time"],
    }
    for name, frame in tables.items():
        output = frame.copy()
        for column in date_columns.get(name, []):
            output[column] = pd.to_datetime(output[column]).dt.strftime("%Y-%m-%d %H:%M:%S")
        output.to_csv(OUTPUT_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")
        print(f"{name:18s} {len(output):>8,} rows")


def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)
    prompts = build_prompt_pool(rng)
    users = build_users(rng)
    experiment = build_experiment(rng, users)
    tasks = build_tasks(rng, users, prompts)
    scores = build_scores(rng, tasks.loc[tasks["status"] == "success"].copy())
    actions, orders = build_actions_and_orders(rng, tasks, prompts, experiment, scores)
    users = finalize_users(users, orders)
    tables = {
        "user_info": users,
        "prompt_pool": prompts,
        "generation_tasks": tasks,
        "user_actions": actions,
        "payment_orders": orders,
        "ab_experiment": experiment,
        "model_scores": scores,
    }
    save_tables(tables)
    print(f"\nData generated in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

