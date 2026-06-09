import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.analysis_service import AnalysisService


def _ingest_spike_events(client) -> None:
    base = datetime.utcnow()
    events = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "ERROR" if minute < 8 else "INFO",
            "service": "orders-api",
            "message": "timeout" if minute < 8 else "ok",
        }
        for minute in range(25, -1, -1)
        for _ in range(10)
    ]
    response = client.post("/api/v1/logs/ingest", json={"events": events})
    assert response.status_code == 200


def test_concurrent_analyze_second_request_returns_409(client) -> None:
    _ingest_spike_events(client)

    original = AnalysisService.run_statistical_phase

    def slow_statistical_phase(self, *, lookback_hours=None):
        time.sleep(0.4)
        return original(self, lookback_hours=lookback_hours)

    with patch.object(AnalysisService, "run_statistical_phase", slow_statistical_phase):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(client.post, "/api/v1/analyze/run")
            time.sleep(0.05)
            second = pool.submit(client.post, "/api/v1/analyze/run")
            responses = [first.result(), second.result()]

    status_codes = sorted(response.status_code for response in responses)
    assert status_codes == [200, 409]
