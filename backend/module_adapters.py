"""Compatibility adapters for Member 1–3 module output formats.

The adapters preserve source details while mapping their native fields to the
stable names expected by the Member 4 API and dashboard.
"""

from __future__ import annotations

from typing import Any


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _first_number(*values: Any) -> float | None:
    for value in values:
        if _is_number(value):
            return float(value)
    return None


def normalize_module_payload(module_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Map known module outputs to the API's standard field names."""
    result = dict(payload)

    if module_name == "speech":
        # Member 1 calls this field speaking_time; the API uses
        # speaking_time_seconds. Preserve both names in the stored result.
        if "speaking_time_seconds" not in result and "speaking_time" in result:
            result["speaking_time_seconds"] = result["speaking_time"]
        return result

    if module_name == "computer_vision":
        eye = result.get("eye_contact")
        posture = result.get("posture")
        gestures = result.get("gestures")
        confidence = result.get("confidence")

        nested_sections = {
            key: value
            for key, value in (
                ("eye_contact", eye),
                ("posture", posture),
                ("gestures", gestures),
                ("confidence", confidence),
                ("meta", result.get("meta")),
            )
            if isinstance(value, dict) or (key == "meta" and value is not None)
        }

        if nested_sections:
            # Keep the source report's nested metrics for the detailed report
            # tab; the top-level fields below are numeric chart values.
            result["cv_module_report"] = nested_sections

            if isinstance(eye, dict):
                face_visibility = _first_number(
                    result.get("face_visibility"),
                    eye.get("face_detected_pct"),
                    posture.get("visible_pct") if isinstance(posture, dict) else None,
                )
                eye_contact = _first_number(
                    eye.get("eye_contact_pct"),
                    result.get("eye_contact"),
                )
                if face_visibility is not None:
                    result["face_visibility"] = round(face_visibility, 2)
                if eye_contact is not None:
                    result["eye_contact"] = round(eye_contact, 2)

            if isinstance(posture, dict) and not _is_number(result.get("posture_score")):
                posture_score = _first_number(
                    posture.get("avg_posture_score"),
                    posture.get("good_posture_pct"),
                )
                if posture_score is not None:
                    result["posture_score"] = round(posture_score, 2)

            if isinstance(gestures, dict) and not _is_number(result.get("movement_score")):
                fidgeting = _first_number(gestures.get("fidgeting_pct"))
                face_touch = _first_number(gestures.get("face_touch_pct"))
                if fidgeting is not None or face_touch is not None:
                    # The source module reports movement categories, not one
                    # overall movement score. Use a clearly-labelled proxy:
                    # lower fidgeting and face-touch percentages score higher.
                    penalty = (fidgeting or 0.0) + 0.5 * (face_touch or 0.0)
                    result["movement_score"] = round(max(0.0, min(100.0, 100.0 - penalty)), 2)
                    result["movement_score_note"] = (
                        "Estimated control proxy: 100 minus fidgeting percentage "
                        "and half the face-touch percentage; not a native CV score."
                    )

        return result

    if module_name == "nlp":
        # Member 3's feedback generator calls this list suggestions.
        if "content_suggestions" not in result and isinstance(result.get("suggestions"), list):
            result["content_suggestions"] = result["suggestions"]

        # The NLP module's primary output is content_score. Keep its detailed
        # component analysis and use this native score instead of inventing
        # unrelated component metrics.
        if "content_score" not in result and _is_number(result.get("score")):
            result["content_score"] = result["score"]

        return result

    return result
