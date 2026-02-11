import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import init_db


def main():
    init_db()
    print("DB initialization complete.")


if __name__ == "__main__":
    main()
