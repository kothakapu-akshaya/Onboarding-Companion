#!/usr/bin/env python3
"""User Role Management Script.

This script provides comprehensive user role management for the Indic
languages corpus application:
- List all users and their assigned roles
- List all available roles in the system
- Find users by phone number or email
- Assign roles to users (replace existing roles)
- Add roles to users (keep existing roles)
- Remove specific roles from users
- Clear all roles from a user

Usage Examples:
    python manage_user_roles.py list-users
    python manage_user_roles.py list-roles
    python manage_user_roles.py find-user --phone 1234567890
    python manage_user_roles.py find-user --email user@example.com
    python manage_user_roles.py assign-role user@example.com admin
python manage_user_roles.py assign-multiple-roles \
    user@example.com admin reviewer
    python manage_user_roles.py add-role user@example.com reviewer
python manage_user_roles.py add-multiple-roles \
    user@example.com reviewer user
    python manage_user_roles.py remove-role user@example.com user
    python manage_user_roles.py clear-roles user@example.com
"""

import argparse
import os
import sys
from typing import Any

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.associations import UserRoleLink
from app.models.role import Role, RoleEnum
from app.models.user import User


def get_database_session() -> Session:
    """Get a database session."""
    return Session(engine)


def list_all_users() -> None:
    """List all users and their roles."""
    print("👥 All Users and Their Roles")
    print("=" * 60)

    with get_database_session() as session:
        users = session.exec(select(User)).all()

        if not users:
            print("No users found in the database.")
            return

        for user in users:
            # Get user roles
            role_links = session.exec(
                select(UserRoleLink).where(UserRoleLink.user_id == user.id)
            ).all()

            role_names = []
            for link in role_links:
                role = session.exec(
                    select(Role).where(Role.id == link.role_id)
                ).first()
                if role:
                    role_names.append(role.name.value)

            roles_str = (
                ", ".join(role_names) if role_names else "No roles assigned"
            )

            print(f"📧 {user.email or 'No email'}")
            print(f"   📱 Phone: {user.phone}")
            print(f"   👤 Name: {user.name}")
            print(f"   🔑 Roles: {roles_str}")
            print(f"   ✅ Active: {user.is_active}")
            print(f"   🆔 ID: {user.id}")
            print("-" * 60)


def list_all_roles() -> None:
    """List all available roles."""
    print("🔑 Available Roles")
    print("=" * 40)

    with get_database_session() as session:
        roles = session.exec(select(Role)).all()

        if not roles:
            print("No roles found in the database.")
            return

        for role in roles:
            print(f"🔹 {role.name.value}")
            print(f"   📝 Description: {role.description or 'No description'}")
            print(f"   🆔 ID: {role.id}")
            print("-" * 40)


def find_user_by_phone(phone: str) -> User | None:
    """Find a user by phone number."""
    with get_database_session() as session:
        return session.exec(select(User).where(User.phone == phone)).first()


def find_user_by_email(email: str) -> User | None:
    """Find a user by email address."""
    with get_database_session() as session:
        return session.exec(select(User).where(User.email == email)).first()


def find_user_command(
    phone: str | None = None, email: str | None = None
) -> None:
    """Find a user by phone or email."""
    if not phone and not email:
        print("❌ Error: Please provide either --phone or --email")
        return

    user = None
    search_type = ""
    search_value = ""

    if phone:
        user = find_user_by_phone(phone)
        search_type = "phone"
        search_value = phone
    elif email:
        user = find_user_by_email(email)
        search_type = "email"
        search_value = email

    print(f"🔍 Searching for user by {search_type}: {search_value}")
    print("=" * 60)

    if not user:
        print(f"❌ No user found with {search_type}: {search_value}")
        return

    # Display user info
    print("✅ User found!")
    print(f"   📧 Email: {user.email or 'No email'}")
    print(f"   📱 Phone: {user.phone}")
    print(f"   👤 Name: {user.name}")
    print(f"   ✅ Active: {user.is_active}")
    print(f"   🆔 ID: {user.id}")

    # Display roles
    with get_database_session() as session:
        role_links = session.exec(
            select(UserRoleLink).where(UserRoleLink.user_id == user.id)
        ).all()

        if role_links:
            print("   🔑 Roles:")
            for link in role_links:
                role = session.exec(
                    select(Role).where(Role.id == link.role_id)
                ).first()
                if role:
                    print(f"      - {role.name.value}")
        else:
            print("   🔑 Roles: No roles assigned")


