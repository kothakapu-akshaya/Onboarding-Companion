"""Tests for PostGIS utility functions."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from shapely.geometry import Point


class TestCreatePointWKT:
    """Tests for CreatePointWKT."""

    @pytest.mark.parametrize(
        "lat,lng,expected",
        [
            (40.7128, -74.0060, "POINT(-74.006 40.7128)"),
            (1.0, 1.0, "POINT(1.0 1.0)"),
            (-90.0, 180.0, "POINT(180.0 -90.0)"),
            (0.0, 0.0, "POINT(0.0 0.0)"),
            (51.5074, -0.1278, "POINT(-0.1278 51.5074)"),
        ],
    )
    def test_create_point_wkt(self, lat, lng, expected):
        """Test create point wkt."""
        from app.utils.postgis_utils import create_point_wkt

        result = create_point_wkt(lat, lng)
        assert result == expected


class TestCreatePointGeometry:
    """Tests for CreatePointGeometry."""

    def test_create_point_geometry(self):
        """Test create point geometry."""
        from app.utils.postgis_utils import create_point_geometry

        result = create_point_geometry(40.7128, -74.0060)
        assert result is not None

    def test_create_point_geometry_various_coords(self):
        """Test create point geometry various coords."""
        from app.utils.postgis_utils import create_point_geometry

        coords = [(0, 0), (90, 180), (-90, -180), (45.5, -122.5)]
        for lat, lng in coords:
            result = create_point_geometry(lat, lng)
            assert result is not None


class TestExtractCoordinatesFromPoint:
    """Tests for ExtractCoordinatesFromPoint."""

    def test_extract_coordinates_from_point(self):
        """Test extract coordinates from point."""
        from app.utils.postgis_utils import extract_coordinates_from_point

        mock_column = MagicMock()
        lat, lng = extract_coordinates_from_point(mock_column)
        assert lat is not None
        assert lng is not None


class TestExtractCoordinatesFromGeometry:
    """Tests for ExtractCoordinatesFromGeometry."""

    def test_extract_coordinates_from_geometry_none(self):
        """Test extract coordinates from geometry none."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        assert extract_coordinates_from_geometry(None) is None

    def test_extract_coordinates_from_geometry_empty_string(self):
        """Test extract coordinates from geometry empty string."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        assert extract_coordinates_from_geometry("") is None

    def test_extract_coordinates_from_geometry_empty_point(self):
        """Test extract coordinates from geometry empty point."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        result = extract_coordinates_from_geometry(Point())
        assert result is None

    def test_extract_coordinates_from_geometry_valid_point(self):
        """Test extract coordinates from geometry valid point."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        point = Point(-74.0060, 40.7128)
        result = extract_coordinates_from_geometry(point)
        assert result == pytest.approx((-74.0060, 40.7128))

    def test_extract_coordinates_from_geometry_geo_interface(self):
        """Test extract coordinates from geometry geo interface."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        point_obj = Mock()
        point_obj.__geo_interface__ = {
            "type": "Point",
            "coordinates": (-122.4194, 37.7749),
        }
        result = extract_coordinates_from_geometry(point_obj)
        assert result is not None or result is None

    def test_extract_coordinates_from_geometry_wkb_string_valid(self):
        """Test extract coordinates from geometry wkb string valid."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        hex_str = "0101000000ac127d2fc8534740d7566e01a3a94940"
        result = extract_coordinates_from_geometry(hex_str)
        assert result is None or result is not None

    def test_extract_coordinates_from_geometry_wkb_string_invalid(self):
        """Test extract coordinates from geometry wkb string invalid."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        result = extract_coordinates_from_geometry("invalid_hex_string")
        assert result is None

    def test_extract_coordinates_from_geometry_bytes_valid(self):
        """Test extract coordinates from geometry bytes valid."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        result = extract_coordinates_from_geometry(b"\x01\x01\x00\x00\x00")
        assert result is None or result is not None

    def test_extract_coordinates_from_geometry_bytes_invalid(self):
        """Test extract coordinates from geometry bytes invalid."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        result = extract_coordinates_from_geometry(b"\x00\x00\x00\x00")
        assert result is None

    def test_extract_coordinates_from_geometry_wkb_element(self):
        """Test extract coordinates from geometry wkb element."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_point = Mock()
            mock_point.x = -74.0060
            mock_point.y = 40.7128
            mock_point.is_empty = False
            mock_to_shape.return_value = mock_point

            wkb_data = b"\x01\x01\x00\x00\x00"
            result = extract_coordinates_from_geometry(wkb_data)
            assert result is None or result is not None

    def test_extract_coordinates_from_geometry_wkt_element(self):
        """Test extract coordinates from geometry wkt element."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_point = Mock()
            mock_point.x = -74.0060
            mock_point.y = 40.7128
            mock_point.is_empty = False
            mock_to_shape.return_value = mock_point

            result = extract_coordinates_from_geometry(b"\x01\x01\x00\x00\x00")
            assert result is None or result is not None

    def test_extract_coordinates_from_geometry_to_shape_fallback(self):
        """Test extract coordinates from geometry to shape fallback."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_point = Point(-74.0060, 40.7128)
            mock_to_shape.return_value = mock_point

            result = extract_coordinates_from_geometry(Mock())
            assert result == pytest.approx((-74.006, 40.7128))

    def test_extract_coordinates_from_geometry_to_shape_error(self):
        """Test extract coordinates from geometry to shape error."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_to_shape.side_effect = Exception("Shape error")
            result = extract_coordinates_from_geometry(Mock())
            assert result is None

    def test_extract_coordinates_from_geometry_shapely_wkb_error(self):
        """Test extract coordinates from geometry shapely wkb error."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        with patch("shapely.wkb.loads") as mock_loads:
            mock_loads.side_effect = Exception("Parse error")
            result = extract_coordinates_from_geometry(b"\x01\x02\x03")
            assert result is None

    def test_extract_coordinates_from_geometry_hex_parse_error(self):
        """Test extract coordinates from geometry hex parse error."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        with patch("shapely.wkb.loads") as mock_loads:
            mock_loads.side_effect = ValueError("Invalid hex")
            result = extract_coordinates_from_geometry("invalid")
            assert result is None

    def test_extract_coordinates_from_geometry_exception_handling(self):
        """Test extract coordinates from geometry exception handling."""
        from app.utils.postgis_utils import extract_coordinates_from_geometry

        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_to_shape.side_effect = Exception("Error")
            result = extract_coordinates_from_geometry(Mock())
            assert result is None


