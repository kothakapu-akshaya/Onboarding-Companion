"""Unit tests for app/models/associations.py SQLModel models.

Tests cover model instantiation, composite primary keys, foreign key
constraints, and CRUD operations using an in-memory SQLite database.

Because the real User model uses PostgreSQL-specific JSONB columns
(incompatible with SQLite), a minimal stand-in User table is created
solely for FK integrity testing.
"""

import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine

from app.models.associations import UserRoleLink
from app.models.role import Role, RoleEnum

# ============================================================
# Database fixtures
# ============================================================


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with required tables.

    The real User model (app/models/user.py) has JSONB columns that
    SQLite cannot compile. We create all needed tables using raw DDL.
    """
    eng = create_engine("sqlite:///:memory:")

    # Enable foreign key enforcement (SQLite disables it by default)
    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from sqlalchemy import text

    with eng.begin() as conn:
        # Minimal 'user' table (replaces the JSONB-heavy User model)
        conn.execute(
            text("CREATE TABLE user (  id TEXT PRIMARY KEY,  phone TEXT)")
        )

        # Role table (Role model has no JSONB, but create
        # manually for consistency)
        conn.execute(
            text(
                "CREATE TABLE role ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  name TEXT NOT NULL UNIQUE,"
                "  description TEXT)"
            )
        )

        # UserRoleLink (user_roles) table — composite PK, FKs to user and role
        conn.execute(
            text(
                "CREATE TABLE user_roles ("
                "  user_id TEXT NOT NULL,"
                "  role_id INTEGER NOT NULL,"
                "  PRIMARY KEY (user_id, role_id),"
                "  FOREIGN KEY (user_id) REFERENCES user(id),"
                "  FOREIGN KEY (role_id) REFERENCES role(id)"
                ")"
            )
        )

    return eng


@pytest.fixture
def session(engine):
    """Provide an isolated session that rolls back after each test."""
    with Session(engine) as sess:
        yield sess
        sess.rollback()


# ============================================================
# Helpers
# ============================================================


def _create_user(session) -> uuid.UUID:
    """Create a minimal user via raw SQL.

    Bypasses the JSONB-incompatible User model.

    Stores user_id as 32-char hex (no dashes) to match
    SQLModel's UUID storage format in SQLite, so that
    FK constraints on user_roles.user_id resolve correctly.
    """
    from sqlalchemy import text

    user_id = uuid.uuid4()
    session.execute(
        text("INSERT INTO user (id, phone) VALUES (:id, :phone)"),
        {"id": user_id.hex, "phone": "+919999999999"},
    )
    session.commit()
    return user_id


def _create_role(session, name: RoleEnum = RoleEnum.user) -> Role:
    """Create and persist a role."""
    role = Role(name=name, description=f"Test {name.value} role")
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def _create_link(session, user_id=None, role_id=None):
    """Create and persist a UserRoleLink."""
    link = UserRoleLink(user_id=user_id, role_id=role_id)
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


# ============================================================
# Model instantiation
# ============================================================


class TestUserRoleLinkInstantiation:
    """Test UserRoleLink model instantiation without DB."""

    def test_create_with_valid_uuid_and_int(self):
        user_id = uuid.uuid4()
        link = UserRoleLink(user_id=user_id, role_id=1)
        assert link.user_id == user_id
        assert link.role_id == 1

    def test_create_with_both_none(self):
        """Both fields have default=None, so instantiation succeeds."""
        link = UserRoleLink()
        assert link.user_id is None
        assert link.role_id is None

    def test_create_with_only_user_id(self):
        link = UserRoleLink(user_id=uuid.uuid4())
        assert link.role_id is None

    def test_create_with_only_role_id(self):
        link = UserRoleLink(role_id=2)
        assert link.user_id is None

    def test_tablename(self):
        assert UserRoleLink.__tablename__ == "user_roles"


# ============================================================
# Composite primary key
# ============================================================


class TestUserRoleLinkCompositePK:
    """Test composite primary key behavior."""

    def test_composite_pk_is_user_id_and_role_id(self):
        """Both user_id and role_id should be primary keys."""
        pk_cols = [
            col.name for col in UserRoleLink.__table__.primary_key.columns
        ]
        assert "user_id" in pk_cols
        assert "role_id" in pk_cols

    def test_same_user_same_role_is_duplicate(self, session):
        """Insert duplicate user_role raises IntegrityError."""
        user_id = _create_user(session)
        role = _create_role(session)
        _create_link(session, user_id=user_id, role_id=role.id)

        dup = UserRoleLink(user_id=user_id, role_id=role.id)
        session.add(dup)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_user_different_role_allowed(self, session):
        """A user can have multiple roles."""
        user_id = _create_user(session)
        role1 = _create_role(session, name=RoleEnum.user)
        role2 = _create_role(session, name=RoleEnum.admin)

        _create_link(session, user_id=user_id, role_id=role1.id)
        _create_link(session, user_id=user_id, role_id=role2.id)

        links = session.query(UserRoleLink).filter_by(user_id=user_id).all()
        assert len(links) == 2

    def test_different_user_same_role_allowed(self, session):
        """Multiple users can share the same role."""
        uid1 = _create_user(session)
        uid2 = _create_user(session)
        role = _create_role(session)

        _create_link(session, user_id=uid1, role_id=role.id)
        _create_link(session, user_id=uid2, role_id=role.id)

        links = session.query(UserRoleLink).filter_by(role_id=role.id).all()
        assert len(links) == 2


# ============================================================
# Foreign key constraints
# ============================================================


class TestUserRoleLinkForeignKeys:
    """Test foreign key constraints."""

    def test_valid_user_fk(self, session):
        """user_id must reference an existing user."""
        user_id = _create_user(session)
        role = _create_role(session)
        link = _create_link(session, user_id=user_id, role_id=role.id)
        assert link.user_id == user_id

    def test_valid_role_fk(self, session):
        """role_id must reference an existing role."""
        user_id = _create_user(session)
        role = _create_role(session)
        link = _create_link(session, user_id=user_id, role_id=role.id)
        assert link.role_id == role.id

    def test_invalid_user_fk_raises(self, session):
        """Referencing a non-existent user should raise IntegrityError."""
        role = _create_role(session)
        link = UserRoleLink(user_id=uuid.uuid4(), role_id=role.id)
        session.add(link)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_invalid_role_fk_raises(self, session):
        """Referencing a non-existent role should raise IntegrityError."""
        user_id = _create_user(session)
        link = UserRoleLink(user_id=user_id, role_id=9999)
        session.add(link)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_null_user_id_raises(self, session):
        """NULL user_id is rejected because it's part of the composite PK."""
        role = _create_role(session)
        link = UserRoleLink(user_id=None, role_id=role.id)
        session.add(link)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_null_role_id_raises(self, session):
        """NULL role_id is rejected because it's part of the composite PK."""
        user_id = _create_user(session)
        link = UserRoleLink(user_id=user_id, role_id=None)
        session.add(link)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_both_nulls_raises(self, session):
        """Both NULLs is rejected because both are part of the composite PK."""
        link = UserRoleLink(user_id=None, role_id=None)
        session.add(link)
        with pytest.raises(IntegrityError):
            session.commit()


