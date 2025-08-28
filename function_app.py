
import os
import logging
import azure.functions as func
from src.function_blueprints.http_check_task_status import bp as check_status_bp
from src.function_blueprints.durable_pipeline import bp as durable_bp

app = func.FunctionApp()


def _configure_logging() -> None:
    lvl = (os.getenv("AZURE_SDK_LOG_LEVEL") or "").upper()
    if lvl:
        level = getattr(logging, lvl, logging.INFO)
        logging.getLogger("azure").setLevel(level)
        logging.getLogger("azure.cosmos").setLevel(level)
    logging.getLogger("autogensocial").setLevel(logging.INFO)


_configure_logging()

app.register_functions(check_status_bp)
app.register_functions(durable_bp)
