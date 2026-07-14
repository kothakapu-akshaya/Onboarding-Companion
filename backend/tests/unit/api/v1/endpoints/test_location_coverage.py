from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints.location import verify_location
from app.schemas import LocationRequest


class DummyResponse:
    def __init__(self, payload=None, error=None):
        self._payload = payload or {}
        self._error = error

    def raise_for_status(self):
        if self._error is not None:
            raise self._error

    def json(self):
        return self._payload


class DummyAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return self.response


@pytest.mark.asyncio
async def test_verify_location_success():
    payload = {
        "display_name": "Hyderabad, Telangana, India",
        "address": {
            "country": "India",
            "state": "Telangana",
            "city": "Hyderabad",
            "postcode": "500081",
        },
    }
    with patch(
        "app.api.v1.endpoints.location.httpx.AsyncClient",
        return_value=DummyAsyncClient(DummyResponse(payload=payload)),
    ):
        result = await verify_location(
            LocationRequest(latitude=17.385, longitude=78.4867)
        )

    assert result.formatted_address == "Hyderabad, Telangana, India"
    assert result.country == "India"
    assert result.city == "Hyderabad"


@pytest.mark.asyncio
async def test_verify_location_http_error():
    with patch(
        "app.api.v1.endpoints.location.httpx.AsyncClient",
        return_value=DummyAsyncClient(
            DummyResponse(error=httpx.HTTPError("service down"))
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await verify_location(
                LocationRequest(latitude=17.385, longitude=78.4867)
            )

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_verify_location_error_payload_becomes_server_error():
    with patch(
        "app.api.v1.endpoints.location.httpx.AsyncClient",
        return_value=DummyAsyncClient(
            DummyResponse(payload={"error": "location not found"})
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await verify_location(
                LocationRequest(latitude=17.385, longitude=78.4867)
            )

    assert exc_info.value.status_code == 500


def test_verify_location_invalid_coordinates_rejected():
    with pytest.raises(ValidationError):
        LocationRequest(latitude=100.0, longitude=78.4867)