def get_user_identifier(identifier: str) -> User | None:
    """Get user by email or phone number."""
    # Try to find by email first
    user = find_user_by_email(identifier)
    if user:
        return user

    # Try to find by phone number
    user = find_user_by_phone(identifier)
    return user


def assign_role_to_user(user_identifier: str, role_name: str) -> None:
    """Assign a role to a user (replaces existing roles)."""
    print(f"🔄 Assigning role '{role_name}' to user: {user_identifier}")
    print("=" * 60)

    # Find user
    user = get_user_identifier(user_identifier)
    if not user:
        print(f"❌ User not found: {user_identifier}")
        return

    # Validate role
    try:
        role_enum = RoleEnum(role_name)
    except ValueError:
        print(f"❌ Invalid role: {role_name}")
        print(f"   Valid roles: {', '.join([r.value for r in RoleEnum])}")
        return

    with get_database_session() as session:
        # Find the role
        role = session.exec(select(Role).where(Role.name == role_enum)).first()
        if not role:
            print(f"❌ Role not found in database: {role_name}")
            return

        # Remove all existing roles
        existing_links = session.exec(
            select(UserRoleLink).where(UserRoleLink.user_id == user.id)
        ).all()

        for link in existing_links:
            session.delete(link)

        # Add new role
        new_link = UserRoleLink(user_id=user.id, role_id=role.id)
        session.add(new_link)
        session.commit()

        print(f"✅ Successfully assigned role '{role_name}' to {user.name}")
        print(f"   📧 User: {user.email or user.phone}")


def assign_multiple_roles_to_user(
    user_identifier: str, role_names: list[str]
) -> None:
    """Assign multiple roles to a user (replaces all existing roles)."""
    print(f"🔄 Assigning multiple roles to user: {user_identifier}")
    print(f"   🎯 Roles: {', '.join(role_names)}")
    print("=" * 60)

    # Find user
    user = get_user_identifier(user_identifier)
    if not user:
        print(f"❌ User not found: {user_identifier}")
        return

    # Validate all roles first
    valid_roles = []
    invalid_roles = []

    for role_name in role_names:
        try:
            role_enum = RoleEnum(role_name)
            valid_roles.append(role_enum)
        except ValueError:
            invalid_roles.append(role_name)

    if invalid_roles:
        print(f"❌ Invalid roles found: {', '.join(invalid_roles)}")
        print(f"   Valid roles: {', '.join([r.value for r in RoleEnum])}")
        return

    with get_database_session() as session:
        # Find all roles in database
        db_roles = []
        missing_roles = []

        for role_enum in valid_roles:
            role = session.exec(
                select(Role).where(Role.name == role_enum)
            ).first()
            if role:
                db_roles.append(role)
            else:
                missing_roles.append(role_enum.value)

        if missing_roles:
            print(f"❌ Roles not found in database: {', '.join(missing_roles)}")
            return

        # Remove all existing roles
        existing_links = session.exec(
            select(UserRoleLink).where(UserRoleLink.user_id == user.id)
        ).all()

        removed_count = len(existing_links)
        for link in existing_links:
            session.delete(link)

        # Add new roles
        for role in db_roles:
            new_link = UserRoleLink(user_id=user.id, role_id=role.id)
            session.add(new_link)

        session.commit()

        print(
            f"✅ Successfully assigned {len(db_roles)} role(s) to {user.name}"
        )
        print(f"   📧 User: {user.email or user.phone}")
        print(f"   🔄 Replaced {removed_count} existing role(s)")
        print(f"   🎯 New roles: {', '.join(role_names)}")


def add_role_to_user(user_identifier: str, role_name: str) -> None:
    """Add a role to a user (keeps existing roles)."""
    print(f"➕ Adding role '{role_name}' to user: {user_identifier}")
    print("=" * 60)

    # Find user
    user = get_user_identifier(user_identifier)
    if not user:
        print(f"❌ User not found: {user_identifier}")
        return

    # Validate role
    try:
        role_enum = RoleEnum(role_name)
    except ValueError:
        print(f"❌ Invalid role: {role_name}")
        print(f"   Valid roles: {', '.join([r.value for r in RoleEnum])}")
        return

    with get_database_session() as session:
        # Find the role
        role = session.exec(select(Role).where(Role.name == role_enum)).first()
        if not role:
            print(f"❌ Role not found in database: {role_name}")
            return

        # Check if user already has this role
        existing_link = session.exec(
            select(UserRoleLink).where(
                UserRoleLink.user_id == user.id, UserRoleLink.role_id == role.id
            )
        ).first()

        if existing_link:
            print(f"ℹ️  User already has role '{role_name}'")
            return

        # Add new role
        new_link = UserRoleLink(user_id=user.id, role_id=role.id)
        session.add(new_link)
        session.commit()

        print(f"✅ Successfully added role '{role_name}' to {user.name}")
        print(f"   📧 User: {user.email or user.phone}")


