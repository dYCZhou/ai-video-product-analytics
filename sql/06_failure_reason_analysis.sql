-- 业务问题：失败由哪些模型、生成类型和原因驱动？
WITH failures AS (
    SELECT model_version, generation_type, fail_reason, COUNT(*) AS failed_tasks
    FROM generation_tasks
    WHERE status <> 'success'
    GROUP BY model_version, generation_type, fail_reason
)
SELECT *,
       ROUND(1.0 * failed_tasks /
             SUM(failed_tasks) OVER (PARTITION BY model_version), 4) AS model_failure_share,
       ROUND(1.0 * failed_tasks /
             SUM(failed_tasks) OVER (), 4) AS overall_failure_share
FROM failures
ORDER BY failed_tasks DESC;
