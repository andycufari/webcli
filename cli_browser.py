"""
CLI Web Browser - BBS Style
Converts websites to text-based navigable menus

This is a proof-of-concept for making websites accessible to AI agents
without using screenshots/vision - just text menus like old BBS systems.

Run: python cli_browser.py

Commands:
  goto <url>           - Navigate to URL
  click <id>           - Click element (L1, B1, etc.)
  fill <id> <text>     - Fill input field
  select <id> <value>  - Select dropdown option
  scroll <up|down>     - Scroll page
  raw                  - Show raw selector map
  json                 - Export current state as JSON
  refresh              - Re-render current page
  quit                 - Exit browser
"""
import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class PageElement:
    """Represents an interactive element"""
    id: str           # Our simple ID (L1, B1, I1, etc.)
    type: str         # link, button, input, select
    text: str         # Visible text
    selector: str     # CSS selector for action
    href: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class PageState:
    """Simplified page representation - the BBS view"""
    url: str
    title: str
    links: List[PageElement] = field(default_factory=list)
    buttons: List[PageElement] = field(default_factory=list)
    inputs: List[PageElement] = field(default_factory=list)
    selects: List[PageElement] = field(default_factory=list)
    text_content: str = ""
    raw_selector_map: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export"""
        return {
            "url": self.url,
            "title": self.title,
            "links": [{"id": l.id, "text": l.text, "href": l.href} for l in self.links],
            "buttons": [{"id": b.id, "text": b.text} for b in self.buttons],
            "inputs": [{"id": i.id, "text": i.text, "type": i.attributes.get("type")} for i in self.inputs],
            "selects": [{"id": s.id, "text": s.text} for s in self.selects],
            "element_count": len(self.links) + len(self.buttons) + len(self.inputs) + len(self.selects),
        }


class CLIBrowser:
    """Text-based web browser for AI agents.

    Supports multiple browser modes via environment variables:
        - chromium: Default isolated browser (no logins)
        - chrome: Use your Chrome profile with logins/cookies
        - cdp: Connect to already-running Chrome instance

    Environment Variables:
        WEBCLI_BROWSER_MODE: chromium|chrome|cdp (default: chromium)
        WEBCLI_HEADLESS: true|false (default: true)
        WEBCLI_STEALTH: true|false (default: true)
        WEBCLI_CHROME_USER_DATA: Path to Chrome profile directory
        WEBCLI_CHROME_PROFILE: Profile name (default: Default)
        WEBCLI_CDP_ENDPOINT: CDP URL (default: http://localhost:9222)
    """

    def __init__(self, headless: bool = None, stealth: bool = None):
        self.session = None
        self.current_state: Optional[PageState] = None
        self.history: List[str] = []

        # Load config from .env and environment
        self._load_env_config()

        # Override with explicit arguments if provided
        if headless is not None:
            self.headless = headless
        if stealth is not None:
            self.stealth = stealth

    def _load_env_config(self):
        """Load configuration from .env file and environment variables."""
        import os

        # Load .env file if exists
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = value

        # Read configuration
        self.browser_mode = os.getenv("WEBCLI_BROWSER_MODE", "chromium").lower()
        self.headless = os.getenv("WEBCLI_HEADLESS", "true").lower() not in ("false", "0", "no")
        self.stealth = os.getenv("WEBCLI_STEALTH", "true").lower() not in ("false", "0", "no")

        # Chrome profile settings
        self.chrome_user_data = os.getenv("WEBCLI_CHROME_USER_DATA")
        self.chrome_profile = os.getenv("WEBCLI_CHROME_PROFILE", "Default")

        # CDP settings
        self.cdp_endpoint = os.getenv("WEBCLI_CDP_ENDPOINT", "http://localhost:9222")

        # Auto-detect Chrome user data path on macOS if not set
        if self.browser_mode == "chrome" and not self.chrome_user_data:
            default_path = Path.home() / "Library/Application Support/Google/Chrome"
            if default_path.exists():
                self.chrome_user_data = str(default_path)

    async def start(self):
        """Initialize browser based on configuration."""
        from browser_use import BrowserSession

        session_kwargs = {"headless": self.headless}

        if self.browser_mode == "chrome":
            # Use Chrome with user profile (keeps logins!)
            session_kwargs["channel"] = "chrome"
            session_kwargs["executable_path"] = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

            if self.chrome_user_data:
                session_kwargs["user_data_dir"] = self.chrome_user_data
                session_kwargs["profile_directory"] = self.chrome_profile

        elif self.browser_mode == "cdp":
            # Connect to existing browser via CDP
            session_kwargs["cdp_url"] = self.cdp_endpoint

        # else: default chromium, no extra config needed

        if self.stealth:
            session_kwargs["disable_security"] = True

        self.session = BrowserSession(**session_kwargs)
        await self.session.start()

        # Apply stealth patches
        if self.stealth:
            await self._apply_stealth_patches()

    async def _apply_stealth_patches(self):
        """Apply JavaScript patches to avoid bot detection."""
        page = await self.session.get_current_page()

        # Stealth JavaScript to patch common detection vectors
        stealth_js = """
            () => {
                // Patch navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Patch chrome runtime
                window.chrome = {
                    runtime: {}
                };

                // Patch permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Patch plugins to look more realistic
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Patch languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            }
        """
        try:
            await page.evaluate(stealth_js)
        except Exception:
            pass  # Stealth patches are best-effort

    async def goto(self, url: str) -> PageState:
        """Navigate to URL and return page state"""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        await self.session.navigate_to(url)

        # Re-apply stealth patches after navigation
        if self.stealth:
            await self._apply_stealth_patches()

        self.history.append(url)
        self.current_state = await self._extract_page_state()
        return self.current_state

    async def search(self, query: str, engine: str = "brave") -> PageState:
        """Search the web using a bot-friendly search engine.

        Args:
            query: Search query string
            engine: Search engine to use. Options:
                   - "brave" (default): Brave Search - bot-friendly, good results
                   - "ddg": DuckDuckGo HTML version
                   - "searx": SearXNG public instance

        Returns:
            PageState with search results
        """
        from urllib.parse import quote_plus

        encoded_query = quote_plus(query)

        engines = {
            "brave": f"https://search.brave.com/search?q={encoded_query}",
            "ddg": f"https://html.duckduckgo.com/html/?q={encoded_query}",
            "searx": f"https://searx.be/search?q={encoded_query}&format=html",
        }

        url = engines.get(engine, engines["brave"])
        return await self.goto(url)

    def _extract_label_from_attrs(self, attrs_str: str, fallback: str = "") -> str:
        """Extract a human-readable label from element attributes.

        Aggressively tries multiple strategies to find meaningful text.
        """
        import re

        # Priority order for label extraction (most semantic first)
        label_attrs = [
            'aria-label',
            'aria-description',
            'title',
            'alt',
            'data-tooltip',
            'data-title',
            'data-label',
            'data-text',
            'data-content',
            'placeholder',
            'value',
            'name',
        ]

        for attr in label_attrs:
            # Match quoted values (handles spaces in values)
            match = re.search(rf'{attr}="([^"]+)"', attrs_str)
            if not match:
                match = re.search(rf"{attr}='([^']+)'", attrs_str)
            if not match:
                # Unquoted single-word values
                match = re.search(rf'{attr}=([^\s>"\']+)', attrs_str)

            if match:
                val = match.group(1).strip()
                # Filter out non-descriptive values
                skip_values = {'submit', 'button', 'text', 'input', 'true', 'false',
                              '1', '0', 'on', 'off', 'yes', 'no', 'undefined', 'null'}
                if val and val.lower() not in skip_values and len(val) > 1:
                    # Clean up common patterns
                    label = val.replace('_', ' ').replace('-', ' ')
                    # Remove common prefixes/suffixes
                    label = re.sub(r'^(btn|icon|img|link|nav)[_-]?', '', label, flags=re.I)
                    label = re.sub(r'[_-]?(btn|icon|img|link)$', '', label, flags=re.I)
                    # Capitalize appropriately
                    if label and label.islower():
                        label = label.title()
                    if label:
                        return label[:40]

        # Try id attribute (lower priority, often technical)
        id_match = re.search(r'id="([^"]+)"', attrs_str) or re.search(r"id='([^']+)'", attrs_str)
        if id_match:
            val = id_match.group(1)
            # Only use if it looks semantic (not random IDs like "a1b2c3")
            if val and not re.match(r'^[a-z0-9]{6,}$', val) and not val.startswith(':'):
                label = val.replace('_', ' ').replace('-', ' ')
                label = re.sub(r'^(btn|icon|img|link|nav)[_-]?', '', label, flags=re.I)
                if label and len(label) > 2:
                    return label.title()[:40]

        # Try to extract hints from class names
        class_match = re.search(r'class="([^"]+)"', attrs_str) or re.search(r"class='([^']+)'", attrs_str)
        if class_match:
            classes = class_match.group(1).lower()
            # Look for semantic class names
            semantic_hints = [
                'search', 'login', 'logout', 'signin', 'signout', 'signup', 'register',
                'submit', 'send', 'post', 'share', 'like', 'follow', 'subscribe',
                'menu', 'nav', 'navigation', 'sidebar', 'header', 'footer',
                'close', 'open', 'toggle', 'expand', 'collapse', 'show', 'hide',
                'next', 'prev', 'previous', 'forward', 'backward', 'back', 'return',
                'home', 'settings', 'profile', 'account', 'user', 'avatar',
                'cart', 'checkout', 'buy', 'add', 'remove', 'delete', 'edit',
                'download', 'upload', 'save', 'cancel', 'confirm', 'ok', 'apply',
                'help', 'info', 'about', 'contact', 'support', 'faq',
                'play', 'pause', 'stop', 'mute', 'unmute', 'volume',
                'copy', 'paste', 'cut', 'undo', 'redo', 'refresh', 'reload',
                'star', 'favorite', 'bookmark', 'pin', 'flag', 'report',
                'comment', 'reply', 'quote', 'retweet', 'repost',
                'arrow', 'chevron', 'caret', 'dropdown', 'popover', 'modal',
                'github', 'twitter', 'facebook', 'linkedin', 'youtube', 'instagram',
            ]
            for hint in semantic_hints:
                if hint in classes:
                    # Capitalize nicely
                    return hint.replace('-', ' ').replace('_', ' ').title()

        # Try href for links - extract domain or path hint
        href_match = re.search(r'href="([^"]+)"', attrs_str) or re.search(r"href='([^']+)'", attrs_str)
        if href_match:
            href = href_match.group(1)
            if href and href not in ('#', '/', 'javascript:void(0)', 'javascript:;'):
                # Extract meaningful part from URL
                if href.startswith('mailto:'):
                    return 'Email'
                if href.startswith('tel:'):
                    return 'Phone'
                if '/search' in href:
                    return 'Search'
                if '/login' in href or '/signin' in href:
                    return 'Login'
                if '/signup' in href or '/register' in href:
                    return 'Sign Up'
                # Try to get last path segment
                path_match = re.search(r'/([^/?#]+)/?(?:\?|#|$)', href)
                if path_match:
                    segment = path_match.group(1)
                    if segment and len(segment) > 2 and not segment.isdigit():
                        label = segment.replace('-', ' ').replace('_', ' ')
                        if label.islower():
                            label = label.title()
                        return label[:30]

        return fallback

    async def _extract_page_state(self) -> PageState:
        """Convert DOM to simplified PageState"""
        import re

        # Get page metadata
        title = await self.session.get_current_page_title()
        url = await self.session.get_current_page_url()

        # Get state as text - this is what browser-use provides for LLMs
        state_text = await self.session.get_state_as_text()

        # Initialize state
        state = PageState(
            url=url,
            title=title,
            text_content=state_text,
            raw_selector_map={}
        )

        # Parse the state text to extract elements
        # Format: [ID]<tag /> or [ID]<tag id=xxx /> followed by optional text
        # Example: [77]<a />\n\tBose is open-sourcing...

        link_count = button_count = input_count = select_count = 0

        # Pattern to match element markers like [32]<a /> or [77]<a id=up_123 />
        pattern = r'\[(\d+)\]<(\w+)([^>]*)/?>'

        lines = state_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            match = re.search(pattern, line)
            if match:
                mmid = match.group(1)
                tag = match.group(2).lower()
                attrs_str = match.group(3).strip()

                # Get text from next indented line(s)
                text = ""
                j = i + 1
                while j < len(lines) and lines[j].startswith('\t'):
                    text += lines[j].strip() + " "
                    j += 1

                # Clean up text: remove nested element markers like [123]<tag ... />
                text = re.sub(r'\s*\*?\[\d+\]<[^>]+>\s*', '|', text)  # Replace with delimiter
                text = re.sub(r'<!--[^>]*-->', '', text)  # Remove HTML comments
                # Take only first segment (before first delimiter)
                text = text.split('|')[0].strip()
                text = re.sub(r'\s+', ' ', text).strip()[:50]

                # Store in raw map
                state.raw_selector_map[mmid] = tag

                # Categorize by element type
                if tag == 'a':
                    link_count += 1
                    # Use visible text, or extract from attributes if empty
                    link_text = text[:50] if text else self._extract_label_from_attrs(attrs_str, "(link)")
                    state.links.append(PageElement(
                        id=f"L{link_count}",
                        type="link",
                        text=link_text,
                        selector=mmid,
                        attributes={"raw": attrs_str}
                    ))

                elif tag == 'button':
                    button_count += 1
                    # Use visible text, or extract from attributes if empty
                    btn_text = text[:30] if text else self._extract_label_from_attrs(attrs_str, "(button)")
                    state.buttons.append(PageElement(
                        id=f"B{button_count}",
                        type="button",
                        text=btn_text,
                        selector=mmid,
                        attributes={"raw": attrs_str}
                    ))

                elif tag in ('input', 'textarea'):
                    # Extract input type first
                    type_match = re.search(r'type=([^\s>]+)', attrs_str)
                    input_type = type_match.group(1).strip('"\'') if type_match else 'text'

                    # Submit/button inputs should be treated as buttons
                    if input_type in ('submit', 'button'):
                        button_count += 1
                        # Get value for button text
                        val_match = re.search(r'value=([^\s>]+)', attrs_str)
                        btn_text = val_match.group(1).strip('"\'') if val_match else 'Submit'
                        state.buttons.append(PageElement(
                            id=f"B{button_count}",
                            type="button",
                            text=btn_text,
                            selector=mmid,
                            attributes={"raw": attrs_str}
                        ))
                        i += 1
                        continue

                    # Skip hidden inputs
                    if input_type == 'hidden':
                        i += 1
                        continue

                    input_count += 1
                    # Try to get a meaningful label from attributes
                    label = text
                    if not label:
                        # Parse attrs_str for placeholder, name, id, aria-label
                        for attr in ['placeholder', 'name', 'aria-label', 'id']:
                            attr_match = re.search(rf'{attr}=([^\s>]+)', attrs_str)
                            if attr_match:
                                val = attr_match.group(1).strip('"\'')
                                if val:
                                    # Make common abbreviations more readable
                                    label = val.replace('_', ' ').replace('-', ' ')
                                    if label.lower() == 'pw':
                                        label = 'password'
                                    elif label.lower() == 'acct':
                                        label = 'username'
                                    break

                    state.inputs.append(PageElement(
                        id=f"I{input_count}",
                        type="input",
                        text=label or f"input-{input_count}",
                        selector=mmid,
                        attributes={"raw": attrs_str, "type": input_type}
                    ))

                elif tag == 'select':
                    select_count += 1
                    state.selects.append(PageElement(
                        id=f"S{select_count}",
                        type="select",
                        text=text or f"select-{select_count}",
                        selector=mmid,
                        attributes={"raw": attrs_str}
                    ))

            i += 1

        return state

    async def click(self, element_id: str) -> PageState:
        """Click an element by our ID (L1, B1, etc.)"""
        element = self._find_element(element_id.upper())
        if not element:
            raise ValueError(f"Element '{element_id}' not found")

        # Get DOM node for backend_node_id
        mmid = int(element.selector)
        dom_node = await self.session.get_element_by_index(mmid)

        if dom_node and dom_node.backend_node_id:
            # Get Element object via page.get_element(backend_node_id)
            page = await self.session.get_current_page()
            elem = await page.get_element(dom_node.backend_node_id)
            await elem.click()
        else:
            raise ValueError(f"Could not find clickable element for {element_id}")

        # Wait a bit for navigation
        await asyncio.sleep(1)

        self.current_state = await self._extract_page_state()
        return self.current_state

    async def fill(self, element_id: str, value: str) -> PageState:
        """Fill an input field"""
        element = self._find_element(element_id.upper())
        if not element:
            raise ValueError(f"Element '{element_id}' not found")

        mmid = int(element.selector)
        dom_node = await self.session.get_element_by_index(mmid)

        if dom_node and dom_node.backend_node_id:
            page = await self.session.get_current_page()
            elem = await page.get_element(dom_node.backend_node_id)
            await elem.fill(value)
        else:
            raise ValueError(f"Could not find input element for {element_id}")

        self.current_state = await self._extract_page_state()
        return self.current_state

    async def select_option(self, element_id: str, value: str) -> PageState:
        """Select an option from dropdown"""
        element = self._find_element(element_id.upper())
        if not element:
            raise ValueError(f"Element '{element_id}' not found")

        mmid = int(element.selector)
        dom_node = await self.session.get_element_by_index(mmid)

        if dom_node and dom_node.backend_node_id:
            page = await self.session.get_current_page()
            elem = await page.get_element(dom_node.backend_node_id)
            await elem.select_option(value)
        else:
            raise ValueError(f"Could not find select element for {element_id}")

        self.current_state = await self._extract_page_state()
        return self.current_state

    async def scroll(self, direction: str = "down") -> PageState:
        """Scroll the page"""
        page = await self.session.get_current_page()
        amount = 500 if direction == "down" else -500
        # browser-use requires arrow function format for evaluate
        await page.evaluate(f"() => window.scrollBy(0, {amount})")
        await asyncio.sleep(0.5)  # Wait for lazy content
        self.current_state = await self._extract_page_state()
        return self.current_state

    async def back(self) -> PageState:
        """Go back in history"""
        page = await self.session.get_current_page()
        await page.go_back()
        await asyncio.sleep(1)
        self.current_state = await self._extract_page_state()
        return self.current_state

    async def read_content(self, max_length: int = 5000) -> str:
        """Extract main text content from the page.

        Attempts to find the main content area and extract readable text,
        filtering out navigation, ads, and other non-content elements.
        """
        page = await self.session.get_current_page()

        # JavaScript to extract main content
        content = await page.evaluate("""
            () => {
                // Try to find main content area
                const selectors = [
                    'main',
                    'article',
                    '[role="main"]',
                    '.content',
                    '.post-content',
                    '.article-content',
                    '.entry-content',
                    '#content',
                    '#main'
                ];

                let mainEl = null;
                for (const sel of selectors) {
                    mainEl = document.querySelector(sel);
                    if (mainEl) break;
                }

                // Fallback to body
                if (!mainEl) mainEl = document.body;

                // Clone to avoid modifying the page
                const clone = mainEl.cloneNode(true);

                // Remove unwanted elements
                const removeSelectors = [
                    'script', 'style', 'nav', 'header', 'footer',
                    'aside', '.sidebar', '.ad', '.advertisement',
                    '.comments', '.social-share', '[role="navigation"]',
                    '.menu', '.nav', 'iframe', 'noscript'
                ];

                for (const sel of removeSelectors) {
                    clone.querySelectorAll(sel).forEach(el => el.remove());
                }

                // Get text content
                let text = clone.innerText || clone.textContent || '';

                // Clean up whitespace
                text = text.replace(/\\n{3,}/g, '\\n\\n');
                text = text.replace(/[ \\t]+/g, ' ');
                text = text.trim();

                return text;
            }
        """)

        # Truncate if needed
        if len(content) > max_length:
            content = content[:max_length] + f"\n\n... [truncated, {len(content) - max_length} more chars]"

        return content
    
    def _find_element(self, element_id: str) -> Optional[PageElement]:
        """Find element by our ID"""
        if not self.current_state:
            return None
        
        all_elements = (
            self.current_state.links + 
            self.current_state.buttons + 
            self.current_state.inputs + 
            self.current_state.selects
        )
        for el in all_elements:
            if el.id == element_id:
                return el
        return None
    
    def render(self, max_links: int = 25, max_buttons: int = 15) -> str:
        """Render current state as BBS-style text"""
        if not self.current_state:
            return "📭 No page loaded. Use 'goto <url>' to navigate."
        
        state = self.current_state
        lines = []
        
        # Header
        lines.append("")
        lines.append("╔" + "═" * 58 + "╗")
        title_display = state.title[:54] if state.title else "(No Title)"
        lines.append(f"║ 📄 {title_display:<54} ║")
        lines.append("╠" + "═" * 58 + "╣")
        url_display = state.url[:54] if len(state.url) <= 54 else state.url[:51] + "..."
        lines.append(f"║ 🔗 {url_display:<54} ║")
        lines.append("╚" + "═" * 58 + "╝")
        
        # Stats
        total = len(state.links) + len(state.buttons) + len(state.inputs) + len(state.selects)
        lines.append(f"\n📊 Found {total} interactive elements")
        
        # Links
        if state.links:
            lines.append(f"\n{'─' * 60}")
            lines.append(f"🔗 LINKS ({len(state.links)} total, showing first {min(len(state.links), max_links)})")
            lines.append(f"{'─' * 60}")
            for link in state.links[:max_links]:
                text = link.text[:45] if link.text else "(no text)"
                lines.append(f"  [{link.id:4}] {text}")
            if len(state.links) > max_links:
                lines.append(f"  ... and {len(state.links) - max_links} more links")
        
        # Buttons
        if state.buttons:
            lines.append(f"\n{'─' * 60}")
            lines.append(f"🔘 BUTTONS ({len(state.buttons)})")
            lines.append(f"{'─' * 60}")
            for btn in state.buttons[:max_buttons]:
                lines.append(f"  [{btn.id:4}] {btn.text}")
        
        # Inputs
        if state.inputs:
            lines.append(f"\n{'─' * 60}")
            lines.append(f"📝 INPUT FIELDS ({len(state.inputs)})")
            lines.append(f"{'─' * 60}")
            for inp in state.inputs:
                inp_type = inp.attributes.get('type', 'text')
                lines.append(f"  [{inp.id:4}] {inp.text} ({inp_type})")
        
        # Selects
        if state.selects:
            lines.append(f"\n{'─' * 60}")
            lines.append(f"📋 DROPDOWNS ({len(state.selects)})")
            lines.append(f"{'─' * 60}")
            for sel in state.selects:
                lines.append(f"  [{sel.id:4}] {sel.text}")
        
        # Help
        lines.append(f"\n{'━' * 60}")
        lines.append("💡 COMMANDS:")
        lines.append("   goto <url>  │  click <id>  │  fill <id> <text>")
        lines.append("   scroll up/down  │  back  │  json  │  quit")
        lines.append("━" * 60)
        
        return "\n".join(lines)
    
    def render_compact(self) -> str:
        """Render minimal version for LLM context"""
        if not self.current_state:
            return "No page loaded"
        
        state = self.current_state
        lines = [
            f"# {state.title}",
            f"URL: {state.url}",
            ""
        ]
        
        if state.links:
            lines.append("## Links")
            for link in state.links[:20]:
                lines.append(f"[{link.id}] {link.text}")
        
        if state.buttons:
            lines.append("\n## Buttons")
            for btn in state.buttons:
                lines.append(f"[{btn.id}] {btn.text}")
        
        if state.inputs:
            lines.append("\n## Inputs")
            for inp in state.inputs:
                lines.append(f"[{inp.id}] {inp.text}")
        
        lines.append("\nActions: click(id), fill(id, value), scroll(up/down)")
        
        return "\n".join(lines)
    
    async def close(self):
        """Cleanup"""
        if self.session:
            await self.session.stop()


async def interactive_session():
    """Run interactive CLI browser session"""
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🖥️  CLI WEB BROWSER - BBS EDITION                       ║
║                                                           ║
║   Browse the web like it's 1994!                          ║
║   Websites → Text Menus → AI-Friendly                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    browser = CLIBrowser(headless=True)
    
    try:
        print("⏳ Starting browser...")
        await browser.start()
        print("✅ Browser ready!\n")
        print("Try: goto news.ycombinator.com")
        print("     goto example.com")
        print("     goto github.com\n")
        
        while True:
            try:
                cmd = input("\n🌐 > ").strip()
                
                if not cmd:
                    continue
                
                parts = cmd.split(maxsplit=2)
                action = parts[0].lower()
                
                if action in ("quit", "q", "exit"):
                    break
                    
                elif action == "goto" and len(parts) > 1:
                    await browser.goto(parts[1])
                    print(browser.render())
                    
                elif action == "click" and len(parts) > 1:
                    await browser.click(parts[1])
                    print(browser.render())
                    
                elif action == "fill" and len(parts) > 2:
                    await browser.fill(parts[1], parts[2])
                    print(browser.render())
                    
                elif action == "select" and len(parts) > 2:
                    await browser.select_option(parts[1], parts[2])
                    print(browser.render())
                    
                elif action == "scroll":
                    direction = parts[1] if len(parts) > 1 else "down"
                    await browser.scroll(direction)
                    print(browser.render())
                    
                elif action == "back":
                    await browser.back()
                    print(browser.render())
                    
                elif action in ("refresh", "r"):
                    print(browser.render())
                    
                elif action == "compact":
                    print(browser.render_compact())
                    
                elif action == "json":
                    if browser.current_state:
                        print(json.dumps(browser.current_state.to_dict(), indent=2))
                    else:
                        print("No page loaded")
                        
                elif action == "raw":
                    if browser.current_state:
                        print(f"\n📋 Raw Selector Map ({len(browser.current_state.raw_selector_map)} entries):")
                        for mmid, sel in list(browser.current_state.raw_selector_map.items())[:20]:
                            print(f"  [{mmid}] {sel[:60]}...")
                    else:
                        print("No page loaded")
                        
                elif action == "save":
                    if browser.current_state:
                        filename = f"page_state_{len(browser.history)}.json"
                        with open(filename, "w") as f:
                            json.dump(browser.current_state.to_dict(), f, indent=2)
                        print(f"💾 Saved to {filename}")
                    else:
                        print("No page loaded")
                        
                elif action == "help":
                    print("""
Commands:
  goto <url>           Navigate to URL
  click <id>           Click element (L1, B1, I1, S1)
  fill <id> <text>     Fill input field
  select <id> <value>  Select dropdown option
  scroll <up|down>     Scroll page
  back                 Go back
  refresh / r          Re-render page
  compact              Minimal LLM-friendly output
  json                 Export current state
  raw                  Show raw selector map
  save                 Save state to file
  quit / q             Exit
                    """)
                else:
                    print("❓ Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n")
                continue
            except Exception as e:
                print(f"❌ Error: {e}")
                
    finally:
        await browser.close()
        print("\n👋 Goodbye!\n")


if __name__ == "__main__":
    asyncio.run(interactive_session())