def add_multiple_roles_to_user(
    user_identifier: str, role_names: list[str]
) -> None:
    """Add multiple roles to a user (keeps existing roles)."""
    print(f"➕ Adding multiple roles to user: {user_identifier}")
    print(f"   🎯 Roles: {', '.join(role_names)}")
    print("=" * 60)

    # Find user
    user = get_user_identifier(user_identifier)
    if not user:
        print(f"❌ User not found: {user_identifier}")
        return

    # Validate all roles first
    valid_roles = []
    invalid_roles = []

    for role_name in role_names:
        try:
            role_enum = RoleEnum(role_name)
            valid_roles.append(role_enum)
        except ValueError:
            invalid_roles.append(role_name)

    if invalid_roles:
        print(f"❌ Invalid roles found: {', '.join(invalid_roles)}")
        print(f"   Valid roles: {', '.join([r.value for r in RoleEnum])}")
        return

    with get_database_session() as session:
        # Find all roles in database
        db_roles = []
        missing_roles = []

        for role_enum in valid_roles:
            role = session.exec(
                select(Role).where(Role.name == role_enum)
            ).first()
            if role:
                db_roles.append(role)
            else:
                missing_roles.append(role_enum.value)

        if missing_roles:
            print(f"❌ Roles not found in database: {', '.join(missing_roles)}")
            return

        # Check which roles user already has and which are new
        existing_role_ids = set()
        existing_links = session.exec(
            select(UserRoleLink).where(UserRoleLink.user_id == user.id)
        ).all()

        for link in existing_links:
            existing_role_ids.add(link.role_id)

        # Add only new roles
        added_roles = []
        skipped_roles = []

        for role in db_roles:
            if role.id not in existing_role_ids:
                new_link = UserRoleLink(user_id=user.id, role_id=role.id)
                session.add(new_link)
                added_roles.append(role.name.value)
            else:
                skipped_roles.append(role.name.value)

        session.commit()

        print(f"✅ Successfully processed role additions for {user.name}")
        print(f"   📧 User: {user.email or user.phone}")

        if added_roles:
            print(f"   ➕ Added roles: {', '.join(added_roles)}")

        if skipped_roles:
            print(f"   ℹ️  Already had roles: {', '.join(skipped_roles)}")

        if not added_roles and not skipped_roles:
            print("   ℹ️  No changes made")


def remove_role_from_user(user_identifier: str, role_name: str) -> None:
    """Remove a specific role from a user."""
    print(f"➖ Removing role '{role_name}' from user: {user_identifier}")
    print("=" * 60)

    # Find user
    user = get_user_identifier(user_identifier)
    if not user:
        print(f"❌ User not found: {user_identifier}")
        return

    # Validate role
    try:
        role_enum = RoleEnum(role_name)
    except ValueError:
        print(f"❌ Invalid role: {role_name}")
        print(f"   Valid roles: {', '.join([r.value for r in RoleEnum])}")
        return

    with get_database_session() as session:
        # Find the role
        role = session.exec(select(Role).where(Role.name == role_enum)).first()
        if not role:
            print(f"❌ Role not found in database: {role_name}")
            return

        # Find and remove the role link
        existing_link = session.exec(
            select(UserRoleLink).where(
                UserRoleLink.user_id == user.id, UserRoleLink.role_id == role.id
            )
        ).first()

        if not existing_link:
            print(f"ℹ️  User does not have role '{role_name}'")
            return

        session.delete(existing_link)
        session.commit()

        print(f"✅ Successfully removed role '{role_name}' from {user.name}")
        print(f"   📧 User: {user.email or user.phone}")


