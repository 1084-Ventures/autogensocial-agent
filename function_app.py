
import os
import logging
import azure.functions as func
from src.function_blueprints.http_orchestrate_content import bp as orchestrate_bp
from src.function_blueprints.http_check_task_status import bp as check_status_bp
from src.function_blueprints.q_content_generate import bp as content_gen_bp
from src.function_blueprints.q_media_generate import bp as media_gen_bp
from src.function_blueprints.q_publish_post import bp as publish_bp

app = func.FunctionApp()


def _configure_logging() -> None:
    lvl = (os.getenv("AZURE_SDK_LOG_LEVEL") or "").upper()
    if lvl:
        level = getattr(logging, lvl, logging.INFO)
        logging.getLogger("azure").setLevel(level)
        logging.getLogger("azure.cosmos").setLevel(level)
    logging.getLogger("autogensocial").setLevel(logging.INFO)


_configure_logging()

app.register_functions(orchestrate_bp)
app.register_functions(check_status_bp)
app.register_functions(content_gen_bp)
app.register_functions(media_gen_bp)
app.register_functions(publish_bp)
