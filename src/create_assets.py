"""Create static charts used by the README and as dashboard evidence."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
ASSETS = ROOT / "assets"


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = ["DejaVu Sans"]
    funnel = pd.read_csv(DATA / "funnel_metrics.csv")
    stage_labels = {
        "注册用户": "Registered",
        "提交生成": "Submitted",
        "生成成功": "Generated",
        "预览视频": "Previewed",
        "下载视频": "Downloaded",
        "付费点击": "Pay click",
        "支付成功": "Paid",
    }
    funnel["stage_en"] = funnel["stage"].map(stage_labels)
    models = pd.read_csv(DATA / "model_metrics.csv")
    ab = pd.read_csv(DATA / "ab_metrics.csv").set_index("group")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(funnel["stage_en"][::-1], funnel["users"][::-1], color="#5B8FF9")
    for i, value in enumerate(funnel["users"][::-1]):
        ax.text(value + max(funnel["users"]) * 0.01, i, f"{value:,}", va="center")
    ax.set_title("User Funnel (simulated data)")
    ax.set_xlabel("Unique users")
    fig.tight_layout()
    fig.savefig(ASSETS / "funnel_chart.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    specs = [
        ("success_rate", "Success rate", "{:.1%}"),
        ("avg_duration_sec", "Avg duration (s)", "{:.1f}"),
        ("human_score", "Human score", "{:.2f}"),
    ]
    for ax, (column, title, fmt) in zip(axes, specs):
        bars = ax.bar(models["model_version"], models[column], color=["#5B8FF9", "#61DDAA", "#F6BD16"])
        ax.set_title(title)
        ax.bar_label(bars, labels=[fmt.format(v) for v in models[column]], padding=3)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "model_comparison.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    metrics = ["pay_click_rate", "user_pay_rate", "download_rate"]
    labels = ["Pay click", "User pay", "Download"]
    x = range(len(metrics))
    width = 0.36
    control = [ab.loc["control", m] for m in metrics]
    treatment = [ab.loc["treatment", m] for m in metrics]
    ax.bar([i - width / 2 for i in x], control, width, label="Control")
    ax.bar([i + width / 2 for i in x], treatment, width, label="Treatment")
    ax.set_xticks(list(x), labels)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_title("A/B test metrics (simulated data)")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "ab_test.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
