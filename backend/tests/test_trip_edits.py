from __future__ import annotations

from app.api.common import wait_for_background_runs


async def test_reorder_bumps_version_and_rejects_a_stale_one(demo):
    listing = await demo.get("/api/v1/trips")
    assert listing.status_code == 200, listing.text
    trip_id = None
    detail = None
    for item in listing.json()["items"]:
        res = await demo.get(f"/api/v1/trips/{item['id']}")
        body = res.json()
        if any(len(day["activities"]) >= 2 for day in body["days"]):
            trip_id = item["id"]
            detail = body
            break
    assert trip_id and detail
    day = next(day for day in detail["days"] if len(day["activities"]) >= 2)
    second = day["activities"][1]
    moved = await demo.post(
        f"/api/v1/trips/{trip_id}/activities/reorder",
        json={"activity_id": second["id"], "expected_version": detail["current_version"], "direction": "up"},
    )
    assert moved.status_code == 200, moved.text
    updated = moved.json()
    assert updated["current_version"] == detail["current_version"] + 1
    same_day = next(item for item in updated["days"] if item["day_number"] == day["day_number"])
    assert same_day["activities"][0]["title"] == second["title"]
    stale = await demo.post(
        f"/api/v1/trips/{trip_id}/activities/reorder",
        json={"activity_id": second["id"], "expected_version": detail["current_version"], "direction": "down"},
    )
    assert stale.status_code == 409


async def _trip_with_days(demo) -> dict:
    listing = await demo.get("/api/v1/trips")
    for item in listing.json()["items"]:
        detail = (await demo.get(f"/api/v1/trips/{item['id']}")).json()
        if detail["days"] and detail["days"][0]["activities"]:
            return detail
    raise AssertionError("seeded demo trips have no itinerary")


async def test_replan_day_rejects_a_stale_version_and_starts_a_scoped_run(demo):
    detail = await _trip_with_days(demo)
    stale = await demo.post(
        f"/api/v1/trips/{detail['id']}/replan-day",
        json={"day_number": detail["days"][0]["day_number"], "expected_version": detail["current_version"] + 9},
    )
    assert stale.status_code == 409
    started = await demo.post(
        f"/api/v1/trips/{detail['id']}/replan-day",
        json={"day_number": detail["days"][0]["day_number"], "expected_version": detail["current_version"]},
    )
    assert started.status_code == 202, started.text
    await wait_for_background_runs(timeout=30)


async def test_another_user_cannot_reorder(demo, reviewer):
    detail = await _trip_with_days(demo)
    activity_id = detail["days"][0]["activities"][0]["id"]
    denied = await reviewer.post(
        f"/api/v1/trips/{detail['id']}/activities/reorder",
        json={"activity_id": activity_id, "expected_version": detail["current_version"], "direction": "down"},
    )
    assert denied.status_code == 404
