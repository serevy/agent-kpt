from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from agent_kpt.ledger import new_ledger


def agent_kpt_home() -> Path:
    override = os.environ.get("AGENT_KPT_HOME")
    return Path(override).expanduser() if override else Path.home() / ".agent-kpt"


def canonical_project_path(project: str | Path) -> Path:
    return Path(project).expanduser().resolve()


def project_key(project: str | Path) -> str:
    canonical = str(canonical_project_path(project))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return digest


def project_state_dir(project: str | Path) -> Path:
    return agent_kpt_home() / "projects" / project_key(project)


def report_dir(project: str | Path) -> Path:
    override = os.environ.get("AGENT_KPT_REPORT_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return project_state_dir(project) / "reports"


def work_dir(project: str | Path) -> Path:
    return project_state_dir(project) / "work"


def project_paths(project: str | Path, *, create: bool = True) -> dict[str, str]:
    state = project_state_dir(project)
    reports = report_dir(project)
    work = work_dir(project)
    if create:
        for path in (state, reports, work):
            path.mkdir(parents=True, exist_ok=True)
    return {
        "state_dir": str(state),
        "report_dir": str(reports),
        "work_dir": str(work),
    }


def ledger_path(project: str | Path) -> Path:
    return project_state_dir(project) / "ledger.json"


def last_packet_path(project: str | Path) -> Path:
    return project_state_dir(project) / "last-packet.json"


def load_ledger(project: str | Path) -> dict[str, Any]:
    path = ledger_path(project)
    if not path.exists():
        return new_ledger()
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"ledger at {path} must be a JSON object")
    return value


def save_ledger(project: str | Path, ledger: Mapping[str, Any]) -> Path:
    path = ledger_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(path, ledger)
    return path


def load_last_packet(project: str | Path) -> dict[str, Any] | None:
    path = last_packet_path(project)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def save_last_packet(project: str | Path, packet: Mapping[str, Any]) -> Path:
    path = last_packet_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(path, packet)
    return path


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
