# AGAD Design Reference

## 1. Project Summary

AGAD captures a patient’s intake details once and uses them to generate department-specific approval documents. The goal is to reduce redundant manual paperwork across hospital departments and present each generated document for human approval before finalization.

## 2. Evidence Base

The design is based on the interview convergence documented in the original project notes:

- Repetitive manual data entry across departments: high confidence
- Desire for automated self-service intake: high confidence
- Uncertainty about approval/cost status: medium confidence
- Billing before insurance verification: low confidence
- Diagnosis wording as denial risk: retired due to lack of evidence

## 3. Feature Scope

### Core features

- Single intake conversation for session-wide patient data capture
- Department-specific document generation from shared session data
- Human approval gate before finalizing any document

### Secondary feature

- Process status visibility to reduce wait-time uncertainty

### Out of scope for this capstone version

- Diagnosis-wording / denial prediction
- Real HMO adjudication or production insurance integrations
- Full cloud production infrastructure
- Custom MCP server protocol

## 4. Architecture

### Implemented components

- `streamlit_app.py`
  - Intake Capture Agent
  - Document Generator Agent
  - Human approval gate

- `references/department-field-requirements.json`
  - Department form rules and templates

- `SKILL.md`
  - Skill mapping description for form generation

- `tests/`
  - Mocked intake-agent compatibility test
  - Smoke test for document rendering

- `.github/workflows/ci.yml`
  - CI test automation

## 5. Next steps

- Complete the ADK graph in the app if possible (Intake → Document Generator → optional Status Agent)
- Add a status/progress view for patient wait-time uncertainty
- Refine the `references/` templates and add more accurate department field mappings if more data becomes available
