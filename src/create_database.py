from pathlib import Path
import sqlite3

import pandas as pd


def create_database() -> None:
    """
    将 data/raw 目录下的 CSV 文件导入 SQLite 数据库。
    每个 CSV 文件会变成一张同名的数据表。
    """

    # 当前文件位于 src/create_database.py
    project_root = Path(__file__).resolve().parent.parent

    csv_directory = project_root / "data" / "raw"
    database_path = project_root / "data" / "ai_video.db"

    if not csv_directory.exists():
        raise FileNotFoundError(
            f"没有找到 CSV 目录：{csv_directory}\n"
            "请确认数据文件位于 data/raw 中。"
        )

    csv_files = list(csv_directory.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"{csv_directory} 中没有找到 CSV 文件。"
        )

    connection = sqlite3.connect(database_path)

    try:
        for csv_path in csv_files:
            table_name = csv_path.stem

            dataframe = pd.read_csv(csv_path)

            dataframe.to_sql(
                name=table_name,
                con=connection,
                if_exists="replace",
                index=False,
            )

            print(
                f"{table_name:<25} "
                f"{len(dataframe):>8,} rows"
            )

        print(f"\n数据库已生成：{database_path}")

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()