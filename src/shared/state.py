import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


_STATE_DIR = Path(".runtime")
_STATE_FILE = _STATE_DIR / "state.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


class RunStateStore:
    @staticmethod
    def set_status(run_trace_id: str, phase: str, status: str, summary: Optional[Dict] = None) -> None:
        data = _read_all()
        entry = data.get(run_trace_id, {})
        entry.update(
            {
                "runTraceId": run_trace_id,
                "currentPhase": phase,
                "status": status,
                "isComplete": phase == "publish" and status == "completed",
                "lastUpdateUtc": _utc_now(),
                "summary": summary,
            }
        )
        data[run_trace_id] = entry
        _write_all(data)

    @staticmethod
    def get_status(run_trace_id: str) -> Optional[Dict]:
        data = _read_all()
        return data.get(run_trace_id)

