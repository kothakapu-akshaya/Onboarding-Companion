"""Tests for create_categories utility functions."""

import json
from unittest.mock import Mock, patch

from requests.exceptions import RequestException


class TestCreateCategory:
    """Tests for create_category function."""

    @patch("app.utils.create_categories.requests.post")
    def test_create_category_success(self, mock_post):
        """Test create category success."""
        from app.utils.create_categories import create_category

        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        category_data = {"name": "Test Category", "description": "Test"}
        result = create_category(category_data, "test_token")

        assert result is True
        mock_post.assert_called_once()

    @patch("app.utils.create_categories.requests.post")
    def test_create_category_bad_request(self, mock_post):
        """Test create category bad request."""
        from app.utils.create_categories import create_category

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Validation error"}
        mock_post.return_value = mock_response

        category_data = {"name": "Test Category"}
        result = create_category(category_data, "test_token")

        assert result is False

    @patch("app.utils.create_categories.requests.post")
    def test_create_category_server_error(self, mock_post):
        """Test create category server error."""
        from app.utils.create_categories import create_category

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        category_data = {"name": "Test Category"}
        result = create_category(category_data, "test_token")

        assert result is False

    @patch("app.utils.create_categories.requests.post")
    def test_create_category_network_error(self, mock_post):
        """Test create category network error."""
        from app.utils.create_categories import create_category

        mock_post.side_effect = RequestException("Network error")

        category_data = {"name": "Test Category"}
        result = create_category(category_data, "test_token")

        assert result is False


class TestCreateCategoriesFromJson:
    """Tests for create_categories_from_json function."""

    def test_create_categories_from_json_no_token(self):
        """Test create categories from json no token."""
        from app.utils.create_categories import create_categories_from_json

        result = create_categories_from_json(token=None)

        assert result is None

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_create_categories_from_json_file_not_found(self, mock_open):
        """Test create categories from json file not found."""
        from app.utils.create_categories import create_categories_from_json

        result = create_categories_from_json(
            json_file_path="/nonexistent/path.json", token="test_token"
        )

        assert result is None

    @patch("builtins.open")
    @patch("json.load")
    def test_create_categories_from_json_invalid_json(
        self, mock_json_load, mock_open
    ):
        """Test create categories from json invalid json."""
        from app.utils.create_categories import create_categories_from_json

        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        result = create_categories_from_json(
            json_file_path="/path/to/invalid.json", token="test_token"
        )

        assert result is None

    def test_create_categories_from_json_no_data_source(self):
        """Test create categories from json no data source."""
        from app.utils.create_categories import create_categories_from_json

        result = create_categories_from_json(token="test_token")

        assert result is None

    def test_create_categories_from_json_no_categories(self):
        """Test create categories from json no categories."""
        from app.utils.create_categories import create_categories_from_json

        result = create_categories_from_json(
            categories_dict={"other_key": "value"}, token="test_token"
        )

        assert result is None

    @patch("app.utils.create_categories.create_category")
    def test_create_categories_from_json_with_categories(
        self, mock_create_category
    ):
        """Test create categories from json with categories."""
        from app.utils.create_categories import create_categories_from_json

        mock_create_category.side_effect = [True, False, True]

        categories_data = {
            "categories": [
                {"name": "Category 1"},
                {"name": "Category 2"},
                {"name": "Category 3"},
            ]
        }

        create_categories_from_json(
            categories_dict=categories_data, token="test_token"
        )

        assert mock_create_category.call_count == 3


class TestMain:
    """Tests for main function."""

    @patch("app.utils.create_categories.create_categories_from_json")
    @patch("builtins.open")
    @patch("json.load")
    def test_main(self, mock_json_load, mock_open, mock_create_categories):
        """Test main."""
        from app.utils.create_categories import main

        mock_json_load.return_value = {
            "categories": [{"name": "Test Category"}]
        }

        main()

        mock_create_categories.assert_called_once()
