# AGAD — Assisted Generation of Approval Documents

AGAD is a Streamlit demo of a multi-agent assisted intake and document generation workflow for hospital approval paperwork.

## What it does

- Captures patient intake data once through a conversational flow
- Uses that data to pre-fill department-specific approval documents
- Requires human review before finalizing any document

## How it works

- `streamlit_app.py` contains the intake UI and document generator UI
- `references/department-field-requirements.json` defines department templates and required fields
- `SKILL.md` describes the document-generation skill mapping
- `design.md` documents the evidence-based pivot and project scope

## Running locally

1. Activate the Python environment
   ```bash
   source /workspaces/AGAD/venv/bin/activate
   ```

2. Set the Gemini API key
   - Option 1: use Streamlit secrets in `.streamlit/secrets.toml`
   - Option 2: export the environment variable
     ```bash
     export GEMINI_API_KEY="YOUR_ACTUAL_KEY"
     ```

3. Run the app
   ```bash
   streamlit run streamlit_app.py
   ```

## Secrets handling

- Do not commit real API keys.
- Add only placeholders to `.streamlit/secrets.toml` if the file exists locally.
- Prefer using an environment variable in shell sessions for local testing.

## Local MCP support

A minimal local MCP reference artifact is included in `mcp/local-mcp.yaml` and explained in `mcp/README.md`.

It documents how repository artifacts map to a local agent tool interface for evaluation and reviewer inspection.

A dedicated unit test (`tests/test_mcp_yaml.py`) validates that `mcp/local-mcp.yaml` is valid YAML and contains the expected MCP metadata.

## Evaluation coverage

This project includes:

- Defensive external API handling in `streamlit_app.py`
- Unit tests for intake agent behavior and document generation
- GitHub Actions CI for automated `pytest -q` runs
- Local MCP reference documentation in `mcp/local-mcp.yaml`
- Design and skill artifacts to support rubric-aligned form generation

## Testing

Run tests with:

```bash
pytest -q
```

## CI

GitHub Actions runs `pytest -q` on push and pull request to `main`.

## Notes

This version is intentionally scoped around one strong user problem: repetitive paperwork and redundant data entry across departments. It does not attempt to predict denials or diagnose insurance adjudication risk.
