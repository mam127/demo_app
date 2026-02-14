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

SCORE_SCALE = 5  # ✅ fixed value

API_URL = "https://public-api.anecdoteai.com/inject"
API_HEADERS = {
    "Authorization": "Bearer nKGPGqhQOpoSoQR8hYiyQM7ojJSp4WTgmlM2YfNJdWksuX6w8YYiqMAQbmBbEzSa"
}

HRDF_GREEN = "#1B8354"


# =========================
# Styling (HRDF look)
# =========================
def inject_hrdf_style():
    st.markdown(
        f"""
        <style>
          :root {{
            --hrdf-green: {HRDF_GREEN};
            --hrdf-green-dark: #146A43;
            --hrdf-bg: #F3FBF6;
            --hrdf-border: rgba(27, 131, 84, 0.22);
          }}

          /* Page spacing */
          .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 860px;
          }}

          /* Header card */
          .hrdf-hero {{
            background: var(--hrdf-bg);
            border: 1px solid var(--hrdf-border);
            border-left: 8px solid var(--hrdf-green);
            border-radius: 18px;
            padding: 16px 18px;
            margin-bottom: 12px;
          }}
          .hrdf-title {{
            font-size: 26px;
            font-weight: 800;
            margin: 0;
            color: #0F2E20;
          }}
          .hrdf-subtitle {{
            margin-top: 4px;
            font-size: 13px;
            color: rgba(15, 46, 32, 0.72);
          }}

          /* Primary button */
          div[data-testid="stButton"] > button {{
            background: var(--hrdf-green);
            border: 1px solid var(--hrdf-green);
            color: white;
            border-radius: 12px;
            padding: 0.6rem 1rem;
            font-weight: 700;
          }}
          div[data-testid="stButton"] > button:hover {{
            background: var(--hrdf-green-dark);
            border-color: var(--hrdf-green-dark);
          }}

          /* Form container */
          div[data-testid="stForm"] {{
            border: 1px solid var(--hrdf-border);
            border-radius: 18px;
            padding: 14px 16px;
            background: white;
          }}

          /* Links / accents */
          a {{
            color: var(--hrdf-green) !important;
          }}

          /* Try to tint slider track/handle (best effort; Streamlit DOM may vary) */
          div[data-baseweb="slider"] div[role="slider"] {{
            background-color: var(--hrdf-green) !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# Helpers
# =========================
def make_reference_id(message: str) -> str:
    digest = hashlib.sha256(message.strip().encode("utf-8")).hexdigest()[:16]
    return f"msg-{digest}"

def now_iso_utc() -> str:
    # Required format: yyyy-MM-ddTHH:mm:ssZ
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def build_payload(message: str, source: str, filters: dict, score: int) -> dict:
    return {
        "project_id": PROJECT_ID,
        "taxonomy_id": TAXONOMY_ID,
        "skip_steps": SKIP_STEPS,
        "batch": [
            {
                "message": message,
                "ds": now_iso_utc(),
                "unique_id": make_reference_id(message),
                "ticket_id": make_reference_id(message),
                "source": source,
                "filters": filters,

                # ✅ NEW fields
                "score": int(score),
                "score_scale": SCORE_SCALE,
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
st.set_page_config(page_title="HRDF Feedback Submission", layout="centered")
inject_hrdf_style()

st.markdown(
    """
    <div class="hrdf-hero">
      <div class="hrdf-title">HRDF Feedback Submission</div>
      <div class="hrdf-subtitle">Submit a message with a required 1–5 score (scale is fixed to 5).</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(f"Submissions will be sent to: **{PROJECT_ID}**")

with st.form("submission_form"):
    st.subheader("Required details")

    # ✅ NEW required score field
    score = st.slider(
        "Score *",
        min_value=1,
        max_value=5,
        value=3,
        step=1,
        help="Choose a score from 1 (lowest) to 5 (highest).",
    )

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
        score=score,  # ✅ pass score
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
