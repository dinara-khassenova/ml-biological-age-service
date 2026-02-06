from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import gradio as gr

from client import BackendClient, ApiError
from config import POLL_INTERVAL_SEC, POLL_TIMEOUT_SEC

client = BackendClient()
TERMINAL_STATUSES = {"DONE", "FAILED"}

# ===================== DEFAULTS FOR QUICK TEST =====================

DEFAULT_TEST_VALUES: Dict[str, Any] = {
    "Height (cm)": 170,
    "Weight (kg)": 70,
    "BMI": 25,
    "Cholesterol Level (mg/dL)": 200,
    "Blood Glucose Level (mg/dL)": 150,
    "Stress Levels": 5,             # 0..10
    "Vision Sharpness": 1.0,        # 0..2
    "Hearing Ability (dB)": 50,     # 0..100
    "Bone Density (g/cm²)": 1.0,    # 0..3
    "BP_Systolic": 120,
    "BP_Diastolic": 80,
}

# ===================== HELPERS =====================

def _safe_detail(e: ApiError) -> str:
    """
    Safely extract detail from ApiError into a readable string.
    """
    try:
        d = getattr(e, "detail", None)
        if d is None:
            return ""
        if isinstance(d, (dict, list)):
            return str(d)
        return str(d)
    except Exception:
        return ""


def format_api_error(e: ApiError, *, context: str = "") -> str:
    """
    Converts API errors into user-friendly messages (no system noise).
    """
    detail_raw = _safe_detail(e)
    detail = (detail_raw or "").lower()

    # Auth
    if e.status_code in (401, 403):
        if context == "login":
            return "❌ Incorrect email or password."
        return "❌ You are not authorized. Please log in again."

    # Validation
    if e.status_code == 422:
        if context == "register":
            return "❌ Registration failed. Password must be at least 8 characters."
        return "❌ Validation error. Please check the input values."

    # Register conflicts / duplicates (depends on how backend implements)
    if context == "register" and e.status_code in (400, 409):
        # common words for duplicates/unique violations
        if any(x in detail for x in ["already", "exists", "duplicate", "unique", "registered", "email"]):
            return "❌ This email is already registered. Please log in or use another email."
        return "❌ Registration failed. Please check your email and try again."

    # Service unavailable
    if e.status_code in (502, 503, 504):
        return "❌ Service is temporarily unavailable. Please try again later."

    # Generic fallback
    # (if backend returned something meaningful, show it briefly)
    if detail_raw:
        return f"❌ Request failed: {detail_raw}"
    return f"❌ Request failed (HTTP {e.status_code})."


