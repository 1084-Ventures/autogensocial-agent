import azure.durable_functions as df
from src.http.autogensocial_workflow import bp as autogensocial_bp

# Use DFApp as the root app so Durable triggers/activities are correctly registered
app = df.DFApp()
app.register_functions(autogensocial_bp)
