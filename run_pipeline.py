"""One-command reproducible pipeline."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STEPS = [
    "src/generate_mock_data.py",
    "src/data_quality_check.py",
    "src/create_database.py",
    "src/analysis.py",
    "src/weekly_report.py",
    "src/create_assets.py",
]


def main() -> None:
    for step in STEPS:
        print(f"\n>>> {step}")
        subprocess.run([sys.executable, str(ROOT / step)], check=True)
    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
