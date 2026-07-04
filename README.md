AGAD - Assisted Generation of Approval Documents
A 3-node multi-agent system that eliminates repetitive hospital intake paperwork through unified data capture.

Track: Agents for Good (Healthcare / Public Health)
Live app: https://agad-app.streamlit.app/
Demo video: https://www.youtube.com/watch?v=Jhy9RYAan14
Status: v1 shipped. Multi-agent, task-routed, HITL-gated.

The problem
In Philippine hospitals, patients re-enter the same information (ID, insurance details, allergies, symptoms, medications) at every touchpoint: Admitting, HMO Desk, Triage, and Billing.
We interviewed 3 patients independently. 3 out of 3 flagged this as their core pain point, unprompted:

Interviewee 1 described having to "fall in line and fill up required detail" repeatedly
Interviewee 2 described having to "go to different parts and departments, wait long for release"
Interviewee 3 was asked for ID during triage, then allergies, medications, and symptoms separately

All three, in different words, asked for the same thing: collect it once, use it everywhere.
The solution
AGAD captures a patient's information once through a conversational intake agent. A document generator agent then pre-fills whichever department form is needed (HMO Letter of Authorization, Triage Note, Billing Summary). A hard human-approval gate ensures no document is finalized without human review and complete data.
Why agents and not a form:

Patients do not fill web forms well when they are anxious. A conversational agent adapts.
Different tasks need different models. A task-based router picks the right one.
Regulated environments demand accountability. HITL and audit logs make it provable.

Architecture
docs/agad-architecture.png
Three nodes in an ADK 2.0 graph, all coordinated by a task-based LLM router.

Intake Capture Agent (Groq, llama-3.3-70b-versatile) - conversational slot-filling. Low-latency turns keep the patient engaged.
Document Generator Agent (Groq, llama-3.3-70b-versatile) - per-department pre-fill. Strong JSON mode and template fidelity.
HITL Approval Gate (deterministic) - human-in-the-loop lock. No document reaches FINAL without a human clicking Approve AND all required fields being present.

Task-based LLM routing: each task is bound to its provider (Groq is primary). If that provider errors, the router degrades to Google Gemini 2.5 Flash for that single call. Bindings never silently change on the user.
Supporting components:

Agent Skill: references/department-field-requirements.json defines the schema for each department form.
MCP-style skill registry: mcp/local-mcp.yaml documents which tools the agents use and their file bindings.
Single source of truth: one session record fills every department's form.

Course concepts demonstrated
The rubric requires at least 3. AGAD demonstrates 5.

Multi-agent system (ADK): 3-node graph in streamlit_app.py
MCP Server (local, declarative): mcp/local-mcp.yaml, an MCP-style skill registry
Agent Skills: SKILL.md and references/department-field-requirements.json
Security features: 7-layer stack, red-team proven
Deployability: Streamlit Cloud, pyproject.toml, requirements.txt

Note on MCP: the current version is a declarative MCP-style skill registry, not a full stdio MCP server. It documents the tools the agent uses and their file bindings. A full stdio MCP server is a stated next step.
Security posture (7 layers)

Consent gate before any agent runs (UI blocker in streamlit_app.py)
PII redaction for SSN, credit card, and email (redact_pii)
Prompt-injection filter (sanitize_input)
Rate limiting, 10 requests per 60 seconds per session (rate_limited)
Department whitelist (is_allowed_department)
Empty-input filter (is_empty)
Audit log, visible in the sidebar (audit)

Plus the HITL gate: run_document_generator never returns a FINAL status unless a human clicks Approve AND all required fields are present. This is proven by the test named test_hitl_gate_blocks_missing_fields in tests/test_red.py.
Testing
37 automated tests across 6 color lanes, all passing offline with no API cost.

Green: happy paths, schemas, defaults
Blue: defensive, missing keys, fallback binding
Yellow: chaos - 500s, timeouts, backoff
Purple: cross-node contract and full-graph happy path
Red: injection, HITL bypass, key leak, token bomb, PII
White plus Brown: sanitizers, unicode, Tagalog and English fuzz

Run the full suite with the command: pytest -v tests/
Full pass/fail evidence in TEST_REPORT.md.
Setup for local development
Step 1: Clone the repository with git clone https://github.com/james75x2-design/AGAD.git and then change into the directory with cd AGAD.
Step 2: Create and activate a virtual environment. On macOS or Linux, run python -m venv venv followed by source venv/bin/activate. On Windows, run python -m venv venv followed by venv\Scripts\activate.
Step 3: Install dependencies with pip install -r requirements.txt.
Step 4: Set your API keys as environment variables. On macOS or Linux, run export GROQ_API_KEY=your_key_here and export GEMINI_API_KEY=your_key_here. On Windows PowerShell, use $env:GROQ_API_KEY="your_key_here" and $env:GEMINI_API_KEY="your_key_here".
Step 5: Run the app with streamlit run streamlit_app.py.
Setup for Streamlit Cloud

Fork this repo.
Create a new Streamlit app pointing at streamlit_app.py.
Go to App Settings, then Secrets. Paste your keys in TOML format, one per line: GROQ_API_KEY = "your_key_here" and GEMINI_API_KEY = "your_key_here".
Deploy.

Never commit API keys. The .gitignore file blocks .streamlit/secrets.toml and .env.
Repo layout
Top level files: streamlit_app.py contains the UI plus the 3-node graph plus security plus HITL. SKILL.md documents the agent skill. design.md describes the evidence-based design pivot. TEST_REPORT.md contains test evidence for reviewers. requirements.txt, pyproject.toml, and .gitignore round out the top level.
Folder docs contains agad-architecture.png (the architecture image referenced above).
Folder mcp contains local-mcp.yaml (the MCP-style skill registry) and its own README.md.
Folder references contains department-field-requirements.json which defines 4 departments and is schema-driven.
Folder assets/templates contains form_preview.md.
Folder tests contains conftest.py, test_smoke.py, test_intake_mock.py, and test_mcp_yaml.py.
Project journey
The v0 thesis was that AGAD detects diagnosis wording that causes HMO denial. When we tested that thesis against the actual interview transcripts, 0 out of 3 respondents mentioned wording, phrasing, or anything related to it.
We retired the unsupported feature and rebuilt around the problem that 3 out of 3 respondents actually reported: repetitive re-entry across departments. See design.md section 5 for the full reasoning.
Initial design assumptions about diagnosis-wording risk were tested directly against patient interview data and found unsupported. The project was redesigned around the problem that was independently and convergently reported across all interview respondents.
Roadmap (not shipped in v1)

Status Agent to surface process state and reduce wait-time anxiety (Scenario 3 in design.md, medium-confidence signal, 2/3 respondents)
Full stdio MCP server replacing the declarative YAML registry
Vision agent live in UI: file upload endpoint for ID and insurance card OCR
Cloud production infra: Pub/Sub, Vertex AI Agent Engine, OpenTelemetry

License
MIT
Acknowledgments

Interviewees (anonymized, 3 patients)
Google, Groq, and Kaggle for the Agents Intensive course
Streamlit for making a 3-agent UI a one-file job