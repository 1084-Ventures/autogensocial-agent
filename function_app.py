
import os
import logging
import azure.functions as func
import azure.durable_functions as df

# Use DFApp as the root app so Durable triggers/activities are correctly registered
app = df.DFApp()


def _configure_logging() -> None:
    lvl = (os.getenv("AZURE_SDK_LOG_LEVEL") or "").upper()
    if lvl:
        level = getattr(logging, lvl, logging.INFO)
        logging.getLogger("azure").setLevel(level)
        logging.getLogger("azure.cosmos").setLevel(level)
    logging.getLogger("autogensocial").setLevel(logging.INFO)


_configure_logging()

