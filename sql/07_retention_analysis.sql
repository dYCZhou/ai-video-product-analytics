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
    SELECT DISTINCT user_id, cohort_date FROM cohort WHERE day_gap = 0
),
data_end AS (
    SELECT MAX(DATE(submit_time)) AS max_date FROM generation_tasks
),
gaps(day_gap) AS (VALUES (0), (1), (7), (14)),
eligible AS (
    SELECT g.day_gap, d.user_id
    FROM gaps g
    CROSS JOIN d0_users d
    CROSS JOIN data_end e
    WHERE d.cohort_date <= DATE(e.max_date, '-' || g.day_gap || ' day')
)
SELECT 'D' || g.day_gap AS retention_day,
       COUNT(DISTINCT CASE WHEN c.day_gap = g.day_gap THEN c.user_id END) AS retained_users,
       COUNT(DISTINCT e.user_id) AS eligible_d0_users,
       ROUND(1.0 * COUNT(DISTINCT CASE WHEN c.day_gap = g.day_gap THEN c.user_id END) /
             COUNT(DISTINCT e.user_id), 4) AS retention_rate
FROM gaps g
LEFT JOIN eligible e ON e.day_gap = g.day_gap
LEFT JOIN cohort c ON c.user_id = e.user_id AND c.day_gap = g.day_gap
GROUP BY g.day_gap
ORDER BY g.day_gap;
