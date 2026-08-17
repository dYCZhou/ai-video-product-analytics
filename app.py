"""Decision-oriented Streamlit dashboard for the AI-video product analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

st.set_page_config(
    page_title="AI 视频产品增长与商业化分析",
    page_icon="🎬",
    layout="wide",
)


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


@st.cache_data
def load_summary() -> dict:
    return json.loads((DATA / "summary.json").read_text(encoding="utf-8"))


def pct(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}%}"


def metric_table(frame: pd.DataFrame, columns: dict[str, str], percent_cols=()) -> pd.DataFrame:
    result = frame[list(columns)].rename(columns=columns).copy()
    for column in percent_cols:
        result[column] = result[column].map(lambda value: pct(value))
    return result


summary = load_summary()
funnel = load_csv("funnel_metrics")
models = load_csv("model_metrics")
prompts = load_csv("prompt_metrics")
channels = load_csv("channel_metrics")
duration = load_csv("duration_metrics")
retention = load_csv("retention_metrics")
ab = load_csv("ab_metrics")

scope = summary["data_scope"]
overall = summary["overall"]
experiment = summary["ab_test"]
ab_indexed = ab.set_index("group")

st.title("AI 视频产品增长与商业化分析")
st.caption(
    f"模拟数据 · {scope['start_date']} 至 {scope['end_date']} · "
    f"{scope['users']:,} 名用户 · {scope['tasks']:,} 次生成任务"
)
st.markdown(
    "**分析目标：**在生成速度、内容质量与商业化收益之间寻找平衡，回答“用户在哪里流失、"
    "不同场景该用哪个模型、付费入口是否值得上线”三个问题。"
)

tabs = st.tabs(
    [
        "决策摘要",
        "用户漏斗",
        "等待体验",
        "商业化",
        "模型评估",
        "A/B 实验",
        "方法与口径",
    ]
)

with tabs[0]:
    st.subheader("核心经营指标")
    cols = st.columns(5)
    cols[0].metric("任务生成成功率", pct(overall["success_rate"]))
    cols[1].metric("平均生成时长", f"{overall['avg_duration_sec']:.1f} 秒")
    cols[2].metric("成功任务下载率", pct(overall["download_rate"]))
    cols[3].metric("用户付费率", pct(overall["payer_rate"]))
    cols[4].metric("模拟收入", f"¥{overall['revenue']:,.0f}")

    st.subheader("三个关键发现")
    finding_cols = st.columns(3)
    finding_cols[0].info(
        "**等待是主要体验风险**\n\n>120 秒任务下载率仅 "
        f"{pct(summary['key_findings']['slow_bucket_download_rate'])}，比 ≤45 秒低 "
        f"{(summary['key_findings']['fast_bucket_download_rate'] - summary['key_findings']['slow_bucket_download_rate']) * 100:.2f}pp。"
    )
    finding_cols[1].info(
        "**模型之间存在明确取舍**\n\nModel_A 快且稳；Model_B 质量最高但等待更久；"
        "Model_C 风格更强，但稳定性和投诉表现较弱。"
    )
    finding_cols[2].info(
        "**商业化入口值得继续灰度**\n\n实验组付费点击率提升 "
        f"{experiment['pay_click_absolute_lift_pp']:.2f}pp，用户付费率提升 "
        f"{experiment['user_pay_absolute_lift_pp']:.2f}pp。"
    )

    st.success(
        "**建议决策：**Model_A 承接新用户和速度敏感流量；Model_B 服务商品广告、品牌宣传等"
        "高商业意图场景；Model_C 仅在风格化场景灰度使用。新版付费入口先定向灰度，不直接全量上线。"
    )
    st.caption(
        "结论边界：数据由固定业务规则模拟，适合展示指标体系、分析流程与决策推导，不能作为真实因果或上线收益证明。"
    )

with tabs[1]:
    st.subheader("用户在哪里流失？")
    st.info(
        f"**结论：**{scope['users']:,} 名注册用户中，{int(funnel.iloc[-1]['users']):,} 人完成支付，"
        f"用户付费转化率为 {pct(funnel.iloc[-1]['overall_conversion'])}；下载到付费点击仍有较大优化空间。"
    )
    funnel_display = funnel.copy()
    funnel_display["阶段"] = funnel_display["stage"]
    fig = px.funnel(
        funnel_display,
        x="users",
        y="阶段",
        title="宽口径用户漏斗（每阶段按用户去重）",
        labels={"users": "用户数"},
    )
    st.plotly_chart(fig, width="stretch")

    cols = st.columns(2)
    cols[0].metric("至少成功生成一次的用户占比", pct(funnel.iloc[2]["overall_conversion"]))
    cols[1].metric("任务生成成功率", pct(overall["success_rate"]))
    st.caption(
        "口径说明：漏斗为宽口径用户漏斗，各阶段统计曾发生过该行为的去重用户；98.56% 是用户成功覆盖率，"
        "87.73% 是成功任务数/全部任务数，两者分母不同。"
    )

    st.subheader("成熟 cohort 留存")
    retention_display = retention.rename(
        columns={
            "retention_day": "留存日",
            "retained_users": "留存用户数",
            "eligible_d0_users": "可观察 D0 用户数",
            "retention_rate": "留存率",
        }
    )
    st.dataframe(
        retention_display.style.format({"留存率": "{:.2%}"}),
        hide_index=True,
        width="stretch",
    )
    st.caption("留存分母仅包含在数据截止日前拥有完整 D1/D7/D14 观察窗口的 D0 用户，避免右截尾低估。")

with tabs[2]:
    st.subheader("等待时间如何影响后续使用？")
    gap_pp = (duration.iloc[0]["download_rate"] - duration.iloc[-1]["download_rate"]) * 100
    st.info(
        f"**结论：**≤45 秒成功任务下载率为 {pct(duration.iloc[0]['download_rate'])}，"
        f">120 秒仅为 {pct(duration.iloc[-1]['download_rate'])}，相差 {gap_pp:.2f}pp。"
    )
    chart_data = duration.rename(
        columns={
            "duration_bucket": "生成时长",
            "preview_rate": "预览率",
            "download_rate": "下载率",
            "exit_rate": "退出率",
        }
    )
    fig = px.bar(
        chart_data,
        x="生成时长",
        y=["预览率", "下载率", "退出率"],
        barmode="group",
        title="生成时长分桶与任务后续行为",
        labels={"value": "任务行为率", "variable": "指标"},
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
    st.success("**建议：**优先优化长尾时延，展示预计等待时间，并为超时任务提供快速模型回退。")
    st.caption(
        "口径与局限：分母为成功任务；该结果是描述性关联。模型、Prompt 类型和生成复杂度可能同时影响时长与下载行为，不能直接解释为因果。"
    )

with tabs[3]:
    st.subheader("哪些场景更有商业价值？")
    st.info(
        f"**结论：**{summary['key_findings']['highest_value_prompt']}单任务收入最高；"
        "商品广告和品牌宣传兼具较强商业意图，适合优先展示商用权益。"
    )
    left, right = st.columns(2)
    prompt_chart = prompts.rename(columns={"prompt_type": "Prompt 类型", "revenue_per_task": "单任务收入"})
    left.plotly_chart(
        px.bar(
            prompt_chart,
            x="Prompt 类型",
            y="单任务收入",
            title="Prompt 类型单任务收入",
            labels={"单任务收入": "单任务收入（元）"},
        ),
        width="stretch",
    )
    channel_chart = channels.rename(columns={"channel": "渠道", "payer_rate": "用户付费率"})
    channel_fig = px.bar(channel_chart, x="渠道", y="用户付费率", title="渠道用户付费率")
    channel_fig.update_yaxes(tickformat=".0%")
    right.plotly_chart(channel_fig, width="stretch")
    with st.expander("查看场景明细"):
        prompt_display = metric_table(
            prompts,
            {
                "prompt_type": "Prompt 类型",
                "tasks": "任务数",
                "success_rate": "成功率",
                "download_rate": "下载率",
                "task_pay_rate": "任务付费率",
                "revenue": "收入（元）",
                "revenue_per_task": "单任务收入（元）",
            },
            ["成功率", "下载率", "任务付费率"],
        )
        st.dataframe(prompt_display, hide_index=True, width="stretch")
    st.success("**建议：**对高商业意图 Prompt 定向展示高清导出、去水印和商用模板，避免全量强化付费入口。")
    st.caption("局限：项目缺少真实获客成本，渠道结果只能比较用户质量与收入，不能据此计算 ROI、CAC 或决定投放预算。")

with tabs[4]:
    st.subheader("不同场景应该选择哪个模型？")
    st.info("**结论：**不存在所有指标都最优的模型；模型路由需要同时平衡速度、成功率、质量和投诉风险。")
    model_chart = models.rename(
        columns={
            "model_version": "模型",
            "avg_duration_sec": "平均生成时长（秒）",
            "human_score": "人工评分",
            "success_rate": "成功率",
            "tasks": "任务数",
        }
    )
    fig = px.scatter(
        model_chart,
        x="平均生成时长（秒）",
        y="人工评分",
        size="任务数",
        color="成功率",
        text="模型",
        title="模型速度—质量—稳定性权衡",
        color_continuous_scale="Blues",
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, width="stretch")

    model_display = metric_table(
        models,
        {
            "model_version": "模型",
            "success_rate": "成功率",
            "avg_duration_sec": "平均时长（秒）",
            "human_score": "人工评分",
            "download_rate": "任务下载率",
            "complaint_rate": "任务投诉率",
        },
        ["成功率", "任务下载率", "任务投诉率"],
    )
    model_display["推荐场景"] = ["新用户、速度敏感", "商品广告、品牌宣传", "二次元、短剧灰度"]
    st.dataframe(model_display, hide_index=True, width="stretch")
    st.success("**建议：**Model_A 做默认与失败回退；Model_B 服务高价值场景并展示预计等待；Model_C 限定风格化场景灰度。")
    st.caption("局限：模型分配与 Prompt 类型有关，观察到的商业差异不能直接解释为模型造成的因果提升。")

with tabs[5]:
    st.subheader("新版付费入口是否值得上线？")
    c, t = ab_indexed.loc["control"], ab_indexed.loc["treatment"]
    st.info(
        f"**结论：**付费点击率从 {pct(c['pay_click_rate'])} 提升到 {pct(t['pay_click_rate'])} "
        f"（+{experiment['pay_click_absolute_lift_pp']:.2f}pp）；用户付费率从 {pct(c['user_pay_rate'])} "
        f"提升到 {pct(t['user_pay_rate'])}（+{experiment['user_pay_absolute_lift_pp']:.2f}pp）。"
    )
    cols = st.columns(4)
    cols[0].metric("对照组有效用户", f"{int(c['eligible_users']):,}")
    cols[1].metric("实验组有效用户", f"{int(t['eligible_users']):,}")
    cols[2].metric("付费点击绝对提升", f"+{experiment['pay_click_absolute_lift_pp']:.2f}pp")
    cols[3].metric("用户付费绝对提升", f"+{experiment['user_pay_absolute_lift_pp']:.2f}pp")

    primary = ab.rename(columns={"group": "实验组", "pay_click_rate": "付费点击率", "user_pay_rate": "用户付费率"})
    primary["实验组"] = primary["实验组"].map({"control": "对照组", "treatment": "实验组"})
    primary_fig = px.bar(
        primary,
        x="实验组",
        y=["付费点击率", "用户付费率"],
        barmode="group",
        title="实验主指标与转化指标",
        labels={"value": "用户转化率", "variable": "指标"},
    )
    primary_fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(primary_fig, width="stretch")

    guardrail = metric_table(
        ab,
        {
            "group": "分组",
            "task_download_rate": "成功任务下载率",
            "task_exit_rate": "任务退出率",
            "task_regenerate_rate": "成功任务重新生成率",
            "task_complaint_rate": "成功任务投诉率",
            "arpu": "ARPU（元）",
        },
        ["成功任务下载率", "任务退出率", "成功任务重新生成率", "成功任务投诉率"],
    )
    guardrail["分组"] = guardrail["分组"].map({"control": "对照组", "treatment": "实验组"})
    st.dataframe(guardrail, hide_index=True, width="stretch")
    st.success("**建议：**商业化指标改善且任务级护栏未见明显恶化，可继续按高商业意图场景灰度；真实上线前需预设 MDE 并观察长期留存与退款。")
    st.caption(
        f"实验口径：随机单元为用户；主指标为成功用户付费点击率；护栏采用任务口径。"
        f"双侧比例检验 p={experiment['pay_click_p_value']:.3g}，SRM p={experiment['srm_p_value']:.3f}。"
        "实验效果由模拟规则植入，显著性只用于验证分析流程。"
    )

with tabs[6]:
    st.subheader("方法、指标口径与结论边界")
    st.markdown(
        """
        **数据结构**

        - 7 张关联表：用户、Prompt、生成任务、行为日志、支付订单、实验分组、模型评分。
        - 多表指标先聚合到任务或用户粒度，再 JOIN，避免一对多关系放大分母。
        - 数据通过主外键、时间顺序、失败任务行为、订单追溯和评分范围校验。

        **核心口径**

        - 任务生成成功率 = 成功任务数 / 全部提交任务数。
        - 成功任务下载率 = 发生下载行为的成功任务数 / 成功任务数。
        - 用户付费率 = 至少一笔成功订单的用户数 / 有效用户数。
        - A/B 主指标按用户计算；体验护栏按任务计算。
        - Dn 留存只纳入拥有完整 n 天观察窗口的 D0 用户。

        **结论边界**

        - 所有数据均由固定随机种子和明确业务规则生成，不代表真实公司经营结果。
        - 模型差异、商业意图和实验效果已写入模拟机制，不能用来证明真实因果关系。
        - 项目证明的是指标设计、SQL/Python 实现、实验分析和业务决策表达能力。
        """
    )
    st.link_button("查看 GitHub 源码与完整 SQL", "https://github.com/dYCZhou/ai-video-product-analytics")
