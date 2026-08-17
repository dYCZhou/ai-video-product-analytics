-- 业务问题：完成页入口改版是否提升商业化，同时不伤害体验？
-- 主指标使用用户级 ITT；下载、退出、重新生成、投诉采用任务级护栏口径。
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
task_score AS (
    SELECT task_id, MAX(complaint_flag) AS complained
    FROM model_scores
    GROUP BY task_id
),
user_metric AS (
    SELECT e.user_id, e."group",
           MAX(t.task_id IS NOT NULL) AS eligible,
           MAX(t.status = 'success') AS successful,
           MAX(COALESCE(a.clicked, 0)) AS clicked,
           MAX(COALESCE(o.paid, 0)) AS paid,
           SUM(COALESCE(o.revenue, 0)) AS revenue
    FROM ab_experiment e
    LEFT JOIN post_entry_task t ON e.user_id = t.user_id
    LEFT JOIN task_action a ON t.task_id = a.task_id
    LEFT JOIN task_order o ON t.task_id = o.task_id
    GROUP BY e.user_id, e."group"
),
user_group AS (
    SELECT "group",
           SUM(eligible) AS eligible_users,
           SUM(successful) AS successful_users,
           SUM(clicked) AS click_users,
           SUM(paid) AS payer_users,
           SUM(revenue) AS revenue
    FROM user_metric
    WHERE eligible = 1
    GROUP BY "group"
),
task_group AS (
    SELECT t."group",
           COUNT(*) AS tasks,
           SUM(t.status = 'success') AS successful_tasks,
           SUM(CASE WHEN t.status = 'success' THEN COALESCE(a.downloaded, 0) ELSE 0 END) AS downloaded_tasks,
           SUM(COALESCE(a.exited, 0)) AS exited_tasks,
           SUM(CASE WHEN t.status = 'success' THEN COALESCE(a.regenerated, 0) ELSE 0 END) AS regenerated_tasks,
           SUM(CASE WHEN t.status = 'success' THEN COALESCE(s.complained, 0) ELSE 0 END) AS complained_tasks
    FROM post_entry_task t
    LEFT JOIN task_action a ON t.task_id = a.task_id
    LEFT JOIN task_score s ON t.task_id = s.task_id
    GROUP BY t."group"
)
SELECT u."group", u.eligible_users, u.successful_users, u.click_users, u.payer_users,
       t.tasks, t.successful_tasks,
       ROUND(1.0 * u.click_users / u.successful_users, 4) AS pay_click_rate,
       ROUND(1.0 * u.payer_users / NULLIF(u.click_users, 0), 4) AS click_to_pay_rate,
       ROUND(1.0 * u.payer_users / u.eligible_users, 4) AS user_pay_rate,
       ROUND(1.0 * t.downloaded_tasks / t.successful_tasks, 4) AS task_download_rate,
       ROUND(1.0 * t.exited_tasks / t.tasks, 4) AS task_exit_rate,
       ROUND(1.0 * t.regenerated_tasks / t.successful_tasks, 4) AS task_regenerate_rate,
       ROUND(1.0 * t.complained_tasks / t.successful_tasks, 4) AS task_complaint_rate,
       ROUND(u.revenue, 2) AS revenue,
       ROUND(u.revenue / u.eligible_users, 2) AS arpu
FROM user_group u
JOIN task_group t ON u."group" = t."group"
ORDER BY u."group";
