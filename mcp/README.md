# Local MCP Configuration for AGAD

This directory contains a minimal `mcp/local-mcp.yaml` file to document how AGAD would expose local agent tools under a Model Context Protocol-style interface.

## Purpose

The repo currently does not run a full MCP server, but this file provides a formal local mapping between agent tools and repository artifacts:

- `references/department-field-requirements.json` — department form field mappings and templates
- `SKILL.md` — AGAD skill documentation for form generation
- `design.md` — project design rationale and evaluation alignment

## How to use it

This is a reference artifact rather than a live server. It can be used by reviewers and extension tooling to understand the intended MCP interface.

Future work could include a lightweight local server that exposes these files via HTTP or a real MCP endpoint.
