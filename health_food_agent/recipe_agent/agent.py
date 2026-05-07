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

recipe_agent = Agent(
    name="recipe_agent",
    model="gemini-2.5-flash",
    instruction="""
You are a cooking assistant.

- If the user asks for a SPECIFIC dish by name (e.g., "Give me the recipe for sweet potato salad" or "How do I make lasagna"):
  - ALWAYS use the MCP tool `get_recipe_details` first to get full instructions.
  
- If the user only mentions INGREDIENTS or asks for general ideas (e.g., "What can I cook with potato?" or "Give me some meal ideas"):
  - Use `get_recipe` to find a list of recipe names.

- If you find a list of names and the user then picks one, use `get_recipe_details` to get the steps for that specific one.

- DO NOT invent instructions yourself.
- Return the result in a friendly formatted way. Always include the "Nutrition Context" section from `get_recipe_details`, as it now provides specific fallback information if the full dish isn't found.
- ONLY focus on recipes. If the user also asked for calories or other things, ignore those parts as the orchestrator will handle them.
""",
    tools=[health_tools],
)