def clear_all_roles_from_user(user_identifier: str) -> None:
    """Remove all roles from a user."""
    print(f"🗑️  Clearing all roles from user: {user_identifier}")
    print("=" * 60)

    # Find user
    user = get_user_identifier(user_identifier)
    if not user:
        print(f"❌ User not found: {user_identifier}")
        return

    with get_database_session() as session:
        # Remove all role links
        existing_links = session.exec(
            select(UserRoleLink).where(UserRoleLink.user_id == user.id)
        ).all()

        if not existing_links:
            print("ℹ️  User has no roles to clear")
            return

        for link in existing_links:
            session.delete(link)

        session.commit()

        print(f"✅ Successfully cleared all roles from {user.name}")
        print(f"   📧 User: {user.email or user.phone}")
        print(f"   🗑️  Removed {len(existing_links)} role(s)")


def main() -> None:
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Indic languages Corpus User Role Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_user_roles.py list-users
  python manage_user_roles.py list-roles
  python manage_user_roles.py find-user --phone 1234567890
  python manage_user_roles.py find-user --email user@example.com
  python manage_user_roles.py assign-role user@example.com admin
  python manage_user_roles.py assign-multiple-roles \
      user@example.com admin reviewer
  python manage_user_roles.py add-role user@example.com reviewer
  python manage_user_roles.py add-multiple-roles user@example.com reviewer user
  python manage_user_roles.py remove-role user@example.com user
  python manage_user_roles.py clear-roles user@example.com

Available roles: admin, user, reviewer
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List users command
    subparsers.add_parser("list-users", help="List all users and their roles")

    # List roles command
    subparsers.add_parser("list-roles", help="List all available roles")

    # Find user command
    find_parser = subparsers.add_parser(
        "find-user", help="Find a user by phone or email"
    )
    find_parser.add_argument("--phone", help="Phone number to search for")
    find_parser.add_argument("--email", help="Email address to search for")

    # Assign role command (replace existing)
    assign_parser = subparsers.add_parser(
        "assign-role", help="Assign a role to user (replaces existing roles)"
    )
    assign_parser.add_argument("user", help="User email or phone number")
    assign_parser.add_argument("role", help="Role name (admin, user, reviewer)")

    # Assign multiple roles command (replace existing)
    assign_multiple_parser = subparsers.add_parser(
        "assign-multiple-roles",
        help=("Assign multiple roles to user (replaces existing roles)"),
    )
    assign_multiple_parser.add_argument(
        "user", help="User email or phone number"
    )
    assign_multiple_parser.add_argument(
        "roles", nargs="+", help="Role names (admin, user, reviewer)"
    )

    # Add role command (keep existing)
    add_parser = subparsers.add_parser(
        "add-role", help="Add a role to user (keeps existing roles)"
    )
    add_parser.add_argument("user", help="User email or phone number")
    add_parser.add_argument("role", help="Role name (admin, user, reviewer)")

    # Add multiple roles command (keep existing)
    add_multiple_parser = subparsers.add_parser(
        "add-multiple-roles",
        help="Add multiple roles to user (keeps existing roles)",
    )
    add_multiple_parser.add_argument("user", help="User email or phone number")
    add_multiple_parser.add_argument(
        "roles", nargs="+", help="Role names (admin, user, reviewer)"
    )

    # Remove role command
    remove_parser = subparsers.add_parser(
        "remove-role", help="Remove a specific role from user"
    )
    remove_parser.add_argument("user", help="User email or phone number")
    remove_parser.add_argument("role", help="Role name (admin, user, reviewer)")

    # Clear roles command
    clear_parser = subparsers.add_parser(
        "clear-roles", help="Remove all roles from user"
    )
    clear_parser.add_argument("user", help="User email or phone number")

    args: Any = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    print("🔑 Indic languages - User Role Management")
    print("=" * 60)

    try:
        if args.command == "list-users":
            list_all_users()
        elif args.command == "list-roles":
            list_all_roles()
        elif args.command == "find-user":
            find_user_command(args.phone, args.email)
        elif args.command == "assign-role":
            assign_role_to_user(args.user, args.role)
        elif args.command == "assign-multiple-roles":
            assign_multiple_roles_to_user(args.user, args.roles)
        elif args.command == "add-role":
            add_role_to_user(args.user, args.role)
        elif args.command == "add-multiple-roles":
            add_multiple_roles_to_user(args.user, args.roles)
        elif args.command == "remove-role":
            remove_role_from_user(args.user, args.role)
        elif args.command == "clear-roles":
            clear_all_roles_from_user(args.user)
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
