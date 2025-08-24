"""
Standardized logging implementation that writes to both Application Insights and Cosmos DB
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from src.shared.cosmos_client import get_cosmos_container
from src.specs.common.trace_logger_spec import TraceLogger

class AzureTraceLogger(TraceLogger):
    def __init__(self, run_trace_id: str):
        self.run_trace_id = run_trace_id
        self._container = get_cosmos_container("agentRuns")
        
    async def log_event(
        self,
        phase: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Log an event to both Application Insights and Cosmos DB
        
        Args:
            phase: The current phase/step (e.g., 'content_generation', 'media_generation')
            status: Current status ('started', 'completed', 'failed')
            details: Optional dictionary of additional details
            error: Optional error information with code and message
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Create the trace document
        trace_doc = {
            "id": f"{self.run_trace_id}-{phase}-{timestamp}",
            "runTraceId": self.run_trace_id,
            "phase": phase,
            "status": status,
            "timestamp": timestamp,
            "details": details or {},
            "error": error
        }
        
        # Log to Application Insights
        log_message = f"[{self.run_trace_id}] {phase} {status}"
        if error:
            logging.error(f"{log_message}: {error['message']}", extra={
                "custom_dimensions": {
                    "runTraceId": self.run_trace_id,
                    "phase": phase,
                    **error
                }
            })
        else:
            logging.info(log_message, extra={
                "custom_dimensions": {
                    "runTraceId": self.run_trace_id,
                    "phase": phase,
                    **(details or {})
                }
            })
            
        # Write to Cosmos DB
        await self._container.create_item(body=trace_doc)
        
    async def get_run_status(self) -> Dict[str, Any]:
        """
        Get the current status of the run by querying Cosmos DB
        
        Returns:
            Dict containing the overall run status and latest phase
        """
        query = f"SELECT * FROM c WHERE c.runTraceId = '{self.run_trace_id}' ORDER BY c.timestamp DESC"
        items = self._container.query_items(query=query, enable_cross_partition_query=True)
        
        # Get the most recent status
        try:
            latest = next(items)
            return {
                "runTraceId": self.run_trace_id,
                "currentPhase": latest["phase"],
                "currentStatus": latest["status"],
                "lastUpdated": latest["timestamp"],
                "error": latest.get("error")
            }
        except StopIteration:
            return {
                "runTraceId": self.run_trace_id,
                "currentPhase": "unknown",
                "currentStatus": "unknown",
                "lastUpdated": None,
                "error": None
            }
