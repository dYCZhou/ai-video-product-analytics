"""Generate a concise Markdown business report from reproducible analysis outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def pct(value: float) -> str:
    return f"{value:.2%}"


def pp(value: float) -> str:
    return f"{value:+.2f}pp"


def main() -> None:
    summary = json.loads((PROCESSED / "summary.json").read_text(encoding="utf-8"))
    models = pd.read_csv(PROCESSED / "model_metrics.csv")
    prompts = pd.read_csv(PROCESSED / "prompt_metrics.csv")
    duration = pd.read_csv(PROCESSED / "duration_metrics.csv")
    ab = pd.read_csv(PROCESSED / "ab_metrics.csv").set_index("group")
    o, exp = summary["overall"], summary["ab_test"]
    model_lines = "\n".join(
        f"| {r.model_version} | {pct(r.success_rate)} | {r.avg_duration_sec:.1f}s | "
        f"{r.human_score:.2f} | {pct(r.download_rate)} | {pct(r.task_pay_rate)} | {pct(r.complaint_rate)} |"
        for r in models.itertuples()
    )
    prompt_lines = "\n".join(
        f"| {r.prompt_type} | {int(r.tasks):,} | {pct(r.download_rate)} | "
        f"{pct(r.task_pay_rate)} | ¥{r.revenue_per_task:.2f} |"
        for r in prompts.head(5).itertuples()
    )
    report = f"""# AI 视频生成产品分析报告

> 数据说明：结论来自固定随机种子生成的业务模拟数据，不代表任何真实公司经营结果。

## 1. 分析范围

- 时间：{summary["data_scope"]["start_date"]} 至 {summary["data_scope"]["end_date"]}
- 规模：{summary["data_scope"]["users"]:,} 名用户、{summary["data_scope"]["tasks"]:,} 次生成任务、{summary["data_scope"]["actions"]:,} 条行为事件
- 目标：定位生成体验、商业化转化与模型策略的关键问题

## 2. 核心指标

- 生成成功率：{pct(o["success_rate"])}
- 平均 / P90 生成时长：{o["avg_duration_sec"]:.1f}s / {o["p90_duration_sec"]:.1f}s
- 成功任务下载率：{pct(o["download_rate"])}
- 二次编辑率：{pct(o["edit_rate"])}
- 付费入口点击率：{pct(o["pay_click_rate"])}
- 用户付费率：{pct(o["payer_rate"])}
- 模拟收入 / ARPU / ARPPU：¥{o["revenue"]:,.1f} / ¥{o["arpu"]:.2f} / ¥{o["arppu"]:.2f}
- 有效视频生成用户数：{o["effective_video_users"]:,}

## 3. 模型综合评估

| 模型 | 成功率 | 平均时长 | 人工评分 | 下载率 | 任务付费率 | 投诉率 |
|---|---:|---:|---:|---:|---:|---:|
{model_lines}

判断：Model_A 更快、更稳定，适合新用户和速度敏感场景；Model_B 人工评分最高但等待更长，适合商品广告、品牌宣传等高价值场景；Model_C 风格分最高但稳定性和投诉表现较弱，宜对二次元、短剧等场景灰度分流，不宜直接全量。

## 4. 高价值 Prompt 场景

| Prompt 类型 | 任务量 | 下载率 | 任务付费率 | 单任务收入 |
|---|---:|---:|---:|---:|
{prompt_lines}

判断：按单任务收入排序，{summary["key_findings"]["highest_value_prompt"]}为最高价值场景。商业意图较强的场景应优先展示高清导出、去水印和商用模板，而非向所有用户统一强化付费入口。

## 5. 等待体验

成功任务中，最快时长桶下载率为 {pct(summary["key_findings"]["fast_bucket_download_rate"])}，最慢时长桶为 {pct(summary["key_findings"]["slow_bucket_download_rate"])}，相差 {(summary["key_findings"]["fast_bucket_download_rate"]-summary["key_findings"]["slow_bucket_download_rate"])*100:.2f} 个百分点。该结果支持“等待时长会传导到内容消费行为”的业务假设，但由于数据为规则驱动模拟，不能解释为真实因果证据。

## 6. A/B 实验

| 指标 | 对照组 | 实验组 |
|---|---:|---:|
| 成功用户付费点击率 | {pct(ab.loc["control","pay_click_rate"])} | {pct(ab.loc["treatment","pay_click_rate"])} |
| 用户付费率 | {pct(ab.loc["control","user_pay_rate"])} | {pct(ab.loc["treatment","user_pay_rate"])} |
| 下载率 | {pct(ab.loc["control","download_rate"])} | {pct(ab.loc["treatment","download_rate"])} |
| 退出率 | {pct(ab.loc["control","exit_rate"])} | {pct(ab.loc["treatment","exit_rate"])} |
| 投诉率 | {pct(ab.loc["control","complaint_rate"])} | {pct(ab.loc["treatment","complaint_rate"])} |
| ARPU | ¥{ab.loc["control","arpu"]:.2f} | ¥{ab.loc["treatment","arpu"]:.2f} |

付费点击率提升 {pp(exp["pay_click_absolute_lift_pp"])}（相对提升 {pct(exp["pay_click_relative_lift"])}，双侧比例检验 p={exp["pay_click_p_value"]:.4g}）；用户付费率提升 {pp(exp["user_pay_absolute_lift_pp"])}（p={exp["user_pay_p_value"]:.4g}）。样本比例失衡检验 p={exp["srm_p_value"]:.4f}，未发现明显分桶异常。

上线判断：实验组商业化指标改善，但真实上线前仍需扩大样本并预注册最小可检测效应；收入分布高度偏斜，ARPU 的 t 检验只能作为辅助。建议先按高商业意图 Prompt 灰度放量，同时监控退出率、投诉率与长期留存。

## 7. 建议

1. Model_A 承接新用户与速度敏感流量，降低首次生成失败和等待成本。
2. Model_B 服务商品广告、品牌宣传等高商业意图场景，并展示预计等待时长。
3. Model_C 限定在风格化场景灰度，设置失败回退到 Model_A 的策略。
4. 商业化入口优先面向高商业意图用户个性化展示，避免全量打扰。
5. 上线真实实验时补充实验污染、跨端身份、退款与长期留存监控。

## 8. 局限

数据由人为规则生成，统计显著性用于展示分析流程，并不验证真实产品策略有效；项目也不代表真实埋点上线、跨团队协作或大规模数仓经验。
"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "analysis_report.md").write_text(report, encoding="utf-8")
    print(REPORTS / "analysis_report.md")


if __name__ == "__main__":
    main()
