import json
from io import BytesIO
from urllib.error import URLError

import pytest

from services.llm import NoRedirect, commentary, sentences, validate_input


@pytest.fixture
def payload():
    return {
        "product": "Logitech Mouse",
        "current_stock": 42,
        "estimated_days_left": 6,
        "anomaly_detected": True,
        "recommended_order": 100,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"current_stock": -1},
        {"current_stock": True},
        {"recommended_order": 1.5},
        {"estimated_days_left": float("nan")},
        {"estimated_days_left": -1},
        {"estimated_days_left": True},
        {"product": ""},
        {"product": "a\nb"},
        {"anomaly_detected": 1},
        {"unexpected": "SQL"},
    ],
)
def test_validation(payload, change):
    with pytest.raises(ValueError):
        validate_input(payload | change)


def test_fallback(payload):
    result = commentary(payload)
    assert result["source"] == "Deterministic summary"
    assert all(str(n) in result["text"] for n in [42, 6, 100])
    assert "unusual" in result["text"]
    result = commentary(
        payload | {"estimated_days_left": None, "anomaly_detected": False, "recommended_order": 0}
    )
    assert "unavailable" in result["text"] and "unusual" not in result["text"]
    assert commentary(payload, "https://example.com")["source"] == "Deterministic summary"


def fake_opener(monkeypatch, body=None, exception=None):
    class Opener:
        def open(self, req, timeout):
            assert req.full_url == "http://localhost:8080/v1/chat/completions"
            sent = json.loads(req.data)
            assert sent["temperature"] == 0
            assert sent["response_format"]["json_schema"]["strict"]
            if exception:
                raise exception
            return BytesIO(body)

    monkeypatch.setattr("services.llm.request.build_opener", lambda *args: Opener())


def response(order):
    return json.dumps({"choices": [{"message": {"content": json.dumps({"order": order})}}]}).encode()


def test_valid_local_llm(monkeypatch, payload):
    fake_opener(monkeypatch, response([0, 2, 1, 3]))
    result = commentary(payload, "http://localhost:8080")
    assert result["source"] == "Local LLM commentary"
    assert result["text"] == " ".join(sentences(payload)[i] for i in [0, 2, 1, 3])


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"{}",
        b"a" * 16385,
        response([0, 1, 2, 999]),
        response([0, 0, 1, 2]),
        response([True, 1, 2, 3]),
        response("bad"),
        response(["invented 99999"]),
    ],
)
def test_bad_llm_output(monkeypatch, payload, body):
    fake_opener(monkeypatch, body)
    assert commentary(payload, "http://localhost:8080")["source"] == "Deterministic summary"


def test_unavailable_llm(monkeypatch, payload):
    fake_opener(monkeypatch, exception=URLError("offline"))
    assert commentary(payload, "http://localhost:8080")["source"] == "Deterministic summary"
    assert NoRedirect().redirect_request(None, None, 302, "", {}, "http://other") is None
