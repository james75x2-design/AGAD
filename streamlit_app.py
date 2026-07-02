import streamlit as st
import json
import os
import time
import requests
import logging
import random
import re

# Page configuration setup
st.set_page_config(page_title="AGAD Portal - Capstone Demo", layout="wide")

st.title("🏥 AGAD: Assisted Generation of Approval Documents")
st.caption("Reducing repetitive hospital paperwork through unified data capture via LLM Multi-Agent System.")

# --- Fetch API Token securely from Streamlit secrets or environment variables ---
try:
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
except Exception:
    api_key = os.environ.get("GEMINI_API_KEY", "")

# Logger for diagnostics (writes to app logs, not the UI)
logger = logging.getLogger("agad")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# --- Load Department Configuration File ---
@st.cache_data
def load_field_requirements():
    try:
        with open("references/department-field-requirements.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Missing references/department-field-requirements.json file.")
        return {}

dept_config = load_field_requirements()

# --- Initialize Shared Memory Session State Cache ---
if "patient_data" not in st.session_state:
    st.session_state.patient_data = {
        "Name": "",
        "Member_ID": "",
        "Company": "",
        "Diagnosis": "",
        "Procedures": ""
    }

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "agent", "text": "Welcome to the AGAD Intake Portal. I'm your processing assistant. Could you please provide your full name and what brings you to the hospital today?"}
    ]

# =====================================================================
# 🛠️ ADK 2.0 GRAPH ARCHITECTURE NODES
# =====================================================================

# --- NODE 1: Intake Capture Agent ---
def run_intake_agent(user_input, history, current_slots):
    # Read API key at call time to allow tests or runtime env changes
    key = os.environ.get("GEMINI_API_KEY", "") or api_key
    if not key:
        # Provide a clear, non-exception path when API key is missing
        return "⚠️ Warning: GEMINI_API_KEY not set. Intake agent disabled (use local testing).", current_slots

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    
    system_instruction = (
        "You are the AGAD Intake Capture Agent, an empathetic medical receptionist. "
        "Your mission is to conversationally collect 5 data points: Patient Name, HMO Member ID, Corporate Company, Symptoms/Diagnosis, and Procedures requested. "
        "Review the currently extracted values, look at what the user just said, and formulate a friendly response. "
        "CRITICAL: You must return your entire answer as a strict JSON object containing exactly two keys: "
        "'response' (the text you say back to the patient) and 'extracted_slots' (an object with keys: Name, Member_ID, Company, Diagnosis, Procedures). "
        "Do not update an extracted slot if it hasn't been mentioned yet or is uncertain."
    )

    prompt = f"Current Extracted Slots State: {json.dumps(current_slots)}\nHistory: {json.dumps(history)}\nInput: \"{user_input}\""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        # Attempt request with simple exponential backoff for transient 5xx errors
        max_attempts = 3
        backoff_base = 1.0
        res = None
        for attempt in range(1, max_attempts + 1):
            try:
                res = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=15)
            except Exception as exc:
                logger.exception("Intake Agent request exception on attempt %s", attempt)
                # If this was the last attempt, surface a generic error to the UI
                if attempt == max_attempts:
                    return f"Intake Agent exception occurred while contacting upstream service.", current_slots
                sleep_for = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                time.sleep(sleep_for)
                continue

            # If response OK, proceed
            if res.ok:
                break

            # For server errors, retry with backoff
            if 500 <= getattr(res, 'status_code', 0) < 600 and attempt < max_attempts:
                # Truncate body in logs to avoid leaking large content
                body_snippet = (getattr(res, 'text', '') or '')[:200]
                logger.warning("Intake Agent HTTP %s (attempt %s). Retrying. Body: %s", res.status_code, attempt, body_snippet)
                sleep_for = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                time.sleep(sleep_for)
                continue

            # Non-retriable or final response
            break

        # Validate response
        if not res or not res.ok:
            # Log truncated response body for diagnostics (not shown in UI)
            try:
                logger.error("Intake Agent HTTP %s response: %.200s", getattr(res, 'status_code', 'N/A'), getattr(res, 'text', ''))
            except Exception:
                logger.error("Intake Agent HTTP %s (no body available)", getattr(res, 'status_code', 'N/A'))
            return f"Intake Agent error: upstream API returned status {getattr(res, 'status_code', 'N/A') }.", current_slots

        res_json = res.json()
        # Navigate safe keys
        candidates = res_json.get('candidates') or []
        if not candidates:
            logger.error("Intake Agent response missing candidates: %s", res_json)
            return "Intake Agent error: no candidates returned by model.", current_slots

        content = candidates[0].get('content', {})
        parts = content.get('parts') or []
        if not parts:
            logger.error("Intake Agent response missing content parts: %s", content)
            return "Intake Agent error: model response missing content parts.", current_slots

        raw_output = parts[0].get('text', '').strip()
        
        # Safe Guard: Clean markdown formatting ticks out if generated by back-end context expansion
        if raw_output.startswith("```"):
            lines = raw_output.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_output = "\n".join(lines).strip()
            
        try:
            parsed_data = json.loads(raw_output)
        except json.JSONDecodeError:
            logger.error("Intake Agent failed to parse model output as JSON: %s", raw_output)
            return "Intake Agent parsing error: model returned non-JSON output.", current_slots
        
        updated_slots = current_slots.copy()
        for k, v in parsed_data.get("extracted_slots", {}).items():
            if v:
                updated_slots[k] = v
                
        return parsed_data.get("response", "Processing details..."), updated_slots
    except Exception as e:
        logger.exception("Intake Agent exception")
        return f"Intake Agent exception occurred. Continuing safely. (Details: {str(e)})", current_slots


