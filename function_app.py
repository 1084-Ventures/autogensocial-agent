
import azure.functions as func
from src.function_blueprints.orchestrate_content_blueprint import bp as orchestrate_bp
from src.function_blueprints.compose_image_blueprint import bp as compose_bp
from src.function_blueprints.process_copywriter_task import bp as copywriter_task_bp
from src.function_blueprints.process_image_task import bp as image_task_bp
from src.function_blueprints.process_publish_task import bp as publish_task_bp
from src.function_blueprints.check_task_status import bp as check_status_bp

app = func.FunctionApp()

# Register HTTP-triggered blueprints
app.register_functions(orchestrate_bp)
app.register_functions(compose_bp)

# Register queue-triggered blueprints
app.register_functions(copywriter_task_bp)
app.register_functions(image_task_bp)
app.register_functions(publish_task_bp)
app.register_functions(check_status_bp)
