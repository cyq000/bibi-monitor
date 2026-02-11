import sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src import db, storage
from datetime import datetime, timedelta


def main():
    # ensure tables
    db.init_db()

    s = storage.storage
    now = datetime.utcnow()
    wm = s.store_window_metric(
        symbol="TESTUSDT",
        window_type="1h",
        window_start=now - timedelta(hours=1),
        window_end=now,
        buy_taker_volume=1000.0,
        sell_taker_volume=200.0,
        total_volume=1200.0,
        score_a=83.33,
        volume_24h_usdt=15000000.0,
    )
    print("Inserted WindowMetric id:", wm.id)

    n = s.create_notification("TESTUSDT", wm.id, event_id=f"TEST-{wm.id}", payload={"message":"test"})
    print("Created Notification id:", None if n is None else n.id)


if __name__ == "__main__":
    main()
