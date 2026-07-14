"""Geographic coordinate schemas for PostGIS integration."""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class Coordinates(BaseModel):
    """Geographic coordinates (latitude, longitude) schema."""

    latitude: float = Field(
        ..., ge=-90, le=90, description="Latitude in decimal degrees"
    )
    longitude: float = Field(
        ..., ge=-180, le=180, description="Longitude in decimal degrees"
    )

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return v

    class Config:
        json_schema_extra = {
            "example": {"latitude": 17.3850, "longitude": 78.4867}
        }


class LocationSearch(BaseModel):
    """Schema for location-based search queries."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: int = Field(
        default=1000, ge=1, le=100000, description="Search radius in meters"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 17.3850,
                "longitude": 78.4867,
                "radius_meters": 5000,
            }
        }


class BoundingBox(BaseModel):
    """Schema for bounding box searches."""

    min_latitude: float = Field(..., ge=-90, le=90)
    min_longitude: float = Field(..., ge=-180, le=180)
    max_latitude: float = Field(..., ge=-90, le=90)
    max_longitude: float = Field(..., ge=-180, le=180)

    @field_validator("max_latitude")
    @classmethod
    def validate_max_latitude(cls, v: float, info: ValidationInfo) -> float:
        if hasattr(info, "data") and info.data and "min_latitude" in info.data:
            if v <= info.data["min_latitude"]:
                raise ValueError(
                    "max_latitude must be greater than min_latitude"
                )
        return v

    @field_validator("max_longitude")
    @classmethod
    def validate_max_longitude(cls, v: float, info: ValidationInfo) -> float:
        if hasattr(info, "data") and info.data and "min_longitude" in info.data:
            if v <= info.data["min_longitude"]:
                raise ValueError(
                    "max_longitude must be greater than min_longitude"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "min_latitude": 17.3000,
                "min_longitude": 78.4000,
                "max_latitude": 17.4700,
                "max_longitude": 78.5734,
            }
        }
