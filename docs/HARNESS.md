# AGAD Harness Design

> **Purpose of this doc:** to describe AGAD as a *harness engineering* project, not just a multi-agent system. This is a self-audit against the three harnesses defined in the Kaggle 5-Day Agents Intensive Vibecoding Course (Day 1): **context**, **constraint**, and **evaluation**.
>
> **Why this matters:** the harness is the scaffolding around the LLM. The harness is what turns a chatbot into a trustworthy agent. A well-designed harness is portable across models; a poorly designed one collapses the moment the model changes.

---

## Summary

| Harness | Current state | Confidence |
|---|---|---|
| **Context harness** | Session-scoped, schema-driven, single source of truth | Solid for v1 |
| **Constraint harness** | 7-layer security stack + HITL gate + task-based routing with fallback | Strong — the standout layer |
| **Evaluation harness** | 37 automated tests across 6 color lanes, offline, no API cost | Strong for v1 |

**Honest read:** AGAD's constraint and evaluation harnesses are more mature than its context harness. That's a deliberate v1 trade-off. The v2 direction is to deepen context (memory, persistence) without weakening the constraint layer.

---

## 1. Context Harness

> *How does the agent know what it needs to know?*

The context harness governs what the agents can see, remember, and retrieve. It sets the bounds of the agent's world.

### What AGAD does today

- **Single-session source of truth.** One patient conversation captures every field. The document generator agent reads from this one session record for all 4 department forms. No re-entry, no reconciliation.
- **Schema-driven per-department context.** `references/department-field-requirements.json` defines the exact fields required for each department. The document generator only sees fields relevant to the requested form.
- **Declarative skill registry.** `mcp/local-mcp.yaml` documents the tools each agent has access to and their file bindings. This is MCP-style — declarative, not a full stdio MCP server.
- **Slot-filling conversational state.** The intake agent tracks which required fields are captured vs missing across turns, and drives the conversation to close the gaps.

### Why these choices

- Session-scoped state is enough for a single-visit workflow. It also keeps the security boundary tight — nothing persists beyond the visit.
- Schema-driven context prevents prompt bloat. The generator never sees fields it doesn't need.
- A declarative skill registry was chosen over a full MCP server for v1 because it's inspectable, testable, and doesn't require running a separate process.

### Honest gaps

- **No long-term memory.** Once the session ends, the patient's context is gone. Returning patients start from zero.
- **No retrieval layer.** There's no RAG over hospital SOPs, past cases, or clinical guidelines. All context is conversational.
- **No cross-session state.** Multi-visit journeys (e.g., admission → discharge → follow-up) aren't stitched together.

### v2 direction

- Add opt-in session persistence with clear consent + expiry
- Add a small retrieval layer for HMO/insurance policy language
- Replace the declarative MCP registry with a full stdio MCP server

---

## 2. Constraint Harness

> *How is the agent prevented from doing bad things?*

The constraint harness is the safety, security, and governance layer. It's what makes the agent safe to point at a real workflow. This is AGAD's strongest layer.

### What AGAD does today

**7-layer security stack:**

1. **Consent gate** — UI blocker in `streamlit_app.py` prevents any agent from running without patient consent
2. **PII redaction** — `redact_pii` strips SSN, credit card, and email from inputs before they reach the model
3. **Prompt-injection filter** — `sanitize_input` filters known attack patterns
4. **Rate limiting** — `rate_limited` caps at 10 requests per 60 seconds per session
5. **Department whitelist** — `is_allowed_department` restricts document generation to approved forms
6. **Empty-input filter** — `is_empty` blocks null-payload attacks
7. **Audit log** — every action logged and visible in the sidebar

**Human-in-the-loop gate:**

- `run_document_generator` never returns a `FINAL` status unless a human clicks Approve AND every required field is present
- This is a *deterministic* gate, not an LLM judgment — it can't be jailbroken because the LLM isn't asked
- Directly proven by `test_hitl_gate_blocks_missing_fields` in `tests/test_red.py`

**Task-based LLM routing with fallback:**

- Each task is bound to its primary provider (Groq)
- On provider error, the router degrades to Google Gemini 2.5 Flash for that single call
- Bindings never silently change on the user — the fallback is scoped and observable

### Why these choices

- Healthcare is a regulated environment. A single unchecked LLM output could produce an unsafe or non-compliant document.
- Deterministic gates (HITL, whitelist, rate limit) sit *outside* the LLM's decision surface. Attackers can't argue with them.
- Fallback bindings ensure the app degrades gracefully instead of failing loudly. But the fallback is scoped — no silent model drift.

