import os
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient
from config import (
    AVIATION_STACK_API_KEY,
    OPENWEATHER_API_KEY,
    TAVILY_API_KEY,
)

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
        "aviationstack": {
            "transport": "stdio",
            "command": sys.executable,  # Uses the current Python environment
            "args": ["-m", "aviationstack_mcp", "mcp", "run"],
            "env": {
                "AVIATION_STACK_API_KEY": AVIATION_STACK_API_KEY
            }
        },
        "weather": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [os.path.join(BASE_DIR, "weather_mcp_server.py")], # Relative path
            "env": {
                "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY
            }
        }
    }
)

_tools_cache = None

async def get_tools():
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = await client.get_tools()
    return _tools_cache

async def call_tool(tool_name: str, args: dict = None):
    tools = await get_tools()
    tool = next((tool for tool in tools if tool.name == tool_name), None)
    if tool is None:
        raise ValueError(f"Tool '{tool_name}' not found")
    return await tool.ainvoke(args or {})

async def tavily_search(query: str):
    return await call_tool("tavily_search", {"query": query})

async def list_airports(search: str = "", limit: int = 10):
    return await call_tool("list_airports", {"search": search, "limit": limit, "offset": 0})

async def list_airlines(search: str = "", limit: int = 10):
    return await call_tool("list_airlines", {"search": search, "limit": limit, "offset": 0})

async def current_weather(city: str):
    return await call_tool("get_current_weather", {"city": city})

async def forecast(city: str):
    return await call_tool("get_forecast", {"city": city})