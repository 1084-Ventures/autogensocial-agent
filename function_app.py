
import azure.functions as func
from src.function_blueprints.orchestrate_content_blueprint import bp as orchestrate_bp
from src.function_blueprints.check_task_status import bp as check_status_bp
from src.function_blueprints.q_content_generate import bp as content_gen_bp
from src.function_blueprints.q_media_generate import bp as media_gen_bp
from src.function_blueprints.q_publish_post import bp as publish_bp

app = func.FunctionApp()

# Register HTTP-triggered blueprints
app.register_functions(orchestrate_bp)
app.register_functions(check_status_bp)

# Register queue handlers
app.register_functions(content_gen_bp)
app.register_functions(media_gen_bp)
app.register_functions(publish_bp)
