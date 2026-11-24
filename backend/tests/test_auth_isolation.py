from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.seed.demo_seed import DEMO_EMAIL, DEMO_PASSWORD, REVIEWER_EMAIL
from tests.conftest import login, new_client

API = "/api/v1"
NEW_PASSWORD = "BrandNewPass!2027"


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def _signup(client, email: str, password: str = "SignupPass!2026", name: str = "Test Traveler"):
    res = await client.post(
        f"{API}/auth/signup",
        json={"full_name": name, "email": email, "password": password, "confirm_password": password},
    )
    return res


async def _first_trip(client, **params):
    res = await client.get(f"{API}/trips", params={"page_size": 100, **params})
    assert res.status_code == 200, res.text
    return res.json()


# --------------------------------------------------------------------------- authentication
async def test_login_sets_httponly_cookie_and_returns_csrf(anon):
    res = await anon.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == DEMO_EMAIL and body["avatar_initials"] == "AK" and body["full_name"] == "Alex Kumar"
    assert body["csrf_token"] and "password" not in json.dumps(body).lower()
    cookie = res.headers["set-cookie"].lower()
    assert "tg_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    me = await anon.get(f"{API}/auth/me")
    assert me.status_code == 200 and me.json()["csrf_token"] == body["csrf_token"]


