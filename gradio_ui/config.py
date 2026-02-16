import os

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://ml-service-app:8080")

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))

POLL_INTERVAL_SEC = float(os.getenv("POLL_INTERVAL_SEC", "1.0"))
POLL_TIMEOUT_SEC = float(os.getenv("POLL_TIMEOUT_SEC", "25"))
