-- 业务问题：哪些 Prompt 场景既有使用价值又有付费价值？
WITH action_flag AS (
    SELECT task_id,
           MAX(action_type = 'download') AS downloaded,
           MAX(action_type = 'pay_click') AS clicked
    FROM user_actions GROUP BY task_id
),
order_agg AS (
    SELECT task_id,
           MAX(pay_status = 'success') AS paid,
           SUM(CASE WHEN pay_status = 'success' THEN amount ELSE 0 END) AS revenue
    FROM payment_orders GROUP BY task_id
)
SELECT p.prompt_type, p.commercial_intent,
       COUNT(*) AS tasks,
       ROUND(AVG(t.status = 'success'), 4) AS success_rate,
       ROUND(AVG(CASE WHEN t.status = 'success' THEN COALESCE(a.downloaded, 0) END), 4) AS download_rate,
       ROUND(AVG(CASE WHEN t.status = 'success' THEN COALESCE(a.clicked, 0) END), 4) AS pay_click_rate,
       ROUND(AVG(CASE WHEN t.status = 'success' THEN COALESCE(o.paid, 0) END), 4) AS task_pay_rate,
       ROUND(SUM(COALESCE(o.revenue, 0)), 2) AS revenue,
       ROUND(SUM(COALESCE(o.revenue, 0)) / COUNT(*), 2) AS revenue_per_task
FROM generation_tasks t
JOIN prompt_pool p USING (prompt_id)
LEFT JOIN action_flag a USING (task_id)
LEFT JOIN order_agg o USING (task_id)
GROUP BY p.prompt_type, p.commercial_intent
ORDER BY revenue_per_task DESC;