async def test_wrong_password_and_unknown_email_look_identical(anon):
    bad_pw = await anon.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": "nope-nope-nope"})
    unknown = await anon.post(f"{API}/auth/login", json={"email": "ghost@example.com", "password": "nope-nope-nope"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json() == unknown.json()
    assert "set-cookie" not in bad_pw.headers


async def test_login_is_throttled_after_repeated_failures(anon):
    for _ in range(8):
        r = await anon.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": "wrong-wrong"})
        assert r.status_code == 401
    blocked = await anon.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert blocked.status_code == 429 and "Retry-After" in blocked.headers


async def test_protected_routes_require_a_session(anon):
    for path in ("/auth/me", "/trips", "/runs", "/evaluations", "/analytics/dashboard", "/analytics/costs", "/me/preferences"):
        res = await anon.get(f"{API}{path}")
        assert res.status_code == 401, path
    assert (await anon.get(f"{API}/health")).status_code == 200  # health is public


async def test_signup_logout_and_session_revocation():
    async with new_client() as c:
        email = _unique_email()
        res = await _signup(c, email)
        assert res.status_code == 201, res.text
        csrf = res.json()["csrf_token"]
        assert res.json()["is_demo"] is False and res.json()["avatar_initials"] == "TT"
        assert (await _signup(c, email)).status_code == 409  # duplicate
        assert (await c.get(f"{API}/auth/me")).status_code == 200

        no_csrf = await c.post(f"{API}/auth/logout")
        assert no_csrf.status_code == 403  # revoking an active session needs the CSRF header
        out = await c.post(f"{API}/auth/logout", headers={"X-CSRF-Token": csrf})
        assert out.status_code == 200
        assert (await c.get(f"{API}/auth/me")).status_code == 401  # cookie cleared AND session revoked


async def test_revoked_session_token_is_rejected_even_if_cookie_is_replayed():
    async with new_client() as c:
        csrf = await login(c, DEMO_EMAIL)
        stolen = c.cookies.get("tg_session")
        assert stolen
        assert (await c.post(f"{API}/auth/logout", headers={"X-CSRF-Token": csrf})).status_code == 200
    async with new_client() as attacker:
        attacker.headers["Cookie"] = f"tg_session={stolen}"
        assert (await attacker.get(f"{API}/auth/me")).status_code == 401


async def test_signup_validation(anon):
    res = await anon.post(
        f"{API}/auth/signup",
        json={"full_name": "A", "email": "not-an-email", "password": "short", "confirm_password": "different"},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "validation_error" and res.json()["errors"]


# --------------------------------------------------------------------------- CSRF
async def test_mutations_require_matching_csrf_header(demo):
    trips = (await _first_trip(demo))["items"]
    trip_id = trips[0]["id"]
    token = demo.headers.pop("X-CSRF-Token")
    try:
        assert (await demo.post(f"{API}/trips/{trip_id}/favorite")).status_code == 403
        assert (await demo.patch(f"{API}/trips/{trip_id}", json={"notes": "x"})).status_code == 403
        assert (await demo.delete(f"{API}/trips/{trip_id}")).status_code == 403
        assert (await demo.post(f"{API}/runs", json={"prompt": "Plan a Goa trip please"})).status_code == 403
        assert (await demo.patch(f"{API}/me/preferences", json={"theme": "dark"})).status_code == 403
        wrong = await demo.post(f"{API}/trips/{trip_id}/favorite", headers={"X-CSRF-Token": "wrong-token"})
        assert wrong.status_code == 403
        assert (await demo.get(f"{API}/trips/{trip_id}")).status_code == 200  # reads need no CSRF
    finally:
        demo.headers["X-CSRF-Token"] = token
    assert (await demo.get(f"{API}/trips/{trip_id}")).status_code == 200


# --------------------------------------------------------------------------- ownership / isolation
async def test_each_user_sees_only_their_own_trips_and_runs(demo, reviewer):
    demo_trips = await _first_trip(demo)
    rev_trips = await _first_trip(reviewer)
    assert demo_trips["total"] == 12 and rev_trips["total"] == 4
    demo_ids = {t["id"] for t in demo_trips["items"]}
    rev_ids = {t["id"] for t in rev_trips["items"]}
    assert not demo_ids & rev_ids
    assert not {t["title"] for t in demo_trips["items"]} & {t["title"] for t in rev_trips["items"]}

    demo_runs = (await demo.get(f"{API}/runs", params={"page_size": 100})).json()
    rev_runs = (await reviewer.get(f"{API}/runs", params={"page_size": 100})).json()
    assert {r["public_id"] for r in demo_runs["items"]}.isdisjoint({r["public_id"] for r in rev_runs["items"]})
    assert rev_runs["total"] == 3 and demo_runs["total"] >= 25


async def test_cross_user_access_to_every_trip_endpoint_is_404(demo, reviewer):
    demo_trip = next(t for t in (await _first_trip(demo))["items"] if t["title"] == "Goa Getaway")
    tid = demo_trip["id"]
    checks = [
        ("get", f"{API}/trips/{tid}", None),
        ("patch", f"{API}/trips/{tid}", {"title": "hijacked"}),
        ("post", f"{API}/trips/{tid}/favorite", None),
        ("post", f"{API}/trips/{tid}/duplicate", None),
        ("get", f"{API}/trips/{tid}/versions", None),
        ("get", f"{API}/trips/{tid}/versions/1", None),
        ("post", f"{API}/trips/{tid}/versions/1/restore", None),
        ("post", f"{API}/trips/{tid}/replan", {"prompt": "steal this plan"}),
        ("delete", f"{API}/trips/{tid}", None),
    ]
    for method, url, body in checks:
        res = await getattr(reviewer, method)(url, **({"json": body} if body is not None else {}))
        assert res.status_code == 404, (method, url, res.status_code)
    # and the victim's data is untouched
    after = (await demo.get(f"{API}/trips/{tid}")).json()
    assert after["title"] == "Goa Getaway" and len(after["days"]) == 5 and after["current_version"] == 2


async def test_cross_user_access_to_run_evaluation_and_cost_endpoints_is_404(demo, reviewer):
    run = (await demo.get(f"{API}/runs/TG-1047")).json()
    for ref in ("TG-1047", run["id"]):
        for path in (
            f"/runs/{ref}",
            f"/runs/{ref}/events",
            f"/runs/{ref}/graph",
            f"/runs/{ref}/stream",
            f"/runs/{ref}/nodes/itinerary",
            f"/analytics/costs/runs/{ref}",
            f"/analytics/costs/runs/{ref}/export",
        ):
            res = await reviewer.get(f"{API}{path}")
            assert res.status_code == 404, path
    assert (await reviewer.delete(f"{API}/runs/TG-1047")).status_code == 404
    # evaluating / comparing someone else's runs
    assert (await reviewer.post(f"{API}/evaluations", json={"run_id": "TG-1047"})).status_code == 404
    mixed = await reviewer.post(f"{API}/evaluations/compare", json={"run_ids": ["TG-1047", "TG-2001"]})
    assert mixed.status_code == 404
    # cost filters cannot reach foreign runs
    assert (await reviewer.get(f"{API}/analytics/costs", params={"run_id": "TG-1047"})).status_code == 404

    evals = (await demo.get(f"{API}/evaluations", params={"page_size": 100})).json()
    ev_id = evals["items"][0]["id"]
    assert (await reviewer.get(f"{API}/evaluations/{ev_id}")).status_code == 404
    rev_evals = (await reviewer.get(f"{API}/evaluations", params={"page_size": 100})).json()
    assert ev_id not in {e["id"] for e in rev_evals["items"]}
    assert all(e["run_public_id"].startswith("TG-2") for e in rev_evals["items"])


async def test_cost_and_dashboard_totals_are_scoped_per_user(demo, reviewer):
    demo_dash = (await demo.get(f"{API}/analytics/dashboard")).json()
    rev_dash = (await reviewer.get(f"{API}/analytics/dashboard")).json()
    assert demo_dash["greeting_name"] == "Alex" and rev_dash["greeting_name"] == "Riya"
    assert (demo_dash["trips_planned"], demo_dash["trips_completed"], demo_dash["trips_in_progress"], demo_dash["trips_draft"]) == (12, 7, 2, 3)
    assert (rev_dash["trips_planned"], rev_dash["agent_runs"]) == (4, 3)
    demo_costs = (await demo.get(f"{API}/analytics/costs", params={"days": 0})).json()
    rev_costs = (await reviewer.get(f"{API}/analytics/costs", params={"days": 0})).json()
    assert demo_costs["run_count"] >= 25 and rev_costs["run_count"] == 3
    assert rev_costs["total_cost_usd"] < demo_costs["total_cost_usd"]


async def test_new_account_starts_empty_and_cannot_see_seed_data():
    async with new_client() as c:
        res = await _signup(c, _unique_email())
        c.headers["X-CSRF-Token"] = res.json()["csrf_token"]
        assert (await _first_trip(c))["total"] == 0
        dash = (await c.get(f"{API}/analytics/dashboard")).json()
        assert dash["trips_planned"] == 0 and dash["agent_runs"] == 0 and dash["avg_plan_quality"] is None
        assert (await c.get(f"{API}/runs/TG-1047")).status_code == 404
        costs = (await c.get(f"{API}/analytics/costs")).json()
        assert costs["total_cost_usd"] == 0 and costs["run_count"] == 0
        assert len(costs["trend"]) >= 30  # zero-filled, not missing


# --------------------------------------------------------------------------- forgot / reset password
def _inbox_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def test_forgot_password_never_leaks_account_existence(anon, inbox_path):
    before = len(_inbox_entries(inbox_path))
    known = await anon.post(f"{API}/auth/forgot-password", json={"email": REVIEWER_EMAIL})
    unknown = await anon.post(f"{API}/auth/forgot-password", json={"email": "nobody-here@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert "link" not in known.text.lower() or "reset link has been sent" in known.text.lower()
    entries = _inbox_entries(inbox_path)[before:]
    assert [e["email"] for e in entries] == [REVIEWER_EMAIL]  # only the real account got a (local) link
    assert "/reset-password/" in entries[0]["link"]


async def test_full_password_reset_flow_is_single_use_and_revokes_sessions(inbox_path):
    async with new_client() as c:
        email = _unique_email()
        old_pw = "OriginalPass!2026"
        res = await _signup(c, email, password=old_pw)
        assert res.status_code == 201
        assert (await c.get(f"{API}/auth/me")).status_code == 200

        assert (await c.post(f"{API}/auth/forgot-password", json={"email": email})).status_code == 200
        link = [e for e in _inbox_entries(inbox_path) if e["email"] == email][-1]["link"]
        token = link.rsplit("/", 1)[1]

        assert (await c.post(f"{API}/auth/reset-password/validate", json={"token": token})).json() == {"valid": True}
        assert (await c.post(f"{API}/auth/reset-password/validate", json={"token": "bogus"})).json() == {"valid": False}
        mismatch = await c.post(
            f"{API}/auth/reset-password",
            json={"token": token, "password": NEW_PASSWORD, "confirm_password": "something-else"},
        )
        assert mismatch.status_code == 422
        bad = await c.post(
            f"{API}/auth/reset-password",
            json={"token": "bogus-token", "password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        )
        assert bad.status_code == 400

        ok = await c.post(
            f"{API}/auth/reset-password",
            json={"token": token, "password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        )
        assert ok.status_code == 200, ok.text
        reuse = await c.post(
            f"{API}/auth/reset-password",
            json={"token": token, "password": "AnotherPass!2028", "confirm_password": "AnotherPass!2028"},
        )
        assert reuse.status_code == 400  # single use
        assert (await c.post(f"{API}/auth/reset-password/validate", json={"token": token})).json() == {"valid": False}
        assert (await c.get(f"{API}/auth/me")).status_code == 401  # existing sessions revoked

    async with new_client() as fresh:
        old = await fresh.post(f"{API}/auth/login", json={"email": email, "password": old_pw})
        assert old.status_code == 401
        assert (await fresh.post(f"{API}/auth/login", json={"email": email, "password": NEW_PASSWORD})).status_code == 200


async def test_requesting_a_new_reset_link_invalidates_the_previous_one(inbox_path):
    async with new_client() as c:
        email = _unique_email()
        await _signup(c, email)
        await c.post(f"{API}/auth/forgot-password", json={"email": email})
        await c.post(f"{API}/auth/forgot-password", json={"email": email})
        links = [e["link"] for e in _inbox_entries(inbox_path) if e["email"] == email]
        first, second = (l.rsplit("/", 1)[1] for l in links[-2:])
        assert (await c.post(f"{API}/auth/reset-password/validate", json={"token": first})).json()["valid"] is False
        assert (await c.post(f"{API}/auth/reset-password/validate", json={"token": second})).json()["valid"] is True


# --------------------------------------------------------------------------- account management
async def test_change_password_requires_current_password_and_signs_out_other_sessions():
    async with new_client() as a, new_client() as b:
        email = _unique_email()
        res = await _signup(a, email, password="FirstPass!2026")
        a.headers["X-CSRF-Token"] = res.json()["csrf_token"]
        await login(b, email, "FirstPass!2026")

        wrong = await a.post(
            f"{API}/me/change-password",
            json={"current_password": "not-it-at-all", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        )
        assert wrong.status_code == 400
        ok = await a.post(
            f"{API}/me/change-password",
            json={"current_password": "FirstPass!2026", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        )
        assert ok.status_code == 200
        assert (await a.get(f"{API}/auth/me")).status_code == 200  # current session survives
        assert (await b.get(f"{API}/auth/me")).status_code == 401  # other device signed out


async def test_account_deletion_removes_user_and_blocks_demo_accounts(demo):
    blocked = await demo.request("DELETE", f"{API}/me", json={"password": DEMO_PASSWORD})
    assert blocked.status_code == 403

    async with new_client() as c:
        email = _unique_email()
        res = await _signup(c, email, password="DeleteMe!2026")
        c.headers["X-CSRF-Token"] = res.json()["csrf_token"]
        # give the account some data first
        created = await c.post(
            f"{API}/trips",
            json={"prompt": "Plan a 3-day Jaipur trip for 2", "launch_run": False, "destination": "Jaipur"},
        )
        assert created.status_code == 201
        wrong = await c.request("DELETE", f"{API}/me", json={"password": "wrong-password"})
        assert wrong.status_code == 400
        gone = await c.request("DELETE", f"{API}/me", json={"password": "DeleteMe!2026"})
        assert gone.status_code == 200, gone.text
        assert (await c.get(f"{API}/auth/me")).status_code == 401
    async with new_client() as again:
        assert (await again.post(f"{API}/auth/login", json={"email": email, "password": "DeleteMe!2026"})).status_code == 401
    # seeded users unaffected
    assert (await demo.get(f"{API}/trips")).json()["total"] == 12


async def test_profile_and_preferences_are_per_user(demo, reviewer):
    patched = await demo.patch(f"{API}/me/preferences", json={"theme": "dark", "reduced_motion": True})
    assert patched.status_code == 200 and patched.json()["theme"] == "dark"
    try:
        assert (await reviewer.get(f"{API}/me/preferences")).json()["theme"] == "system"
        assert (await demo.get(f"{API}/me/preferences")).json()["interests"][0] == "beaches"
        bad = await demo.patch(f"{API}/me/preferences", json={"budget_min": 90000, "budget_max": 1000})
        assert bad.status_code == 422
        prof = await demo.patch(f"{API}/me/profile", json={"full_name": "Alex Q Kumar"})
        assert prof.status_code == 200 and prof.json()["avatar_initials"] == "AK"
    finally:
        await demo.patch(f"{API}/me/preferences", json={"theme": "system", "reduced_motion": False})
        await demo.patch(f"{API}/me/profile", json={"full_name": "Alex Kumar"})


async def test_export_contains_only_the_callers_data(reviewer):
    res = await reviewer.get(f"{API}/me/export")
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["email"] == REVIEWER_EMAIL
    assert len(body["trips"]) == 4 and len(body["runs"]) == 3
    assert "password" not in json.dumps(body).lower().replace("password_reset", "")
    assert "TG-1047" not in json.dumps(body)


async def test_health_is_non_sensitive(anon):
    body = (await anon.get(f"{API}/health")).json()
    assert body["status"] == "ok" and body["database"] == "ok" and body["ai_mode"] == "demo"
    assert body["openai_configured"] is False
    assert set(body) == {"status", "ai_mode", "openai_configured", "database", "version", "timestamp"}


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
async def test_cors_allows_the_frontend_origin_with_credentials(anon, origin):
    res = await anon.options(
        f"{API}/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == origin
    assert res.headers["access-control-allow-credentials"] == "true"
    evil = await anon.options(
        f"{API}/auth/login",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in evil.headers
