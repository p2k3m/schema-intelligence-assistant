import api


def test_api_health():
    assert api.health() == {"status": "ok"}

