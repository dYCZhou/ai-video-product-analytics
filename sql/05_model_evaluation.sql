-- 业务问题：哪个模型在稳定性、速度、质量和商业价值之间更均衡？
WITH action_flag AS (
    SELECT task_id,
           MAX(action_type = 'download') AS downloaded,
           MAX(action_type = 'edit_again') AS edited
    FROM user_actions GROUP BY task_id
),
order_flag AS (
    SELECT task_id, MAX(pay_status = 'success') AS paid
    FROM payment_orders GROUP BY task_id
),
task_level AS (
    SELECT t.*, a.downloaded, a.edited, o.paid,
           s.human_score, s.style_score, s.complaint_flag
    FROM generation_tasks t
    LEFT JOIN action_flag a USING (task_id)
    LEFT JOIN order_flag o USING (task_id)
    LEFT JOIN model_scores s USING (task_id)
)
SELECT model_version,
       COUNT(*) AS tasks,
       ROUND(AVG(status = 'success'), 4) AS success_rate,
       ROUND(AVG(generation_duration), 2) AS avg_duration_sec,
       ROUND(AVG(human_score), 3) AS human_score,
       ROUND(AVG(style_score), 3) AS style_score,
       ROUND(AVG(CASE WHEN status = 'success' THEN COALESCE(downloaded, 0) END), 4) AS download_rate,
       ROUND(AVG(CASE WHEN status = 'success' THEN COALESCE(edited, 0) END), 4) AS edit_rate,
       ROUND(AVG(CASE WHEN status = 'success' THEN COALESCE(paid, 0) END), 4) AS task_pay_rate,
       ROUND(AVG(complaint_flag), 4) AS complaint_rate
FROM task_level
GROUP BY model_version
ORDER BY model_version;
