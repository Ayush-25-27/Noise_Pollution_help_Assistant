"""
tests/test_api.py

FastAPI route tests using TestClient (no live server needed).
Run with: pytest tests/ -v
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_PROVIDER", "mock")

from app.main import app

client = TestClient(app)


class TestReportEndpoint:
    def test_valid_request_returns_200(self):
        resp = client.post("/api/report", json={
            "location": "Near Lotus Public School, Sector 12",
            "zone": "silence",
            "db": 78,
            "time_of_day": "night",
            "duration": "sustained",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["exceeds"] is True
        assert data["limit"] == 40
        assert data["over_by"] == 38

    def test_invalid_zone_returns_422(self):
        resp = client.post("/api/report", json={
            "location": "Somewhere",
            "zone": "park",  # invalid
            "db": 60,
            "time_of_day": "day",
            "duration": "sustained",
        })
        assert resp.status_code == 422

    def test_invalid_time_of_day_returns_422(self):
        resp = client.post("/api/report", json={
            "location": "Somewhere",
            "zone": "residential",
            "db": 60,
            "time_of_day": "morning",  # invalid
            "duration": "sustained",
        })
        assert resp.status_code == 422

    def test_db_out_of_range_returns_422(self):
        resp = client.post("/api/report", json={
            "location": "Somewhere",
            "zone": "residential",
            "db": 999,  # out of range
            "time_of_day": "day",
            "duration": "sustained",
        })
        assert resp.status_code == 422

    def test_omit_db_uses_fallback(self):
        resp = client.post("/api/report", json={
            "location": "Unknown New Place",
            "zone": "residential",
        })
        assert resp.status_code == 200
        assert resp.json()["data_source"].startswith("sample_data")

    def test_response_schema_complete(self):
        resp = client.post("/api/report", json={
            "location": "Test",
            "zone": "commercial",
            "db": 70,
            "time_of_day": "day",
            "duration": "sustained",
        })
        data = resp.json()
        for field in ("location", "zone", "zone_label", "db", "time_of_day", "duration",
                      "data_source", "limit", "exceeds", "over_by", "source_guess",
                      "regulation_passages", "answer"):
            assert field in data, f"Missing field: {field}"


class TestReadingsEndpoint:
    def test_submit_valid_reading(self):
        resp = client.post("/api/readings", json={
            "location": "Test Submit Street",
            "db": 72,
            "time_of_day": "day",
            "duration": "sustained",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "created"
        assert data["location"] == "Test Submit Street"

    def test_submit_invalid_time_returns_422(self):
        resp = client.post("/api/readings", json={
            "location": "Test",
            "db": 60,
            "time_of_day": "evening",  # invalid
            "duration": "brief",
        })
        assert resp.status_code == 422

    def test_submit_db_out_of_range(self):
        resp = client.post("/api/readings", json={
            "location": "Test",
            "db": -5,
            "time_of_day": "day",
            "duration": "brief",
        })
        assert resp.status_code == 422
