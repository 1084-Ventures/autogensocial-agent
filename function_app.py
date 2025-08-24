
import azure.functions as func
from src.function_blueprints.orchestrate_content_blueprint import bp as orchestrate_bp
from src.function_blueprints.check_task_status import bp as check_status_bp
from src.function_blueprints.queue_handlers import bp as queue_handlers_bp

app = func.FunctionApp()

# Register HTTP-triggered blueprints
app.register_functions(orchestrate_bp)
app.register_functions(check_status_bp)

# Register queue handlers
app.register_functions(queue_handlers_bp)
