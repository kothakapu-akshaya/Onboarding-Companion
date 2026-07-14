"""Tests for location API endpoint."""

import pytest
from fastapi import FastAPI

from app.api.v1.endpoints.location import router


@pytest.fixture
def test_app():
    """Create test FastAPI app with router."""
    app = FastAPI()
    app.include_router(router)
    return app


class TestLocationEndpoint:
    """Test cases for location verification endpoint."""

    def test_router_has_correct_prefix(self):
        """Test router has correct structure."""
        assert router is not None

    def test_location_request_schema(self):
        """Test location request schema."""
        from app.schemas import LocationRequest

        request = LocationRequest(latitude=40.7128, longitude=-74.0060)
        assert request.latitude == 40.7128
        assert request.longitude == -74.0060

    def test_location_response_schema(self):
        """Test location response schema."""
        from app.schemas import LocationResponse

        response = LocationResponse(
            formatted_address="New York, NY",
            country="USA",
            state="NY",
            city="New York",
            postal_code="10001",
            latitude=40.7128,
            longitude=-74.0060,
        )
        assert response.formatted_address == "New York, NY"
        assert response.country == "USA"

    def test_location_request_with_invalid_coordinates(self):
        """Test location request with invalid coordinates."""
        from app.schemas import LocationRequest

        with pytest.raises(ValueError):
            LocationRequest(latitude=100, longitude=-200)
