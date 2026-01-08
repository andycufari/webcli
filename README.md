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

**A text-mode web browser that converts websites into BBS-style menus for AI agents.**

99% fewer tokens. Zero screenshots. Full JavaScript support.

<video src="assets/webcli.mp4" controls width="700"></video>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io/)

---

## The Problem

AI agents browsing the web typically need **screenshots + vision APIs**:

| Approach | Tokens per page | Cost | Speed |
|----------|----------------|------|-------|
| Screenshots + Vision | 10,000 - 50,000+ | High | Slow |
| Raw HTML | 50,000+ | High | Fast |
| **WebCLI** | **~500** | **Minimal** | **Fast** |

That's a **99% reduction** in token usage.

## The Solution

WebCLI converts any website into simple numbered menus:

```
╔══════════════════════════════════════════════════════════╗
║ 📄 Hacker News                                           ║
╠══════════════════════════════════════════════════════════╣
║ 🔗 https://news.ycombinator.com/                         ║
╚══════════════════════════════════════════════════════════╝

📊 Found 227 interactive elements

────────────────────────────────────────────────────────────
🔗 LINKS (226 total)
────────────────────────────────────────────────────────────
  [L1  ] Hacker News
  [L2  ] new
  [L3  ] past
  [L12 ] Show HN: I built a CLI browser for AI agents
  [L13 ] github.com/user/webcli
  ...

────────────────────────────────────────────────────────────
📝 INPUT FIELDS (1)
────────────────────────────────────────────────────────────
  [I1  ] search (text)

💡 COMMANDS: click L12 | fill I1 "AI agents" | scroll down
```

- **`[L1]`, `[L2]`** = Links (clickable)
- **`[B1]`, `[B2]`** = Buttons (clickable)  
- **`[I1]`, `[I2]`** = Input fields (fillable)
- **`[S1]`, `[S2]`** = Select dropdowns

## Why This Works

The BBS/TUI paradigm from the 1990s is perfect for LLMs:

1. **Numbered menus** are unambiguous — `click L12` has exactly one meaning
2. **Text-only** means no vision API needed
3. **Structured but readable** — works for both humans and machines
4. **Action-oriented** — every element has a clear interaction

## Installation

```bash
# Clone
git clone https://github.com/andycufari/webcli.git
cd webcli

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Quick Start

### As MCP Server (Claude Desktop)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Then ask Claude:
> "Go to news.ycombinator.com and click on the top story"

### As CLI

```bash
python webcli.py
```

```
🖥️  CLI WEB BROWSER - BBS EDITION

🌐 > goto news.ycombinator.com
🌐 > click L12
🌐 > fill I1 "machine learning"
🌐 > scroll down
🌐 > back
🌐 > quit
```

### As Python Library

```python
from webcli import CLIBrowser
import asyncio

async def main():
    browser = CLIBrowser(headless=True, stealth=True)
    await browser.start()
    
    await browser.goto("https://amazon.com")
    await browser.fill("I1", "mechanical keyboard")
    await browser.click("B1")  # Search button
    
    print(browser.render())
    await browser.close()

asyncio.run(main())
```

## MCP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `web_goto` | Navigate to URL | `web_goto("amazon.com")` |
| `web_click` | Click element by ID | `web_click("L12")` |
| `web_fill` | Fill input field | `web_fill("I1", "query")` |
| `web_scroll` | Scroll page | `web_scroll("down")` |
| `web_back` | Go back | `web_back()` |
| `web_read` | Extract page text | `web_read()` |
| `web_state` | Get JSON state | `web_state()` |
| `web_search` | Search (beta) | `web_search("query")` |

## Features

### ✅ JavaScript Support
Handles React, Vue, Angular sites via Playwright + browser-use's DOM extraction.

### ✅ Stealth Mode  
Patches browser fingerprints to reduce bot detection (enabled by default).

### ✅ Smart Label Extraction
Extracts meaningful labels from aria-labels, data attributes, class names, href paths.

### ✅ Content Extraction
`web_read` extracts main article/page content, filtering out nav, ads, footers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM / AI Agent                           │
│              (Claude, GPT, local models)                    │
└─────────────────────────────┬───────────────────────────────┘
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     mcp_server.py                           │
│                  8 tools via JSON-RPC                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    cli_browser.py                           │
│            CLIBrowser - BBS rendering + actions             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      browser-use                            │
│               DOM extraction + state management             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Playwright                             │
│                   Headless Chromium                         │
└─────────────────────────────────────────────────────────────┘
```

## Use Cases

- 🛒 **E-commerce** — Search products, compare prices, add to cart
- 📰 **Content extraction** — Navigate news sites, read articles
- 📝 **Form automation** — Fill repetitive web forms
- 🔍 **Research** — Navigate docs, extract information
- 🧪 **Testing** — Web testing without brittle CSS selectors

## From an AI Agent's Perspective

> *"I tested WebCLI as an actual user — an AI agent browsing the web. Here's my honest take."*
>
> **What I love:**
> - **I can actually read the web.** Instead of guessing pixel coordinates from screenshots, I see `[L15] AULA F99 Wireless Mechanical Keyboard... $93,457 [B2] Add to cart`. Clear, unambiguous, actionable.
> - **Context stays together.** Product name, price, rating, and "Add to cart" button appear in order. I know which button belongs to which product.
> - **Token efficient.** A full Amazon search results page costs me ~500 tokens instead of 50,000+ for a screenshot. That's 100x more browsing per dollar.
> - **Fast iteration.** Fill form, click, read result, adjust — the loop is tight and natural.
>
> **When I'd still want screenshots:**
> - Visual layouts (maps, charts, design review)
> - CAPTCHAs (obviously)
> - "Does this look right?" verification
>
> **Verdict:** For research, shopping, form filling, and navigation — this is how I *want* to browse. The BBS paradigm from the 90s turns out to be optimal for AI in the 2020s.
>
> — *Claude (Opus 4.5), January 2026*

## Limitations

- **Search engines** — Google, Bing, DuckDuckGo have aggressive bot detection. Direct navigation works best.
- **CAPTCHAs** — Cannot solve CAPTCHAs (by design)
- **Complex SPAs** — Some apps may need scrolling to load all content
- **File uploads** — Not yet supported

## Comparison

| Feature | WebCLI | Browser-Use | Playwright | Selenium |
|---------|--------|-------------|------------|----------|
| AI-optimized output | ✅ | Partial | ❌ | ❌ |
| Token efficient | ✅ ~500 | ~2000 | N/A | N/A |
| Human readable | ✅ | ❌ | ❌ | ❌ |
| JS support | ✅ | ✅ | ✅ | ✅ |
| MCP server | ✅ | ❌ | ❌ | ❌ |
| Stealth mode | ✅ | Cloud | Plugin | Plugin |

## Contributing

PRs welcome! Areas that need love:

- [ ] Better label extraction for edge cases
- [ ] Multi-tab support
- [ ] File upload support
- [ ] Session/cookie persistence
- [ ] More stealth techniques

## Credits

Built on:
- [browser-use](https://github.com/browser-use/browser-use) — Browser automation for AI
- [Playwright](https://playwright.dev/) — Browser automation
- [MCP](https://modelcontextprotocol.io/) — Model Context Protocol

## License

MIT © [CM64.studio](https://cm64.studio)

---

<p align="center">
  <i>Built with ❤️ in Buenos Aires by <a href="https://x.com/andycufari">Andy Cufari</a></i>
</p>