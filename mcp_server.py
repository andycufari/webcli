"""
MCP Server for CLI Web Browser

Exposes the CLI browser as MCP tools for AI agents to browse the web
without screenshots - just text menus like old BBS systems.

Run: python mcp_server.py
"""
import asyncio
import json
import sys
import os
import logging
from typing import Any

# CRITICAL: MCP servers communicate via JSON on stdout
# Any other output (logs, prints) breaks the protocol
# Suppress ALL logging before importing anything else
os.environ["BROWSER_USE_LOGGING_LEVEL"] = "CRITICAL"
logging.disable(logging.CRITICAL)

# Suppress specific loggers that might still output
for logger_name in ['browser_use', 'playwright', 'asyncio', 'urllib3']:
    logging.getLogger(logger_name).disabled = True
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from webcli import CLIBrowser

# Global browser instance
browser: CLIBrowser | None = None


async def get_browser() -> CLIBrowser:
    """Get or create browser instance"""
    global browser
    if browser is None:
        browser = CLIBrowser(headless=True)
        await browser.start()
    return browser


# Create MCP server
app = Server("webcli-browser")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available browser tools"""
    return [
        Tool(
            name="web_goto",
            description="Navigate to a URL. Returns the page as a text menu with clickable element IDs (L1, L2 for links, B1, B2 for buttons, I1, I2 for inputs).",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to (e.g., 'news.ycombinator.com' or 'https://github.com')"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="web_click",
            description="Click an element by its ID. Use IDs from the page state (L1 for first link, B1 for first button, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "element_id": {
                        "type": "string",
                        "description": "Element ID to click (e.g., 'L1', 'B2', 'L15')"
                    }
                },
                "required": ["element_id"]
            }
        ),
        Tool(
            name="web_fill",
            description="Fill an input field with text. Use input IDs from the page state (I1, I2, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "element_id": {
                        "type": "string",
                        "description": "Input element ID (e.g., 'I1', 'I2')"
                    },
                    "value": {
                        "type": "string",
                        "description": "Text to fill in the input"
                    }
                },
                "required": ["element_id", "value"]
            }
        ),
        Tool(
            name="web_scroll",
            description="Scroll the page up or down to see more content",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down"],
                        "description": "Scroll direction"
                    }
                },
                "required": ["direction"]
            }
        ),
        Tool(
            name="web_back",
            description="Go back to the previous page",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="web_state",
            description="Get the current page state as JSON (useful for programmatic access)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="web_read",
            description="Extract the main text content from the current page. Useful for reading articles, documentation, or any text-heavy content. Filters out navigation, ads, and other non-content elements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum characters to return (default: 5000)",
                        "default": 5000
                    }
                }
            }
        ),
        Tool(
            name="web_search",
            description="Search the web using a bot-friendly search engine. Returns search results as clickable links. Use this instead of navigating directly to Google (which blocks bots).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "engine": {
                        "type": "string",
                        "enum": ["brave", "ddg", "searx"],
                        "description": "Search engine: 'brave' (default, best results), 'ddg' (DuckDuckGo), 'searx' (privacy-focused)",
                        "default": "brave"
                    }
                },
                "required": ["query"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    try:
        b = await get_browser()

        if name == "web_goto":
            url = arguments["url"]
            await b.goto(url)
            return [TextContent(type="text", text=b.render())]

        elif name == "web_click":
            element_id = arguments["element_id"]
            await b.click(element_id)
            return [TextContent(type="text", text=b.render())]

        elif name == "web_fill":
            element_id = arguments["element_id"]
            value = arguments["value"]
            await b.fill(element_id, value)
            return [TextContent(type="text", text=b.render())]

        elif name == "web_scroll":
            direction = arguments["direction"]
            await b.scroll(direction)
            return [TextContent(type="text", text=b.render())]

        elif name == "web_back":
            await b.back()
            return [TextContent(type="text", text=b.render())]

        elif name == "web_state":
            if b.current_state:
                return [TextContent(
                    type="text",
                    text=json.dumps(b.current_state.to_dict(), indent=2)
                )]
            else:
                return [TextContent(type="text", text="No page loaded")]

        elif name == "web_read":
            if not b.current_state:
                return [TextContent(type="text", text="No page loaded. Use web_goto first.")]
            max_length = arguments.get("max_length", 5000)
            content = await b.read_content(max_length)
            return [TextContent(type="text", text=content)]

        elif name == "web_search":
            query = arguments["query"]
            engine = arguments.get("engine", "brave")
            await b.search(query, engine)
            return [TextContent(type="text", text=b.render())]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
