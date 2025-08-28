import os
from typing import Dict, Optional, Any, List

try:
    from azure.cosmos import CosmosClient  # type: ignore
except Exception:  # pragma: no cover
    CosmosClient = None  # type: ignore

from .state_common import utc_now
from src.shared.logging_utils import info as log_info


class CosmosRunStateStore:
    _client: Any = None
    _container: Any = None
    _pk_path: Optional[str] = None

    @classmethod
    def _ensure_container(cls):
        if cls._container is not None:
            return cls._container

        conn = os.getenv("COSMOS_DB_CONNECTION_STRING")
        db_name = os.getenv("COSMOS_DB_NAME")
        container_name = os.getenv("COSMOS_DB_CONTAINER_AGENT_RUNS")
        if not conn or not db_name or not container_name:
            raise RuntimeError("Cosmos configuration is missing")
        if CosmosClient is None:
            raise RuntimeError("azure-cosmos package not available")

        client = CosmosClient.from_connection_string(conn)
        db = client.get_database_client(db_name)
        container = db.get_container_client(container_name)
        try:
            props = container.read()
            pk = props.get("partitionKey") or {}
            paths = pk.get("paths") or pk.get("Paths") or []
            cls._pk_path = paths[0] if isinstance(paths, list) and paths else None
        except Exception:
            cls._pk_path = None
        cls._client = client
        cls._container = container
        log_info(None, "cosmos:agent_runs:init", container=container_name, pkPath=str(cls._pk_path))
        return container

    @classmethod
    def set_status(
        cls,
        run_trace_id: str,
        phase: str,
        status: str,
        summary: Optional[Dict] = None,
        brand_id: Optional[str] = None,
        post_plan_id: Optional[str] = None,
    ) -> None:
        container = cls._ensure_container()
        doc_id = run_trace_id
        now = utc_now()
        body = {
            "id": doc_id,
            "runTraceId": run_trace_id,
            "partitionKey": run_trace_id,
            "currentPhase": phase,
            "status": status,
            "isComplete": phase == "publish" and status == "completed",
            "lastUpdateUtc": now,
            "summary": summary,
        }
        if brand_id is not None:
            body["brandId"] = brand_id
        if post_plan_id is not None:
            body["postPlanId"] = post_plan_id

        pk_path = (cls._pk_path or "").lower()
        if pk_path in ("/runtraceid", "/partitionkey", "/id"):
            pk_value = run_trace_id
        elif pk_path == "/brandid":
            pk_value = brand_id or run_trace_id
        elif pk_path == "/postplanid":
            pk_value = post_plan_id or run_trace_id
        else:
            pk_value = run_trace_id
        try:
            container.upsert_item(body)
            log_info(
                run_trace_id,
                "cosmos:agent_runs:upsert_status",
                phase=phase,
                status=status,
            )
        except Exception as exc:
            print(f"[RunStateStore] Cosmos upsert failed for {run_trace_id}: {exc}")

    @classmethod
    def get_status(cls, run_trace_id: str) -> Optional[Dict]:
        container = cls._ensure_container()
        try:
            item = container.read_item(item=run_trace_id, partition_key=run_trace_id)
            log_info(run_trace_id, "cosmos:agent_runs:read_status", method="read_item")
        except Exception:
            try:
                query = (
                    "SELECT TOP 1 c.id, c.runTraceId, c.currentPhase, c.status, c.isComplete, c.lastUpdateUtc, c.summary "
                    "FROM c WHERE c.id = @id OR c.runTraceId = @id"
                )
                items = list(
                    container.query_items(
                        query=query,
                        parameters=[{"name": "@id", "value": run_trace_id}],
                        enable_cross_partition_query=True,
                    )
                )
                item = items[0] if items else None
                if item:
                    log_info(run_trace_id, "cosmos:agent_runs:read_status", method="query")
            except Exception as exc:
                print(f"[RunStateStore] Cosmos query failed for {run_trace_id}: {exc}")
                item = None

        if not item:
            return None
        return {
            "runTraceId": item.get("runTraceId", run_trace_id),
            "currentPhase": item.get("currentPhase"),
            "status": item.get("status"),
            "isComplete": item.get("isComplete"),
            "lastUpdateUtc": item.get("lastUpdateUtc"),
            "summary": item.get("summary"),
            "brandId": item.get("brandId"),
            "postPlanId": item.get("postPlanId"),
            "events": item.get("events"),
        }

    @classmethod
    def add_event(
        cls,
        run_trace_id: str,
        *,
        phase: str,
        action: str,
        message: Optional[str] = None,
        status: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        container = cls._ensure_container()
        item = None
        try:
            item = container.read_item(item=run_trace_id, partition_key=run_trace_id)
        except Exception:
            try:
                query = "SELECT TOP 1 c FROM c WHERE c.id = @id OR c.runTraceId = @id"
                items = list(
                    container.query_items(
                        query=query,
                        parameters=[{"name": "@id", "value": run_trace_id}],
                        enable_cross_partition_query=True,
                    )
                )
                item = items[0]["c"] if items and isinstance(items[0], dict) and "c" in items[0] else (
                    items[0] if items else None
                )
            except Exception as exc:
                print(f"[RunStateStore] Cosmos read for event failed {run_trace_id}: {exc}")
                item = None
        if not item:
            item = {
                "id": run_trace_id,
                "runTraceId": run_trace_id,
                "partitionKey": run_trace_id,
            }
        events: List[Dict[str, Any]] = item.get("events") or []
        ev: Dict[str, Any] = {"ts": utc_now(), "phase": phase, "action": action}
        if message:
            ev["message"] = message
        if status:
            ev["status"] = status
        if data is not None:
            ev["data"] = data
        events.append(ev)
        item["events"] = events
        item["lastUpdateUtc"] = utc_now()
        try:
            container.upsert_item(item)
            log_info(run_trace_id, "cosmos:agent_runs:upsert_event", phase=phase, action=action)
        except Exception as exc:
            print(f"[RunStateStore] Cosmos upsert event failed {run_trace_id}: {exc}")
