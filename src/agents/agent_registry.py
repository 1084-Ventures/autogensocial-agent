import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any

from azure.cosmos import CosmosClient  # type: ignore


class AgentRegistry:
    """Persist a mapping from logical agent names to agent IDs.

    Uses Cosmos DB when configured, otherwise falls back to a local temp file.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("autogensocial")
        self._backend = self._select_backend()

    def _select_backend(self):
        conn_str = os.getenv("COSMOS_DB_CONNECTION_STRING")
        db_name = os.getenv("COSMOS_DB_NAME")
        container = os.getenv("COSMOS_DB_CONTAINER_AGENTS")
        if conn_str and db_name and container:
            try:
                client = CosmosClient.from_connection_string(conn_str)
                db = client.get_database_client(db_name)
                cont = db.get_container_client(container)
                # Probe read to validate access
                _ = cont.read()
                self._logger.info("AgentRegistry using Cosmos container '%s'", container)
                return ("cosmos", cont)
            except Exception as exc:  # pragma: no cover - best effort
                self._logger.warning(
                    "Cosmos not available for AgentRegistry (%s); falling back to file",
                    exc,
                )
        # fallback to file
        base = Path(tempfile.gettempdir()) / "autogensocial"
        base.mkdir(parents=True, exist_ok=True)
        path = base / "agents.json"
        if not path.exists():
            path.write_text("{}", encoding="utf-8")
        self._logger.info("AgentRegistry using file '%s'", path)
        return ("file", path)

    def get(self, logical_name: str) -> Optional[str]:
        kind, target = self._backend
        if kind == "cosmos":
            cont = target
            try:
                doc = cont.read_item(item=logical_name, partition_key=logical_name)
                return doc.get("agentId")
            except Exception:
                return None
        # file backend
        path: Path = target
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            value = data.get(logical_name)
            if isinstance(value, dict):
                return value.get("agentId")
            return value
        except Exception:
            return None

    def set(self, logical_name: str, agent_id: str) -> None:
        kind, target = self._backend
        if kind == "cosmos":
            cont = target
            # Merge if doc exists
            try:
                doc = cont.read_item(item=logical_name, partition_key=logical_name)
            except Exception:
                doc = {"id": logical_name, "logicalName": logical_name}
            doc["agentId"] = agent_id
            doc.setdefault("kind", "AgentConfig")
            cont.upsert_item(doc)
            return
        # file backend
        path: Path = target
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        value = data.get(logical_name)
        if isinstance(value, dict):
            value["agentId"] = agent_id
            data[logical_name] = value
        else:
            data[logical_name] = {"agentId": agent_id, "kind": "AgentConfig"}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Extended config support
    def get_config(self, logical_name: str) -> Optional[Dict[str, Any]]:
        kind, target = self._backend
        if kind == "cosmos":
            cont = target
            try:
                doc = cont.read_item(item=logical_name, partition_key=logical_name)
                return dict(doc)
            except Exception:
                return None
        # file backend
        path: Path = target
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            value = data.get(logical_name)
            if isinstance(value, dict):
                return value
            if value is None:
                return None
            # Back-compat: plain agentId string only
            return {"agentId": value, "kind": "AgentConfig"}
        except Exception:
            return None

    def upsert_config(self, logical_name: str, config: Dict[str, Any]) -> None:
        kind, target = self._backend
        if kind == "cosmos":
            cont = target
            doc = dict(config)
            doc.setdefault("id", logical_name)
            doc.setdefault("logicalName", logical_name)
            doc.setdefault("kind", "AgentConfig")
            cont.upsert_item(doc)
            return
        # file backend
        path: Path = target
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        doc = dict(config)
        doc.setdefault("kind", "AgentConfig")
        data[logical_name] = doc
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
