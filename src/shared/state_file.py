import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any, List

from .state_common import utc_now

# Use a temp-based directory by default to avoid Azure Functions
_DEFAULT_STATE_BASE = Path(tempfile.gettempdir()) / "autogensocial-agent-runtime"
_STATE_DIR = Path(os.getenv("RUNTIME_STATE_DIR", str(_DEFAULT_STATE_BASE)))
_STATE_FILE = _STATE_DIR / "state.json"


def _read_all() -> Dict[str, dict]:
    if not _STATE_FILE.exists():
        return {}
    try:
        return json.loads(_STATE_FILE.read_text())
    except Exception:
        return {}


def _write_all(data: Dict[str, dict]) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data))


class FileRunStateStore:
    @staticmethod
    def set_status(
        run_trace_id: str,
        phase: str,
        status: str,
        summary: Optional[Dict] = None,
        brand_id: Optional[str] = None,
        post_plan_id: Optional[str] = None,
    ) -> None:
        data = _read_all()
        entry = data.get(run_trace_id, {})
        entry.update(
            {
                "runTraceId": run_trace_id,
                "currentPhase": phase,
                "status": status,
                "isComplete": phase == "publish" and status == "completed",
                "lastUpdateUtc": utc_now(),
                "summary": summary,
                "brandId": brand_id or entry.get("brandId"),
                "postPlanId": post_plan_id or entry.get("postPlanId"),
            }
        )
        data[run_trace_id] = entry
        _write_all(data)

    @staticmethod
    def get_status(run_trace_id: str) -> Optional[Dict]:
        data = _read_all()
        return data.get(run_trace_id)

    @staticmethod
    def add_event(
        run_trace_id: str,
        *,
        phase: str,
        action: str,
        message: Optional[str] = None,
        status: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        store = _read_all()
        entry = store.get(run_trace_id) or {
            "runTraceId": run_trace_id,
            "currentPhase": phase,
            "status": status or "in_progress",
            "isComplete": False,
            "lastUpdateUtc": utc_now(),
        }
        events: List[Dict[str, Any]] = entry.get("events") or []
        ev: Dict[str, Any] = {"ts": utc_now(), "phase": phase, "action": action}
        if message:
            ev["message"] = message
        if status:
            ev["status"] = status
        if data is not None:
            ev["data"] = data
        events.append(ev)
        entry["events"] = events
        entry["lastUpdateUtc"] = utc_now()
        store[run_trace_id] = entry
        _write_all(store)
