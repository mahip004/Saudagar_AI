from unittest.mock import patch

from app.agents.demand_capture import demand_capture_agent


@patch("app.services.gemini_service.GeminiService.verify_demand_event")
def test_accepts_a_verified_grounded_product_to_reply_mapping(mock_verify):
    transcript = "Chocolate hai kya? Nahi bhai, khatam ho gaya."
    mock_verify.return_value = {
        "verified": True,
        "customer_requested": "Chocolate",
        "availability": "unavailable",
        "evidence": "Nahi bhai, khatam ho gaya",
        "confidence": 0.94,
    }
    result = demand_capture_agent._verify_events(
        [{"customer_requested": "Chocolate", "availability": "unavailable", "evidence": "Nahi bhai, khatam ho gaya"}], transcript
    )
    assert result[0]["customer_requested"] == "Chocolate"
    assert result[0]["availability"] == "unavailable"


@patch("app.services.gemini_service.GeminiService.verify_demand_event")
def test_rejects_ungrounded_or_low_confidence_verification(mock_verify):
    mock_verify.return_value = {
        "verified": True,
        "customer_requested": "Maggi",
        "availability": "unavailable",
        "evidence": "not in transcript",
        "confidence": 0.95,
    }
    result = demand_capture_agent._verify_events(
        [{"customer_requested": "Maggi", "availability": "unavailable", "evidence": ""}],
        "Chocolate hai kya? Nahi bhai, khatam ho gaya.",
    )
    assert result == []


def test_product_cleaner_post_check_rejects_hallucinated_brand():
    assert demand_capture_agent._validate_cleaner_output("sabun dena", "lux sabun") is False
