"""PostGIS Geometry Utilities for handling spatial data."""

from geoalchemy2.functions import ST_X, ST_Y, ST_GeomFromText
from sqlalchemy import func


def create_point_wkt(latitude: float, longitude: float) -> str:
    """Create a Well-Known Text (WKT) representation of a Point.

    Created from lat/lng coordinates.

    Args:
        latitude: Latitude coordinate (WGS84)
        longitude: Longitude coordinate (WGS84)

    Returns:
        WKT string representation of the point
    """
    return f"POINT({longitude} {latitude})"


def create_point_geometry(latitude: float, longitude: float):
    """Create a PostGIS Point geometry from lat/lng coordinates.

    Args:
        latitude: Latitude coordinate (WGS84)
        longitude: Longitude coordinate (WGS84)

    Returns:
        SQLAlchemy expression for creating the geometry
    """
    wkt = create_point_wkt(latitude, longitude)
    return ST_GeomFromText(wkt, 4326)  # SRID 4326 = WGS84


def extract_coordinates_from_point(location_column):
    """Extract latitude and longitude expressions from a PostGIS Point.

    Extracts from a PostGIS Point geometry column.

    Use this for building SQL queries.

    Args:
        location_column: SQLAlchemy column containing PostGIS Point geometry

    Returns:
        Tuple of (latitude_expression, longitude_expression)
        for use in SQL queries
    """
    latitude = ST_Y(location_column)
    longitude = ST_X(location_column)
    return latitude, longitude


def extract_coordinates_from_geometry(geometry_data) -> tuple | None:
    """Extract actual coordinate values from PostGIS geometry data.

    Use this to get lat/lng values from database records.

    Args:
        geometry_data: PostGIS Point geometry data (can be bytes,
            WKBElement, or other formats)

    Returns:
        Tuple of (longitude, latitude) or None if invalid/empty
    """
    if not geometry_data:
        return None

    try:
        import shapely.wkb
        from geoalchemy2.elements import WKBElement, WKTElement
        from geoalchemy2.shape import to_shape
        from shapely.geometry import Point

        point = None

        # Handle different types of geometry data
        if isinstance(geometry_data, (WKBElement, WKTElement)):
            # Standard geoalchemy2 elements
            point = to_shape(geometry_data)
        elif isinstance(geometry_data, str):
            # Hexadecimal WKB string (common from direct SQL queries)
            try:
                wkb_bytes = bytes.fromhex(geometry_data)
                point = shapely.wkb.loads(wkb_bytes)
            except (ValueError, Exception):
                return None
        elif isinstance(geometry_data, bytes):
            # Raw binary data - try to parse as WKB
            try:
                point = shapely.wkb.loads(geometry_data)
            except Exception:
                # If WKB parsing fails, might be different format
                return None
        elif hasattr(geometry_data, "__geo_interface__"):
            # Shapely or other geometry objects
            point = geometry_data
        else:
            # Try to convert using geoalchemy2 anyway
            try:
                point = to_shape(geometry_data)
            except Exception:
                return None

        if isinstance(point, Point) and not point.is_empty:
            # Return as (longitude, latitude) following GeoJSON convention
            return (point.x, point.y)

    except Exception as e:
        # Log error but don't raise to avoid breaking API responses
        print(f"Error extracting coordinates: {e}")
        return None

    return None


def point_to_dict(location_column) -> dict:
    """Convert a PostGIS Point to a dictionary with lat/lng keys.

    Use this in SELECT queries to return coordinates as dict.

    Args:
        location_column: SQLAlchemy column containing PostGIS Point geometry

    Returns:
        Dictionary with 'latitude' and 'longitude' keys
    """
    lat_expr, lng_expr = extract_coordinates_from_point(location_column)
    return {"latitude": lat_expr, "longitude": lng_expr}


def distance_query(
    location_column, latitude: float, longitude: float, distance_meters: float
):
    """Create a query expression to find records within a certain distance.

    Args:
        location_column: SQLAlchemy column containing PostGIS Point geometry
        latitude: Target latitude
        longitude: Target longitude
        distance_meters: Search radius in meters

    Returns:
        SQLAlchemy boolean expression for the distance filter
    """
    target_point = create_point_geometry(latitude, longitude)
    # ST_DWithin with geography type automatically uses meters
    return func.ST_DWithin(
        func.ST_Transform(location_column, 4326),  # Ensure WGS84
        func.ST_Transform(target_point, 4326),
        distance_meters,
        True,  # Use spheroid for accurate distance calculation
    )


def bbox_query(
    location_column,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
):
    """Create a query expression to find records within a bounding box.

    Args:
        location_column: SQLAlchemy column containing PostGIS Point geometry
        min_lat: Minimum latitude
        min_lng: Minimum longitude
        max_lat: Maximum latitude
        max_lng: Maximum longitude

    Returns:
        SQLAlchemy boolean expression for the bounding box filter
    """
    bbox_wkt = (
        f"POLYGON(({min_lng} {min_lat}, {max_lng} {min_lat}, "
        f"{max_lng} {max_lat}, {min_lng} {max_lat}, {min_lng} {min_lat}))"
    )
    bbox_geom = ST_GeomFromText(bbox_wkt, 4326)
    return func.ST_Within(location_column, bbox_geom)


def calculate_distance_meters(
    location_column, latitude: float, longitude: float
):
    """Calculate distance in meters from a point to the stored location.

    Args:
        location_column: SQLAlchemy column containing PostGIS Point geometry
        latitude: Target latitude
        longitude: Target longitude

    Returns:
        SQLAlchemy expression that returns distance in meters
    """
    create_point_geometry(latitude, longitude)
    # Use text() for PostgreSQL-specific geography casting syntax
    from sqlalchemy import text

    return text(
        "ST_Distance(ST_Transform(location, 4326)::geography, "
        "ST_Transform(ST_GeomFromText(:target_wkt, 4326), 4326)::geography)"
    ).params(target_wkt=create_point_wkt(latitude, longitude))


# Helper functions for API serialization
def serialize_point_to_coords(point_data) -> dict | None:
    """Convert PostGIS point data to latitude/longitude for API responses.

    Args:
        point_data: Raw point data from database

    Returns:
        Dictionary with 'latitude' and 'longitude' keys, or None if no data
    """
    if not point_data:
        return None

    # If point_data is already a dict (from explicit SELECT with ST_X/ST_Y)
    if isinstance(point_data, dict):
        return point_data

    # If point_data is WKT string or other format, parse it
    # This would need additional implementation based on your specific use case
    return None


def coords_to_point_wkt(coords: dict) -> str | None:
    """Convert coordinate dictionary to WKT for database storage.

    Args:
        coords: Dictionary with 'latitude' and 'longitude' keys

    Returns:
        WKT string or None if invalid coordinates
    """
    if not coords or "latitude" not in coords or "longitude" not in coords:
        return None

    try:
        lat = float(coords["latitude"])
        lng = float(coords["longitude"])
        return create_point_wkt(lat, lng)
    except (ValueError, TypeError):
        return None


def create_point_for_record(latitude: float, longitude: float):
    """Create a PostGIS Point geometry value for Record model fields.

    This uses the WKT string format that GeoAlchemy2 can convert automatically.

    Args:
        latitude: Latitude coordinate (WGS84)
        longitude: Longitude coordinate (WGS84)

    Returns:
        WKT string that GeoAlchemy2 will convert to PostGIS geometry
    """
    return create_point_wkt(latitude, longitude)
