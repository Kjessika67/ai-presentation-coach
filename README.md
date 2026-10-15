# AI Presentation Coach

Member 4 module: Flask backend, SQLite session storage, integration API, score aggregation, and Streamlit dashboard.

> **Note:** Scores are starter heuristics and are not a validated measure of presentation ability. Agree on metric definitions and score scales with all teammates before relying on the report.

## Project structure

~~~text
ai-presentation-coach/
├── backend/
│   ├── app.py
│   └── module_adapters.py
├── dashboard/
│   └── app.py
├── sample_data/
│   ├── session-example.json
│   ├── speech-module-example.json
│   ├── computer-vision-module-example.json
│   └── nlp-module-example.json
├── data/                 # Created automatically; local SQLite file is ignored by Git
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
~~~

## Run locally on Windows PowerShell

Open PowerShell in this repository folder. You do not need VS Code.

Install dependencies:

~~~powershell
python -m pip install -r requirements.txt
~~~

Start the backend in **PowerShell window 1** and keep it open:

~~~powershell
python backend\app.py
~~~

Test in a browser: http://127.0.0.1:5000/api/health

Start the dashboard in **PowerShell window 2**:

~~~powershell
python -m streamlit run dashboard\app.py
~~~

Open the local URL Streamlit prints, normally http://localhost:8501. Use **Create demo report** for an example; demo values do not access a microphone or webcam.

## Import results from Member 1, 2, and 3

The teammate implementations are in a separate repository and currently produce different output formats. This integration branch adds backend/module_adapters.py to normalize their outputs, and an **Import real module JSON files** expander on the dashboard.

1. Run the speech, computer-vision, and/or NLP module and export its output as a .json file. Each file must contain one JSON object.
2. In the Streamlit dashboard, open **Import real module JSON files**.
3. Enter the presenter and topic, then upload all module JSON files available for this presentation.
4. Click **Create report from uploaded JSON**. A report is created for the uploaded module(s), saved to SQLite, and shown with the other reports in the dashboard.

To create one combined report, select all JSON files for that presentation in the same import action. Importing just one module creates a report with that module's results and leaves the other sections empty.

### Supported source formats

**Member 1 — Speech-to-text**

The browser module's createBackendData() JSON includes transcript, speaking_time, words_per_minute, pause_count, and filler_word_count. The adapter maps speaking_time to the API field speaking_time_seconds. The value is expected to be seconds.

**Member 2 — Computer vision**

The Python CVAnalyzer.summary() output contains nested eye_contact, posture, gestures, and confidence objects. The adapter maps eye_contact.eye_contact_pct, eye_contact.face_detected_pct, posture.avg_posture_score, and movement-related values into the dashboard's numeric fields. The full nested source report is preserved under cv_module_report.

The current CV module reports several movement percentages, not one native movement score. For dashboard compatibility, movement_score is a clearly-labelled proxy derived from fidgeting and face-touch percentages. It should be reviewed with the team before being treated as a comparable performance score.

**Member 3 — NLP / content analysis**

The output from build_analysis_result(text, topic) includes content_score, suggestions, and detailed analysis. The adapter maps suggestions to content_suggestions and uses content_score as the report's content score. Detailed source output remains available in **Report data**.

**Important limitation:** JSON import connects the outputs; it does not automatically start the microphone or webcam, and it does not run the NLP analyzer for you. The teammate modules must be run separately to generate real outputs. A later integration can have each module submit results directly to the API.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | / | Backend information |
| GET | /api/health | Check whether the API is running |
| POST | /api/sessions | Create a session, optionally with module results |
| GET | /api/sessions | List up to 100 recent sessions |
| GET | /api/sessions/<session_id> | Retrieve one report |
| PATCH | /api/sessions/<session_id> | Merge results from one or more modules and recalculate scores |

### API payload format

Create a session with POST http://127.0.0.1:5000/api/sessions:

~~~json
{
  "presenter_name": "Jessika",
  "topic": "Cybersecurity Awareness",
  "speech": {
    "transcript": "Today I will discuss safe passwords.",
    "speaking_time_seconds": 30,
    "words_per_minute": 100,
    "pause_count": 2,
    "filler_word_count": 1
  },
  "computer_vision": {
    "face_visibility": 90,
    "eye_contact": 75,
    "posture_score": 85,
    "movement_score": 80
  },
  "nlp": {
    "keyword_score": 80,
    "content_relevance": 88,
    "vocabulary_score": 75,
    "repetition_score": 90,
    "content_suggestions": ["Add one real-world example."]
  }
}
~~~

Modules can also submit results individually using PATCH and the same session ID. The top-level keys are speech, computer_vision, and nlp.

## Score definitions

- Speech score: averages the available speaking-pace heuristic and filler words per 100 transcript words.
- Computer-vision score: average of the available normalized computer-vision fields.
- NLP score: uses the native content_score when provided; otherwise, averages available NLP component scores.
- Overall score: average of the available category scores. Missing modules are not counted as zero.
- Pause count and speaking duration are displayed but not included in the score.

Treat the overall number as a **starter score**, not a scientifically validated rating. Review scoring weights and the computer-vision movement proxy with the team.

## Troubleshooting

- If the dashboard cannot connect, keep the Flask backend running in a separate PowerShell window.
- The default backend address is http://127.0.0.1:5000.
- The local SQLite database is created automatically under data/; do not commit it to Git.
