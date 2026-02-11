import sys
import os
import json

# ensure repo root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src import config


def main():
    print(json.dumps(config.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
