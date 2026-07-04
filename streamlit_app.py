"""
AGAD — Assisted Generation of Approval Documents
Streamlit Capstone Demo

Design reference : design.md (Sections 1–4)
Field mapping    : references/department-field-requirements.json

Task-Based LLM Routing:
  - Groq   (llama-3.3-70b-versatile)  -> text chat, slot-fill, doc generation
  - Gemini (gemini-2.5-flash)          -> uploaded images / PDFs (vision + OCR)
"""

import streamlit as st
import json
import os
import logging
import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="AGAD Portal — Capstone Demo", layout="wide")
st.title("🏥 AGAD: Assisted Generation of Approval Documents")
st.caption("Unified intake -> auto-generated department docs -> human sign-off.")

# ========== SECRETS ==========
def _get_secret(name: str) -> str:
    try:
        v = st.secrets.get(name)
        if v:
            return v
    except Exception:
        pass
    return os.environ.get(name, "")

GROQ_API_KEY   = _get_secret("GROQ_API_KEY")
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")

# ========== LOGGER ==========
logger = logging.getLogger("agad")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

# ========== FIELD REQUIREMENTS ==========
@st.cache_data
def load_field_requirements() -> dict:
    try:
        with open("references/department-field-requirements.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Missing references/department-field-requirements.json")
        return {"touchpoints": [], "shared_fields_across_touchpoints": []}

DEPT_CONFIG   = load_field_requirements()
TOUCHPOINTS   = DEPT_CONFIG.get("touchpoints", [])
SHARED_FIELDS = DEPT_CONFIG.get("shared_fields_across_touchpoints", [])
ALL_FIELDS    = sorted({f["field"] for tp in TOUCHPOINTS for f in tp.get("fields", [])})

# ========== SAFEGUARDS ==========
PII_PATTERNS = {
    "SSN-like":    r"\b\d{3}-\d{2}-\d{4}\b",
    "Credit Card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "Email":       r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
    "PH Mobile":   r"(\+63|0)9\d{9}\b",
}

# R1 FIX: broader injection patterns to catch multi-word variants
INJECTION_PATTERNS = [
    r"ignore\s+(?:\w+\s+){0,3}instructions?",
    r"disregard\s+(?:\w+\s+){0,3}(?:instructions?|prompt|rules)",
    r"forget\s+(everything|your\s+instructions|all\s+prior)",
    r"you\s+are\s+now\s+",
    r"system\s+prompt",
    r"reveal\s+(your|the)\s+(prompt|instructions)",
    r"</?(system|instruction)>",
    r"jailbreak|dan\s+mode|developer\s+mode",
]
RATE_LIMIT_PER_SESSION = 60

def detect_pii(t: str) -> Listif not t:
        return []
    return [n for n, p in PII_PATTERNS.items() if re.search(p, t)]

def is_prompt_injection(t: str) -> bool:
    if not t:
        return False
    return any(re.search(p, t, re.IGNORECASE) for p in INJECTION_PATTERNS)

def check_rate_limit() -> bool:
    return st.session_state.get("call_count", 0) < RATE_LIMIT_PER_SESSION

def bump_rate_limit():
    st.session_state.call_count = st.session_state.get("call_count", 0) + 1

# ========== SESSION STATE ==========
def init_state():
    ss = st.session_state
    ss.setdefault("consent_given", False)
    ss.setdefault("patient_record", {f: "" for f in ALL_FIELDS})
    ss.setdefault("messages", [{
        "role": "agent",
        "text": ("Welcome to the AGAD Intake Portal. To avoid asking you the "
                 "same details at every department, I'll collect what's needed "
                 "just once. Could we start with your full name and what brings "
                 "you to the hospital today?")
    }])
    ss.setdefault("drafts", {})
    ss.setdefault("audit_log", [])
    ss.setdefault("call_count", 0)

def audit(event: str, details: Optional[dict] = None):
    st.session_state.audit_log.append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "details": details or {},
    })

init_state()

# ========== CONSENT GATE ==========
if not st.session_state.consent_given:
    st.warning(
        "⚠️ **CAPSTONE DEMO — USE SYNTHETIC / TEST DATA ONLY**\n\n"
        "This app sends conversation text to Groq and uploaded images/PDFs "
        "to Gemini. Free-tier traffic may be used by providers to improve "
        "their models. Do NOT enter real patient information."
    )
    if st.button("✅ I understand — use synthetic data only", type="primary"):
        st.session_state.consent_given = True
        audit("consent_given")
        st.rerun()
    st.stop()

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ Session Controls")
    st.markdown("**API status**")
    st.markdown(f"- Groq (text): {'✅' if GROQ_API_KEY and Groq else '❌'}")
    st.markdown(f"- Gemini (vision): {'✅' if GEMINI_API_KEY and genai else '❌'}")
    st.markdown("---")
    st.metric("LLM calls used", f"{st.session_state.call_count}/{RATE_LIMIT_PER_SESSION}")
    st.progress(min(st.session_state.call_count / RATE_LIMIT_PER_SESSION, 1.0))
    st.markdown("---")
    if st.button("🗑️ End session & wipe data"):
        audit("session_wiped")
        for k in list(st.session_state.keys()):
            if k != "consent_given":
                del st.session_state[k]
        st.rerun()
    with st.expander("📜 Audit log"):
        for e in st.session_state.audit_log[-20:]:
            st.caption(f"`{e['ts']}` — {e['event']}")

# ========== LLM CALLERS ==========
@st.cache_resource
def get_groq_client():
    if not GROQ_API_KEY or Groq is None:
        return None
    return Groq(api_key=GROQ_API_KEY)

