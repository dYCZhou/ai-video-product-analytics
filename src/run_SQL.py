from pathlib import Path
import sqlite3

import pandas as pd


project_root = Path(__file__).resolve().parent.parent
database_path = project_root / "data" / "ai_video.db"

sql = """
SELECT
    t.task_id,
    t.model_version,
    d.task_id AS downloaded_task_id
FROM generation_tasks AS t
LEFT JOIN (
    SELECT DISTINCT
        task_id
    FROM user_actions
    WHERE action_type = 'download'
) AS d
    ON t.task_id = d.task_id
WHERE t.status = 'success'
LIMIT 10;
"""

connection = sqlite3.connect(database_path)

try:
    result = pd.read_sql_query(sql, connection)
    print(result.to_string(index=False))
finally:
    connection.close()