# WebCLI 🖥️

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ██╗    ██╗███████╗██████╗  ██████╗██╗     ██╗                   ║
║   ██║    ██║██╔════╝██╔══██╗██╔════╝██║     ██║                   ║
║   ██║ █╗ ██║█████╗  ██████╔╝██║     ██║     ██║                   ║
║   ██║███╗██║██╔══╝  ██╔══██╗██║     ██║     ██║                   ║
║   ╚███╔███╔╝███████╗██████╔╝╚██████╗███████╗██║                   ║
║    ╚══╝╚══╝ ╚══════╝╚═════╝  ╚═════╝╚══════╝╚═╝                   ║
║                                                                   ║
║   Browse the web like it's 1994 — for AI agents                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

**WebCLI** is a text-mode web browser designed for AI agents.

It converts modern websites into **BBS-style, numbered text menus**, so LLMs can navigate the web using the same format they already reason in: text.

No screenshots.  
No raw HTML dumps.  
No brittle selectors.

![WebCLI Demo](assets/webcli.gif)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io/)

---

## Why This Exists

Working with browsers + LLMs today is painful.

Most agent setups:
- rely on screenshots + vision models
- or feed raw HTML full of JavaScript, hidden nodes, and noise

Both approaches are:
- expensive
- slow
- hard for models to reason about
- fragile across sites

I built WebCLI after repeatedly hitting these problems while experimenting with browser-based agents.

This project explores a different idea: **what if the browser spoke the same language as the agent?**

---

## What It Does

Turns this:
```html
<a href="/story/123" class="storylink">How I Built X</a>
<span class="score">172 points</span>
<!-- ... 10,000 more lines ... -->
```

Into this:
```
[L10] How I Built X
172 points by developer | 3 hours ago
[L15] 113 comments
```

This keeps interaction deterministic, readable, and cheap.

## Installation

```bash
git clone https://github.com/andycufari/webcli.git
cd webcli
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

### MCP Server (Claude Desktop / Claude Code)

Add to your config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "webcli": {
      "command": "/path/to/webcli/venv/bin/python",
      "args": ["/path/to/webcli/mcp_server.py"]
    }
  }
}
```

Restart Claude. Then:
> "Go to news.ycombinator.com and tell me the top stories"

### CLI

```bash
python webcli.py
```

```
🌐 > goto news.ycombinator.com
🌐 > click L12
🌐 > fill I1 "search term"
🌐 > back
🌐 > quit
```

### Python

```python
from webcli import CLIBrowser
import asyncio

async def main():
    browser = CLIBrowser(headless=True)
    await browser.start()
    await browser.goto("https://amazon.com")
    await browser.fill("I1", "mechanical keyboard")
    await browser.click("B1")
    print(browser.render())
    await browser.close()

asyncio.run(main())
```

## Tools

| Tool | What it does |
|------|--------------|
| `web_goto` | Navigate to URL |
| `web_click` | Click element (L1, B2, etc.) |
| `web_fill` | Fill input field |
| `web_scroll` | Scroll up/down |
| `web_back` | Go back |
| `web_read` | Extract page text |
| `web_state` | Raw JSON state |
| `web_search` | Search via Brave (beta) |

## Element IDs

```
[L1], [L2]...  = Links
[B1], [B2]...  = Buttons  
[I1], [I2]...  = Inputs
[S1], [S2]...  = Selects
```

## How It Works

```
LLM ──► MCP Server ──► CLIBrowser ──► browser-use ──► Playwright ──► Chromium
```

- **Playwright** runs headless Chrome
- **browser-use** extracts interactive elements from DOM
- **CLIBrowser** renders them as numbered text menus
- **MCP Server** exposes tools to Claude/other LLMs

## Limitations

- Search engines (Google, Bing) block automated browsers
- Can't solve CAPTCHAs
- Some SPAs need scrolling to load content
- No file uploads yet

## Use Cases

- E-commerce: search products, compare prices
- Research: navigate docs, extract info
- Forms: fill repetitive web forms
- Testing: web tests without brittle selectors

## Built With

- [browser-use](https://github.com/browser-use/browser-use)
- [Playwright](https://playwright.dev/)
- [MCP](https://modelcontextprotocol.io/)

## License

MIT © [Andy Cufari](https://x.com/andycufari) / [CM64.studio](https://cm64.studio)

---

<p align="center">
  Built in Buenos Aires 🇦🇷
</p>