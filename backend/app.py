"""Flask API for the AI Presentation Coach project.

Accepts outputs from the speech, computer-vision, and NLP modules; saves sessions
in SQLite; and builds an explainable starter report from the metrics received.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

from module_adapters import normalize_module_payload

BASE_DIR = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(BASE_DIR / "NLP"))
from feedback_generator import build_analysis_result

DB_PATH = Path(os.environ.get("PRESENTATION_COACH_DB", BASE_DIR / "data" / "presentation_sessions.db"))
SPEECH_DIR = BASE_DIR / "speech_to_text"

app = Flask(__name__)

MODULES = ("speech", "computer_vision", "nlp")
SCORE_FIELDS = {
    "computer_vision": ("face_visibility", "eye_contact", "posture_score", "movement_score"),
    "nlp": ("keyword_score", "content_relevance", "vocabulary_score", "repetition_score"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                presenter_name TEXT NOT NULL,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL,
                speech_json TEXT NOT NULL DEFAULT '{}',
                cv_json TEXT NOT NULL DEFAULT '{}',
                nlp_json TEXT NOT NULL DEFAULT '{}',
                speech_score REAL,
                cv_score REAL,
                nlp_score REAL,
                overall_score REAL
            )
            """
        )


def numeric_value(value: Any, field: str, minimum: float = 0, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{field}' must be a number.")
    number = float(value)
    if number < minimum:
        raise ValueError(f"'{field}' must be at least {minimum}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"'{field}' must be at most {maximum}.")
    return number


def validate_module(module_name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"'{module_name}' must be a JSON object.")
    result = normalize_module_payload(module_name, value)

    if module_name == "speech":
        if "transcript" in result and not isinstance(result["transcript"], str):
            raise ValueError("'transcript' must be text.")
        for field in ("speaking_time_seconds", "words_per_minute", "pause_count", "filler_word_count"):
            if field in result and result[field] is not None:
                number = numeric_value(result[field], field)
                if field in ("pause_count", "filler_word_count") and not number.is_integer():
                    raise ValueError(f"'{field}' must be a whole number.")
                result[field] = int(number) if number.is_integer() else round(number, 2)
    else:
        score_fields = SCORE_FIELDS[module_name]
        if module_name == "nlp":
            score_fields = score_fields + ("content_score",)
        for field in score_fields:
            if field in result and result[field] is not None:
                result[field] = round(numeric_value(result[field], field, maximum=100), 2)
        if module_name == "nlp" and "content_suggestions" in result:
            suggestions = result["content_suggestions"]
            if not isinstance(suggestions, list) or not all(isinstance(item, str) for item in suggestions):
                raise ValueError("'content_suggestions' must be a list of text strings.")

    return result


def average_score(data: dict[str, Any], fields: tuple[str, ...]) -> float | None:
    values = [
        float(data[field]) for field in fields
        if isinstance(data.get(field), (int, float)) and not isinstance(data.get(field), bool)
    ]
    return round(mean(values), 2) if values else None


def calculate_speech_score(speech: dict[str, Any]) -> float | None:
    parts: list[float] = []
    wpm = speech.get("words_per_minute")
    if isinstance(wpm, (int, float)) and not isinstance(wpm, bool):
        if 110 <= wpm <= 160:
            pace_score = 100.0
        elif wpm < 110:
            pace_score = max(0.0, 100.0 * (wpm - 50.0) / 60.0)
        else:
            pace_score = max(0.0, 100.0 * (220.0 - wpm) / 60.0)
        parts.append(pace_score)

    transcript = speech.get("transcript", "")
    filler_count = speech.get("filler_word_count")
    if isinstance(transcript, str) and transcript.strip() and isinstance(filler_count, (int, float)):
        word_count = len(transcript.split())
        if word_count:
            fillers_per_100_words = float(filler_count) * 100 / word_count
            parts.append(max(0.0, 100.0 - fillers_per_100_words * 15.0))

    return round(mean(parts), 2) if parts else None


def calculate_scores(speech: dict[str, Any], cv: dict[str, Any], nlp: dict[str, Any]) -> dict[str, float | None]:
    native_content_score = nlp.get("content_score")
    if isinstance(native_content_score, (int, float)) and not isinstance(native_content_score, bool):
        nlp_score = round(float(native_content_score), 2)
    else:
        nlp_score = average_score(nlp, SCORE_FIELDS["nlp"])

    scores: dict[str, float | None] = {
        "speech_score": calculate_speech_score(speech),
        "cv_score": average_score(cv, SCORE_FIELDS["computer_vision"]),
        "nlp_score": nlp_score,
    }
    available = [score for score in scores.values() if score is not None]
    scores["overall_score"] = round(mean(available), 2) if available else None
    return scores


def row_to_session(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "presenter_name": row["presenter_name"],
        "topic": row["topic"],
        "created_at": row["created_at"],
        "speech": json.loads(row["speech_json"]),
        "computer_vision": json.loads(row["cv_json"]),
        "nlp": json.loads(row["nlp_json"]),
        "scores": {
            "speech_score": row["speech_score"],
            "cv_score": row["cv_score"],
            "nlp_score": row["nlp_score"],
            "overall_score": row["overall_score"],
        },
    }


@app.get("/speech/")
def speech_module():
    """Serve the browser speech-to-text page."""
    return send_from_directory(SPEECH_DIR, "index.html")


@app.get("/speech/<path:filename>")
def speech_assets(filename: str):
    """Serve speech page CSS and JavaScript."""
    return send_from_directory(SPEECH_DIR, filename)


@app.get("/")
def home():
    """Serve the integrated project landing page."""
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Presentation Coach API is running."})


@app.post("/api/sessions")
def create_session():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Send a JSON object in the request body."}), 400

    presenter_name = payload.get("presenter_name", "Presenter")
    topic = payload.get("topic", "Untitled presentation")
    if not isinstance(presenter_name, str) or not presenter_name.strip():
        return jsonify({"error": "'presenter_name' must be a non-empty string."}), 400
    if not isinstance(topic, str) or not topic.strip():
        return jsonify({"error": "'topic' must be a non-empty string."}), 400

    try:
        modules = {name: validate_module(name, payload.get(name, {})) for name in MODULES}
        transcript = modules["speech"].get("transcript", "")
        if isinstance(transcript, str) and transcript.strip() and not modules["nlp"].get("content_score"):
            # Analyze the speech transcript so NLP is saved in the same session.
            modules["nlp"].update(build_analysis_result(transcript, topic))
        scores = calculate_scores(modules["speech"], modules["computer_vision"], modules["nlp"])
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    session_id = str(uuid.uuid4())
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO sessions
            (id, presenter_name, topic, created_at, speech_json, cv_json, nlp_json,
             speech_score, cv_score, nlp_score, overall_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, presenter_name.strip(), topic.strip(), utc_now(),
                json.dumps(modules["speech"]), json.dumps(modules["computer_vision"]),
                json.dumps(modules["nlp"]), scores["speech_score"], scores["cv_score"],
                scores["nlp_score"], scores["overall_score"],
            ),
        )
        row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    return jsonify({"message": "Session created.", "session": row_to_session(row)}), 201


@app.get("/api/sessions")
def list_sessions():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT 100").fetchall()
    return jsonify({"sessions": [row_to_session(row) for row in rows]})


@app.get("/api/sessions/<session_id>")
def get_session(session_id: str):
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Session not found."}), 404
    return jsonify({"session": row_to_session(row)})


@app.patch("/api/sessions/<session_id>")
def update_session(session_id: str):
    """Merge results from one or more modules into an existing session."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Send a JSON object in the request body."}), 400

    supplied_modules = [name for name in MODULES if name in payload]
    if not supplied_modules:
        return jsonify({"error": "Include at least one module: speech, computer_vision, or nlp."}), 400

    with get_connection() as connection:
        row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Session not found."}), 404

        modules = {
            "speech": json.loads(row["speech_json"]),
            "computer_vision": json.loads(row["cv_json"]),
            "nlp": json.loads(row["nlp_json"]),
        }
        try:
            for module_name in supplied_modules:
                incoming = validate_module(module_name, payload[module_name])
                modules[module_name].update(incoming)
            scores = calculate_scores(modules["speech"], modules["computer_vision"], modules["nlp"])
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        connection.execute(
            """UPDATE sessions SET speech_json = ?, cv_json = ?, nlp_json = ?,
               speech_score = ?, cv_score = ?, nlp_score = ?, overall_score = ?
               WHERE id = ?""",
            (
                json.dumps(modules["speech"]), json.dumps(modules["computer_vision"]),
                json.dumps(modules["nlp"]), scores["speech_score"], scores["cv_score"],
                scores["nlp_score"], scores["overall_score"], session_id,
            ),
        )
        updated = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    return jsonify({"message": "Session updated.", "session": row_to_session(updated)})


initialize_database()

if __name__ == "__main__":
    # Local development only; do not enable debug mode on a public server.
    debug_enabled = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug_enabled)
