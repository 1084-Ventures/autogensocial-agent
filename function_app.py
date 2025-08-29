import azure.durable_functions as df
from src.http.copywriter_workflow import bp as copywriter_bp

# Use DFApp as the root app so Durable triggers/activities are correctly registered
app = df.DFApp()
app.register_functions(copywriter_bp)
