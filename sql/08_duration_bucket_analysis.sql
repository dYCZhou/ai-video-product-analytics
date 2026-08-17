-- 业务问题：等待时长与预览、下载、退出行为有什么关系？
WITH action_flag AS (
    SELECT task_id,
           MAX(action_type = 'preview') AS previewed,
           MAX(action_type = 'download') AS downloaded,
           MAX(action_type = 'exit') AS exited
    FROM user_actions GROUP BY task_id
),
bucketed AS (
    SELECT t.task_id,
           CASE WHEN generation_duration <= 45 THEN '01_≤45s'
                WHEN generation_duration <= 75 THEN '02_46–75s'
                WHEN generation_duration <= 120 THEN '03_76–120s'
                ELSE '04_>120s' END AS duration_bucket,
           COALESCE(a.previewed, 0) AS previewed,
           COALESCE(a.downloaded, 0) AS downloaded,
           COALESCE(a.exited, 0) AS exited
    FROM generation_tasks t
    LEFT JOIN action_flag a USING (task_id)
    WHERE t.status = 'success'
)
SELECT duration_bucket, COUNT(*) AS successful_tasks,
       ROUND(AVG(previewed), 4) AS preview_rate,
       ROUND(AVG(downloaded), 4) AS download_rate,
       ROUND(AVG(exited), 4) AS exit_rate
FROM bucketed
GROUP BY duration_bucket
ORDER BY duration_bucket;
