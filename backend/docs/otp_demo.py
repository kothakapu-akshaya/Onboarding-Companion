#!/usr/bin/env python3
"""Simple OTP Authentication Demo.

This script demonstrates how to use the OTP authentication API.
"""

import time

import requests

# Configuration
API_BASE = "http://localhost:8000/api/v1/auth"
TEST_PHONE = "+919177980938"  # Replace with your test phone number


def demo_otp_flow():
    """Demonstrate the complete OTP authentication flow."""
    print("🚀 OTP Authentication Demo")
    print("=" * 50)

    # Step 1: Send OTP
    print(f"📱 Sending OTP to {TEST_PHONE}...")

    send_data = {"phone": TEST_PHONE}

    try:
        response = requests.post(f"{API_BASE}/send-otp", json=send_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ OTP sent successfully!")
            print(f"   Message: {result['message']}")
            print(f"   Reference ID: {result['reference_id']}")
        else:
            print(f"❌ Failed to send OTP: {response.status_code}")
            print(f"   Error: {response.text}")
            return

    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Step 2: Get OTP from user
    print("\n📥 Check your phone for the OTP message")
    otp_code = input("Enter the OTP code: ").strip()

    if not otp_code:
        print("❌ No OTP entered. Exiting.")
        return

    # Step 3: Verify OTP
    print("\n🔐 Verifying OTP...")

    verify_data = {"phone": TEST_PHONE, "otp_code": otp_code}

    try:
        response = requests.post(f"{API_BASE}/verify-otp", json=verify_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ OTP verified successfully!")
            print(f"   Token Type: {result['token_type']}")
            print(f"   User ID: {result['user_id']}")
            print(f"   Phone: {result['phone']}")

            access_token = result["access_token"]

        else:
            print(f"❌ Failed to verify OTP: {response.status_code}")
            print(f"   Error: {response.text}")
            return

    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Step 4: Test authenticated endpoint
    print("\n👤 Testing authenticated endpoint...")

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(f"{API_BASE}/me", headers=headers)

        if response.status_code == 200:
            user_info = response.json()
            print("✅ Successfully accessed user info!")
            print(f"   User ID: {user_info['id']}")
            print(f"   Phone: {user_info['phone']}")
            print(f"   Name: {user_info.get('name', 'Not set')}")
            print(f"   Active: {user_info['is_active']}")
            print(f"   Last Login: {user_info.get('last_login_at', 'Never')}")

        else:
            print(f"❌ Failed to access user info: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n🎉 Demo completed!")
    print("=" * 50)


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n⚡ Testing Rate Limiting...")
    print("-" * 30)

    send_data = {"phone": TEST_PHONE}

    # Try to send multiple OTPs quickly
    for i in range(5):
        print(f"   Attempt {i + 1}...")

        try:
            response = requests.post(f"{API_BASE}/send-otp", json=send_data)

            if response.status_code == 200:
                print("   ✅ OTP sent")
            elif response.status_code == 429:
                print("   ⚠️  Rate limited (expected)")
                break
            else:
                print(f"   ❌ Error: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        time.sleep(0.5)  # Small delay between requests


def main():
    """Main demo function."""
    print("Choose an option:")
    print("1. Full OTP Authentication Demo")
    print("2. Rate Limiting Test")
    print("3. Both")

    choice = input("\nEnter your choice (1-3): ").strip()

    if choice == "1":
        demo_otp_flow()
    elif choice == "2":
        test_rate_limiting()
    elif choice == "3":
        demo_otp_flow()
        test_rate_limiting()
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    main()
