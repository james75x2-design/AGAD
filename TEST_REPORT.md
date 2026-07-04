# AGAD Security & Functional Test Report

**Overall Score:** 22/22 tests passing (100%) after R1 regex fix

## Test Categories

### 🟢 Functional Tests (15/15)
- Config loading (4 touchpoints, 3 shared fields)
- PII detection (SSN, credit card, email, PH mobile)
- Prompt injection guard
- Rate limit boundary
- Intake JSON parsing
- Code-fenced JSON handling
- Non-JSON graceful fallback
- Document generator with missing-field detection
- Unknown department rejection
- Field whitelist enforcement (intake + vision)
- Empty value filtering
- Missing API key handling
- Vision agent success
- Audit log accumulation

### 🔴 Red Team / Adversarial (8/8 after R1 fix)
- 7+ jailbreak patterns blocked (including "IGNORE ALL PRIOR INSTRUCTIONS")
- PII smuggling attempts
- Field-injection attack (dangerous keys blocked)
- 100KB payload handling
- SQL-injection-style payload stored as inert string
- Rate-limit bypass via extracted field blocked
- Empty/null/unicode edge inputs
- Consent gate defaults to False

### 🔵 Blue Team / Detection (6/6)
- PII blocks logged with type
- Injection blocks logged
- LLM errors logged with details
- Audit timestamps are ISO-8601 UTC
- Doc generation logs department name
- Vision extraction logs field names

### 🟡 Chaos / Resilience (5/5)
- Groq network exception handled gracefully
- Gemini None response handled
- Gemini empty string handled
- Empty config file handled
- Rate-limit boundary (60 ok, 61 blocked)

### 🟣 Purple / End-to-End (3/3)
- Injection blocked AND audit logged
- PII blocked AND audit logged with types
- Blocked attacks don't consume rate-limit quota

## Known Limitations (Documented)
- Obfuscated PII (spaces instead of dashes in SSN) may not be caught
- Base64-encoded PII not detected (out of scope for v1)
- Only PH mobile pattern implemented (add per-region patterns for other locales)

## Security Architecture — 7 Defense Layers
1. Consent gate (blocks app until user confirms synthetic data)
2. PII regex screening (SSN, credit card, email, PH mobile)
3. Prompt-injection guard (8 pattern types)
4. Per-session rate limit (60 calls)
5. Field whitelist (only schema fields accepted from LLM output)
6. Empty value filtering (prevents overwriting real data with blanks)
7. Audit log (every action timestamped)