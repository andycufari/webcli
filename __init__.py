"""
WebCLI - A text-mode web browser for AI agents

Browse the web like it's 1994. Converts websites into BBS-style menus
with numbered actions, perfect for LLM agents.

Usage:
    from webcli import CLIBrowser

    browser = CLIBrowser(headless=True)
    await browser.start()
    await browser.goto("https://example.com")
    print(browser.render())
"""

from cli_browser import CLIBrowser, PageState, PageElement

__version__ = "0.1.0"
__all__ = ["CLIBrowser", "PageState", "PageElement"]
