"""Minimal metrics abstraction. Uses prometheus_client if available, otherwise no-op stubs."""
try:
    from prometheus_client import Counter, Gauge
    has_prom = True
except Exception:
    has_prom = False


if has_prom:
    METRIC_NOTIFICATIONS = Counter('bibi_notifications_total', 'Total notifications sent')
    METRIC_ERRORS = Counter('bibi_errors_total', 'Total errors')

    def inc_notifications(n: int = 1):
        METRIC_NOTIFICATIONS.inc(n)

    def inc_errors(n: int = 1):
        METRIC_ERRORS.inc(n)
else:
    def inc_notifications(n: int = 1):
        return None

    def inc_errors(n: int = 1):
        return None
