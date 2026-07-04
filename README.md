# 🏥 AGAD: Assisted Generation of Approval Documents

A multi-agent system reducing repetitive hospital intake paperwork through unified data capture — collect once, generate department-specific documents, human-approve before finalization.

## 🏗️ Architecture

Three-node ADK 2.0 graph with task-based LLM routing:

- **Node 1 — Intake Capture Agent** (Groq · llama-3.3-70b-versatile · text)
- **Node 2 — Document Generator Agent** (Groq · per-department documents)
- **Node 3 — Vision/OCR Agent** (Gemini · gemini-2.5-flash · uploads)
- **HITL Gate** — Human approval required before any document is finalized

## 🔐 Security — 7 Defense Layers

1. Consent banner (demo disclaimer)
2. PII regex screening
3. Prompt-injection guard
4. Per-session rate limit
5. Field whitelist enforcement
6. Empty-value filtering
7. Timestamped audit log

See `TEST_REPORT.md` for the 37-test verification suite.

## 🚀 Deploy

1. Fork this repo
2. Deploy on https://share.streamlit.io
3. In App Settings → Secrets, add:
   ```
   GROQ_API_KEY = "your-groq-key"
   GEMINI_API_KEY = "your-gemini-key"
   ```
4. Done!

## 🔑 Get API Keys

- **Groq** (free): https://console.groq.com/keys
- **Gemini** (free): https://aistudio.google.com/apikey

## 🧪 Local Development

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Fill in your API keys in secrets.toml
streamlit run streamlit_app.py
```

## 📖 Design Reference

See `design.md` for the evidence base, interview findings, and architectural decisions.

## ⚠️ Important

This is a **capstone demo**. Do NOT enter real patient information. The app uses free-tier LLM APIs which may use inputs for model improvement.