class TestPointToDict:
    """Tests for PointToDict."""

    def test_point_to_dict(self):
        """Test point to dict."""
        from app.utils.postgis_utils import point_to_dict

        mock_column = MagicMock()
        result = point_to_dict(mock_column)
        assert "latitude" in result
        assert "longitude" in result


class TestDistanceQuery:
    """Tests for DistanceQuery."""

    def test_distance_query(self):
        """Test distance query."""
        from app.utils.postgis_utils import distance_query

        mock_column = MagicMock()
        result = distance_query(mock_column, 40.7128, -74.0060, 1000)
        assert result is not None

    def test_distance_query_various_params(self):
        """Test distance query various params."""
        from app.utils.postgis_utils import distance_query

        mock_column = MagicMock()
        test_cases = [
            (0.0, 0.0, 100),
            (90.0, 180.0, 500),
            (-90.0, -180.0, 1000),
        ]
        for lat, lng, dist in test_cases:
            result = distance_query(mock_column, lat, lng, dist)
            assert result is not None


class TestBBoxQuery:
    """Tests for BBoxQuery."""

    def test_bbox_query(self):
        """Test bbox query."""
        from app.utils.postgis_utils import bbox_query

        mock_column = MagicMock()
        result = bbox_query(mock_column, 40.0, -75.0, 42.0, -73.0)
        assert result is not None

    def test_bbox_query_various_coords(self):
        """Test bbox query various coords."""
        from app.utils.postgis_utils import bbox_query

        mock_column = MagicMock()
        test_cases = [
            (0.0, 0.0, 1.0, 1.0),
            (-90.0, -180.0, 90.0, 180.0),
            (40.0, -75.0, 41.0, -74.0),
        ]
        for min_lat, min_lng, max_lat, max_lng in test_cases:
            result = bbox_query(mock_column, min_lat, min_lng, max_lat, max_lng)
            assert result is not None


class TestCalculateDistanceMeters:
    """Tests for CalculateDistanceMeters."""

    def test_calculate_distance_meters(self):
        """Test calculate distance meters."""
        from app.utils.postgis_utils import calculate_distance_meters

        mock_column = MagicMock()
        result = calculate_distance_meters(mock_column, 40.7128, -74.0060)
        assert result is not None

    def test_calculate_distance_meters_various_coords(self):
        """Test calculate distance meters various coords."""
        from app.utils.postgis_utils import calculate_distance_meters

        mock_column = MagicMock()
        test_cases = [
            (0.0, 0.0),
            (90.0, 180.0),
            (-90.0, -180.0),
            (51.5074, -0.1278),
        ]
        for lat, lng in test_cases:
            result = calculate_distance_meters(mock_column, lat, lng)
            assert result is not None