def _format_dt(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        s = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return value
    return str(value)


def _format_answers_multiline(ans: Any) -> str:
    """
    Multi-line key=value to make History readable.
    """
    if not ans:
        return ""
    if isinstance(ans, dict):
        lines = [f"{k}: {ans[k]}" for k in sorted(ans.keys())]
        return "\n".join(lines)
    return str(ans)


def _format_result_short(item: dict) -> str:
    """
    Compact result for History table.
    """
    if item.get("status") != "DONE":
        return ""
    res = item.get("result") or {}
    age = res.get("biological_age")
    if age is None:
        return "DONE"
    return f"age={age}"


def _user_validation_message(errors: List[Dict[str, Any]]) -> str:
    if not errors:
        return "❌ Please check the input values."

    lines = []
    for e in errors:
        field = e.get("field_name") or "field"
        msg = e.get("message") or "Invalid value"
        lines.append(f"- **{field}**: {msg}")
    return "❌ Please fix the following fields:\n" + "\n".join(lines)


def _user_result_markdown(task: dict) -> str:
    status = task.get("status")

    if status == "DONE":
        result = task.get("result") or {}
        bio_age = result.get("biological_age")
        charged = task.get("charged_amount") or 0

        md = (
            "✅ **Done!**\n\n"
            f"- **Biological age:** `{bio_age}`\n"
            f"- **Credits charged:** `{charged}`\n"
        )

        factors = result.get("factors") or []
        if factors:
            md += "\n### Factors\n"
            for f in factors:
                name = f.get("name", "factor")
                group = f.get("group", "")
                value = f.get("value", "")
                desc = f.get("description", "")
                md += f"- **{name}** ({group}) = `{value}` — {desc}\n"

        return md

    if status == "FAILED":
        return f"❌ **Execution failed**: {task.get('error_message')}"

    return f"⏳ **Status:** `{status}`"





def _debug_predict_message(task_id: str, task: dict) -> str:
    return (
        f"task_id={task_id}; status={task.get('status')}; "
        f"model_id={task.get('model_id')}; user_id={task.get('user_id')}; "
        f"worker_id={task.get('worker_id')}; charged={task.get('charged_amount')}; "
        f"error={task.get('error_message')}"
    )


def _build_feature_table(feature_names: List[str], defaults: Dict[str, Any] | None = None) -> List[List[Any]]:
    defaults = defaults or {}
    return [[name, defaults.get(name)] for name in feature_names]


def _coerce_cell_value(v: Any) -> Any:
    """
    Gradio Dataframe often returns values as str.
    We try to coerce to int/float.
    """
    if v is None:
        return None

    if isinstance(v, bool):
        return v

    if isinstance(v, (int, float)):
        return v

    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        s2 = s.replace(",", ".")
        try:
            if "." in s2:
                return float(s2)
            return int(s2)
        except ValueError:
            return s

    return v


def _answers_from_table(feature_names: List[str], table: Any) -> Dict[str, Any]:
    answers: Dict[str, Any] = {}

    if table is None:
        rows = []
    elif hasattr(table, "values"):  # pandas.DataFrame
        rows = table.values.tolist()
    else:
        rows = table

    rows = rows or []

    for idx, fname in enumerate(feature_names):
        val = None
        if idx < len(rows) and len(rows[idx]) >= 2:
            val = rows[idx][1]

        val = _coerce_cell_value(val)

        if val not in (None, "", " "):
            answers[fname] = val

    return answers


def _val_errors_to_rows(errors: Any) -> List[List[str]]:
    if not errors:
        return []
    rows: List[List[str]] = []
    if isinstance(errors, list):
        for e in errors:
            if isinstance(e, dict):
                rows.append([str(e.get("field_name", "")), str(e.get("message", ""))])
            else:
                rows.append(["", str(e)])
    else:
        rows.append(["", str(errors)])
    return rows


# ===================== AUTH =====================

def ui_register(email: str, password: str) -> str:
    try:
        client.register(email=email, password=password)
        return "✅ Registration successful. You can now log in."
    except ApiError as e:
        return format_api_error(e, context="register")
    except Exception:
        return "❌ Registration failed. Please try again."


def ui_login(email: str, password: str) -> Tuple[str, str]:
    try:
        token = client.login(email=email, password=password)
        return token, "✅ Logged in successfully."
    except ApiError as e:
        # force user-friendly message for wrong credentials
        if e.status_code in (401, 403):
            return "", "❌ Incorrect email or password."
        return "", format_api_error(e, context="login")
    except Exception:
        return "", "❌ Login failed. Please try again."


# ===================== WALLET =====================

def ui_balance(token: str) -> str:
    if not token:
        return "❌ Please log in first."
    try:
        bal = client.get_balance(token)
        return f"💰 **Your balance:** `{bal}` credits"
    except ApiError as e:
        return format_api_error(e)
    except Exception:
        return "❌ Failed to load balance. Please try again."


def ui_topup(token: str, amount: int) -> str:
    if not token:
        return "❌ Please log in first."
    try:
        tx = client.topup(token, int(amount))
        return f"✅ Balance topped up by **{tx['amount']}** credits."
    except ApiError as e:
        return format_api_error(e)
    except Exception:
        return "❌ Top up failed. Please try again."


# ===================== FEATURES FROM DB =====================

def ui_load_features_from_db() -> Tuple[List[List[Any]], List[str], str, dict]:
    """
    Auto-load default model + features from DB:
    GET /api/ml-models/default
    """
    try:
        m = client.get_default_model()
        feature_names = m.get("feature_names") or []
        if not feature_names:
            return [], [], "❌ Default model has no feature list.", m

        table = _build_feature_table(feature_names, defaults=DEFAULT_TEST_VALUES)
        return table, feature_names, f"✅ Loaded {len(feature_names)} features.", m

    except ApiError as e:
        return [], [], format_api_error(e), {"error": str(e), "detail": getattr(e, "detail", None)}
    except Exception as e:
        return [], [], f"❌ Load features error: {e}", {"error": str(e)}


# ===================== PREDICT =====================

def ui_predict(token: str, feature_names: List[str], table: List[List[Any]]):
    if not token:
        return "", "❌ Please log in first.", "debug: no token", [], {}

    if not feature_names:
        return "", "❌ Failed to load model features. Please refresh the page.", "debug: empty feature_names", [], {}

    answers = _answers_from_table(feature_names, table)

    try:
        task_id = client.predict(token, answers=answers, model_id=None)
    except ApiError as e:
        if e.status_code == 422 and isinstance(e.detail, dict):
            errors = e.detail.get("validation_errors", []) or []
            return (
                e.detail.get("task_id", ""),
                _user_validation_message(errors),
                f"debug: 422 detail={e.detail}",
                _val_errors_to_rows(errors),
                {},
            )
        return "", format_api_error(e), f"debug: api_error={e}", [], {}
    except Exception as e:
        return "", f"❌ Predict failed: {e}", f"debug: exception={e}", [], {}

    deadline = time.time() + POLL_TIMEOUT_SEC
    last_task: Dict[str, Any] = {}

    while time.time() < deadline:
        try:
            last_task = client.get_task(token, task_id)
            if last_task.get("status") in TERMINAL_STATUSES:
                break
        except ApiError as e:
            return task_id, format_api_error(e), f"debug: poll_error={e}", [], {}
        time.sleep(POLL_INTERVAL_SEC)

    val_errors = last_task.get("validation_errors", []) or []
    return (
        task_id,
        _user_result_markdown(last_task),
        _debug_predict_message(task_id, last_task),
        _val_errors_to_rows(val_errors),
        last_task,
    )


# ===================== HISTORY + VIEW TASK =====================

def ui_history(token: str):
    empty_rows: List[List[Any]] = []

    if not token:
        return "❌ **Please log in first.**", empty_rows, []

    try:
        items = client.get_history(token) or []
        if not items:
            return "ℹ️ **No tasks yet.**", empty_rows, []

        rows = []
        for i in items[:200]:
            rows.append(
                [
                    i.get("id", ""),
                    i.get("external_id", ""),
                    _format_dt(i.get("created_at")),
                    _format_answers_multiline(i.get("answers")),
                    i.get("status", ""),
                    i.get("charged_amount", 0) or 0,
                    _format_result_short(i),
                ]
            )

        return f"✅ **Loaded: {len(rows)} records**", rows, items

    except ApiError as e:
        return format_api_error(e), empty_rows, []
    except Exception as e:
        return f"❌ **History error:** `{e}`", empty_rows, []


def ui_pick_history_row(raw_items: List[dict], selected: gr.SelectData) -> str:
    """
    When user clicks a row, return external_id into textbox for quick view.
    """
    try:
        row_idx = selected.index[0] if isinstance(selected.index, (list, tuple)) else selected.index
        if row_idx is None:
            return ""
        if row_idx < 0 or row_idx >= len(raw_items):
            return ""
        return str(raw_items[row_idx].get("external_id", "") or "")
    except Exception:
        return ""


def ui_view_task(token: str, task_id: str):
    """
    Returns:
      - user markdown
      - raw task json
      - debug text
    """
    if not token:
        return "❌ Please log in first.", {}, ""

    task_id = (task_id or "").strip()
    if not task_id:
        return "ℹ️ Enter a task_id (uuid) or select a row from History.", {}, ""

    try:
        t = client.get_task(token, task_id)
        md = _user_result_markdown(t)
        dbg = _debug_predict_message(task_id, t)
        return md, t, dbg
    except ApiError as e:
        return format_api_error(e), {}, ""
    except Exception:
        return "❌ Failed to load task.", {}, ""


# ===================== UI =====================

CUSTOM_CSS = """
#features_df table td:nth-child(1),
#features_df table th:nth-child(1) {
  pointer-events: none;
  opacity: 0.85;
}

/* Make History 'answers' column wrap nicely */
#history_df table td:nth-child(4),
#history_df table th:nth-child(4) {
  white-space: pre-wrap !important;
  word-break: break-word;
}

/* Wrap result column too */
#history_df table td:nth-child(7),
#history_df table th:nth-child(7) {
  white-space: pre-wrap !important;
  word-break: break-word;
}

/* Remove frame-like look for markdown messages under buttons */
.msgbox {
  padding: 6px 2px;
  margin-top: 6px;
}
"""

with gr.Blocks(title="ML Service Cabinet") as demo:
    gr.Markdown("# ML Biological Age Service")

    token_state = gr.State("")
    feature_names_state = gr.State([])
    history_raw_state = gr.State([])

    with gr.Tabs():
        with gr.Tab("Home"):
            gr.Markdown(
                """
## What this service does

This app estimates your **biological age** using a small set of health metrics (height, weight, blood pressure, glucose, cholesterol, etc.).
It is a demo ML service with:
- secure access (**Register / Login**),
- a credit-based billing model (**Wallet**),
- asynchronous processing via a worker (**Predict**),
- and history tracking (**History**).

### Typical workflow
1) **Register**  
2) **Login**  
3) **Wallet** (top up credits)  
4) **Predict** (submit metrics and wait for the result)  
5) **History** (review past tasks and open full results)

💳 Credits are charged **only after a successful calculation**.
"""
            )

        with gr.Tab("Register"):
            gr.Markdown("Create a new account. Password must be **at least 8 characters**.")
            email_r = gr.Textbox(label="Email", placeholder="name@example.com")
            password_r = gr.Textbox(label="Password", type="password", placeholder="Min 8 characters")

            reg_btn = gr.Button("Register", variant="primary")
            reg_msg = gr.Markdown("", elem_classes=["msgbox"])
            reg_btn.click(ui_register, [email_r, password_r], reg_msg)

        with gr.Tab("Login"):
            gr.Markdown("Log in to continue.")
            email_l = gr.Textbox(label="Email", placeholder="name@example.com")
            password_l = gr.Textbox(label="Password", type="password")

            login_btn = gr.Button("Login", variant="primary")
            login_msg = gr.Markdown("", elem_classes=["msgbox"])
            login_btn.click(ui_login, [email_l, password_l], [token_state, login_msg])

        with gr.Tab("Wallet"):
            gr.Markdown(
                """
### Balance
Click **Check balance** to see your current credits.

### Top up
Enter an amount (e.g., 25, 50, 100) and click **Top up**.
"""
            )

            btn_balance = gr.Button("Check balance", variant="secondary")
            out_balance_md = gr.Markdown("", elem_classes=["msgbox"])
            btn_balance.click(ui_balance, token_state, out_balance_md)

            amount = gr.Number(label="Top up amount", value=25, precision=0)
            btn_topup = gr.Button("Top up", variant="primary")
            out_topup_md = gr.Markdown("", elem_classes=["msgbox"])
            btn_topup.click(ui_topup, [token_state, amount], out_topup_md)

        with gr.Tab("Predict"):
            gr.Markdown("## Biological Age Prediction")
            gr.Markdown(
                """
Enter your health metrics below and click **Predict**.

**Units / typical ranges (guide only):**
- Height: cm (140–210)
- Weight: kg (35–160)
- BMI: (12–45)
- Cholesterol: mg/dL (100–350)
- Glucose: mg/dL (60–200)
- BP Systolic: (90–200)
- BP Diastolic: (50–120)
- Stress: 0–10
- Hearing: dB (0–100)
- Bone density: g/cm² (0–3)
- Vision sharpness: 0–2

✅ The table is pre-filled with default values for quick testing.
"""
            )

            feature_table = gr.Dataframe(
                label="Input features",
                headers=["feature", "value"],
                column_count=(2, "fixed"),
                row_count=(0, "dynamic"),
                interactive=True,
                elem_id="features_df",
            )

            gr.Markdown("---")

            out_task_id = gr.Textbox(label="task_id (uuid)", interactive=False)
            out_user_md = gr.Markdown()

            with gr.Accordion("Raw JSON for debug", open=False):
                out_debug = gr.Textbox(label="Debug summary", interactive=False)
                out_val = gr.Dataframe(
                    label="Validation errors",
                    headers=["field", "message"],
                    column_count=(2, "fixed"),
                    row_count=(0, "dynamic"),
                    type="array",
                )
                out_json = gr.JSON(label="Raw task")

            gr.Button("Predict", variant="primary").click(
                ui_predict,
                [token_state, feature_names_state, feature_table],
                [out_task_id, out_user_md, out_debug, out_val, out_json],
            )

        with gr.Tab("History"):
            hist_status = gr.Markdown("ℹ️ Click **Load history**")

            out_hist = gr.Dataframe(
                label="History",
                headers=["id", "task_id (uuid)", "created_at", "answers", "status", "charged", "result"],
                column_count=(7, "fixed"),
                row_count=(0, "dynamic"),
                type="array",
                elem_id="history_df",
            )

            gr.Button("Load history", variant="primary").click(
                ui_history,
                token_state,
                outputs=[hist_status, out_hist, history_raw_state],
            )

            with gr.Accordion("View full task result", open=True):
                gr.Markdown("Select a row above (or paste a task_id) and click **View task**.")
                selected_task_id = gr.Textbox(label="task_id (uuid)")
                btn_view = gr.Button("View task", variant="secondary")

                view_md = gr.Markdown("")
                view_json = gr.JSON(label="Raw task", visible=False)
                view_dbg = gr.Textbox(label="Debug summary", interactive=False, visible=False)

                btn_view.click(
                    ui_view_task,
                    [token_state, selected_task_id],
                    [view_md, view_json, view_dbg],
                )

            # Click row -> fill task_id textbox
            out_hist.select(
                ui_pick_history_row,
                inputs=[history_raw_state],
                outputs=[selected_task_id],
            )

    demo.load(
        ui_load_features_from_db,
        inputs=None,
        outputs=[feature_table, feature_names_state, gr.Textbox(visible=False), gr.JSON(visible=False)],
        # NOTE: we intentionally hide status + raw model to avoid extra UI noise
    )

demo.launch(css=CUSTOM_CSS, server_name="0.0.0.0", server_port=7860, root_path="/ui")




'''
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import gradio as gr

from client import BackendClient, ApiError
from config import POLL_INTERVAL_SEC, POLL_TIMEOUT_SEC

client = BackendClient()
TERMINAL_STATUSES = {"DONE", "FAILED"}


# ===================== DEFAULTS FOR QUICK TEST =====================

DEFAULT_TEST_VALUES: Dict[str, Any] = {
    "Height (cm)": 170,
    "Weight (kg)": 70,
    "BMI": 25,
    "Cholesterol Level (mg/dL)": 200,
    "Blood Glucose Level (mg/dL)": 150,
    "Stress Levels": 5,             # 0..10 (assumption)
    "Vision Sharpness": 1.0,        # 0..2-ish (assumption)
    "Hearing Ability (dB)": 50,     # 0..100 (assumption)
    "Bone Density (g/cm²)": 1.0,    # 0..3-ish (assumption)
    "BP_Systolic": 120,
    "BP_Diastolic": 80,
}


# ===================== HELPERS =====================

def format_api_error(e: ApiError, *, context: str = "") -> str:
    """
    Converts API errors into user-friendly messages.
    """
    # If backend returns useful detail for auth failures, show friendly text
    if e.status_code in (401, 403):
        msg = "❌ You are not authorized. Please log in again."
        if context == "login":
            # Typical backend detail: "Incorrect email or password"
            msg = "❌ Incorrect email or password. Please try again."
        return msg

    if e.status_code == 422:
        # For register: show simple validation message, not raw pydantic structure
        if context == "register":
            return "❌ Registration failed. Please check your email and password (password must be at least 8 characters)."
        return "❌ Validation error. Please check the input values."

    if e.status_code in (502, 503, 504):
        return "❌ Service is temporarily unavailable. Please try again later."

    # Fallback: still avoid dumping system internals where possible
    return f"❌ Request failed (HTTP {e.status_code})."


def _format_dt(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        s = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return value
    return str(value)


def _format_answers_multiline(ans: Any) -> str:
    """
    Multi-line key=value to make History readable.
    """
    if not ans:
        return ""
    if isinstance(ans, dict):
        lines = [f"{k}: {ans[k]}" for k in sorted(ans.keys())]
        return "\n".join(lines)
    return str(ans)


def _format_result_short(item: dict) -> str:
    """
    Compact result for History table.
    """
    status = item.get("status")
    if status != "DONE":
        return ""
    res = item.get("result") or {}
    age = res.get("biological_age")
    if age is None:
        return "DONE"
    return f"age={age}"


def _user_validation_message(errors: List[Dict[str, Any]]) -> str:
    if not errors:
        return "❌ Please check the input values."

    lines = []
    for e in errors:
        field = e.get("field_name") or "field"
        msg = e.get("message") or "Invalid value"
        lines.append(f"- **{field}**: {msg}")
    return "❌ Please fix the following fields:\n" + "\n".join(lines)


def _user_result_markdown(task: dict) -> str:
    status = task.get("status")

    if status == "DONE":
        result = task.get("result") or {}
        bio_age = result.get("biological_age")
        charged = task.get("charged_amount") or 0

        md = (
            "✅ **Done!**\n\n"
            f"- **Biological age:** `{bio_age}`\n"
            f"- **Credits charged:** `{charged}`\n"
        )

        factors = result.get("factors") or []
        if factors:
            md += "\n### Factors\n"
            for f in factors:
                name = f.get("name", "factor")
                group = f.get("group", "")
                value = f.get("value", "")
                desc = f.get("description", "")
                md += f"- **{name}** ({group}) = `{value}` — {desc}\n"

        return md

    if status == "FAILED":
        return f"❌ **Execution failed**: {task.get('error_message')}"

    return f"⏳ **Status:** `{status}`"


def _debug_predict_message(task_id: str, task: dict) -> str:
    return (
        f"task_id={task_id}; status={task.get('status')}; "
        f"model_id={task.get('model_id')}; user_id={task.get('user_id')}; "
        f"worker_id={task.get('worker_id')}; charged={task.get('charged_amount')}; "
        f"error={task.get('error_message')}"
    )


def _build_feature_table(feature_names: List[str], defaults: Dict[str, Any] | None = None) -> List[List[Any]]:
    defaults = defaults or {}
    rows: List[List[Any]] = []
    for name in feature_names:
        rows.append([name, defaults.get(name)])
    return rows


def _coerce_cell_value(v: Any) -> Any:
    """
    Gradio Dataframe often returns values as str.
    We try to coerce to int/float.
    """
    if v is None:
        return None

    if isinstance(v, (int, float)):
        return v

    if isinstance(v, bool):
        return v

    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        s2 = s.replace(",", ".")
        try:
            if "." in s2:
                return float(s2)
            return int(s2)
        except ValueError:
            return s

    return v


def _answers_from_table(feature_names: List[str], table: Any) -> Dict[str, Any]:
    answers: Dict[str, Any] = {}

    if table is None:
        rows = []
    elif hasattr(table, "values"):  # pandas.DataFrame
        rows = table.values.tolist()
    else:
        rows = table

    rows = rows or []

    for idx, fname in enumerate(feature_names):
        val = None
        if idx < len(rows) and len(rows[idx]) >= 2:
            val = rows[idx][1]

        val = _coerce_cell_value(val)

        if val not in (None, "", " "):
            answers[fname] = val

    return answers


def _val_errors_to_rows(errors: Any) -> List[List[str]]:
    if not errors:
        return []
    rows: List[List[str]] = []
    if isinstance(errors, list):
        for e in errors:
            if isinstance(e, dict):
                rows.append([str(e.get("field_name", "")), str(e.get("message", ""))])
            else:
                rows.append(["", str(e)])
    else:
        rows.append(["", str(errors)])
    return rows


# ===================== AUTH =====================

def ui_register(email: str, password: str) -> str:
    try:
        client.register(email=email, password=password)
        return "✅ Registration successful. You can now log in."
    except ApiError as e:
        return format_api_error(e, context="register")
    except Exception:
        return "❌ Registration failed. Please try again."


def ui_login(email: str, password: str) -> Tuple[str, str]:
    try:
        token = client.login(email=email, password=password)
        return token, "✅ Logged in successfully."
    except ApiError as e:
        return "", format_api_error(e, context="login")
    except Exception:
        return "", "❌ Login failed. Please try again."


# ===================== WALLET =====================

def ui_balance(token: str) -> str:
    if not token:
        return "❌ Please log in first."
    try:
        return f"💰 Your balance: **{client.get_balance(token)}** credits"
    except ApiError as e:
        return format_api_error(e)
    except Exception:
        return "❌ Failed to load balance. Please try again."


def ui_topup(token: str, amount: int) -> str:
    if not token:
        return "❌ Please log in first."
    try:
        tx = client.topup(token, int(amount))
        return f"✅ Balance topped up by **{tx['amount']}** credits."
    except ApiError as e:
        return format_api_error(e)
    except Exception:
        return "❌ Top up failed. Please try again."


# ===================== FEATURES FROM DB =====================

def ui_load_features_from_db() -> Tuple[List[List[Any]], List[str], str, dict]:
    """
    Auto-load default model + features from DB:
    GET /api/ml-models/default
    """
    try:
        m = client.get_default_model()
        feature_names = m.get("feature_names") or []
        if not feature_names:
            return [], [], "❌ Default model has no feature list.", m

        table = _build_feature_table(feature_names, defaults=DEFAULT_TEST_VALUES)
        return table, feature_names, f"✅ Loaded {len(feature_names)} features.", m

    except ApiError as e:
        return [], [], format_api_error(e), {"error": str(e), "detail": getattr(e, "detail", None)}
    except Exception as e:
        return [], [], f"❌ Load features error: {e}", {"error": str(e)}


# ===================== PREDICT =====================

def ui_predict(token: str, feature_names: List[str], table: List[List[Any]]):
    if not token:
        return "", "❌ Please log in first.", "debug: no token", [], {}

    if not feature_names:
        return "", "❌ Failed to load model features. Please refresh the page.", "debug: empty feature_names", [], {}

    answers = _answers_from_table(feature_names, table)

    try:
        task_id = client.predict(token, answers=answers, model_id=None)
    except ApiError as e:
        if e.status_code == 422 and isinstance(e.detail, dict):
            errors = e.detail.get("validation_errors", []) or []
            return (
                e.detail.get("task_id", ""),
                _user_validation_message(errors),
                f"debug: 422 detail={e.detail}",
                _val_errors_to_rows(errors),
                {},
            )
        return "", format_api_error(e), f"debug: api_error={e}", [], {}
    except Exception as e:
        return "", f"❌ Predict failed: {e}", f"debug: exception={e}", [], {}

    deadline = time.time() + POLL_TIMEOUT_SEC
    last_task: Dict[str, Any] = {}

    while time.time() < deadline:
        try:
            last_task = client.get_task(token, task_id)
            if last_task.get("status") in TERMINAL_STATUSES:
                break
        except ApiError as e:
            return task_id, format_api_error(e), f"debug: poll_error={e}", [], {}
        time.sleep(POLL_INTERVAL_SEC)

    val_errors = last_task.get("validation_errors", []) or []
    return (
        task_id,
        _user_result_markdown(last_task),
        _debug_predict_message(task_id, last_task),
        _val_errors_to_rows(val_errors),
        last_task,
    )


# ===================== HISTORY + VIEW TASK =====================

def ui_history(token: str):
    empty_rows: List[List[Any]] = []

    if not token:
        return "❌ **Please log in first.**", empty_rows, []

    try:
        items = client.get_history(token) or []
        if not items:
            return "ℹ️ **No tasks yet.**", empty_rows, []

        rows = []
        for i in items[:200]:
            rows.append(
                [
                    i.get("id", ""),
                    i.get("external_id", ""),  # IMPORTANT: show uuid
                    _format_dt(i.get("created_at")),
                    _format_answers_multiline(i.get("answers")),
                    i.get("status", ""),
                    i.get("charged_amount", 0) or 0,
                    _format_result_short(i),
                ]
            )

        return f"✅ **Loaded: {len(rows)} records**", rows, items

    except ApiError as e:
        return format_api_error(e), empty_rows, []
    except Exception as e:
        return f"❌ **History error:** `{e}`", empty_rows, []


def ui_pick_history_row(history_rows: List[List[Any]], raw_items: List[dict], selected: gr.SelectData):
    """
    When user clicks a row, store external_id into a textbox for quick view.
    """
    try:
        row_idx = selected.index[0] if isinstance(selected.index, (list, tuple)) else selected.index
        if row_idx is None:
            return ""
        if row_idx < 0 or row_idx >= len(raw_items):
            return ""
        ext = raw_items[row_idx].get("external_id", "")
        return str(ext or "")
    except Exception:
        return ""


def ui_view_task(token: str, task_id: str):
    if not token:
        return "❌ Please log in first.", {}, ""

    task_id = (task_id or "").strip()
    if not task_id:
        return "ℹ️ Enter a task_id (uuid) or select a row from History.", {}, ""

    try:
        t = client.get_task(token, task_id)
        md = _user_result_markdown(t)
        # Extra compact JSON-safe summary
        dbg = _debug_predict_message(task_id, t)
        return md, t, dbg
    except ApiError as e:
        return format_api_error(e), {}, ""
    except Exception:
        return "❌ Failed to load task.", {}, ""


# ===================== UI =====================

CUSTOM_CSS = """
#features_df table td:nth-child(1),
#features_df table th:nth-child(1) {
  pointer-events: none;
  opacity: 0.85;
}

/* Make History 'answers' column wrap nicely */
#history_df table td:nth-child(4),
#history_df table th:nth-child(4) {
  white-space: pre-wrap !important;
  word-break: break-word;
}

/* Also wrap result column a bit */
#history_df table td:nth-child(7),
#history_df table th:nth-child(7) {
  white-space: pre-wrap !important;
  word-break: break-word;
}
"""

with gr.Blocks(title="ML Service Cabinet", css=CUSTOM_CSS) as demo:
    gr.Markdown("# ML Biological Age Service")

    token_state = gr.State("")
    feature_names_state = gr.State([])
    history_raw_state = gr.State([])  # store raw items for row selection mapping

    with gr.Tabs():
        with gr.Tab("Home"):
            gr.Markdown(
                """
## What this service does

This app estimates your **biological age** using a small set of health metrics (height, weight, blood pressure, glucose, cholesterol, etc.).
It is designed as a **demo ML service** with:
- secure access (**Register / Login**),
- a credit-based billing model (**Wallet**),
- asynchronous processing via a worker (**Predict**),
- and full history tracking (**History**).

### Typical workflow
1) **Register** (create an account)  
2) **Login** (get your access token automatically inside the UI)  
3) **Wallet** (top up credits)  
4) **Predict** (submit metrics and wait for result)  
5) **History** (review past tasks and open a full result)

💳 Credits are charged **only after a successful calculation**.
"""
            )

        with gr.Tab("Register"):
            gr.Markdown("Create a new account. Password must be **at least 8 characters**.")
            email_r = gr.Textbox(label="Email", placeholder="name@example.com")
            password_r = gr.Textbox(label="Password", type="password", placeholder="Min 8 characters")

            reg_btn = gr.Button("Register", variant="primary")
            reg_msg = gr.Markdown("")  
            reg_btn.click(ui_register, [email_r, password_r], reg_msg)

        with gr.Tab("Login"):
            gr.Markdown("Log in to continue. If you enter a wrong email or password, you will see a clear message below.")
            email_l = gr.Textbox(label="Email", placeholder="name@example.com")
            password_l = gr.Textbox(label="Password", type="password")

            login_btn = gr.Button("Login", variant="primary")
            login_msg = gr.Markdown("")
            login_btn.click(ui_login, [email_l, password_l], [token_state, login_msg])

        with gr.Tab("Wallet"):
            gr.Markdown(
                """
### Balance
Click **Check balance** to see how many credits you currently have.

### Top up
Enter an amount (e.g., 25, 50, 100) and click **Top up**.
"""
            )

            btn_balance = gr.Button("Check balance", variant="secondary")
            out_balance_md = gr.Markdown("")

            btn_balance.click(ui_balance, token_state, out_balance_md)

            amount = gr.Number(label="Top up amount", value=25, precision=0)
            btn_topup = gr.Button("Top up", variant="primary")
            out_topup_md = gr.Markdown("")
            btn_topup.click(ui_topup, [token_state, amount], out_topup_md)

        with gr.Tab("Predict"):
            gr.Markdown("## Biological Age Prediction")
            gr.Markdown(
                """
Enter your health metrics below and click **Predict**.

**Notes on units / typical ranges (guide only):**
- Height: cm (e.g., 140–210)
- Weight: kg (e.g., 35–160)
- BMI: (e.g., 12–45)
- Cholesterol: mg/dL (e.g., 100–350)
- Glucose: mg/dL (e.g., 60–200)
- BP Systolic: (e.g., 90–200)
- BP Diastolic: (e.g., 50–120)
- Stress: 0–10
- Hearing: dB (e.g., 0–100)
- Bone density: g/cm² (e.g., 0–3)
- Vision sharpness: typically 0–2

✅ The table is pre-filled with default values for quick testing.
"""
            )

            # features_status = gr.Textbox(label="Features status", interactive=False)

            # gr.Accordion("For expert / debug", open=False):
                #default_model_raw = gr.JSON(label="Default model (raw)")

            feature_table = gr.Dataframe(
                label="Input your personal feature values",
                headers=["feature", "value"],
                column_count=(2, "fixed"),
                row_count=(0, "dynamic"),
                interactive=True,
                elem_id="features_df",
            )

            gr.Markdown("---")

            out_task_id = gr.Textbox(label="task_id (uuid)", interactive=False)
            out_user_md = gr.Markdown()

            with gr.Accordion("Raw JSON for information", open=False):
                out_debug = gr.Textbox(label="Debug summary", interactive=False)
                out_val = gr.Dataframe(
                    label="Validation errors",
                    headers=["field", "message"],
                    column_count=(2, "fixed"),
                    row_count=(0, "dynamic"),
                    type="array",
                )
                out_json = gr.JSON(label="Raw task")

            gr.Button("Predict", variant="primary").click(
                ui_predict,
                [token_state, feature_names_state, feature_table],
                [out_task_id, out_user_md, out_debug, out_val, out_json],
            )

        with gr.Tab("History"):
            hist_status = gr.Markdown("ℹ️ Click **Load history**")

            out_hist = gr.Dataframe(
                label="History",
                headers=["id", "task_id (uuid)", "created_at", "answers", "status", "charged", "result"],
                column_count=(7, "fixed"),
                row_count=(0, "dynamic"),
                type="array",
                elem_id="history_df",
                wrap=True,
            )

            with gr.Accordion("View full task result", open=True):
                gr.Markdown("Select a row above (or paste a task_id) and click **View task**.")
                selected_task_id = gr.Textbox(label="task_id (uuid)", placeholder="e.g. 3710000d-c26a-4172-96b0-e48e74b778e0")
                btn_view = gr.Button("View task", variant="secondary")
                view_md = gr.Markdown("")
                # view_json = gr.JSON(label="Raw task")
                #view_dbg = gr.Textbox(label="Debug summary", interactive=False)

                btn_view.click(ui_view_task, [token_state, selected_task_id], [view_md])

            gr.Button("Load history", variant="primary").click(
                ui_history,
                token_state,
                outputs=[hist_status, out_hist, history_raw_state],
            )

            # When clicking a row -> put external_id into textbox
            out_hist.select(
                ui_pick_history_row,
                inputs=[out_hist, history_raw_state],
                outputs=[selected_task_id],
            )

    demo.load(
        ui_load_features_from_db,
        inputs=None,
        outputs=[feature_table, feature_names_state],
    )

demo.launch(server_name="0.0.0.0", server_port=7860, root_path="/ui")
'''
