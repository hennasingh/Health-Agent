import os
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StdioServerParameters,
)

server_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "mcp_server",
    "mcp_health_server.py",
)

health_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[server_path],
        )
    )
)

calorie_agent = Agent(
    name="calorie_agent",
    model="gemini-2.5-flash",
    instruction="""
You are a nutrition expert.

When the user asks about calories, food energy, or nutrition:
- ALWAYS use the MCP tool `get_calories`
- DO NOT guess calories yourself
- Return the tool result in a short friendly sentence.
- ONLY focus on nutrition. If the user also asked for recipes or other things, ignore those parts as the orchestrator will handle them.
""",
    tools=[health_tools],
)