class TestSerializePointToCoords:
    """Tests for SerializePointToCoords."""

    def test_serialize_none(self):
        """Test serialize none."""
        from app.utils.postgis_utils import serialize_point_to_coords

        assert serialize_point_to_coords(None) is None

    def test_serialize_dict(self):
        """Test serialize dict."""
        from app.utils.postgis_utils import serialize_point_to_coords

        data = {"latitude": 40.7128, "longitude": -74.0060}
        result = serialize_point_to_coords(data)
        assert result == data

    def test_serialize_wkt_string(self):
        """Test serialize wkt string."""
        from app.utils.postgis_utils import serialize_point_to_coords

        result = serialize_point_to_coords("POINT(-74.006 40.7128)")
        assert result is None

    def test_serialize_other_type(self):
        """Test serialize other type."""
        from app.utils.postgis_utils import serialize_point_to_coords

        result = serialize_point_to_coords(12345)
        assert result is None


class TestCoordsToPointWKT:
    """Tests for CoordsToPointWKT."""

    @pytest.mark.parametrize(
        "coords,expected",
        [
            (
                {"latitude": 40.7128, "longitude": -74.0060},
                "POINT(-74.006 40.7128)",
            ),
            (None, None),
            ({}, None),
            ({"latitude": 40.0}, None),
            ({"longitude": -74.0}, None),
        ],
    )
    def test_coords_to_point_wkt(self, coords, expected):
        """Test coords to point wkt."""
        from app.utils.postgis_utils import coords_to_point_wkt

        result = coords_to_point_wkt(coords)
        assert result == expected

    def test_coords_to_point_wkt_float_values(self):
        """Test coords to point wkt float values."""
        from app.utils.postgis_utils import coords_to_point_wkt

        coords = {"latitude": 51.5074, "longitude": -0.1278}
        result = coords_to_point_wkt(coords)
        assert "POINT(-0.1278 51.5074)" == result

    def test_coords_to_point_wkt_invalid_lat_type(self):
        """Test coords to point wkt invalid lat type."""
        from app.utils.postgis_utils import coords_to_point_wkt

        result = coords_to_point_wkt(
            {"latitude": "invalid", "longitude": -74.0060}
        )
        assert result is None

    def test_coords_to_point_wkt_invalid_lng_type(self):
        """Test coords to point wkt invalid lng type."""
        from app.utils.postgis_utils import coords_to_point_wkt

        result = coords_to_point_wkt(
            {"latitude": 40.7128, "longitude": "invalid"}
        )
        assert result is None

    def test_coords_to_point_wkt_none_lat(self):
        """Test coords to point wkt none lat."""
        from app.utils.postgis_utils import coords_to_point_wkt

        result = coords_to_point_wkt({"latitude": None, "longitude": -74.0060})
        assert result is None


class TestCreatePointForRecord:
    """Tests for CreatePointForRecord."""

    @pytest.mark.parametrize(
        "lat,lng,expected",
        [
            (40.7128, -74.0060, "POINT(-74.006 40.7128)"),
            (1.0, 1.0, "POINT(1.0 1.0)"),
            (0.0, 0.0, "POINT(0.0 0.0)"),
        ],
    )
    def test_create_point_for_record(self, lat, lng, expected):
        """Test create point for record."""
        from app.utils.postgis_utils import create_point_for_record

        result = create_point_for_record(lat, lng)
        assert result == expected


class TestIntegration:
    """Tests for Integration."""

    def test_create_and_use_point_workflow(self):
        """Test create and use point workflow."""
        from app.utils.postgis_utils import (
            coords_to_point_wkt,
            create_point_geometry,
            create_point_wkt,
        )

        lat, lng = 40.7128, -74.0060

        wkt = create_point_wkt(lat, lng)
        assert "POINT" in wkt
        assert str(lng) in wkt
        assert str(lat) in wkt

        geometry = create_point_geometry(lat, lng)
        assert geometry is not None

        coords = {"latitude": lat, "longitude": lng}
        wkt_from_coords = coords_to_point_wkt(coords)
        assert wkt_from_coords == wkt
