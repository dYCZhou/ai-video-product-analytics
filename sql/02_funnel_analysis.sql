-- 业务问题：注册到支付的主要用户流失发生在哪一步？
-- 口径：用户级漏斗；每阶段每名用户只计一次。
WITH user_stage AS (
    SELECT u.user_id,
           MAX(t.task_id IS NOT NULL) AS submitted,
           MAX(t.status = 'success') AS generated,
           MAX(a.action_type = 'preview') AS previewed,
           MAX(a.action_type = 'download') AS downloaded,
           MAX(a.action_type = 'pay_click') AS clicked,
           MAX(o.pay_status = 'success') AS paid
    FROM user_info u
    LEFT JOIN generation_tasks t ON u.user_id = t.user_id
    LEFT JOIN user_actions a ON t.task_id = a.task_id
    LEFT JOIN payment_orders o ON t.task_id = o.task_id
    GROUP BY u.user_id
),
stages(stage_no, stage, users) AS (
    SELECT 1, '注册用户', COUNT(*) FROM user_stage
    UNION ALL SELECT 2, '提交生成', SUM(submitted) FROM user_stage
    UNION ALL SELECT 3, '生成成功', SUM(generated) FROM user_stage
    UNION ALL SELECT 4, '预览视频', SUM(previewed) FROM user_stage
    UNION ALL SELECT 5, '下载视频', SUM(downloaded) FROM user_stage
    UNION ALL SELECT 6, '付费点击', SUM(clicked) FROM user_stage
    UNION ALL SELECT 7, '支付成功', SUM(paid) FROM user_stage
),
with_previous AS (
    SELECT *, LAG(users) OVER (ORDER BY stage_no) AS previous_users,
           FIRST_VALUE(users) OVER (ORDER BY stage_no) AS registered_users
    FROM stages
)
SELECT stage_no, stage, users,
       ROUND(1.0 * users / registered_users, 4) AS overall_conversion,
       ROUND(CASE WHEN previous_users IS NULL THEN 1.0
                  ELSE 1.0 * users / previous_users END, 4) AS step_conversion
FROM with_previous
ORDER BY stage_no;
