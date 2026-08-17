# 数据字典

## 表关系与粒度

| 表 | 一行代表什么 | 主键 | 主要外键 |
|---|---|---|---|
| user_info | 一名注册用户 | user_id | — |
| prompt_pool | 一条 Prompt | prompt_id | — |
| generation_tasks | 一次视频生成任务 | task_id | user_id, prompt_id |
| user_actions | 一次任务后行为事件 | event_id | user_id, task_id |
| payment_orders | 一次支付尝试 | order_id | user_id, task_id |
| ab_experiment | 一名用户在本实验中的分组 | user_id | user_id |
| model_scores | 一个成功任务的模型评分 | task_id | task_id |

## user_info

| 字段 | 含义 |
|---|---|
| user_id | 用户唯一标识 |
| register_date | 注册日期 |
| first_visit_date | 首次访问日期 |
| channel | 获客渠道 |
| device | 首次使用设备 |
| region | 用户地区 |
| user_type | free 或 payer，由成功订单反推 |
| is_paid | 是否至少有一笔成功订单 |

## prompt_pool

| 字段 | 含义 |
|---|---|
| prompt_id | Prompt 唯一标识 |
| prompt_text | 示例 Prompt 文本 |
| prompt_type | 业务场景类型 |
| language | zh 或 en |
| prompt_length | 文本字符数 |
| commercial_intent | high、medium、low |

## generation_tasks

| 字段 | 含义 |
|---|---|
| task_id | 生成任务唯一标识 |
| user_id | 提交用户 |
| prompt_id | 使用的 Prompt |
| submit_time | 提交时间 |
| finish_time | 任务结束时间 |
| model_version | Model_A、Model_B、Model_C |
| generation_type | 文生、图生或模板视频 |
| status | success、failed、timeout |
| fail_reason | 失败原因；成功时为 none |
| generation_duration | 任务耗时，单位为秒 |
| is_first_generation | 是否为该用户首次生成 |

## user_actions

| 字段 | 含义 |
|---|---|
| event_id | 行为事件唯一标识 |
| user_id | 行为用户 |
| task_id | 行为所属任务 |
| event_time | 行为时间 |
| action_type | preview、download、share、favorite、edit_again、regenerate、exit、retry、pay_click |
| session_id | 会话标识；同一任务的后续行为属于同一会话 |

## payment_orders

| 字段 | 含义 |
|---|---|
| order_id | 订单唯一标识 |
| user_id | 下单用户 |
| task_id | 触发订单的任务 |
| order_time | 下单时间 |
| plan_type | 购买套餐 |
| amount | 订单金额，人民币元 |
| pay_status | success 或 failed |
| pay_entrance | 付费入口 |

## ab_experiment

| 字段 | 含义 |
|---|---|
| user_id | 入组用户 |
| experiment_id | 实验标识 |
| group | control 或 treatment |
| enter_time | 入组时间 |
| experiment_version | 实验版本 |

## model_scores

| 字段 | 含义 |
|---|---|
| task_id | 成功生成任务 |
| model_version | 模型版本 |
| clarity_score | 清晰度，1—5 分 |
| motion_score | 动作连贯性，1—5 分 |
| style_score | 风格一致性，1—5 分 |
| human_score | 综合人工评分，1—5 分 |
| complaint_flag | 是否产生质量投诉 |

