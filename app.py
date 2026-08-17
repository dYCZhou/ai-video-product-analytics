"""Interactive Streamlit dashboard for the AI-video product analysis."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

st.set_page_config(page_title="AI Video Analytics", layout="wide")
st.title("AI 视频生成产品分析看板")
st.caption("固定随机种子生成的模拟数据；用于展示分析方法，不代表真实公司经营结果。")


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


funnel = load("funnel_metrics")
models = load("model_metrics")
prompts = load("prompt_metrics")
channels = load("channel_metrics")
duration = load("duration_metrics")
retention = load("retention_metrics")
ab = load("ab_metrics")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["核心漏斗", "用户体验", "商业化", "模型评估", "A/B 实验"]
)

with tab1:
    cols = st.columns(4)
    cols[0].metric("注册用户", f"{int(funnel.iloc[0].users):,}")
    cols[1].metric("生成成功用户", f"{int(funnel.iloc[2].users):,}")
    cols[2].metric("下载用户", f"{int(funnel.iloc[4].users):,}")
    cols[3].metric("付费用户", f"{int(funnel.iloc[6].users):,}")
    fig = px.funnel(funnel, x="users", y="stage", title="全链路用户漏斗")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(retention, use_container_width=True)

with tab2:
    fig = px.bar(
        duration,
        x="duration_bucket",
        y=["preview_rate", "download_rate", "exit_rate"],
        barmode="group",
        title="生成时长分桶与后续行为",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            prompts,
            x="prompt_type",
            y="revenue_per_task",
            title="Prompt 类型单任务收入",
        ),
        use_container_width=True,
    )
    right.plotly_chart(
        px.bar(channels, x="channel", y="payer_rate", title="渠道用户付费率"),
        use_container_width=True,
    )
    st.dataframe(prompts, use_container_width=True)

with tab4:
    metric = st.selectbox(
        "选择模型指标",
        [
            "success_rate",
            "avg_duration_sec",
            "human_score",
            "download_rate",
            "task_pay_rate",
            "complaint_rate",
        ],
    )
    st.plotly_chart(
        px.bar(models, x="model_version", y=metric, color="model_version"),
        use_container_width=True,
    )
    st.dataframe(models, use_container_width=True)

with tab5:
    st.plotly_chart(
        px.bar(
            ab,
            x="group",
            y=["pay_click_rate", "user_pay_rate", "download_rate"],
            barmode="group",
            title="实验核心指标",
        ),
        use_container_width=True,
    )
    st.dataframe(ab, use_container_width=True)