### Honest gaps

- **No output validation against clinical schemas.** The generator produces a document; there's no downstream check that clinical fields make clinical sense.
- **No policy engine.** All constraints are hardcoded in Python. A policy layer (OPA, CEL) would let non-engineers change rules.
- **No adversarial red-team automation.** The red-lane tests are static. There's no fuzz-driven or LLM-generated attack pipeline.

### v2 direction

- Add JSON Schema + Pydantic output validation on every generator response
- Add a small policy layer for department-specific rules (e.g., "HMO forms require member ID validation before FINAL")
- Add an adversarial harness that generates novel prompt-injection variants weekly

---

## 3. Evaluation Harness

> *How do you prove the agent works?*

The evaluation harness is what makes the system provable. Without it, "it works on my machine" is the strongest claim you can make.

### What AGAD does today

**37 automated tests across 6 color lanes:**

- **Green** — happy paths, schemas, defaults
- **Blue** — defensive: missing keys, fallback binding behaviour
- **Yellow** — chaos: 500s, timeouts, backoff logic
- **Purple** — cross-node contract, full-graph happy path
- **Red** — injection, HITL bypass, key leak, token bomb, PII
- **White + Brown** — sanitizers, unicode, Tagalog + English fuzz

**Test properties:**

- All 37 tests run offline — no API cost, no external dependency
- Deterministic — no LLM-in-the-loop for pass/fail (the LLM is mocked at the boundary)
- Fast — full suite runs in seconds via `pytest -v tests/`
- Evidence-visible — pass/fail record captured in `TEST_REPORT.md`

**Design pivot evidence:**

- The v0 → v1 pivot is itself an evaluation output. The v0 thesis (diagnosis wording detection) was tested against real patient interview data and rejected: 0/3 respondents mentioned wording as a pain point.
- The v1 thesis (repetitive re-entry) was independently and convergently reported by 3/3 respondents.
- This qualitative eval reshaped the entire project. It's documented in `design.md` section 5.

### Why these choices

- Color-lane organization forces coverage across failure *categories*, not just line-count. It prevents the "100 tests but only 2 code paths" trap.
- Offline-only tests keep the eval loop tight and CI-safe. Rubric reviewers can run them cost-free.
- Deterministic gating on HITL means the eval can *prove* the safety invariant, not just observe it holding.

### Honest gaps

- **No end-to-end eval on the live model.** All tests mock the LLM. There's no measurement of actual model output quality on real inputs.
- **No regression tracking over time.** Test outcomes aren't recorded across model versions or prompt changes.
- **No user-facing quality metrics.** There's no dashboard for "how often does intake complete on the first try?" or "how often does HITL reject a draft?"

### v2 direction

- Add a small **golden dataset** (20–30 hand-crafted patient conversations) and score generator outputs against expected schema
- Add **regression tracking** — every commit runs the golden set and records deltas
- Add **production observability** — trace which agent called which tool, which fallbacks fired, which HITL decisions were made

---

## The Three Harnesses Together

A well-designed harness is coherent — the three layers reinforce each other:

- The **context harness** decides *what the agent sees.* Narrow context → tighter constraints → simpler evals.
- The **constraint harness** decides *what the agent can do.* Strong constraints → smaller failure surface → smaller eval matrix.
- The **evaluation harness** decides *what the agent has proven.* Good evals feed back into context tightening and constraint hardening.

AGAD v1 leans hardest on **constraints and evaluation** because the domain (healthcare) demands it. v2 will deepen **context** without weakening the other two.

---

## What This Means for AGAD's Growth Path

Mapping this back to the 16-week learning plan:

| Week | Harness area | Deliverable |
|---|---|---|
| 2 | Context — document current harness | This file (`HARNESS.md`) |
| 3 | Context — tools & interop | Add one new tool integration |
| 4 | Context — memory | Add lightweight session memory |
| 6 | Evaluation — deepen | Build 20-case golden set + scoring |
| 7 | Constraint + Evaluation — observability | Add production trace logging |
| 12 | Constraint — schema hardening | JSON Schema + Pydantic validation on generator outputs |

Every future AGAD improvement can be located on this map. That's the point of doing this audit now.

---

## References

- Kaggle 5-Day Agents Intensive Vibecoding Course, Day 1 (Foundations)
- AGAD `README.md`
- AGAD `design.md` (v0 → v1 pivot reasoning)
- AGAD `TEST_REPORT.md` (37-test evidence)
- AGAD `SKILL.md` (agent skill documentation)