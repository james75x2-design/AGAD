# AGAD Skill Specification

This repository uses a simple skill to configure the intake and document generation workflow for hospital departments.

## Purpose

- Define which fields are required by each department.
- Provide the text template for department-specific pre-filled documents.
- Support the Document Generator Agent in producing human-reviewable drafts.

## Structure

`references/department-field-requirements.json` contains one entry per department/form type:

- `required_fields`: list of baseline field names extracted during intake.
- `display_template`: a simple format string used to render the pre-filled document.

## Supported fields

The intake flow currently captures the following fields:

- `Name`
- `Member_ID`
- `Company`
- `Diagnosis`
- `Procedures`

These fields are intentionally lightweight and aligned to the strongest evidence from the interview data: repetitive re-entry of ID, insurance, and symptoms across departments.

## Usage

The Document Generator Agent calls `run_document_generator(target_department, extracted_slots, config)` with:

- `target_department` selected by the user
- `extracted_slots` populated by the Intake Capture Agent
- `config` loaded from `references/department-field-requirements.json`

The agent must render a department-specific document draft and report any missing required fields.
