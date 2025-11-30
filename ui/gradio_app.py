import gradio as gr
import asyncio
import os
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any
import re

import tzlocal  # pip install tzlocal

from src.agents.orchestrator import create_orchestrator

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUTS_DIR = os.path.join(ROOT_DIR, "data", "outputs")
HISTORY_INDEX = os.path.join(OUTPUTS_DIR, "history_index.json")
REMINDERS_FIRED = os.path.join(OUTPUTS_DIR, "reminders_fired.json")

os.makedirs(OUTPUTS_DIR, exist_ok=True)

NOTIFICATION_BUFFER: List[Dict[str, Any]] = []
NOTIFICATION_LOCK = threading.Lock()
STOP_THREAD = False

LOCAL_TZ = tzlocal.get_localzone()


def _read_uploaded_file(uploaded) -> Tuple[str, Optional[str]]:
    if not uploaded:
        return "", None
    if isinstance(uploaded, dict):
        path = uploaded.get("name") or uploaded.get("tmp_path") or uploaded.get("file_name")
        if path and os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return f.read().decode("utf-8", errors="replace"), path
            except Exception:
                pass
        content = uploaded.get("data") or uploaded.get("content") or str(uploaded)
        return str(content), None
    try:
        if hasattr(uploaded, "read"):
            raw = uploaded.read()
            if isinstance(raw, (bytes, bytearray)):
                return raw.decode("utf-8", errors="replace"), getattr(uploaded, "name", None)
            else:
                return str(raw), getattr(uploaded, "name", None)
    except Exception:
        pass
    if isinstance(uploaded, str):
        if os.path.exists(uploaded):
            try:
                with open(uploaded, "rb") as f:
                    return f.read().decode("utf-8", errors="replace"), uploaded
            except Exception:
                pass
        return uploaded, None
    return str(uploaded), None


