# AI Presentation Coach

Member 4 module: Flask backend, SQLite session storage, integration API, score aggregation, and Streamlit dashboard.

> **Note:** The scores in this starter are simple, explainable demo heuristics. They are not a validated measure of presentation ability. Agree on metric definitions and score scales with all teammates before relying on the report.

## Project structure

\`\`\`text
ai-presentation-coach/
├── backend/
│   └── app.py
├── dashboard/
│   └── app.py
├── sample_data/
│   └── session-example.json
├── data/                 # Created automatically; local SQLite file is ignored by Git
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
\`\`\`

## Run locally on Windows

1. Install Python 3.10 or newer.
2. Open this repository folder in VS Code.
3. In the VS Code terminal, run:

\`\`\`powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
\`\`\`

Start the backend in Terminal 1:

\`\`\`powershell
python backend/app.py
\`\`\`

Test it in your browser: http://127.0.0.1:5000/api/health

Start the dashboard in Terminal 2. Activate the same virtual environment first:

\`\`\`powershell
streamlit run dashboard/app.py
\`\`\`

The dashboard opens in your browser. Use **Create demo report** to populate an example report. The demo does not analyze real audio or video.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | \`/\` | Backend information |
| GET | \`/api/health\` | Check whether the API is running |
| POST | \`/api/sessions\` | Create a presentation session, optionally with all module results |
| GET | \`/api/sessions\` | List up to 100 recent sessions |
| GET | \`/api/sessions/<session_id>\` | Retrieve one report |
| PATCH | \`/api/sessions/<session_id>\` | Merge results from one or more modules and recalculate scores |

### 1. Create a session

Send JSON to \`POST http://127.0.0.1:5000/api/sessions\`:

\`\`\`json
{
  "presenter_name": "Jessika",
  "topic": "Cybersecurity Awareness"
}
\`\`\`

Save the returned \`session.id\`. Each module can submit its results later using the same ID.

### 2. Submit speech results

Send JSON to \`PATCH http://127.0.0.1:5000/api/sessions/<session_id>\`:

\`\`\`json
{
  "speech": {
    "transcript": "Today I will discuss safe passwords.",
    "speaking_time_seconds": 30,
    "words_per_minute": 100,
    "pause_count": 2,
    "filler_word_count": 1
  }
}
\`\`\`

### 3. Submit computer-vision results

\`\`\`json
{
  "computer_vision": {
    "face_visibility": 90,
    "eye_contact": 75,
    "posture_score": 85,
    "movement_score": 80
  }
}
\`\`\`

### 4. Submit NLP results

\`\`\`json
{
  "nlp": {
    "keyword_score": 80,
    "content_relevance": 88,
    "vocabulary_score": 75,
    "repetition_score": 90,
    "content_suggestions": ["Add one real-world example."]
  }
}
\`\`\`

Each of the three module payloads can be sent separately to the same PATCH endpoint. Include the module name as the top-level JSON key. The backend merges submitted fields into the existing results and recalculates available scores.

## Metric contract for teammates

- Speech: \`transcript\` is text; \`speaking_time_seconds\`, \`words_per_minute\`, \`pause_count\`, and \`filler_word_count\` are non-negative numbers. Pause and filler counts must be whole numbers.
- Computer Vision scores: \`face_visibility\`, \`eye_contact\`, \`posture_score\`, and \`movement_score\` are from 0 to 100, where higher means better.
- NLP scores: \`keyword_score\`, \`content_relevance\`, \`vocabulary_score\`, and \`repetition_score\` are from 0 to 100, where higher means better. Define \`repetition_score\` as the ability to avoid unnecessary repetition, not a raw repetition count.
- \`content_suggestions\` must be a list of text strings.
- Omit unavailable values or send \`null\` for optional score fields. Do not send a fake zero to fill a missing value.

## How scores are calculated

- Speech score: averages the available speaking-pace heuristic and filler words per 100 transcript words.
- Computer-vision score: average of the available computer-vision scores.
- NLP score: average of the available NLP scores.
- Overall score: average of whichever category scores are available. Missing modules are not counted as zero.
- Pause count and speaking duration are displayed but not included in the score.

Tune and document these weights with your project team. A raw pause or movement count alone does not say whether the behaviour was appropriate.

## Troubleshooting

- If the dashboard cannot connect, make sure the Flask backend is running in a separate terminal.
- The default backend address is \`http://127.0.0.1:5000\`.
- For a different backend address, set \`PRESENTATION_COACH_API_URL\` before starting Streamlit.
- The local SQLite database is created automatically under \`data/\`; do not commit it to Git.