def call_groq_text(system: str, user: str,
                   model: str = "llama-3.3-70b-versatile"
                   ) -> Tuple[Optional[str], Optional[str]]:
    client = get_groq_client()
    if client is None:
        return None, "Groq unavailable (missing key or SDK)"
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            temperature=0.2,
            max_tokens=900,
        )
        return r.choices[0].message.content, None
    except Exception as e:
        logger.exception("Groq call failed")
        return None, f"Groq error: {e}"

@st.cache_resource
def get_gemini_vision():
    if not GEMINI_API_KEY or genai is None:
        return None
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-2.5-flash")

def call_gemini_vision(prompt: str, file_bytes: bytes, mime_type: str
                       ) -> Tuple[Optional[str], Optional[str]]:
    model = get_gemini_vision()
    if model is None:
        return None, "Gemini unavailable (missing key or SDK)"
    try:
        r = model.generate_content(
            [prompt, {"mime_type": mime_type, "data": file_bytes}],
            generation_config={"temperature": 0.1, "max_output_tokens": 800},
        )
        return r.text, None
    except Exception as e:
        logger.exception("Gemini vision call failed")
        return None, f"Gemini error: {e}"

# ========== NODE 1: INTAKE AGENT ==========
INTAKE_SYSTEM = f"""You are AGAD's Intake Capture Agent for a Philippine hospital.
Collect the following fields ONCE, then confirm and stop.
Fields: {json.dumps(ALL_FIELDS)}
Prioritize shared fields first: {SHARED_FIELDS}

Rules:
1. Ask ONE clarifying question at a time.
2. Warm, concise, professional. No medical advice.
3. NEVER echo back sensitive data in full.
4. When you have enough, say "Ready to generate documents."
5. Respond in STRICT JSON only:
{{"assistant_reply":"...","extracted":{{"<field>":"<value>"}},"ready":true|false}}
"""

def run_intake_agent(user_input: str) -> Tuple[str, Dict[str, str], bool]:
    if not check_rate_limit():
        return "Session limit reached. End session to reset.", {}, False
    history = "\n".join(f"{m['role']}: {m['text']}"
                        for m in st.session_state.messages[-8:])
    user = (f"Conversation so far:\n{history}\n\n"
            f"Latest user input:\n{user_input}\n\n"
            f"Current patient record:\n"
            f"{json.dumps(st.session_state.patient_record, indent=2)}")
    reply, err = call_groq_text(INTAKE_SYSTEM, user)
    bump_rate_limit()
    if err:
        audit("intake_error", {"error": err})
        return f"⚠️ Intake unavailable ({err}).", {}, False
    extracted, ready, msg = {}, False, reply
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", reply.strip(),
                         flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        msg = data.get("assistant_reply", reply)
        extracted = {k: v for k, v in data.get("extracted", {}).items()
                     if k in ALL_FIELDS and v}
        ready = bool(data.get("ready", False))
    except json.JSONDecodeError:
        logger.info("Intake reply not JSON; using raw text")
    audit("intake_turn", {"fields": list(extracted.keys()), "ready": ready})
    return msg, extracted, ready

# ========== NODE 2: DOC GENERATOR ==========
def get_touchpoint(name: str) -> Optionalreturn next((tp for tp in TOUCHPOINTS if tp["department"] == name), None)

def run_document_generator(department: str
                           ) -> Tuple[str, List[str], Optional[str]]:
    tp = get_touchpoint(department)
    if tp is None:
        return "", [], f"Unknown department: {department}"
    required = [f["field"] for f in tp.get("fields", [])]
    record   = st.session_state.patient_record
    missing  = [f for f in required if not record.get(f)]
    if not check_rate_limit():
        return "", missing, "Session limit reached."
    system = (f"You are AGAD's Document Generator Agent. Produce a professional "
              f"draft '{tp['document_type']}' for the '{department}' desk, "
              f"using ONLY the patient record provided. "
              f"If a required field is missing, insert [MISSING: field_name] — "
              f"do NOT invent values. End with a 'For Human Review & Approval' block.")
    user = (f"Document type: {tp['document_type']}\n"
            f"Required fields: {required}\n"
            f"Patient record:\n{json.dumps(record, indent=2)}")
    draft, err = call_groq_text(system, user)
    bump_rate_limit()
    if err:
        audit("doc_gen_error", {"department": department, "error": err})
        return "", missing, err
    audit("doc_generated", {"department": department, "missing": len(missing)})
    return draft, missing, None

# ========== NODE 3: VISION (Gemini) ==========
def run_vision_agent(file_bytes: bytes, mime_type: str
                     ) -> Tuple[Dict[str, str], Optional[str]]:
    if not check_rate_limit():
        return {}, "Session limit reached."
    prompt = ("You are extracting patient intake data from an uploaded document. "
              f"Return STRICT JSON using keys from: {ALL_FIELDS}. "
              'Schema: {"extracted":{"<field>":"<value>"}}')
    raw, err = call_gemini_vision(prompt, file_bytes, mime_type)
    bump_rate_limit()
    if err:
        audit("vision_error", {"error": err})
        return {}, err
    if not raw:
        return {}, "Empty vision response"
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(),
                         flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        extracted = {k: v for k, v in data.get("extracted", {}).items()
                     if k in ALL_FIELDS and v}
        audit("vision_extracted", {"fields": list(extracted.keys())})
        return extracted, None
    except json.JSONDecodeError:
        return {}, "Could not parse vision output as JSON."

# ========== UI ==========
left_col, right_col = st.columns([1, 1])

with left_col:
    st.header("🤖 Intake Capture Agent")
    st.caption("Node 1 · Groq (text)  •  Node 3 · Gemini (uploads)")
    with st.expander("📎 Upload ID / HMO card / PDF (optional)"):
