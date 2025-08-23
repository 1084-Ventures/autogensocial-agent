


import os
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import CodeInterpreterTool, FunctionTool
from src.tools.get_posts_tool import get_posts_tool
from src.specs.agents.copywriter_agent_spec import CopywriterAgentRequest, CopywriterAgentResponse
from src.specs.tools.get_posts_tool_spec import GetPostsResponse
from src.specs.documents.post_document_spec import PostContent

def copywriter_generate_content(request: CopywriterAgentRequest) -> CopywriterAgentResponse:
    """
    Generates post content for a brand and post plan, fetching previous posts for context.
    Args:
        request: CopywriterAgentRequest (Pydantic model)
    Returns:
        CopywriterAgentResponse (Pydantic model)
    """
    try:
        posts = get_posts_tool(
            brand_id=request.brand_document.id,
            post_plan_id=request.post_plan_document.id if request.post_plan_document else None,
            fields=None,
            limit=10
        )
        previous_posts = GetPostsResponse(posts=posts)
    except Exception as e:
        return CopywriterAgentResponse(
            success=False,
            message=f"Failed to fetch previous posts: {str(e)}",
            traceId=request.run_trace_id,
            post_content=None,
            metadata={}
        )

    # Generate post content (stub)
    post_content = PostContent(
        media_type="image",
        topic="Exciting Launch!",
        comment="Check out our new product, now available!",
        hashtags=["#launch", "#exciting"],
        media=[],
        call_to_action="Learn more at our website!",
        mentions=[],
        language="en",
        location=None
    )

    return CopywriterAgentResponse(
        success=True,
        message="Copy generated successfully.",
        traceId=request.run_trace_id,
        post_content=post_content,
        metadata={"source": "copywriter_agent_stub"}
    )

copywriter_function_tool = FunctionTool(functions={copywriter_generate_content})

def main():
    """
    Main entrypoint for registering and running the Copywriter Agent with Azure AI Foundry.
    """
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    model_name = os.environ.get("MODEL_DEPLOYMENT_NAME")
    if not project_endpoint or not model_name:
        raise EnvironmentError("PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME environment variables must be set.")

    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )
    code_interpreter = CodeInterpreterTool()

    with project_client:
        agent = project_client.agents.create_agent(
            model=model_name,
            name="copywriter-agent",
            instructions="You are a helpful copywriter agent. Use the copywriter tool to generate social media content, and the Code Interpreter tool for any data visualization or math tasks.",
            tools=copywriter_function_tool.definitions + code_interpreter.definitions,
        )
        print(f"Created agent, ID: {agent.id}")

        thread = project_client.agents.threads.create()
        print(f"Created thread, ID: {thread.id}")

        # Example message (in production, pass a valid CopywriterAgentRequest as content/tool input)
        message = project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content="Generate a social media post for our new product launch.",
        )
        print(f"Created message, ID: {message['id']}")

        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
            additional_instructions="Please address the user as Alex Smith. The user is a marketing manager.",
        )
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        messages = project_client.agents.messages.list(thread_id=thread.id)
        for message in messages:
            print(f"Role: {message.role}, Content: {message.content}")
            for img in getattr(message, 'image_contents', []):
                file_id = img.image_file.file_id
                file_name = f"{file_id}_image_file.png"
                project_client.agents.files.save(file_id=file_id, file_name=file_name)
                print(f"Saved image file to: {Path.cwd() / file_name}")

        project_client.agents.delete_agent(agent.id)
        print("Deleted agent")

if __name__ == "__main__":
    main()