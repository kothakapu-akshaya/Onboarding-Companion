"""Tests for app/db/session.py."""

from unittest.mock import MagicMock, patch

from sqlalchemy.engine import Engine

from app.db.session import (
    engine,
    get_db,
    get_session,
)


class TestEngine:
    """Test database engine configuration."""

    def test_engine_exists(self):
        """Test engine is created."""
        assert engine is not None
        assert isinstance(engine, Engine)

    def test_engine_has_pool_config(self):
        """Test engine has pool configuration."""
        assert engine.pool.size() == 10

    def test_engine_pool_pre_ping_enabled(self):
        """Test pool_pre_ping is enabled."""
        assert engine.pool._pre_ping is True

    def test_engine_pool_recycle_set(self):
        """Test pool_recycle is set to 3600."""
        assert engine.pool._recycle == 3600

    def test_engine_pool_timeout_set(self):
        """Test pool_timeout is set."""
        assert engine.pool._timeout == 30


class TestGetSession:
    """Test get_session dependency."""

    def test_get_session_is_generator(self):
        """Test get_session is a generator function."""
        import types

        result = get_session()
        assert isinstance(result, types.GeneratorType)

    def test_get_session_yields_session(self):
        """Test get_session yields a session."""
        with patch("app.db.session.Session") as mock_session:
            mock_engine = MagicMock()
            with patch("app.db.session.engine", mock_engine):
                mock_session_instance = MagicMock()
                mock_session.return_value.__enter__ = MagicMock(
                    return_value=mock_session_instance
                )
                mock_session.return_value.__exit__ = MagicMock(
                    return_value=False
                )

                gen = get_session()
                session = next(gen)
                assert session is mock_session_instance


class TestGetDb:
    """Test get_db dependency (alias for get_session)."""

    def test_get_db_is_generator(self):
        """Test get_db is a generator function."""
        import types

        result = get_db()
        assert isinstance(result, types.GeneratorType)

    def test_get_db_yields_session(self):
        """Test get_db yields a session."""
        with patch("app.db.session.Session") as mock_session:
            mock_engine = MagicMock()
            with patch("app.db.session.engine", mock_engine):
                mock_session_instance = MagicMock()
                mock_session.return_value.__enter__ = MagicMock(
                    return_value=mock_session_instance
                )
                mock_session.return_value.__exit__ = MagicMock(
                    return_value=False
                )

                gen = get_db()
                session = next(gen)
                assert session is mock_session_instance


class TestCreateDbAndTables:
    """Test create_db_and_tables function."""

    def test_create_db_and_tables_function_exists(self):
        """Test function exists and is callable."""
        from app.db.session import create_db_and_tables

        assert callable(create_db_and_tables)

    @patch("app.db.session.SQLModel.metadata.create_all")
    def test_creates_only_onboarding_tables(self, mock_create_all):
        """Test startup initialization is scoped to onboarding tables."""
        from app.db.session import (
            OnboardingEvidence,
            OnboardingProgress,
            create_db_and_tables,
            engine,
        )

        create_db_and_tables()

        mock_create_all.assert_called_once_with(
            engine,
            tables=[
                OnboardingProgress.__table__,
                OnboardingEvidence.__table__,
            ],
            checkfirst=True,
        )
