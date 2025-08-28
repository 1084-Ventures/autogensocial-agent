"""
Azure Foundry/OpenAI function tools definitions for runtime tool-calling.

Provides:
 - function_tools: list of tool specs to pass into Chat Completions/Agents
 - call_function_tool(name, args): executes the tool and returns a JSON-serializable result

Usage (OpenAI-like tool calling):

    from openai import AzureOpenAI
    import json
    from src.tools.foundry_function_tools import function_tools, call_function_tool

    client = AzureOpenAI(...)
    messages = [
        {"role": "system", "content": "You are a helpful agent."},
        {"role": "user", "content": "Write a caption for brand X's plan Y"},
    ]
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=messages,
        tools=function_tools,
        tool_choice="auto",
    )
    for choice in response.choices:
        for tool_call in choice.message.tool_calls or []:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            tool_result = call_function_tool(name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": json.dumps(tool_result),
            })

"""

from typing import Dict, Any, List

from src.tools import get_brand_tool as _brand
from src.tools import get_post_plan_tool as _postplan


function_tools: List[Dict[str, Any]] = [
    _brand.FUNCTION_TOOL,
    _postplan.FUNCTION_TOOL,
]


def call_function_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == _brand.FUNCTION_TOOL["function"]["name"]:
        return _brand.call_function_tool(args)
    if name == _postplan.FUNCTION_TOOL["function"]["name"]:
        return _postplan.call_function_tool(args)
    return {
        "status": "failed",
        "error": {"code": "unknown_tool", "message": f"No such tool: {name}"},
    }