# --- NODE 2: Document Generator Agent ---
def run_document_generator(target_department, extracted_slots, config):
    if not config or target_department not in config:
        return "Draft document pending...", ["Configuration Missing"]
        
    form_rules = config[target_department]
    required = form_rules["required_fields"]
    template = form_rules["display_template"]
    
    missing_fields = [field for field in required if not extracted_slots.get(field, "")]
    
    render_map = {
        k: (v if v else f"[{k.upper()} PENDING...]") 
        for k, v in extracted_slots.items()
    }
    
    try:
        rendered_output = template.format(**render_map)
    except Exception:
        rendered_output = template
        
    return rendered_output, missing_fields

# =====================================================================
# 🏥 USER INTERFACE VIEW LAYER RENDER
# =====================================================================

left_col, right_col = st.columns([1, 1])

# --- LEFT COLUMN: Chat Interface (Triggers Node 1) ---
with left_col:
    st.header("🤖 Intake Capture Agent")
    st.subheader("Patient Conversation")
    
    chat_container = st.container(height=400, border=True)
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "agent":
                st.write(f"🤖 **Agent:** {msg['text']}")
            else:
                st.write(f"🧑‍💻 **You:** {msg['text']}")
                
    if user_response := st.chat_input("Type your response here..."):
        st.session_state.messages.append({"role": "user", "text": user_response})
        
        with st.spinner("Intake Agent processing parameters..."):
            agent_reply, updated_slots = run_intake_agent(
                user_response, 
                st.session_state.messages[:-1], 
                st.session_state.patient_data
            )
            
        st.session_state.patient_data = updated_slots
        st.session_state.messages.append({"role": "agent", "text": agent_reply})
        st.rerun()

# --- RIGHT COLUMN: Form Automation Panel (Triggers Node 2) ---
with right_col:
    st.header("📄 Document Generator Agent")
    
    available_depts = list(dept_config.keys()) if dept_config else ["Default Form"]
    target_dept = st.selectbox("Select Requesting Department / Form Type:", available_depts)
    
    st.subheader(f"Form Preview: {target_dept}")
    
    rendered_text, missing_fields = run_document_generator(
        target_dept, 
        st.session_state.patient_data, 
        dept_config
    )
    
    doc_preview_box = st.container(height=320, border=True)
    with doc_preview_box:
        if depts_rules := dept_config.get(target_dept, None):
            st.markdown("##### 🔍 Required Parameter Audit Checklist")
            required_list = depts_rules["required_fields"]
            cols = st.columns(len(required_list))
            for i, field in enumerate(required_list):
                with cols[i]:
                    if st.session_state.patient_data.get(field, ""):
                        st.success(f"✓ {field}")
                    else:
                        st.error(f"✗ {field}")
            
            st.markdown("---")
            st.markdown("##### 📑 Real-Time Pre-Fill Render")
            st.code(rendered_text, language="text")
        else:
            st.info("Draft document view will populate here as the intake conversation progresses.")

    # --- HITL Security Gate Button ---
    st.markdown("### 🔒 Security & Human-in-the-Loop Gate")
    approve_button = st.button("Approve & Finalize Document", use_container_width=True)
    
    if approve_button:
        if missing_fields:
            st.error(f"Action Blocked: Cannot approve document. Missing metrics for: {', '.join(missing_fields)}")
        else:
            os.makedirs("final_documents", exist_ok=True)
            # Safely sanitize patient name and department for filenames
            raw_name = st.session_state.patient_data.get('Name') or 'unknown'
            safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", raw_name.strip().replace(' ', '_'))
            safe_dept = re.sub(r"[^A-Za-z0-9_-]", "_", target_dept.strip().replace('/', '_'))
            filename = f"final_documents/final_{safe_name.lower()}_{safe_dept.lower()}.json"

            output_payload = {
                "timestamp": time.time(),
                "department": target_dept,
                "collected_data": st.session_state.patient_data,
                "rendered_output": rendered_text
            }

            # Atomic write: write to temp file then rename
            tmp_filename = filename + ".tmp"
            with open(tmp_filename, "w") as f:
                json.dump(output_payload, f, indent=4)
            os.replace(tmp_filename, filename)

            st.success(f"🔒 Document Finalized! Signed-off state written to: `{filename}`")
