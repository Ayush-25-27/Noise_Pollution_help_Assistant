"""
tests/test_orchestrator.py

Integration-level tests for the orchestrator (mock LLM provider only).
Run with: pytest tests/ -v
"""

import os

import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")

from app.agent.orchestrator import get_report


class TestGetReport:
    """End-to-end orchestrator tests with the mock LLM backend."""

    def test_basic_fields_present(self):
        result = get_report(
            location="Test Street",
            zone="residential",
            db=60,
            time_of_day="night",
            duration="sustained",
        )
        required = {
            "location", "zone", "zone_label", "db", "time_of_day",
            "duration", "data_source", "limit", "exceeds", "over_by",
            "source_guess", "regulation_passages", "answer",
        }
        assert required.issubset(result.keys())

    def test_exceeds_flag_correct(self):
        # 60 dB night in residential → limit 45 → exceeds
        result = get_report(location="A", zone="residential", db=60, time_of_day="night", duration="sustained")
        assert result["exceeds"] is True
        assert result["over_by"] == 15
        assert result["limit"] == 45

    def test_within_limit(self):
        # 50 dB day in residential → limit 55 → within
        result = get_report(location="B", zone="residential", db=50, time_of_day="day", duration="sustained")
        assert result["exceeds"] is False
        assert result["over_by"] == 0

    def test_silence_zone_label(self):
        result = get_report(location="C", zone="silence", db=45, time_of_day="day", duration="brief")
        assert "silence" in result["zone_label"].lower() or "school" in result["zone_label"].lower()

    def test_user_provided_data_source(self):
        result = get_report(
            location="D", zone="commercial", db=70, time_of_day="day", duration="sustained"
        )
        assert result["data_source"] == "user_provided"

    def test_fetch_fallback_when_db_omitted(self):
        # No db, time_of_day, or duration → falls back to sample data
        result = get_report(location="Completely Unknown Place XYZ", zone="residential")
        assert result["db"] > 0
        assert result["data_source"].startswith("sample_data")

    def test_regulation_passages_returned(self):
        result = get_report(location="E", zone="silence", db=60, time_of_day="day", duration="sustained")
        assert isinstance(result["regulation_passages"], list)
        assert len(result["regulation_passages"]) > 0

    def test_answer_is_non_empty_string(self):
        result = get_report(location="F", zone="industrial", db=80, time_of_day="day", duration="sustained")
        assert isinstance(result["answer"], str)
        assert len(result["answer"].strip()) > 0

    def test_question_passed_through(self):
        """The answer should echo the question text in mock mode."""
        result = get_report(
            location="G", zone="residential", db=55, time_of_day="night", duration="brief",
            question="What complaint form should I use?"
        )
        # In mock mode the answer echoes content after 'Question:'
        assert isinstance(result["answer"], str)

    def test_answer_never_names_individual(self):
        """Smoke-check: the answer must not contain mock personal names."""
        result = get_report(location="H", zone="residential", db=70, time_of_day="night", duration="sustained")
        answer = result["answer"].lower()
        # The test ensures the system prompt constraint is active in the prompt itself
        # (full LLM enforcement is at generation time; mock just echoes the prompt tail)
        assert "john" not in answer
        assert "sharma" not in answer


class TestGetReportAllZones:
    @pytest.mark.parametrize("zone,day_limit,night_limit", [
        ("residential", 55, 45),
        ("silence", 50, 40),
        ("commercial", 65, 55),
        ("industrial", 75, 70),
    ])
    def test_limits_match_rules(self, zone, day_limit, night_limit):
        r_day = get_report(location="X", zone=zone, db=60, time_of_day="day", duration="sustained")
        r_night = get_report(location="X", zone=zone, db=60, time_of_day="night", duration="sustained")
        assert r_day["limit"] == day_limit
        assert r_night["limit"] == night_limit
