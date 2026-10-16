# AI Presentation Coach

**One combined report for Speech Analysis, Computer Vision and NLP feedback.** The Flask API stores modules under one Session ID in SQLite; the Streamlit dashboard shows aggregated scores, detailed analysis and report history.

> Scores are starter heuristics, not a scientifically validated measure of presentation ability.

## Project team
- **K Jessika Santhosh (Member 4 — backend integration and dashboard):** [@Kjessika67](https://github.com/Kjessika67)
- **Chaithra S:** [@chaithra-chaii](https://github.com/chaithra-chaii)
- **Arsha S:** [@arshasunil06-cyber](https://github.com/arshasunil06-cyber)
- **Adhulya V:** [@adhulyav](https://github.com/adhulyav)

## Modules
- **Speech:** browser microphone capture, live transcript, speaking time, WPM, pauses and filler words.
- **Computer Vision:** webcam eye contact, posture, gesture and confidence analysis.
- **NLP:** content scoring, strengths, areas to improve and suggestions.
- **Combined report:** Flask API, SQLite session history and Streamlit dashboard.

## Run locally (Windows PowerShell)
From project root, install dependencies and CV models:
```powershell
python -m pip install -r requirements.txt
python -m pip install -r computer_vision\requirements.txt
python computer_vision\download_models.py
```
Start Flask in PowerShell window 1:
```powershell
python backend\app.py
```
Open http://127.0.0.1:5000/ or Speech Analysis at http://127.0.0.1:5000/speech/. Finish speaking and click **Send results to dashboard**. NLP feedback is generated from the saved transcript.

Start dashboard in PowerShell window 2:
```powershell
python -m streamlit run dashboard\app.py
```
Open the Streamlit URL, normally http://localhost:8501.

## Save every module under the same Session ID
1. Run Speech Analysis and click **Send results to dashboard**. Copy the Session ID shown.
2. Run CV: `python computer_vision\analyzer.py`. Press **C** to calibrate and **Q** to finish. The analyzer saves `data/computer_vision_report.json`.
3. In Streamlit, expand **Import or attach module results**, choose **Attach to an existing session ID**, paste that ID, upload the CV JSON and click **Attach results to this session**.
4. The dashboard updates the existing session; it does not create a duplicate. Speech and NLP remain under the original ID.

For a new report from JSON exports, upload all available module files and choose **Create a new combined report**.

## Project layout
```text
index.html                  Landing page and team profile links
speech_to_text/             Browser speech analysis
computer_vision/             Webcam analyzer and model downloader
NLP/                         Content analysis and feedback generation
backend/app.py               Flask API, session storage and NLP integration
backend/module_adapters.py   Normalize module result formats
dashboard/app.py             Combined Streamlit report
tests/                       Adapter and integration tests
sample_data/                 Example JSON payloads
data/                        Local database and CV report
```

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | / | Landing page |
| GET | /speech/ | Speech UI |
| GET | /api/health | Health check |
| POST | /api/sessions | Create session |
| GET | /api/sessions | List reports |
| GET | /api/sessions/<session_id> | Retrieve report |
| PATCH | /api/sessions/<session_id> | Attach module results to existing session |

Run tests with `python -m unittest discover -s tests -v`.