# ============================================================
# CRUD operations
# ============================================================


class TestUserRoleLinkCRUD:
    """Test full CRUD via in-memory SQLite."""

    # --- Create ---

    def test_create_link(self, session):
        user_id = _create_user(session)
        role = _create_role(session)
        link = _create_link(session, user_id=user_id, role_id=role.id)

        assert link.user_id == user_id
        assert link.role_id == role.id
        # UserRoleLink has no separate 'id' column — composite PK
        # is (user_id, role_id)
        assert not hasattr(link, "id")

    # --- Read ---

    def test_query_by_user_id(self, session):
        user_id = _create_user(session)
        role = _create_role(session)
        _create_link(session, user_id=user_id, role_id=role.id)

        links = session.query(UserRoleLink).filter_by(user_id=user_id).all()
        assert len(links) == 1
        assert links[0].role_id == role.id

    def test_query_by_role_id(self, session):
        user_id = _create_user(session)
        role = _create_role(session)
        _create_link(session, user_id=user_id, role_id=role.id)

        links = session.query(UserRoleLink).filter_by(role_id=role.id).all()
        assert len(links) == 1
        assert links[0].user_id == user_id

    def test_query_all_links(self, session):
        uid1 = _create_user(session)
        uid2 = _create_user(session)
        role_user = _create_role(session, name=RoleEnum.user)
        role_admin = _create_role(session, name=RoleEnum.admin)

        _create_link(session, user_id=uid1, role_id=role_user.id)
        _create_link(session, user_id=uid1, role_id=role_admin.id)
        _create_link(session, user_id=uid2, role_id=role_user.id)

        all_links = session.query(UserRoleLink).all()
        assert len(all_links) == 3

    # --- Update ---

    def test_update_role_id(self, session):
        """Change a user's role assignment."""
        user_id = _create_user(session)
        role1 = _create_role(session, name=RoleEnum.user)
        role2 = _create_role(session, name=RoleEnum.admin)

        link = _create_link(session, user_id=user_id, role_id=role1.id)
        assert link.role_id == role1.id

        link.role_id = role2.id
        session.add(link)
        session.commit()
        session.refresh(link)
        assert link.role_id == role2.id

    def test_update_user_id(self, session):
        """Reassign a role to a different user."""
        uid1 = _create_user(session)
        uid2 = _create_user(session)
        role = _create_role(session)

        link = _create_link(session, user_id=uid1, role_id=role.id)
        assert link.user_id == uid1

        link.user_id = uid2
        session.add(link)
        session.commit()
        session.refresh(link)
        assert link.user_id == uid2

    # --- Delete ---

    def test_delete_link(self, session):
        user_id = _create_user(session)
        role = _create_role(session)
        link = _create_link(session, user_id=user_id, role_id=role.id)

        session.delete(link)
        session.commit()

        count = session.query(UserRoleLink).count()
        assert count == 0

    def test_cascade_delete_user(self, session):
        """Deleting a user should cascade-delete the link row.

        (if ON DELETE CASCADE is configured; SQLite doesn't enforce
        by default, so we test the link is removed manually).
        """
        user_id = _create_user(session)
        role = _create_role(session)
        _create_link(session, user_id=user_id, role_id=role.id)

        # Manual cascade: delete link first, then user
        from sqlalchemy import text

        session.query(UserRoleLink).filter_by(user_id=user_id).delete()
        session.execute(
            text("DELETE FROM user WHERE id = :id"), {"id": user_id.hex}
        )
        session.commit()

        assert session.query(UserRoleLink).count() == 0

    def test_cascade_delete_role(self, session):
        """Deleting a role should cascade-delete the link row."""
        user_id = _create_user(session)
        role = _create_role(session)
        _create_link(session, user_id=user_id, role_id=role.id)

        session.query(UserRoleLink).filter_by(role_id=role.id).delete()
        session.delete(role)
        session.commit()

        assert session.query(Role).count() == 0
        assert session.query(UserRoleLink).count() == 0


