"""Project smoke tests: schemas, SQL execution, metric agreement and syntax."""

from __future__ import annotations

import json
import py_compile
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def close(a: float, b: float, tolerance: float = 5e-4) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def main() -> None:
    for path in [ROOT / "app.py", ROOT / "run_pipeline.py", *sorted((ROOT / "src").glob("*.py"))]:
        py_compile.compile(str(path), doraise=True)

    summary = json.loads(
        (ROOT / "data" / "processed" / "summary.json").read_text(encoding="utf-8")
    )
    connection = sqlite3.connect(ROOT / "data" / "ai_video.db")
    sql_results: dict[str, pd.DataFrame] = {}
    for path in sorted((ROOT / "sql").glob("*.sql")):
        frame = pd.read_sql_query(path.read_text(encoding="utf-8"), connection)
        assert not frame.empty, f"{path.name} returned no rows"
        sql_results[path.name] = frame
        print(f"[PASS] {path.name}: {len(frame)} rows")

    model_sql = sql_results["05_model_evaluation.sql"].set_index("model_version")
    model_py = pd.read_csv(
        ROOT / "data" / "processed" / "model_metrics.csv"
    ).set_index("model_version")
    for model in model_py.index:
        assert close(model_sql.loc[model, "success_rate"], model_py.loc[model, "success_rate"])
        assert close(model_sql.loc[model, "download_rate"], model_py.loc[model, "download_rate"])

    daily = sql_results["01_daily_metrics.sql"]
    weighted_success = daily["submitted_tasks"].mul(daily["success_rate"]).sum() / daily[
        "submitted_tasks"
    ].sum()
    assert close(weighted_success, summary["overall"]["success_rate"])

    funnel_sql = sql_results["02_funnel_analysis.sql"]
    funnel_py = pd.read_csv(ROOT / "data" / "processed" / "funnel_metrics.csv")
    assert funnel_sql["users"].tolist() == funnel_py["users"].tolist()

    ab_sql = sql_results["09_ab_test_analysis.sql"].set_index("group")
    ab_py = pd.read_csv(ROOT / "data" / "processed" / "ab_metrics.csv").set_index("group")
    for group in ["control", "treatment"]:
        assert close(ab_sql.loc[group, "pay_click_rate"], ab_py.loc[group, "pay_click_rate"])
        assert close(ab_sql.loc[group, "user_pay_rate"], ab_py.loc[group, "user_pay_rate"])
        assert close(ab_sql.loc[group, "revenue"], ab_py.loc[group, "revenue"], tolerance=0.01)

    connection.close()
    assert len(list((ROOT / "sql").glob("*.sql"))) == 10
    assert len(list((ROOT / "data" / "raw").glob("*.csv"))) == 7
    print("[PASS] Python/SQL metric agreement")
    print("[PASS] Project validation completed")


if __name__ == "__main__":
    main()
