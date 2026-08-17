-- 业务问题：按周变化的成功率由哪个模型与失败原因驱动？
WITH weekly AS (
    SELECT STRFTIME('%Y-%W', submit_time) AS year_week,
           model_version,
           COUNT(*) AS tasks,
           SUM(status = 'success') AS success_tasks,
           SUM(status <> 'success') AS failed_tasks
    FROM generation_tasks
    GROUP BY year_week, model_version
),
with_change AS (
    SELECT *,
           ROUND(1.0 * success_tasks / tasks, 4) AS success_rate,
           ROUND(1.0 * success_tasks / tasks -
                 LAG(1.0 * success_tasks / tasks)
                 OVER (PARTITION BY model_version ORDER BY year_week), 4) AS wow_change
    FROM weekly
)
SELECT year_week, model_version, tasks, success_tasks, failed_tasks,
       success_rate, wow_change,
       RANK() OVER (PARTITION BY year_week ORDER BY wow_change) AS decline_rank
FROM with_change
ORDER BY year_week, decline_rank;
