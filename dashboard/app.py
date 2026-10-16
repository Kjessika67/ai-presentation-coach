"""Streamlit dashboard for AI Presentation Coach reports."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

DEFAULT_API_URL = os.environ.get("PRESENTATION_COACH_API_URL", "http://127.0.0.1:5000")

st.set_page_config(page_title="AI Presentation Coach", page_icon="🎤", layout="wide")
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1400px;}
    [data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.28); padding: 14px; border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎤 AI Presentation Coach")

st.caption("One report for speech, body language, and presentation content.")

with st.expander("Import or attach module results", expanded=False):
    st.caption("Upload JSON outputs from the three modules. To keep one report, attach later results to the Session ID created by Speech Analysis.")
    import_mode = st.radio("How should these results be saved?", ("Create a new combined report", "Attach to an existing session ID"), horizontal=True, key="import_mode")
    if import_mode == "Attach to an existing session ID":
        existing_session_id = st.text_input("Existing Session ID (from Speech Analysis success message)", key="import_existing_session_id", placeholder="Paste the session UUID").strip()
        st.caption("This merges results into the selected report and preserves its other modules.")
    else:
        existing_session_id = ""
        import_name = st.text_input("Presenter name", value="Jessika", key="import_presenter_name")
        import_topic = st.text_input("Presentation topic", value="", key="import_presentation_topic")
    speech_json_file = st.file_uploader("Speech module JSON", type=["json"], key="import_speech_json")
    cv_json_file = st.file_uploader("Computer-vision module JSON", type=["json"], key="import_cv_json")
    nlp_json_file = st.file_uploader("NLP module JSON", type=["json"], key="import_nlp_json")
    import_clicked = st.button("Attach results to this session" if import_mode == "Attach to an existing session ID" else "Create one combined report", key="create_imported_report", use_container_width=True)

if import_clicked:
    uploaded_modules = {}
    import_errors = []
    for module_name, uploaded_file in (("speech", speech_json_file), ("computer_vision", cv_json_file), ("nlp", nlp_json_file)):
        if uploaded_file is None:
            continue
        try:
            parsed = json.loads(uploaded_file.getvalue().decode("utf-8-sig"))
            if not isinstance(parsed, dict):
                import_errors.append(f"{uploaded_file.name} must contain one JSON object.")
            else:
                uploaded_modules[module_name] = parsed
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            import_errors.append(f"Could not read {uploaded_file.name} as JSON: {exc}")
    if import_errors:
        for import_error in import_errors:
            st.error(import_error)
    elif not uploaded_modules:
        st.warning("Upload at least one module JSON file first.")
    elif import_mode == "Attach to an existing session ID" and not existing_session_id:
        st.warning("Paste the existing Session ID. Do not create a new report if you want one combined session.")
    else:
        try:
            import_api_url = st.session_state.get("backend_api_url", DEFAULT_API_URL).strip().rstrip("/")
            if import_mode == "Attach to an existing session ID":
                response = requests.patch(f"{import_api_url}/api/sessions/{existing_session_id}", json=uploaded_modules, timeout=15)
                response.raise_for_status()
                updated_session = response.json().get("session", {})
                st.success(f"Results attached to the existing report. Session ID: {updated_session.get('id', existing_session_id)}")
            else:
                payload = {"presenter_name": import_name.strip() or "Presenter", "topic": import_topic.strip() or "Untitled presentation", **uploaded_modules}
                response = requests.post(f"{import_api_url}/api/sessions", json=payload, timeout=15)
                response.raise_for_status()
                created_session = response.json().get("session", {})
                st.success(f"Combined report created. Session ID: {created_session.get('id', 'created')}")
            st.rerun()
        except requests.RequestException as exc:
            details = exc.response.text if isinstance(exc, requests.HTTPError) and exc.response is not None else str(exc)
            st.error(f"Could not save module results: {details}")

with st.sidebar:
    st.header("Backend connection")
    api_url = st.text_input(
        "Backend API URL",
        value=DEFAULT_API_URL,
        key="backend_api_url",
    ).strip().rstrip("/")
    if st.button("Check backend", use_container_width=True):
        try:
            check = requests.get(f"{api_url}/api/health", timeout=3)
            check.raise_for_status()
            st.success("Backend connected.")
        except requests.RequestException as exc:
            st.error(f"Could not connect: {exc}")

    st.divider()
    st.subheader("Create a demo report")
    st.caption("Example data only. This does not access a microphone or webcam.")
    demo_name = st.text_input("Presenter name", value="Demo Presenter")
    demo_topic = st.text_input("Presentation topic", value="The Importance of Cybersecurity")
    make_demo = st.button("Create demo report", type="primary", use_container_width=True)

if make_demo:
    demo_payload = {
        "presenter_name": demo_name.strip() or "Demo Presenter",
        "topic": demo_topic.strip() or "Untitled presentation",
        "speech": {
            "transcript": (
                "Good morning everyone. Today I will explain cybersecurity. "
                "Strong passwords, multi-factor authentication, and phishing awareness help protect accounts."
            ),
            "speaking_time_seconds": 42,
            "words_per_minute": 128,
            "pause_count": 3,
            "filler_word_count": 2,
        },
        "computer_vision": {
            "face_visibility": 95,
            "eye_contact": 80,
            "posture_score": 86,
            "movement_score": 82,
        },
        "nlp": {
            "keyword_score": 88,
            "content_relevance": 91,
            "vocabulary_score": 79,
            "repetition_score": 90,
            "content_suggestions": [
                "Add a short real-world example.",
                "Finish with one clear action for the audience.",
            ],
        },
    }
    try:
        response = requests.post(f"{api_url}/api/sessions", json=demo_payload, timeout=10)
        response.raise_for_status()
        st.success("Demo report created.")
        st.rerun()
    except requests.RequestException as exc:
        st.error(f"Could not create the demo report: {exc}")


def request_json(path: str) -> dict[str, Any]:
    response = requests.get(f"{api_url}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


def score_text(value: Any) -> str:
    return "Not available" if value is None else f"{float(value):.1f}/100"


try:
    sessions = request_json("/api/sessions").get("sessions", [])
except requests.RequestException as exc:
    st.warning("The dashboard cannot load reports until the Flask backend is running.")
    st.code("python backend/app.py", language="powershell")
    st.caption(f"Connection detail: {exc}")
    st.stop()

if not sessions:
    st.info("No reports yet. Create a demo report from the sidebar or let a teammate submit module results to the API.")
    st.stop()

session_labels = {
    item["id"]: (
        f'{item["presenter_name"]} — {item["topic"]} '
        f'({item["created_at"][:16].replace("T", " ")})'
    )
    for item in sessions
}
selected_id = st.selectbox(
    "Select a presentation",
    options=list(session_labels.keys()),
    format_func=lambda value: session_labels[value],
)

try:
    session = request_json(f"/api/sessions/{selected_id}")["session"]
except (requests.RequestException, KeyError) as exc:
    st.error(f"Could not load this report: {exc}")
    st.stop()

st.subheader(session["topic"])
st.caption(f'Presenter: {session["presenter_name"]}  ·  Session ID: {session["id"]}')
scores = session["scores"]

metric_cols = st.columns(4)
metric_cols[0].metric("Overall score", score_text(scores.get("overall_score")))
metric_cols[1].metric("Speech", score_text(scores.get("speech_score")))
metric_cols[2].metric("Computer vision", score_text(scores.get("cv_score")))
metric_cols[3].metric("Content", score_text(scores.get("nlp_score")))

if scores.get("overall_score") is not None:
    st.progress(min(max(float(scores["overall_score"]) / 100, 0.0), 1.0), text="Combined starter score")
else:
    st.info("The overall score appears once one or more modules provide scoreable metrics.")

speech_tab, cv_tab, nlp_tab, report_tab = st.tabs(
    ["🗣️ Speech analysis", "👁️ Computer vision", "🧠 Content analysis", "📦 Report data"]
)

with speech_tab:
    speech = session.get("speech", {})
    cols = st.columns(4)
    duration = speech.get("speaking_time_seconds")
    cols[0].metric("Speaking time", f"{duration} sec" if duration is not None else "—")
    wpm = speech.get("words_per_minute")
    cols[1].metric("Speaking speed", f"{wpm} WPM" if wpm is not None else "—")
    cols[2].metric("Pauses", speech.get("pause_count", "—"))
    cols[3].metric("Filler words", speech.get("filler_word_count", "—"))
    st.markdown("**Presentation transcript**")
    st.write(speech.get("transcript") or "The speech module has not submitted a transcript.")
    st.caption("Speech score is a transparent starter heuristic, not a validated public-speaking assessment.")

with cv_tab:
    cv = session.get("computer_vision", {})
    cv_labels = {
        "Face visibility": "face_visibility",
        "Eye contact": "eye_contact",
        "Posture": "posture_score",
        "Movement control": "movement_score",
    }
    cv_rows = [
        {"Metric": label, "Score": cv[field]}
        for label, field in cv_labels.items()
        if isinstance(cv.get(field), (int, float)) and not isinstance(cv.get(field), bool)
    ]
    if cv_rows:
        st.bar_chart(pd.DataFrame(cv_rows).set_index("Metric"), y="Score")
    else:
        st.info("No computer-vision metrics submitted yet.")
    if isinstance(cv.get("cv_module_report"), dict):
        with st.expander("View detailed computer-vision measurements"):
            st.json(cv["cv_module_report"])
    st.caption("Agree with the CV teammate that these scores use a 0–100 scale, with higher meaning better.")

with nlp_tab:
    nlp = session.get("nlp", {})
    nlp_labels = {
        "Keyword coverage": "keyword_score",
        "Topic relevance": "content_relevance",
        "Vocabulary": "vocabulary_score",
        "Avoiding repetition": "repetition_score",
    }
    nlp_rows = [
        {"Metric": label, "Score": nlp[field]}
        for label, field in nlp_labels.items()
        if isinstance(nlp.get(field), (int, float)) and not isinstance(nlp.get(field), bool)
    ]
    if nlp_rows:
        st.bar_chart(pd.DataFrame(nlp_rows).set_index("Metric"), y="Score")
    elif isinstance(nlp.get("content_score"), (int, float)) and not isinstance(nlp.get("content_score"), bool):
        st.metric("Content quality score", f"{float(nlp['content_score']):.1f}/100")
    else:
        st.info("No NLP metrics submitted yet.")

    st.markdown("**Content-improvement suggestions**")
    suggestions = nlp.get("content_suggestions", [])
    if suggestions:
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")
    else:
        st.write("No suggestions submitted yet.")
    st.caption("The NLP teammate should define repetition_score as how well unnecessary repetition is avoided.")

with report_tab:
    st.json(session)
    st.download_button(
        "Download report as JSON",
        data=json.dumps(session, indent=2, ensure_ascii=False),
        file_name=f"presentation-report-{session['id'][:8]}.json",
        mime="application/json",
    )

st.divider()
st.subheader("Presentation history")
history = []
for item in sessions:
    item_scores = item.get("scores", {})
    history.append({
        "Presenter": item["presenter_name"],
        "Topic": item["topic"],
        "Created": item["created_at"],
        "Overall": item_scores.get("overall_score"),
        "Speech": item_scores.get("speech_score"),
        "Computer vision": item_scores.get("cv_score"),
        "Content": item_scores.get("nlp_score"),
    })
st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
