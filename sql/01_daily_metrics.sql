-- 业务问题：每日生成体验、有效使用与收入是否出现异常？
-- 粒度控制：先按 task_id 聚合行为与订单，避免一对多 JOIN 放大任务数。
WITH action_flag AS (
    SELECT task_id,
           MAX(action_type = 'download') AS downloaded,
           MAX(action_type IN ('download','share','favorite','edit_again','regenerate')) AS effective
    FROM user_actions
    GROUP BY task_id
),
order_agg AS (
    SELECT task_id,
           SUM(CASE WHEN pay_status = 'success' THEN amount ELSE 0 END) AS revenue
    FROM payment_orders
    GROUP BY task_id
)
SELECT DATE(t.submit_time) AS dt,
       COUNT(DISTINCT t.user_id) AS active_users,
       COUNT(*) AS submitted_tasks,
       ROUND(AVG(t.status = 'success'), 4) AS success_rate,
       ROUND(AVG(t.generation_duration), 2) AS avg_duration_sec,
       COUNT(DISTINCT CASE WHEN COALESCE(a.effective, 0) = 1 THEN t.user_id END) AS effective_video_users,
       ROUND(AVG(CASE WHEN t.status = 'success' THEN COALESCE(a.downloaded, 0) END), 4) AS download_rate,
       ROUND(SUM(COALESCE(o.revenue, 0)), 2) AS revenue,
       ROUND(SUM(COALESCE(o.revenue, 0)) / COUNT(DISTINCT t.user_id), 2) AS arpu
FROM generation_tasks t
LEFT JOIN action_flag a USING (task_id)
LEFT JOIN order_agg o USING (task_id)
GROUP BY DATE(t.submit_time)
ORDER BY dt;
