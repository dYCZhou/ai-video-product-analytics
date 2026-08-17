-- 业务问题：注册用户在 D1、D7、D14 是否再次提交生成任务？
WITH activity AS (
    SELECT DISTINCT user_id, DATE(submit_time) AS active_date
    FROM generation_tasks
),
cohort AS (
    SELECT u.user_id, DATE(u.register_date) AS cohort_date,
           CAST(julianday(a.active_date) - julianday(DATE(u.register_date)) AS INTEGER) AS day_gap
    FROM user_info u
    LEFT JOIN activity a ON u.user_id = a.user_id
),
d0_users AS (
    SELECT DISTINCT user_id FROM cohort WHERE day_gap = 0
),
gaps(day_gap) AS (VALUES (0), (1), (7), (14))
SELECT 'D' || g.day_gap AS retention_day,
       COUNT(DISTINCT CASE WHEN c.day_gap = g.day_gap AND d.user_id IS NOT NULL THEN c.user_id END) AS retained_users,
       (SELECT COUNT(*) FROM d0_users) AS d0_cohort_users,
       ROUND(1.0 * COUNT(DISTINCT CASE WHEN c.day_gap = g.day_gap AND d.user_id IS NOT NULL THEN c.user_id END) /
             (SELECT COUNT(*) FROM d0_users), 4) AS retention_rate
FROM gaps g
LEFT JOIN cohort c ON c.day_gap = g.day_gap
LEFT JOIN d0_users d ON c.user_id = d.user_id
GROUP BY g.day_gap
ORDER BY g.day_gap;
