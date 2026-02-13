# app.py
import hashlib
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st


# =========================
# Internal (fixed in code)
# =========================
PROJECT_ID = "hrdf-care"          # ✅ set your project_id here
TAXONOMY_ID = "default"
SKIP_STEPS = {}

API_URL = "https://public-api.anecdoteai.com/inject"
API_HEADERS = {
    "Authorization": "Bearer nKGPGqhQOpoSoQR8hYiyQM7ojJSp4WTgmlM2YfNJdWksuX6w8YYiqMAQbmBbEzSa"
}


# =========================
# Helpers
# =========================
def make_reference_id(message: str) -> str:
    digest = hashlib.sha256(message.strip().encode("utf-8")).hexdigest()[:16]
    return f"msg-{digest}"

def now_iso_utc() -> str:
    # Required format: yyyy-MM-ddTHH:mm:ssZ
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def build_payload(message: str, source: str, filters: dict) -> dict:
    return {
        "project_id": PROJECT_ID,
        "taxonomy_id": TAXONOMY_ID,
        "skip_steps": SKIP_STEPS,
        "batch": [
            {
                "message": message,
                "ds": now_iso_utc(),
                "unique_id": make_reference_id(message),
                "source": source,
                "filters": filters,
            }
        ],
    }

def send_to_api(payload: dict):
    if not API_URL.strip():
        return False, None, "API_URL is not set. (Sending is disabled.)"

    try:
        resp = requests.post(
            API_URL.strip(),
            json=payload,
            headers=API_HEADERS,
        )
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return resp.ok, resp.status_code, body
    except requests.exceptions.RequestException as e:
        return False, None, str(e)


# =========================
# UI
# =========================
st.set_page_config(page_title="Feedback Submission", layout="centered")
st.title("Feedback Submission")

# (Optional) show which project this is going to, without allowing edits
st.caption(f"Submissions will be sent to: {PROJECT_ID}")

with st.form("submission_form"):
    st.subheader("Required details")
    message = st.text_area("Message *", placeholder="Type the message here...")

    # Optional fields hidden by default
    source_value = "Demo Data"
    filters_dict = {}

    with st.expander("Optional details (click to expand)", expanded=False):
        source_input = st.text_input(
            "Data source (optional)",
            placeholder='Defaults to "Demo Data"',
            help='Where did this message come from? If left blank, it will be set to "Demo Data".',
        )
        source_value = source_input.strip() if source_input.strip() else "Demo Data"

        st.markdown("**Extra attributes (optional)**")
        st.caption("Add any extra details as key/value pairs (example: platform = iOS).")

        default_rows = pd.DataFrame([{"Attribute": "", "Value": ""} for _ in range(3)])
        edited = st.data_editor(
            default_rows,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
        )

        # Convert to dict, ignoring empty keys
        for _, row in edited.iterrows():
            k = str(row.get("Attribute", "")).strip()
            if k:
                v = row.get("Value", "")
                filters_dict[k] = "" if v is None else str(v)

    submitted = st.form_submit_button("Create submission")

if submitted:
    if not message.strip():
        st.error("Message is required.")
        st.stop()

    payload = build_payload(
        message=message.strip(),
        source=source_value,
        filters=filters_dict if isinstance(filters_dict, dict) else {},
    )

    st.success("Submission created.")
    with st.expander("View technical preview (optional)", expanded=False):
        st.json(payload)

    ok, status, body = send_to_api(payload)

    if status is None and not ok:
        st.info(body)
    else:
        st.write(f"Result: **{status}**")
        if ok:
            st.success("Sent successfully.")
        else:
            st.error("Sending failed.")
        with st.expander("Response details", expanded=False):
            if isinstance(body, (dict, list)):
                st.json(body)
            else:
                st.text(str(body))