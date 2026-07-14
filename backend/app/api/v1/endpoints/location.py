import httpx
from fastapi import APIRouter, HTTPException

from app.schemas import LocationRequest, LocationResponse

router = APIRouter()


@router.post("/verify-location", response_model=LocationResponse)
async def verify_location(location: LocationRequest):
    """Reverse geocode coordinates to get human-readable address information.

    Uses Nominatim (OpenStreetMap) API - free and no API key required.
    """
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "format": "json",
            "addressdetails": 1,
        }
        headers = {"User-Agent": "api.corpus.swecha.org"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, params=params, headers=headers, timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            raise HTTPException(status_code=404, detail="Location not found")

        address = data.get("address", {})

        # Extract location components
        country = address.get("country")
        state = address.get("state") or address.get("province")
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
        )
        postal_code = address.get("postcode")
        formatted = data.get("display_name", "Unknown location")

        return LocationResponse(
            formatted_address=formatted,
            country=country,
            state=state,
            city=city,
            postal_code=postal_code,
            latitude=location.latitude,
            longitude=location.longitude,
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503, detail=f"Geocoding service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )
