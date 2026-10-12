from __future__ import annotations

import json


PROFILE_PREFIX = "ezlove-profile:v1:"
PROFILE_FIELDS = ("elder_age", "elder_gender", "living_status")


def read_elder_profile(value: str | None) -> dict:
    profile = {"elder_age": None, "elder_gender": None, "living_status": None, "health_notes": value}
    if not value or not value.startswith(PROFILE_PREFIX):
        return profile
    try:
        saved = json.loads(value[len(PROFILE_PREFIX):])
    except (TypeError, ValueError, json.JSONDecodeError):
        return profile
    for field in PROFILE_FIELDS:
        profile[field] = saved.get(field)
    profile["health_notes"] = saved.get("legacy_health_notes")
    return profile


def write_elder_profile(value: str | None, updates: dict) -> str:
    profile = read_elder_profile(value)
    for field in PROFILE_FIELDS:
        if field in updates:
            profile[field] = updates[field]
    saved = {field: profile[field] for field in PROFILE_FIELDS}
    if profile["health_notes"]:
        saved["legacy_health_notes"] = profile["health_notes"]
    return PROFILE_PREFIX + json.dumps(saved, ensure_ascii=False, separators=(",", ":"))
