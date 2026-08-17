-- 业务问题：完成页入口改版是否提升商业化，同时不伤害体验？
-- 口径：用户级 ITT；仅纳入入组后至少提交一次任务的用户。
WITH post_entry_task AS (
    SELECT t.*, e."group"
    FROM generation_tasks t
    JOIN ab_experiment e ON t.user_id = e.user_id
    WHERE t.submit_time >= e.enter_time
),
task_action AS (
    SELECT task_id,
           MAX(action_type = 'pay_click') AS clicked,
           MAX(action_type = 'download') AS downloaded,
           MAX(action_type = 'exit') AS exited,
           MAX(action_type = 'regenerate') AS regenerated
    FROM user_actions
    GROUP BY task_id
),
task_order AS (
    SELECT task_id,
           MAX(pay_status = 'success') AS paid,
           SUM(CASE WHEN pay_status = 'success' THEN amount ELSE 0 END) AS revenue
    FROM payment_orders
    GROUP BY task_id
),
user_metric AS (
    SELECT e.user_id, e."group",
           MAX(t.task_id IS NOT NULL) AS eligible,
           MAX(t.status = 'success') AS successful,
           MAX(COALESCE(a.clicked, 0)) AS clicked,
           MAX(COALESCE(a.downloaded, 0)) AS downloaded,
           MAX(COALESCE(a.exited, 0)) AS exited,
           MAX(COALESCE(a.regenerated, 0)) AS regenerated,
           MAX(COALESCE(o.paid, 0)) AS paid,
           SUM(COALESCE(o.revenue, 0)) AS revenue
    FROM ab_experiment e
    LEFT JOIN post_entry_task t ON e.user_id = t.user_id
    LEFT JOIN task_action a ON t.task_id = a.task_id
    LEFT JOIN task_order o ON t.task_id = o.task_id
    GROUP BY e.user_id, e."group"
)
SELECT "group",
       SUM(eligible) AS eligible_users,
       SUM(successful) AS successful_users,
       SUM(clicked) AS click_users,
       SUM(paid) AS payer_users,
       ROUND(1.0 * SUM(clicked) / SUM(successful), 4) AS pay_click_rate,
       ROUND(1.0 * SUM(paid) / NULLIF(SUM(clicked), 0), 4) AS click_to_pay_rate,
       ROUND(1.0 * SUM(paid) / SUM(eligible), 4) AS user_pay_rate,
       ROUND(1.0 * SUM(downloaded) / SUM(successful), 4) AS download_rate,
       ROUND(1.0 * SUM(exited) / SUM(eligible), 4) AS exit_rate,
       ROUND(1.0 * SUM(regenerated) / SUM(successful), 4) AS regenerate_rate,
       ROUND(SUM(revenue), 2) AS revenue,
       ROUND(SUM(revenue) / SUM(eligible), 2) AS arpu
FROM user_metric
WHERE eligible = 1
GROUP BY "group"
ORDER BY "group";
