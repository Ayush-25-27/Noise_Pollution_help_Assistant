"""
tests/test_classification_tool.py

Unit tests for the deterministic classification tool.
Run with: pytest tests/ -v
"""

import pytest

from app.agent.tools.classification_tool import check_limit, infer_source, ZONE_LIMITS


class TestCheckLimit:
    """check_limit must always return a checkable, reproducible verdict."""

    def test_residential_day_within(self):
        result = check_limit(50, "residential", "day")
        assert result["limit"] == 55
        assert result["exceeds"] is False
        assert result["over_by"] == 0

    def test_residential_night_exceeds(self):
        result = check_limit(50, "residential", "night")
        assert result["limit"] == 45
        assert result["exceeds"] is True
        assert result["over_by"] == 5

    def test_silence_day_exceeds(self):
        result = check_limit(60, "silence", "day")
        assert result["limit"] == 50
        assert result["exceeds"] is True
        assert result["over_by"] == 10

    def test_silence_night_exceeds(self):
        result = check_limit(42, "silence", "night")
        assert result["limit"] == 40
        assert result["exceeds"] is True
        assert result["over_by"] == 2

    def test_commercial_day_within(self):
        result = check_limit(64, "commercial", "day")
        assert result["limit"] == 65
        assert result["exceeds"] is False
        assert result["over_by"] == 0

    def test_commercial_day_exactly_at_limit(self):
        result = check_limit(65, "commercial", "day")
        assert result["exceeds"] is False
        assert result["over_by"] == 0

    def test_commercial_day_one_over(self):
        result = check_limit(66, "commercial", "day")
        assert result["exceeds"] is True
        assert result["over_by"] == 1

    def test_industrial_day_exceeds(self):
        result = check_limit(80, "industrial", "day")
        assert result["limit"] == 75
        assert result["exceeds"] is True
        assert result["over_by"] == 5

    def test_industrial_night_within(self):
        result = check_limit(70, "industrial", "night")
        assert result["limit"] == 70
        assert result["exceeds"] is False
        assert result["over_by"] == 0

    def test_over_by_never_negative(self):
        """over_by should be 0, never a negative number."""
        result = check_limit(10, "residential", "day")
        assert result["over_by"] == 0

    def test_all_zones_have_limits(self):
        for zone in ("residential", "silence", "commercial", "industrial"):
            for tod in ("day", "night"):
                result = check_limit(60, zone, tod)
                assert "limit" in result
                assert "exceeds" in result
                assert "over_by" in result


class TestInferSource:
    """infer_source must return a non-empty string for all valid input combos."""

    def test_brief_high_intensity(self):
        result = infer_source(90, "day", "brief")
        assert "loudspeaker" in result or "horn" in result or "celebration" in result

    def test_sustained_night(self):
        result = infer_source(65, "night", "sustained")
        assert "generator" in result or "machinery" in result or "nighttime" in result

    def test_sustained_day_high(self):
        result = infer_source(80, "day", "sustained")
        assert "construction" in result or "industrial" in result

    def test_sustained_day_moderate(self):
        result = infer_source(60, "day", "sustained")
        assert "traffic" in result

    def test_unclear_pattern_returns_string(self):
        result = infer_source(50, "night", "brief")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string_always(self):
        for db in (30, 60, 85, 100):
            for tod in ("day", "night"):
                for dur in ("brief", "sustained"):
                    assert isinstance(infer_source(db, tod, dur), str)