def _parse_iso_to_local(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        s = ts.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    except Exception:
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(LOCAL_TZ)
    except Exception:
        return dt


def _format_time_from_iso(ts: str) -> str:
    dt_local = _parse_iso_to_local(ts)
    if not dt_local:
        return ts or ""
    return dt_local.strftime("%I:%M %p")


def _format_date_display(ts: str) -> str:
    dt_local = _parse_iso_to_local(ts)
    if not dt_local:
        return ts or ""
    return dt_local.strftime("%B %d, %Y at %I:%M %p")


def run_orchestrator_on_input(raw_text: str) -> dict:
    orch = create_orchestrator()
    result = asyncio.run(orch.process_tasks(raw_text))
    return result


def format_schedule_html(result: dict, created_at_iso: Optional[str] = None) -> str:
    """
    Convert orchestrator result to Bootstrap-styled HTML schedule.
    Ensures the header timestamp uses the same created_at_iso that is used for filename + history.
    Also normalizes priority icons and supports plain-text input like:
        "Task name (high, 60 min)"
    """
    outputs = result.get("outputs", {}) or {}
    planned = outputs.get("planned", {}) or {}
    reminders = outputs.get("reminders", {}) or {}
    evaluation = outputs.get("evaluation", {}) or {}

    scheduled = planned.get("scheduled_tasks", []) or []
    tasks = [t for t in scheduled if t.get("type") == "task"]
    breaks = [b for b in scheduled if b.get("type") == "break"]

    total_work = sum(int(t.get("duration", 0)) for t in tasks)
    total_break = sum(int(b.get("duration", 0)) for b in breaks)
    reminder_count = reminders.get("reminder_count", 0)

    score = evaluation.get("total_score", 0)
    grade = evaluation.get("grade", "N/A")
    scores = evaluation.get("scores_breakdown", {}) or {}
    recommendations = evaluation.get("recommendations", []) or []

    # Single canonical timestamp for filename + history + header
    if created_at_iso:
        now_str = created_at_iso
    else:
        now_str = result.get("completed_at") or datetime.utcnow().replace(
            tzinfo=timezone.utc
        ).isoformat()
    gen_display = _format_date_display(now_str)

    # --- Header card ---
    html = f"""
<div class='output-scroll-wrapper'>
  <div class="container-fluid output-container">

    <!-- Header / title card -->
    <div class="card schedule-card header-card mb-3">
      <div class="card-body d-flex align-items-start gap-3">
        <div class="d-flex align-items-center justify-content-center rounded-3 bg-light bg-opacity-25" style="width:42px;height:42px;">
          <span class="fs-4">🤖</span>
        </div>
        <div>
          <h5 class="card-title mb-1">Agent Schedule Summary</h5>
          <p class="card-subtitle small mb-0 opacity-75">{gen_display}</p>
        </div>
      </div>
    </div>
"""

    # --- Score / evaluation card ---
    html += f"""
    <div class="card schedule-card score-card mb-3">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-3">
          <div class="d-flex align-items-center justify-content-center rounded-3 bg-dark bg-opacity-50" style="width:36px;height:36px;">
            <span class="fs-5">📊</span>
          </div>
          <h5 class="card-title mb-0">
            Plan Quality · {score:.1f}/100 · Grade {grade}
          </h5>
        </div>
        <div class="score-bars d-flex flex-column gap-3">
"""

    for key, value in scores.items():
        pretty_name = key.replace("_", " ").title()
        try:
            v = float(value)
        except Exception:
            v = 0.0
        pct = max(0.0, min(v / 25.0, 1.0)) * 100.0
        html += f"""
          <div class="score-row row align-items-center g-2">
            <div class="col-12 col-md-3">
              <span class="score-label text-secondary fw-semibold small">{pretty_name}</span>
            </div>
            <div class="col">
              <div class="score-bar-container bg-dark rounded-pill overflow-hidden">
                <div class="score-bar-fill bg-success" style="width: {pct:.1f}%;"></div>
              </div>
            </div>
            <div class="col-auto">
              <span class="score-num fw-bold small">{v:.1f}/25</span>
            </div>
          </div>
"""

    html += """
        </div>
      </div>
    </div>
"""

    # --- Overview stats ---
    html += f"""
    <div class="card schedule-card overview-card mb-3">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-3">
          <div class="d-flex align-items-center justify-content-center rounded-3 bg-dark bg-opacity-50" style="width:36px;height:36px;">
            <span class="fs-5">📋</span>
          </div>
          <h5 class="card-title mb-0">Overview</h5>
        </div>
        <div class="overview-grid">
          <div class="overview-item">
            <div class="ov-label">Total Tasks</div>
            <div class="ov-value">{len(tasks)}</div>
          </div>
          <div class="overview-item">
            <div class="ov-label">Planned Work</div>
            <div class="ov-value">{total_work // 60}h {total_work % 60}m</div>
          </div>
          <div class="overview-item">
            <div class="ov-label">Planned Breaks</div>
            <div class="ov-value">{total_break // 60}h {total_break % 60}m</div>
          </div>
          <div class="overview-item">
            <div class="ov-label">Reminders</div>
            <div class="ov-value">{reminder_count}</div>
          </div>
        </div>
      </div>
    </div>
"""

    # --- Timeline (tasks + breaks) ---
    html += """
    <div class="card schedule-card tasks-card mb-3">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-3">
          <div class="d-flex align-items-center justify-content-center rounded-3 bg-dark bg-opacity-50" style="width:36px;height:36px;">
            <span class="fs-5">🗂</span>
          </div>
          <h5 class="card-title mb-0">Agent Timeline</h5>
        </div>
        <div class="tasks-list">
"""

    for item in scheduled:
        item_type = (item.get("type") or "task").lower()
        if item_type == "task":
            start = _format_time_from_iso(item.get("start_time", ""))
            end = _format_time_from_iso(item.get("end_time", ""))
            dur = int(item.get("duration", 0))

            raw_name = item.get("name") or ""
            display_name = raw_name

            # detect priority, first from structured field:
            raw_pr = (item.get("priority") or "").strip().lower()

            # if that is missing / generic, try to infer from "(high, 30 min)" pattern in the name
            m = re.search(r"\((high|medium|low)\s*,", raw_name, flags=re.IGNORECASE)
            if m:
                raw_pr = m.group(1).lower()
                # clean the name to remove the "(high, 30 min)" annotation
                display_name = re.sub(r"\s*\([^)]*\)\s*$", "", raw_name).strip()

            # normalize and map to icon
            if raw_pr.startswith("high"):
                icon = "🔴"
            elif raw_pr.startswith("low"):
                icon = "🟢"
            elif raw_pr.startswith("med"):
                icon = "🟡"
            else:
                icon = "🟡"

            category = (item.get("category") or "General").title()

            html += f"""
          <div class="task-item d-flex align-items-start gap-2">
            <div class="task-priority-icon flex-shrink-0 pt-1">{icon}</div>
            <div class="task-details">
              <div class="task-name">{display_name}</div>
              <div class="task-meta small text-secondary">
                <span class="me-2">⏱️ {start} - {end} ({dur} min)</span>
                <span>🏷️ {category}</span>
              </div>
            </div>
          </div>
"""
        else:
            start = _format_time_from_iso(item.get("start_time", ""))
            end = _format_time_from_iso(item.get("end_time", ""))
            dur = int(item.get("duration", 0))
            html += f"""
          <div class="break-item d-flex align-items-start gap-2">
            <div class="break-icon flex-shrink-0 pt-1">☕</div>
            <div class="break-details">
              <span class="break-time d-block">{start} - {end}</span>
              <span class="break-duration small text-secondary">({dur} min break)</span>
            </div>
          </div>
"""

    html += """
        </div>
      </div>
    </div>
"""

    # --- Tips & recommendations ---
    html += """
    <div class="card schedule-card tips-card mb-3">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-3">
          <div class="d-flex align-items-center justify-content-center rounded-3 bg-dark bg-opacity-50" style="width:36px;height:36px;">
            <span class="fs-5">💡</span>
          </div>
          <h5 class="card-title mb-0">Tips & Recommendations</h5>
        </div>
        <ul class="tips-list list-unstyled mb-0">
"""
    if recommendations:
        for rec in recommendations:
            html += f"          <li>{rec}</li>\n"
    else:
        html += """          <li>Take regular breaks to stay focused.</li>
          <li>Start your day with the highest-priority tasks.</li>
          <li>Review the plan mid-day and adjust if needed.</li>
"""

    html += """
        </ul>
      </div>
    </div>

  </div>
</div>
"""
    return html


def _save_history_entry(html_content: str, meta: dict) -> dict:
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    # get a single canonical timestamp, defaulting to now UTC
    created_at = meta.get("created_at") or datetime.utcnow().replace(
        tzinfo=timezone.utc
    ).isoformat()

    # use it for filename (sanitized) and index
    ts_for_filename = created_at.replace(":", "-").replace(".", "-")
    filename = f"schedule_{ts_for_filename}.html"
    path = os.path.join(OUTPUTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)

    index: List[dict] = []
    if os.path.exists(HISTORY_INDEX):
        try:
            with open(HISTORY_INDEX, "r", encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = []

    entry = {
        "id": filename,
        "title": meta.get("title", "Schedule"),
        "created_at": created_at,
    }
    index.insert(0, entry)
    index = index[:500]
    with open(HISTORY_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    return entry


def _load_history_index() -> List[dict]:
    if os.path.exists(HISTORY_INDEX):
        try:
            with open(HISTORY_INDEX, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _read_history_file(filename: str) -> str:
    if not filename or not isinstance(filename, str):
        return "<div class='card schedule-card'><div class='card-body'><h5 class='card-title mb-0'>Not found</h5></div></div>"
    path = os.path.join(OUTPUTS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<div class='card schedule-card'><div class='card-body'><h5 class='card-title mb-0'>Not found</h5></div></div>"


def _write_reminders_file(entries: List[dict]) -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
    filename = f"reminders_session_{ts}.json"
    path = os.path.join(OUTPUTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str)
    return path


def _load_all_reminders() -> List[dict]:
    reminders: List[dict] = []
    for fname in os.listdir(OUTPUTS_DIR):
        if fname.startswith("reminders_session_") and fname.endswith(".json"):
            try:
                path = os.path.join(OUTPUTS_DIR, fname)
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        reminders.extend(data)
            except Exception:
                continue
    return reminders


def _persist_fired(fired_set: set):
    try:
        with open(REMINDERS_FIRED, "w", encoding="utf-8") as f:
            json.dump(list(fired_set), f)
    except Exception:
        pass


def _load_fired() -> set:
    if not os.path.exists(REMINDERS_FIRED):
        return set()
    try:
        with open(REMINDERS_FIRED, "r", encoding="utf-8") as f:
            arr = json.load(f)
            return set(arr if isinstance(arr, list) else [])
    except Exception:
        return set()


def _reminder_checker_loop(interval_seconds: int = 30):
    fired = _load_fired()
    while not STOP_THREAD:
        try:
            all_reminders = _load_all_reminders()
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            for rem in all_reminders:
                st = rem.get("scheduled_time") or rem.get("time") or rem.get("when")
                if not st:
                    continue
                scheduled_dt_local = _parse_iso_to_local(st)
                if scheduled_dt_local is None:
                    continue
                try:
                    scheduled_dt_utc = scheduled_dt_local.astimezone(timezone.utc)
                except Exception:
                    scheduled_dt_utc = scheduled_dt_local.replace(tzinfo=timezone.utc)
                unique_id = rem.get("id") or (rem.get("message") or "") + "_" + str(st)
                if unique_id in fired:
                    continue
                if scheduled_dt_utc <= now + timedelta(seconds=1):
                    notif = {
                        "id": unique_id,
                        "message": rem.get("message") or rem.get("text") or "Reminder",
                        "scheduled_time": st,
                        "meta": rem,
                    }
                    with NOTIFICATION_LOCK:
                        NOTIFICATION_BUFFER.append(notif)
                    fired.add(unique_id)
            _persist_fired(fired)
        except Exception:
            pass
        for _ in range(int(interval_seconds / 1)):
            if STOP_THREAD:
                break
            time.sleep(1)


checker_thread = threading.Thread(
    target=_reminder_checker_loop, args=(30,), daemon=True
)
checker_thread.start()


def build_ui():
    # --- Bootstrap-based styling (light custom CSS only for layout + theme) ---
    css = r"""
@import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css');

/* ---------- Color system (inspired by your screenshot) ---------- */
:root {
    --primary: #00C853;          /* main green */
    --primary-dark: #00A344;
    --primary-soft: #E7FBEF;
    --primary-soft-strong: #CCF5DE;
    --bg-main: #F4F6FB;
    --bg-surface: #FFFFFF;
    --bg-chat: #F8FAFF;
    --text-main: #102A43;
    --text-muted: #7B8794;
    --border-subtle: #E1E5F0;
    --shadow-soft: 0 14px 40px rgba(15, 23, 42, 0.10);
}

/* ---------- Base ---------- */

* { box-sizing: border-box; }

body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background-color: var(--bg-main);
    color: var(--text-main);
}

.gradio-container {
    max-width: 100% !important;
    background: transparent !important;
}

/* ---------- Layout ---------- */

.main-container {
    display: flex;
    flex-direction: row;
    width: 100%;
    min-height: calc(100vh - 40px);   /* leave space for Gradio footer */
    align-items: stretch;             /* children stretch to same row height */
}


/* sidebar: fixed width, full column, scroll inside if needed */
.sidebar {
    width: 260px;
    max-width: 260px;
    background: var(--bg-surface);
    border-right: 1px solid var(--border-subtle);
    display: flex !important;
    flex-direction: column;
    flex: 0 0 260px;
    box-shadow: 5px 0 20px rgba(15, 23, 42, 0.04);
    z-index: 5;
    /* no explicit height; flex will match main column height */
}
/* main content: fills remaining width */
.content-area {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    background: radial-gradient(circle at top, #FFFFFF 0, var(--bg-main) 60%);
    /* no explicit height; flex takes row height */
}

/* ---------- Top bar ---------- */

.content-header {
    padding: 0.35rem 1.25rem !important;
    border-bottom: 1px solid rgba(226, 232, 240, 0.85);
    background: var(--bg-surface);
    position: sticky;
    top: 0;
    z-index: 3;
}

.content-title {
    font-size: 1.25rem;
    font-weight: 650;
    color: var(--text-main);
}

.content-subtitle {
    font-size: 0.88rem;
    color: var(--text-muted);
}

/* ---------- Sidebar content ---------- */

.sidebar-nav-header {
    padding: 1.25rem 1.25rem 0.8rem 1.25rem;
    border-bottom: 1px solid var(--border-subtle);
}

.sidebar-title-block {
    display: flex;
    gap: 0.75rem;
    align-items: center;
}

.sidebar-avatar {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    border-radius: 50%;
    background: var(--primary);
    color: #FFFFFF;
    box-shadow: 0 8px 18px rgba(0, 200, 83, 0.35);
    font-size: 1.1rem;
}

.sidebar-title-main {
    font-size: 0.98rem;
    font-weight: 600;
    color: var(--text-main);
}

.sidebar-title-sub {
    font-size: 0.78rem;
    color: var(--text-muted);
}

/* Sidebar nav buttons */
.sidebar-btn {
    width: calc(100% - 1.5rem);
    margin: 0.35rem 0.75rem;
    padding: 0.55rem 0.95rem;
    border-radius: 999px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.88rem;
    display: flex !important;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    transition: all 0.12s ease-in-out;
    visibility: visible !important;
    opacity: 1 !important;
}

.sidebar-btn:hover {
    background: var(--primary-soft);
    border-color: var(--primary-soft-strong);
    color: var(--primary-dark);
}

.sidebar-btn-active {
    background: var(--primary);
    border-color: var(--primary-dark);
    color: #FFFFFF;
    box-shadow: 0 0 0 2px rgba(0, 200, 83, 0.18);
}

/* Legend & footer */
.sidebar-footer {
    padding: 0.9rem 1.25rem 1.1rem 1.25rem;
    margin-top: auto;
    font-size: 0.75rem;
    color: var(--text-muted);
    border-top: 1px solid var(--border-subtle);
}

/* ---------- Output container (center "chat" panel) ---------- */

.output-scroll-wrapper {
    padding: 0.5rem 1rem !important;
}

/* ---------- Cards / schedule area ---------- */

.schedule-card.card {
    border-radius: 18px;
    border: 1px solid var(--border-subtle);
    background-color: var(--bg-surface);
    box-shadow: var(--shadow-soft);
}

/* Header card: like green app bar from your screenshot */
.schedule-card.header-card {
    background: var(--primary);
    border: none;
    color: #ffffff;
    box-shadow: 0 16px 35px rgba(0, 200, 83, 0.35);
}

.schedule-card.header-card .card-title,
.schedule-card.header-card .card-subtitle {
    color: #ffffff;
}

/* Overview tiles */
.overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
    margin-top: 0.75rem;
}

.overview-item {
    border-radius: 0.9rem;
    padding: 0.85rem 0.9rem;
    background: var(--primary-soft);
    border: 1px solid var(--primary-soft-strong);
}

.ov-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--text-muted);
    margin-bottom: 0.15rem;
}

.ov-value {
    font-size: 1.35rem;
    font-weight: 650;
    color: var(--primary-dark);
}

/* Score bars */
.score-bar-container {
    height: 6px;
    border-radius: 999px;
    background: #E5E7EB;
}

.score-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--primary);
}

/* Timeline list styled like chat messages */
.tasks-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 0.5rem;
}

.task-item,
.break-item {
    border-radius: 1rem;
    padding: 0.65rem 0.8rem;
    background: var(--bg-chat);
}

.task-item {
    border: 1px solid var(--border-subtle);
}

.break-item {
    border: 1px solid rgba(0, 200, 83, 0.4);
    background: #F1FFF6;
}

.task-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-main);
}

.task-meta {
    font-size: 0.8rem;
    color: var(--text-muted);
}

.break-duration,
.break-time {
    font-size: 0.82rem;
}

/* Tips */
.tips-list li {
    padding-left: 1.2rem;
    position: relative;
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
}

.tips-list li::before {
    content: "•";
    position: absolute;
    left: 0;
    top: 0;
    color: var(--primary-dark);
    font-size: 1rem;
    line-height: 1;
}

/* ---------- Empty state (first view) ---------- */

.empty-state {
    border-radius: 18px;
    border: 1px dashed var(--border-subtle);
    padding: 3rem 1.5rem;
    text-align: center;
    background: var(--bg-surface);
    box-shadow: var(--shadow-soft);
}

.empty-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: var(--primary);
    display:flex;
    align-items:center;
    justify-content:center;
    font-size: 2.4rem;
    margin: 0 auto 1rem auto;
    color: #ffffff;
    box-shadow: 0 16px 40px rgba(0, 200, 83, 0.45);
}

.empty-state h3 {
    font-size: 1.1rem;
    margin-bottom: 0.3rem;
    color: var(--text-main);
}

.empty-state p {
    font-size: 0.9rem;
    color: var(--text-muted);
    max-width: 460px;
    margin: 0 auto;
}

/* ---------- Input area (bottom) - Reduced Height Version ---------- */

.input-area {
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-surface);

    /* Reduced padding */
    padding: 0.45rem 1rem 0.60rem 1rem !important;

    position: sticky;
    bottom: 0;
    z-index: 2;

    /* Smaller shadow for a tighter feel */
    box-shadow: 0 -4px 10px rgba(15, 23, 42, 0.04) !important;
}

/* Textbox area slimmed down */
#task_input {
    min-height: 65px !important;      /* was 120px → now compact */
    border-radius: 6px !important;
    border: 1px solid var(--border-subtle);
    background: var(--bg-chat);

    padding: 0.45rem 0.75rem !important; /* reduced padding */
}

#task_input textarea {
    border-radius: 6px !important;
    line-height: 1.25 !important;      /* more density */
    padding: 0.25rem 0.5rem !important; /* inner textarea padding */
}

/* Generate button */
#generate_btn {
    font-weight: 600;
    border-radius: 999px !important;

    /* slightly smaller button */
    padding: 0.35rem 1rem !important;
    font-size: 0.88rem !important;

    background: var(--primary) !important;
    border-color: var(--primary-dark) !important;
}

#generate_btn:hover {
    background: var(--primary-dark) !important;
}

/* ---------- Reminders list ---------- */

.reminders-scroll {
    max-height: 480px;
    overflow-y: auto;
    padding: 1.25rem 1.75rem;
    background: transparent;
}

.reminder-date-header {
    font-size: 0.83rem;
    font-weight: 600;
    padding: 0.4rem 0.75rem;
    border-radius: 999px;
    background: var(--primary-soft);
    border: 1px solid var(--primary-soft-strong);
    margin-bottom: 0.5rem;
    color: var(--primary-dark);
}

.reminder-item {
    border-radius: 1rem;
    padding: 0.55rem 0.8rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    font-size: 0.85rem;
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom: 0.45rem;
}

.reminder-message {
    color: var(--text-main);
}

.reminder-time {
    color: var(--text-muted);
    font-size: 0.8rem;
    white-space: nowrap;
    padding-left: 0.75rem;
}

/* ---------- Toast notifications (bottom-right) ---------- */

.toast-wrap {
    position: fixed;
    right: 1.5rem;
    bottom: 1.5rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.toast {
    background: var(--bg-surface);
    border-radius: 14px;
    border: 1px solid var(--primary-soft-strong);
    padding: 0.85rem 1rem;
    display: flex;
    gap: 0.6rem;
    align-items: flex-start;
    box-shadow: var(--shadow-soft);
}

.toast .title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-main);
}

.toast .time {
    font-size: 0.8rem;
    color: var(--text-muted);
}

/* ---------- Help panel ---------- */

.help-container {
    padding: 1.75rem;
    font-size: 0.9rem;
    background: var(--bg-surface);
    border-radius: 18px;
    border: 1px solid var(--border-subtle);
    box-shadow: var(--shadow-soft);
    margin: 1.25rem 1.75rem;
}

.help-container h3 {
    font-size: 1.05rem;
    margin-bottom: 0.75rem;
    color: var(--text-main);
}


.help-container ul {
    padding-left: 1.25rem;
}

.help-container li {
    margin-bottom: 0.45rem;
    color: var(--text-muted);
}

/* ---------- Responsive ---------- */
/* ---------- Mobile / Tablet Responsive Layout ---------- */
@media (max-width: 992px) {

    /* Entire layout becomes vertical */
    .main-container {
        flex-direction: column;
    }

    /* Sidebar becomes a TOP NAVBAR (not scrollable) */
    /* Sidebar becomes a TOP NAVBAR (not scrollable) */
.sidebar {
    width: 100% !important;
    max-width: 100% !important;

    display: flex !important;
    flex-direction: row !important;
    justify-content: space-around !important;
    align-items: center !important;

    padding: 0.60rem 0.75rem;

    border-right: none !important;
    border-bottom: 1px solid var(--border-subtle) !important;

    overflow-x: hidden !important;  /* prevents horizontal scroll */
    overflow-y: hidden !important;  /* prevents vertical scroll */

    box-shadow: none !important;
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--bg-surface) !important;

    /* 👇 IMPORTANT: DO NOT SET HEIGHT! */
    height: auto !important;
}


    /* Hide header block inside sidebar */
    .sidebar-nav-header,
    .sidebar-footer {
        display: none !important;
    }

    /* Turn nav buttons into horizontal pills */
    .sidebar-btn {
        flex: 1 1 auto;
        white-space: nowrap;
        text-align: center;
        margin: 0.25rem;
        border-radius: 8px !important;
    }

    /* Make ACTIVE button bold + visible */
    .sidebar-btn-active {
        background: var(--primary-dark) !important;
        color: white !important;
        border-color: var(--primary) !important;
    }

    .content-area {
        min-height: auto;
    }
}


/* ensure nav buttons are always clickable */
button.sidebar-btn {
    pointer-events: auto !important;
    user-select: none !important;
}
"""

    with gr.Blocks(css=css, title="Personal Productivity Agent", theme=gr.themes.Soft()) as demo:
        with gr.Column(elem_classes="main-container"):
            # ---------- SIDEBAR ----------
            with gr.Column(scale=0, elem_classes="sidebar"):
                gr.HTML(
                    """
                <div class="sidebar-nav-header">
                    <div class="sidebar-title-block">
                        <div class="sidebar-avatar">PA</div>
                        <div>
                            <div class="sidebar-title-main">Productivity Agent</div>
                            <div class="sidebar-title-sub">Structured daily planning</div>
                        </div>
                    </div>
                </div>
                """
                )

                # Navigation buttons (classes toggled in Python)
                btn_new = gr.Button(" New Schedule", elem_classes="sidebar-btn sidebar-btn-active")
                btn_history = gr.Button(" History", elem_classes="sidebar-btn")
                btn_reminders = gr.Button(" Reminders", elem_classes="sidebar-btn")
                btn_help = gr.Button(" Help & Guide", elem_classes="sidebar-btn")

                gr.HTML(
                    """
                    <div style="padding:12px">
                        <div style="font-size:11px;color:#9ca3af;font-weight:600;margin-bottom:6px;text-transform:uppercase;letter-spacing:.08em;">Priority Legend</div>
                        <div class="border rounded-3 p-2" style="font-size:12px;border-color:rgba(148,163,184,0.4)!important;background:rgba(15,23,42,0.92);">
                            <div class="mb-1 text-light"><span>🔴</span> High · Urgent & critical</div>
                            <div class="mb-1 text-light"><span>🟡</span> Medium · Important</div>
                            <div class="text-light"><span>🟢</span> Low · Flexible</div>
                        </div>
                    </div>
                """
                )
                gr.HTML(
                    """
                    <div class="sidebar-footer">
                        <div>Powered by Gemini-based orchestration.</div>
                        <div>Designed for structured, reliable planning.</div>
                    </div>
                """
                )

            # ---------- MAIN AREA ----------
            with gr.Column(scale=4, elem_classes="content-area"):
                gr.HTML(
                    """
                    <div class="content-header">
                        <div>
                            <div class="content-title">Personal Productivity Agent</div>
                            <div class="content-subtitle">Describe your tasks and constraints – the agent will design an optimized, realistic schedule.</div>
                        </div>
                    </div>
                    """
                )

                notification_area = gr.HTML(
                    "<div class='toast-wrap' id='toast_wrap'></div>", elem_id="notification_area"
                )

                # New Schedule output
                new_output_html = gr.HTML(
                    "<div class='output-scroll-wrapper'><div class='output-area'><div class='empty-state'><div class='empty-icon'>🤖</div><h3>Ready to plan your day with the agent?</h3><p>Type your tasks, meetings and constraints below. The agent will respond with a full schedule.</p></div></div></div>",
                    elem_id="new_output",
                )

                # History section (hidden by default)
                history_label = gr.Markdown("**Saved Schedules**", visible=False)
                history_dropdown = gr.Dropdown(
                    choices=[],
                    label="",
                    show_label=False,
                    elem_id="history_dropdown",
                    visible=False,
                    interactive=True,
                    allow_custom_value=True,
                    type="value",
                )

                history_preview = gr.HTML(
                    "<div style='padding:24px;'>History preview will appear here.</div>",
                    elem_id="history_preview",
                    visible=False,
                )

                # Reminders section (hidden by default)
                reminder_input = gr.Textbox(
                    show_label=False,
                    placeholder="Add a reminder (e.g., Call Alice at 4:00 PM)",
                    visible=False,
                )
                add_reminder_btn = gr.Button("Add Reminder", visible=False)
                reminders_html = gr.HTML(
                    "<div class='reminders-scroll'>No reminders yet.</div>",
                    elem_id="rem_list",
                    visible=False,
                )

                help_html = gr.HTML(
                    """
                    <div class="help-container" style="padding: 1rem; line-height: 1.6; font-size: 15px;">
                        <h3 style="margin-bottom: 10px;">How to Use the Productivity Agent</h3>

                        <p>The agent can understand tasks written in <strong>plain language</strong> or provided as
                        <strong>structured JSON</strong>. Follow the examples below to get the best results.</p>

                        <h4>✔ Plain Language Example</h4>
                        <pre style="background:#f5f5f5;padding:10px;border-radius:6px;white-space:pre-wrap;">
                Roadmap planning (high, 120 min)
                User feedback analysis (medium, 90 min)
                Backlog grooming (medium, 60 min)
                Stakeholder meeting (high, 90 min)
                Competitor research (low, 45 min)
                        </pre>

                        <h4>✔ JSON Input Example</h4>
                        <pre style="background:#f5f5f5;padding:10px;border-radius:6px;white-space:pre-wrap;">
                {
                "tasks": [
                    {
                    "name": "Roadmap planning session",
                    "category": "planning",
                    "priority": "high",
                    "estimated_duration": 120,
                    "deadline": "2025-11-19T14:00:00"
                    },
                    {
                    "name": "User feedback analysis",
                    "category": "research",
                    "priority": "medium",
                    "estimated_duration": 90,
                    "deadline": "2025-11-20T16:00:00"
                    },
                    {
                    "name": "Backlog grooming",
                    "category": "planning",
                    "priority": "medium",
                    "estimated_duration": 60,
                    "deadline": "2025-11-21T11:00:00"
                    },
                    {
                    "name": "Stakeholder update meeting",
                    "category": "meeting",
                    "priority": "high",
                    "estimated_duration": 90,
                    "deadline": "2025-11-22T10:00:00"
                    },
                    {
                    "name": "Competitor analysis",
                    "category": "research",
                    "priority": "low",
                    "estimated_duration": 45,
                    "deadline": "2025-11-23T15:00:00"
                    },
                    {
                    "name": "Product demo preparation",
                    "category": "preparation",
                    "priority": "medium",
                    "estimated_duration": 60,
                    "deadline": "2025-11-24T12:00:00"
                    }
                ]
                }
                        </pre>

                        <h4>✔ Other features</h4>
                        <ul>
                            <li>View old schedules in the <strong>History</strong> tab.</li>
                            <li>Create time-based notifications from the <strong>Reminders</strong> tab.</li>
                            <li>Use the left navigation menu to switch between features.</li>
                        </ul>
                    </div>
                    """,
                    visible=False,
                )
     # Input area (only visible on New Schedule)
                with gr.Column(elem_classes="input-area") as input_area:
                    text_input = gr.Textbox(
                        lines=6,
                        placeholder=(
                            "Example: \n"
                            "Morning standup (high, 30 min)\n"
                            "Code new feature (high, 180 min)\n"
                            "Debug login issue (medium, 90 min)\n"
                            "Write unit tests (medium, 120 min)\n"
                            "Team retrospective (low, 45 min)\n\n"
                            "You can also paste JSON with a 'tasks' list."
                        ),
                        show_label=False,
                        elem_id="task_input",
                    )
                    uploaded_file = gr.File(
                        label="Upload .json/.txt (optional)",
                        file_types=[".json", ".txt"],
                        show_label=False,
                        elem_id="file_input",
                    )
                    gen_btn = gr.Button(
                        "🚀  Generate Schedule",
                        elem_id="generate_btn",
                        elem_classes="btn btn-primary mt-2",
                    )

        chat_state = gr.State([])

        # ---------- PAGE SWITCHING + ACTIVE NAV ----------
        def set_page(page: str):
            """Return updates for: main panels + which nav button is active."""
            idx = _load_history_index()
            choices = []
            for e in idx:
                try:
                    created_at = e.get("created_at")
                    label = _format_date_display(created_at)
                except Exception:
                    label = e.get("id", "Schedule")
                choices.append((label, e.get("id")))

            active = "sidebar-btn sidebar-btn-active"
            inactive = "sidebar-btn"

            if page == "new":
                return (
                    # panels
                    gr.update(visible=True),   # new_output_html
                    gr.update(visible=False),  # history_label
                    gr.update(visible=False),  # history_dropdown
                    gr.update(visible=False),  # history_preview
                    gr.update(visible=False),  # reminder_input
                    gr.update(visible=False),  # add_reminder_btn
                    gr.update(visible=False),  # reminders_html
                    gr.update(visible=False),  # help_html
                    gr.update(visible=True),   # input_area
                    [],             # chat_state
                    # nav buttons
                    gr.update(elem_classes=active),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=inactive),
                )

            if page == "history":
                idx = _load_history_index()

                choices = []
                today_id = None
                today_str = datetime.utcnow().strftime("%Y-%m-%d")

                for e in idx:
                    created_at = e.get("created_at")
                    try:
                        label = _format_date_display(created_at)
                        date_only = created_at[:10] if created_at else ""
                    except Exception:
                        label = e.get("id", "Schedule")
                        date_only = ""

                    schedule_id = e.get("id")
                    choices.append((label, schedule_id))

                    # detect today's schedule
                    if date_only == today_str and today_id is None:
                        today_id = schedule_id

                # fallback to latest if no today schedule
                default_id = today_id or (choices[0][1] if choices else None)

                preview_html = (
                    _read_history_file(default_id)
                    if default_id
                    else "<div style='padding:24px;'>No history available.</div>"
                )

                return (
                    gr.update(visible=False),
                    gr.update(visible=True, value="**Saved Schedules**"),
                    gr.update(
                        visible=True,
                        choices=choices,
                        value=("Select a schedule" if not default_id else default_id),
                    ),
                    gr.update(visible=True, value=preview_html),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.State([]),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=active),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=inactive),
                )

            if page == "reminders":
                rems = _load_all_reminders()
                if rems:
                    from collections import defaultdict
                    grouped: Dict[tuple, List[dict]] = defaultdict(list)
                    for r in rems:
                        st = r.get("scheduled_time", "")
                        dt_local = _parse_iso_to_local(st)
                        if dt_local:
                            date_key = dt_local.strftime("%Y-%m-%d")
                            date_display = dt_local.strftime("%A, %B %d, %Y")
                        else:
                            date_key = "unknown"
                            date_display = "Unknown Date"
                        grouped[(date_key, date_display)].append(r)
                    sorted_dates = sorted(grouped.keys(), key=lambda x: x[0])
                    html = "<div class='reminders-scroll'>"
                    for date_key, date_display in sorted_dates:
                        html += "<div class='reminder-date-group mb-3'>"
                        html += f"<div class='reminder-date-header'>📅 {date_display}</div>"
                        for r in grouped[(date_key, date_display)]:
                            time_display = _format_time_from_iso(r.get('scheduled_time', ''))
                            html += f"""
                            <div class='reminder-item'>
                                <div class='reminder-message'>🔔 {r.get('message', '-')}</div>
                                <div class='reminder-time'>{time_display}</div>
                            </div>
                            """
                        html += "</div>"
                    html += "</div>"
                else:
                    html = "<div class='reminders-scroll text-secondary'>No reminders yet.</div>"

                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=True, value=html),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.State([]),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=active),
                    gr.update(elem_classes=inactive),
                )

            if page == "help":
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.State([]),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=inactive),
                    gr.update(elem_classes=active),
                )

            # default: new
            return set_page("new")

        # nav button clicks
        outputs_list = [
            new_output_html,
            history_label,
            history_dropdown,
            history_preview,
            reminder_input,
            add_reminder_btn,
            reminders_html,
            help_html,
            input_area,
            chat_state,
            btn_new,
            btn_history,
            btn_reminders,
            btn_help,
        ]

        btn_new.click(fn=lambda: set_page("new"), inputs=None, outputs=outputs_list)
        btn_history.click(fn=lambda: set_page("history"), inputs=None, outputs=outputs_list)
        btn_reminders.click(fn=lambda: set_page("reminders"), inputs=None, outputs=outputs_list)
        btn_help.click(fn=lambda: set_page("help"), inputs=None, outputs=outputs_list)

        # ---------- GENERATE SCHEDULE ----------
        def _generate_and_save(text_input_value, uploaded_file_value, chat_state_val):
            file_text, _ = _read_uploaded_file(uploaded_file_value)
            raw_text = (
                file_text.strip()
                if file_text and str(file_text).strip()
                else (text_input_value or "").strip()
            )

            if not raw_text:
                error_html = """
<div class='output-scroll-wrapper'>
  <div class='card schedule-card'>
    <div class='card-body'>
      <div class='d-flex align-items-center gap-2 mb-2'>
        <span class='fs-5'>⚠️</span>
        <h5 class='card-title mb-0'>No tasks provided</h5>
      </div>
      <p class='mb-0 text-danger small'>
        Please enter tasks in the text box or upload a JSON/TXT file before generating a schedule.
      </p>
    </div>
  </div>
</div>
"""
                return (
                    chat_state_val,
                    gr.update(value=error_html),
                    gr.update(),
                    gr.update(value=error_html),
                )

            try:
                result = run_orchestrator_on_input(raw_text)

                # Local timestamp for user-facing things
                created_at_dt = datetime.now(LOCAL_TZ)
                created_at_iso = created_at_dt.isoformat()

                schedule_html = format_schedule_html(result, created_at_iso=created_at_iso)
                wrapped = f"<div class='output-scroll-wrapper'>{schedule_html}</div>"

                # Save history entry
                title = (raw_text[:80] + "...") if len(raw_text) > 80 else raw_text
                _save_history_entry(
                    wrapped,
                    meta={
                        "title": title,
                        "created_at": created_at_iso,
                        "source": "schedule",
                    },
                )

                # Build reminders from scheduled tasks
                outputs = result.get("outputs", {}) or {}
                planned = outputs.get("planned", {}) or {}
                scheduled = planned.get("scheduled_tasks", []) or []
                reminders_to_save: List[dict] = []

                for item in scheduled:
                    if item.get("type") == "task":
                        start_iso = item.get("start_time")
                        if start_iso:
                            reminders_to_save.append(
                                {
                                    "id": f"task_start_{item.get('name')}_{start_iso}",
                                    "scheduled_time": start_iso,
                                    "message": f"Start: {item.get('name')}",
                                }
                            )
                            raw_pr = (item.get("priority") or "").strip().lower()
                            is_high = raw_pr.startswith("high")
                            if is_high:
                                try:
                                    dt_local = _parse_iso_to_local(start_iso)
                                    if dt_local:
                                        early_local = (dt_local - timedelta(minutes=10)).astimezone(
                                            timezone.utc
                                        ).isoformat()
                                        reminders_to_save.append(
                                            {
                                                "id": f"task_high_alert_{item.get('name')}_{early_local}",
                                                "scheduled_time": early_local,
                                                "message": f"Upcoming (high-priority): {item.get('name')}",
                                            }
                                        )
                                except Exception:
                                    pass
                        due = item.get("due_date")
                        if due:
                            try:
                                dt_due_local = _parse_iso_to_local(due)
                                if dt_due_local:
                                    deadline_utc = (dt_due_local - timedelta(minutes=30)).astimezone(
                                        timezone.utc
                                    ).isoformat()
                                    reminders_to_save.append(
                                        {
                                            "id": f"task_due_{item.get('name')}_{deadline_utc}",
                                            "scheduled_time": deadline_utc,
                                            "message": f"Deadline soon: {item.get('name')}",
                                        }
                                    )
                            except Exception:
                                pass

                if reminders_to_save:
                    _write_reminders_file(reminders_to_save)

                # Refresh history dropdown
                idx = _load_history_index()
                choices = []
                default_id = None
                for i, e in enumerate(idx):
                    try:
                        label = _format_date_display(e.get("created_at"))
                    except Exception:
                        label = e.get("id")
                    schedule_id = e.get("id")
                    choices.append((label, schedule_id))
                    if i == 0:
                        default_id = schedule_id

                # Update chat state (optional preview)
                new_state = list(chat_state_val or [])
                preview_text = raw_text[:100] + ("..." if len(raw_text) > 100 else "")
                new_state.append(["Tasks submitted", preview_text])

                return (
                    new_state,
                    gr.update(value=wrapped),
                    gr.update(choices=choices, value=default_id),
                    gr.update(value=wrapped),
                )
            except Exception as e:
                err_html = f"""
<div class='output-scroll-wrapper'>
  <div class='card schedule-card'>
    <div class='card-body'>
      <div class='d-flex align-items-center gap-2 mb-2'>
        <span class='fs-5'>❌</span>
        <h5 class='card-title mb-0'>Error</h5>
      </div>
      <p class='mb-0 text-danger small'>{str(e)}</p>
    </div>
  </div>
</div>
"""
                return (
                    chat_state_val,
                    gr.update(value=err_html),
                    gr.update(),
                    gr.update(value=err_html),
                )

        gen_btn.click(
            fn=_generate_and_save,
            inputs=[text_input, uploaded_file, chat_state],
            outputs=[chat_state, new_output_html, history_dropdown, history_preview],
        )

        # ---------- HISTORY PREVIEW ----------
        def preview_history_file(selected):
            if not selected:
                return "<div style='padding:24px;'>No schedule selected.</div>"
            return _read_history_file(selected)

        history_dropdown.change(
            fn=preview_history_file,
            inputs=[history_dropdown],
            outputs=[history_preview],
        )

        # ---------- REMINDERS MANUAL ADD ----------
        def add_reminder(text):
            if not text or not text.strip():
                rems = _load_all_reminders()
                if rems:
                    html = "<div class='reminders-scroll'>" + "".join(
                        f"<div>{r.get('message')} <small class='text-secondary'>({_format_date_display(r.get('scheduled_time') or '')})</small></div>"
                        for r in rems
                    ) + "</div>"
                else:
                    html = "<div class='reminders-scroll text-secondary'>No reminders yet.</div>"
                return gr.update(value=""), gr.update(value=html)

            parsed_time = None
            msg = text.strip()
            try:
                lowered = text.lower()
                if " at " in lowered:
                    parts = text.rsplit(" at ", 1)
                    msg_text = parts[0].strip() if parts[0].strip() else "Reminder"
                    time_part = parts[1].strip()
                    try:
                        dt_try = datetime.strptime(time_part, "%I:%M %p")
                        today = datetime.utcnow().date()
                        combined = datetime.combine(today, dt_try.time())
                        parsed_time = combined.replace(tzinfo=timezone.utc).isoformat()
                        msg = msg_text if msg_text else msg
                    except Exception:
                        try:
                            dt_try = datetime.fromisoformat(time_part)
                            if dt_try.tzinfo is None:
                                dt_try = dt_try.replace(tzinfo=timezone.utc)
                            parsed_time = dt_try.astimezone(timezone.utc).isoformat()
                        except Exception:
                            parsed_time = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                else:
                    parsed_time = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                parsed_time = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

            rem = {
                "id": f"manual_{int(time.time())}",
                "scheduled_time": parsed_time,
                "message": msg,
            }
            _write_reminders_file([rem])
            rems = _load_all_reminders()
            html = "<div class='reminders-scroll'>" + "".join(
                f"<div>{r.get('message')} <small class='text-secondary'>({_format_date_display(r.get('scheduled_time') or '')})</small></div>"
                for r in rems
            ) + "</div>"
            return gr.update(value=""), gr.update(value=html)

        add_reminder_btn.click(
            fn=add_reminder,
            inputs=[reminder_input],
            outputs=[reminder_input, reminders_html],
        )

        # ---------- REMINDER POLLING ----------
        def poll_notifications():
            with NOTIFICATION_LOCK:
                items = NOTIFICATION_BUFFER.copy()
                NOTIFICATION_BUFFER.clear()
            if not items:
                return "<div class='toast-wrap' id='toast_wrap'></div>"
            toasts_html = "<div class='toast-wrap' id='toast_wrap'>"
            for it in items:
                try:
                    st = it.get("scheduled_time", "")
                    disp_time = _format_time_from_iso(st) or st
                    toasts_html += f"""
                    <div class="toast">
                        <div class="icon fs-4">🔔</div>
                        <div class="txt">
                            <div class="title">{it.get('message')}</div>
                            <div class="time">{disp_time}</div>
                        </div>
                    </div>
                    """
                except Exception:
                    continue
            toasts_html += "</div>"
            return toasts_html

        try:
            demo.load(fn=poll_notifications, inputs=None, outputs=[notification_area], every=3)
        except TypeError:
            demo.load(fn=poll_notifications, inputs=None, outputs=[notification_area])

        # initial page = New Schedule with New highlighted
        demo.load(
            fn=lambda: set_page("new"),
            inputs=None,
            outputs=[
                new_output_html,
                history_label,
                history_dropdown,
                history_preview,
                reminder_input,
                add_reminder_btn,
                reminders_html,
                help_html,
                input_area,
                chat_state,
                btn_new,
                btn_history,
                btn_reminders,
                btn_help,
            ],
        )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch(server_name="0.0.0.0", server_port=None, share=False, show_api=False)
