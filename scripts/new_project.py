"""Create a new Excel-to-video project folder from the template.

Usage: python new_project.py <target-folder> --name "فیلم مجمع ۱۴۰۵" --year 1405
Never overwrites existing files.
"""
import argparse
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "project-template"
STAGES = ["assets", "1-excel", "1-excel/sources", "2-deck", "3-script", "4-audio", "5-video"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--name", required=True)
    ap.add_argument("--year", required=True)
    a = ap.parse_args()

    root = Path(a.target)
    root.mkdir(parents=True, exist_ok=True)
    for s in STAGES:
        (root / s).mkdir(exist_ok=True)
    for src in TEMPLATE.glob("*.md"):
        dst = root / src.name
        if dst.exists():
            print(f"skip (exists): {dst}")
            continue
        text = src.read_text(encoding="utf-8")
        text = text.replace("{{PROJECT_NAME}}", a.name).replace("{{YEAR}}", a.year)
        dst.write_text(text, encoding="utf-8")
        print(f"created: {dst}")


if __name__ == "__main__":
    sys.exit(main())