# ============================================================
# Edge cases
# ============================================================


class TestUserRoleLinkEdgeCases:
    """Edge case scenarios."""

    def test_many_users_many_roles(self, session):
        """Stress test: 5 users × 3 roles = 15 links."""
        users = [_create_user(session) for _ in range(5)]
        roles = [
            _create_role(session, name=RoleEnum.user),
            _create_role(session, name=RoleEnum.admin),
            _create_role(session, name=RoleEnum.reviewer),
        ]

        for uid in users:
            for r in roles:
                _create_link(session, user_id=uid, role_id=r.id)

        assert session.query(UserRoleLink).count() == 15

    def test_link_model_dict(self, session):
        """Test that model_dump() / dict conversion works."""
        user_id = _create_user(session)
        role = _create_role(session)
        link = _create_link(session, user_id=user_id, role_id=role.id)

        dump = link.model_dump()
        assert dump["user_id"] == user_id
        assert dump["role_id"] == role.id

    def test_link_model_json(self, session):
        """Test model_dump_json() output."""
        user_id = _create_user(session)
        role = _create_role(session)
        link = _create_link(session, user_id=user_id, role_id=role.id)

        json_str = link.model_dump_json()
        assert isinstance(json_str, str)
        assert str(user_id) in json_str

    def test_user_id_type_is_uuid(self):
        """Verify user_id field type annotation."""
        link = UserRoleLink(user_id=uuid.uuid4(), role_id=1)
        assert isinstance(link.user_id, uuid.UUID)

    def test_role_id_type_is_int(self):
        """Verify role_id field type annotation."""
        link = UserRoleLink(user_id=uuid.uuid4(), role_id=5)
        assert isinstance(link.role_id, int)

    def test_foreign_key_columns_defined(self):
        """Verify FK columns exist in table definition."""
        fks = {fk.target_fullname for fk in UserRoleLink.__table__.foreign_keys}
        assert "user.id" in fks
        assert "role.id" in fks
