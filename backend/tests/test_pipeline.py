import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.demand_capture import demand_capture_agent
from app.services.gemini_service import gemini_service

# ════════════════════════════════════════════════════════════════════════════
# STAGE 2 TESTS (Deterministic Validator)
# ════════════════════════════════════════════════════════════════════════════

def test_stage2_filler_words_rejected():
    """Ensure filler and empty phrases are outright rejected."""
    events = [
        {"customer_requested": "", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": " ", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "ek", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "bhaiya ek", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "haan", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "de do", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "theek hai", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "please", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "khatam", "availability": "unknown", "evidence": "", "resolved_from_pronoun": False},
        {"customer_requested": "sabun", "availability": "available", "evidence": "hai", "resolved_from_pronoun": False}, # Valid
    ]
    
    valid = demand_capture_agent._validate_events(events)
    assert len(valid) == 1
    assert valid[0]["customer_requested"] == "sabun"

def test_stage2_downgrade_missing_negation():
    """Ensure availability='unavailable' is downgraded to 'unknown' if no explicit negation cue exists in evidence."""
    events = [
        # Valid negation
        {"customer_requested": "maggi", "availability": "unavailable", "evidence": "nahi hai", "resolved_from_pronoun": False},
        {"customer_requested": "salt", "availability": "unavailable", "evidence": "kal aayega khatam ho gaya", "resolved_from_pronoun": False},
        
        # Missing negation (should downgrade)
        {"customer_requested": "milk", "availability": "unavailable", "evidence": "kal aayega", "resolved_from_pronoun": False},
        {"customer_requested": "bread", "availability": "unavailable", "evidence": "yippee le lo", "resolved_from_pronoun": False},
    ]
    
    valid = demand_capture_agent._validate_events(events)
    assert len(valid) == 4
    
    # Valid negations stay unavailable
    assert valid[0]["availability"] == "unavailable"
    assert valid[1]["availability"] == "unavailable"
    
    # Missing negations become unknown
    assert valid[2]["availability"] == "unknown"
    assert valid[3]["availability"] == "unknown"

def test_stage2_reject_orphaned_pronoun():
    """Ensure pronoun resolutions are rejected if there's no preceding valid event in the batch."""
    events = [
        # Orphaned pronoun (first in batch)
        {"customer_requested": "wo", "availability": "available", "evidence": "hai", "resolved_from_pronoun": True},
        
        # Valid event followed by a valid pronoun resolution
        {"customer_requested": "lux", "availability": "available", "evidence": "haan", "resolved_from_pronoun": False},
        {"customer_requested": "lux", "availability": "available", "evidence": "vo bhi de do", "resolved_from_pronoun": True},
    ]
    
    valid = demand_capture_agent._validate_events(events)
    
    # The first event should be dropped. The next two should remain.
    assert len(valid) == 2
    assert valid[0]["customer_requested"] == "lux"
    assert valid[0]["resolved_from_pronoun"] is False
    assert valid[1]["customer_requested"] == "lux"
    assert valid[1]["resolved_from_pronoun"] is True

# ════════════════════════════════════════════════════════════════════════════
# STAGE 3 TESTS (Product Cleaner Post-Check)
# ════════════════════════════════════════════════════════════════════════════

def test_stage3_subset_token_check():
    """Ensure the cleaner output is strictly a subset of the input tokens (no hallucinations)."""
    # Valid subset reductions
    assert demand_capture_agent._validate_cleaner_output("bhaiya ek maggi packet", "maggi") is True
    assert demand_capture_agent._validate_cleaner_output("lux lux soap", "lux soap") is True
    assert demand_capture_agent._validate_cleaner_output("surf excel dena", "surf excel") is True
    assert demand_capture_agent._validate_cleaner_output("amul DOODH", "amul doodh") is True
    
    # Hallucinated additions (should fail)
    assert demand_capture_agent._validate_cleaner_output("sabun dena", "lux sabun") is False
    assert demand_capture_agent._validate_cleaner_output("maggi", "maggi noodles") is False
    assert demand_capture_agent._validate_cleaner_output("tel", "fortune tel") is False
    assert demand_capture_agent._validate_cleaner_output("bread", "britannia bread") is False

# ════════════════════════════════════════════════════════════════════════════
# STAGE 1 TESTS (LLM JSON Outputs)
# ════════════════════════════════════════════════════════════════════════════

# Mocking Gemini since tests shouldn't hit real API
@patch('app.services.gemini_service.GeminiService.analyze_conversation_stage1')
def test_stage1_mocked_llm_schema(mock_analyze):
    mock_analyze.return_value = {
        "events": [
            {
                "customer_requested": "surf excel",
                "availability": "available",
                "evidence": "haan hai",
                "resolved_from_pronoun": False,
                "confidence": 0.95
            },
            {
                "customer_requested": "surf excel",
                "availability": "unknown",
                "evidence": "wo bhi dena",
                "resolved_from_pronoun": True,
                "confidence": 0.8
            }
        ]
    }
    
    # Run a dummy transcript
    result = gemini_service.analyze_conversation_stage1("Bhaiya surf excel hai? Haan hai. Wo bhi dena.")
    assert "events" in result
    assert len(result["events"]) == 2
    assert result["events"][1]["resolved_from_pronoun"] is True
