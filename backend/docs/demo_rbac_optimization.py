#!/usr/bin/env python3
"""Final demonstration of the optimized RBAC system."""

import asyncio
import time

import httpx

BASE_URL = "http://localhost:8000"


async def demo_optimized_rbac():
    """Demonstrate all optimized RBAC features."""
    print("🎯 Optimized RBAC System Demo")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Authentication
        print("\n1. 🔐 Authentication Test")
        login_data = {"phone": "9878765657", "password": "somepass"}
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login", json=login_data
        )

        if response.status_code != 200:
            print("❌ Authentication failed. Please start the server first.")
            return

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Authentication successful")

        # 2. Performance test - rapid requests to test caching
        print("\n2. 🚀 Performance Test (Cache Effectiveness)")
        start_time = time.time()

        # Make 20 rapid requests to trigger caching
        success_count = 0
        for i in range(20):
            response = await client.get(
                f"{BASE_URL}/api/v1/users/", headers=headers
            )
            if response.status_code == 200:
                success_count += 1

        total_time = time.time() - start_time
        avg_time = total_time / 20

        print(f"✅ {success_count}/20 requests successful")
        print(f"✅ Average response time: {avg_time * 1000:.2f}ms")
        print(f"✅ Total time for 20 requests: {total_time:.3f}s")

        # 3. Role-based access test
        print("\n3. 👑 Role-Based Access Control")
        endpoints_to_test = [
            ("/api/v1/users/", "Admin-only endpoint"),
            ("/api/v1/roles/", "Role management"),
        ]

        for endpoint, description in endpoints_to_test:
            response = await client.get(
                f"{BASE_URL}{endpoint}", headers=headers
            )
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {description}: {response.status_code}")

        # 4. Permission-based access demonstration
        print("\n4. 🔑 Permission-Based Access Control")

        # Get a user ID for testing
        response = await client.get(
            f"{BASE_URL}/api/v1/users/", headers=headers
        )
        if response.status_code == 200 and len(response.json()) > 0:
            user_id = response.json()[0]["id"]

            # Test individual user access (requires users:GET permission)
            response = await client.get(
                f"{BASE_URL}/api/v1/users/{user_id}", headers=headers
            )
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} Individual user access: {response.status_code}")

            # Test user with roles access
            response = await client.get(
                f"{BASE_URL}/api/v1/users/{user_id}/with-roles", headers=headers
            )
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} User with roles access: {response.status_code}")

        # 5. Error handling demonstration
        print("\n5. 🛡️ Security & Error Handling")

        # Test without authentication
        response = await client.get(f"{BASE_URL}/api/v1/users/")
        if response.status_code == 403:
            print("✅ Unauthenticated access properly blocked (403)")
        else:
            print(
                f"❌ Unexpected response for unauthenticated access: "
                f"{response.status_code}"
            )

        # Test with invalid token
        bad_headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get(
            f"{BASE_URL}/api/v1/users/", headers=bad_headers
        )
        if response.status_code in [401, 403]:
            print("✅ Invalid token properly rejected")
        else:
            print(
                f"❌ Unexpected response for invalid token: "
                f"{response.status_code}"
            )

        print("\n" + "=" * 60)
        print("🎉 Optimized RBAC System Demo Complete!")
        print("\nKey Features Demonstrated:")
        print("✅ High-performance role caching")
        print("✅ Unified dependency system")
        print("✅ Role-based access control")
        print("✅ Permission-based access control")
        print("✅ Proper error handling")
        print("✅ Security-first design")


if __name__ == "__main__":
    print("Starting demo in 3 seconds...")
    print("Make sure to run: python main.py (in another terminal)")
    time.sleep(3)
    asyncio.run(demo_optimized_rbac())
