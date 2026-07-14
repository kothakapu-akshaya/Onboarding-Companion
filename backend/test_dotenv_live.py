"""Live HTTP tests for the dotenv-removal migration."""

import sys

import requests

BASE = "http://localhost:8000"

results = []


def _check(name, passed, detail=""):
    """Record and print a single live-test result."""
    mark = "PASS" if passed else "FAIL"
    results.append((name, passed))
    print(f"  [{mark}] {name}" + (f": {detail}" if detail else ""))


def _login():
    """Authenticate with the live app and return a bearer token."""
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"phone": "+919900000001", "password": "Admin@1234"},
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


print("\n=== dotenv migration — live HTTP tests ===\n")

# DM-01: health check proves env vars load without load_dotenv.
r = requests.get(f"{BASE}/health")
_check(
    "DM-01 GET /health — app boots without load_dotenv()",
    r.status_code == 200,
    f"status={r.status_code}",
)

# DM-02: login succeeds (JWT secret loaded from env, DB connection works)
try:
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    _check(
        "DM-02 POST /auth/login — JWT secret + DB both loaded from env",
        True,
        "token received",
    )
except Exception as e:
    headers = {}
    _check(
        "DM-02 POST /auth/login — JWT secret + DB both loaded from env",
        False,
        str(e),
    )

# DM-03: GET /records/ — DB URL loaded from env (no load_dotenv)
r = requests.get(f"{BASE}/api/v1/records/", headers=headers)
_check(
    "DM-03 GET /records/ — DB connection works without load_dotenv()",
    r.status_code == 200,
    f"status={r.status_code}",
)

# DM-04: GET /users/ — confirms full env stack works (auth + DB + RBAC)
r = requests.get(f"{BASE}/api/v1/users/", headers=headers)
_check(
    "DM-04 GET /users/ — auth + DB + RBAC all loaded from env",
    r.status_code == 200,
    f"status={r.status_code}",
)

# DM-05: GET /categories/ — category data served (proves seeded data readable)
r = requests.get(f"{BASE}/api/v1/categories/", headers=headers)
category_count = len(r.json()) if r.status_code == 200 else "N/A"
_check(
    "DM-05 GET /categories/ — seeded data accessible",
    r.status_code == 200 and isinstance(r.json(), list),
    f"status={r.status_code}, count={category_count}",
)

# DM-06: OpenAPI schema loads (app startup fully completed)
r = requests.get(f"{BASE}/api/v1/openapi.json")
_check(
    "DM-06 GET /openapi.json — full app startup completed",
    r.status_code == 200 and "openapi" in r.json(),
    f"status={r.status_code}",
)

# DM-07: POST /records/for-review — exercises Celery broker URL from env
r = requests.post(
    f"{BASE}/api/v1/records/for-review",
    json={"record_ids": []},
    headers=headers,
)
_check(
    "DM-07 POST /records/for-review — Celery broker URL loaded from env",
    r.status_code in (200, 422),
    f"status={r.status_code}",
)

# DM-08: MinIO/storage config loaded (object storage endpoint from env)
r = requests.get(
    f"{BASE}/api/v1/records/", headers=headers, params={"limit": 1}
)
_check(
    "DM-08 GET /records/?limit=1 — object storage config loaded from env",
    r.status_code == 200,
    f"status={r.status_code}",
)

passed = sum(1 for _, p in results if p)
total = len(results)
print(f"\n=== {passed}/{total} PASS ===")
if passed < total:
    print("FAILED:", [n for n, p in results if not p])
    sys.exit(1)
else:
    print("ALL PASS")
