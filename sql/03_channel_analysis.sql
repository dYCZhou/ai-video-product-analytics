-- 业务问题：哪个获客渠道带来的用户质量和商业价值更高？
WITH user_value AS (
    SELECT u.user_id, u.channel,
           MAX(t.status = 'success') AS generated_successfully,
           MAX(o.pay_status = 'success') AS paid,
           SUM(CASE WHEN o.pay_status = 'success' THEN o.amount ELSE 0 END) AS revenue
    FROM user_info u
    LEFT JOIN generation_tasks t ON u.user_id = t.user_id
    LEFT JOIN payment_orders o ON t.task_id = o.task_id
    GROUP BY u.user_id, u.channel
)
SELECT channel,
       COUNT(*) AS users,
       ROUND(AVG(generated_successfully), 4) AS success_user_rate,
       ROUND(AVG(paid), 4) AS payer_rate,
       ROUND(SUM(revenue) / COUNT(*), 2) AS arpu,
       ROUND(SUM(revenue) / NULLIF(SUM(paid), 0), 2) AS arppu,
       ROUND(SUM(revenue), 2) AS revenue
FROM user_value
GROUP BY channel
ORDER BY payer_rate DESC;
