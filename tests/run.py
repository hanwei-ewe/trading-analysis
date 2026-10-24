import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def main():
    total = 0
    failures = 0
    for path in sorted(HERE.glob("test_*.py")):
        module = importlib.import_module(path.stem)
        for name in sorted(dir(module)):
            if name.startswith("test_") and callable(getattr(module, name)):
                total += 1
                try:
                    getattr(module, name)()
                    print(f"PASS {path.stem}::{name}")
                except Exception as err:
                    failures += 1
                    print(f"FAIL {path.stem}::{name}: {err}")
    print(f"\n{total - failures}/{total} passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
