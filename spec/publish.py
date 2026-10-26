#!/usr/bin/env python3
"""Rebuild the reading edition and its downloadable source package."""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT.parent / "dist")
    args = parser.parse_args()
    requirements = ROOT.parent / "DEVELOPMENT-REQUIREMENTS.md"
    if requirements.exists():
        shutil.copy2(requirements, ROOT / requirements.name)
    for script in ["build_artifacts.py", "render_diagrams.py", "verify_contracts.py"]:
        subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)
    output = args.output.resolve()
    downloads = output / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    for name in ["contract-model.json", "reading-model.json", "verification-report.json"]:
        shutil.copy2(ROOT / name, output / name)
    for name in ["keel-developer-contracts.md", "keel-delivery.drawio", "verification-report.md", "DEVELOPMENT-REQUIREMENTS.md", "collection-event.schema.json"]:
        shutil.copy2(ROOT / name, downloads / name)
    shutil.copytree(ROOT / "diagrams", output / "diagrams", dirs_exist_ok=True)
    files = [
        "README.md", "acceptance-cases.json", "build_artifacts.py", "contract-model.json",
        "reading.py", "guide.py", "collection.py", "walkthrough.py", "collection_model.py", "verify_walkthrough.py", "collection-event.schema.json", "DEVELOPMENT-REQUIREMENTS.md", "data_contracts.py", "reading-model.json", "traceability.json", "publish.py",
        "keel-delivery.drawio", "keel-developer-contracts.md", "narrative.md",
        "validation-notes.md", "render_diagrams.py", "verify_contracts.py",
        "verification-report.json", "verification-report.md", "source/keel-delivery-fishbone.md",
        "source/PRD.md", "source/DESIGN-SYSTEM.md",
    ]
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "diagrams").glob("*.svg"))]
    with zipfile.ZipFile(downloads / "keel-development-handoff.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(ROOT / name, name)
    print("Published reading edition:", output)

if __name__ == "__main__":
    main()
