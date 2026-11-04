"""Reproduce the Python tests and three synthetic evidence bundles offline."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tools/reproduce.py NEW_OUTPUT_DIRECTORY")
    target = Path(sys.argv[1]).resolve()
    target.mkdir(parents=True, exist_ok=False)
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                           cwd=ROOT, capture_output=True, text=True)
    (target / "tests.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    if tests.returncode:
        print(tests.stdout + tests.stderr)
        return tests.returncode
    results = {}
    for name, expected in [("good", 0), ("five_faults", 1), ("missing_evidence", 3)]:
        process = subprocess.run([sys.executable, "-m", "worldqa", "inspect",
                                  str(ROOT / "fixtures" / (name + ".json")),
                                  "--output", str(target / name)], cwd=ROOT,
                                 capture_output=True, text=True)
        results[name] = {"exit_code": process.returncode, "expected": expected,
                         "stdout": process.stdout, "stderr": process.stderr}
        if process.returncode != expected:
            print(process.stdout + process.stderr)
            raise RuntimeError(f"{name}: expected {expected}, got {process.returncode}")
    (target / "reproduction.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Python suite and all 3 synthetic bundles reproduced:", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
