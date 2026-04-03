import httpx

from backend.services.analyzer.client import AnalyzerHttpClient


def test_analyzer_status_timeout_allows_longer_reads():
    timeout = AnalyzerHttpClient._status_timeout()

    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 5.0
    assert timeout.read == 30.0
    assert timeout.write == 10.0
    assert timeout.pool == 5.0