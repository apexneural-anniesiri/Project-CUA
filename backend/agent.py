"""
WebSurferAgent - Implements the CUA Execution Loop from Synapse Report 2026.

This agent autonomously browses the web by:
1. Capturing screenshots of the current page
2. Sending them to GPT-4o for decision making
3. Executing actions (click, type, scroll, finish)
4. Repeating until the objective is complete
"""

import asyncio
import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Dict, Optional, Tuple

from openai import OpenAI
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext


class WebSurferAgent:
    """
    Autonomous web browsing agent that uses GPT-4o vision to make decisions.
    """
    
    def __init__(self, objective: str):
        self.objective = objective
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.reasoning_logs: list = []
        # Thread pool executor for running sync Playwright operations
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    async def initialize(self):
        """Initialize the Playwright browser in headless mode using sync API in thread."""
        def _init():
            pw = sync_playwright().start()
            # Launch browser with more realistic settings
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            # Create context with realistic browser fingerprint
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation"],
                geolocation={"latitude": 40.7128, "longitude": -74.0060},  # New York
                color_scheme="light",
                # Add extra HTTP headers
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
            # Add script to hide webdriver property
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            page = context.new_page()
            # Start with a neutral page instead of Google to avoid immediate security checks
            # Use about:blank or a simple page first
            page.goto("about:blank", wait_until="domcontentloaded", timeout=10000)
            return pw, browser, context, page
        
        loop = asyncio.get_event_loop()
        self.playwright, self.browser, self.context, self.page = await loop.run_in_executor(
            self.executor, _init
        )
        
    async def capture_screenshot(self) -> str:
        """
        Capture the current page screenshot and convert to Base64.
        
        Returns:
            Base64-encoded string of the screenshot
        """
        def _screenshot():
            return self.page.screenshot(full_page=False)
        
        loop = asyncio.get_event_loop()
        screenshot_bytes = await loop.run_in_executor(self.executor, _screenshot)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        return screenshot_base64
    
    async def take_action(self) -> Dict:
        """
        Implements the CUA Execution Loop from Synapse Report 2026.
        
        Captures screenshot, sends to GPT-4o, and executes the returned action.
        
        Returns:
            Dictionary with action details and reasoning
        """
        # Capture current state
        screenshot_base64 = await self.capture_screenshot()
        
        def _get_url():
            return self.page.url
        
        loop = asyncio.get_event_loop()
        current_url = await loop.run_in_executor(self.executor, _get_url)
        
        # System prompt for the CUA
        system_prompt = """You are a Computer-Using Agent (CUA) that can autonomously browse the web to complete tasks.

You can perform the following actions:
1. **navigate** - Navigate directly to a URL. Use this to go to specific websites. Provide the "url" field with the full URL (e.g., "https://reddit.com").
2. **click** - Click on an element. Provide a CSS selector or descriptive text to identify the element.
3. **type** - Type text into an input field. Provide the selector and the text to type.
4. **scroll** - Scroll the page. Provide direction: "up", "down", "left", or "right".
5. **finish** - Complete the task when the objective has been achieved.

IMPORTANT SELECTOR GUIDELINES:
- For Google search: Use selector "input[name='q']" or "textarea[name='q']" for the search box
- For input fields: Use CSS selectors like "input[name='fieldname']", "input[type='text']", or placeholder text
- For buttons: Use button text, role="button", or CSS selector
- For Google search box specifically: selector should be "input[name='q']" or just "q" as the name

IMPORTANT: If you encounter a CAPTCHA, security challenge, or "unusual traffic" page:
- Look for buttons like "Continue", "Verify", or "I'm not a robot" checkbox
- Click the checkbox or button to proceed
- If you see "Why did this happen?" link, ignore it and look for the main action button
- If completely stuck on a security page, use "finish" action and note in reasoning that a security challenge blocked progress

Return a JSON object with this exact structure:
{
    "action": "navigate" | "click" | "type" | "scroll" | "finish",
    "url": "Full URL to navigate to (required for navigate action, e.g., 'https://reddit.com')",
    "selector": "CSS selector or descriptive text (required for click/type). For Google search use: input[name='q']",
    "text": "Text to type (required for type action)",
    "direction": "up" | "down" | "left" | "right" (required for scroll action),
    "reasoning": "Your step-by-step reasoning for this action"
}

Be precise with selectors. Use visible text, IDs, classes, or data attributes when possible."""

        # User prompt with objective and context
        user_prompt = f"""Objective: {self.objective}

Current URL: {current_url}

NAVIGATION STRATEGY - CRITICAL:
- ALWAYS use "navigate" action to go directly to websites mentioned in the objective
- If objective says "Go to Reddit" → use action: "navigate", url: "https://reddit.com"
- If objective says "Go to Amazon" → use action: "navigate", url: "https://amazon.com"
- NEVER search Google for websites you already know - navigate directly!
- Only use Google search if you need to find something unknown or search within a site
- Common sites: reddit.com, amazon.com, github.com, techcrunch.com, wikipedia.org

IMPORTANT: If you see a security page saying "unusual traffic" or "verify you're not a robot":
- This is a CAPTCHA/security challenge
- Try clicking any "Continue" or "Verify" button if available
- If there's a checkbox, click it
- If stuck, use "finish" action and note that a security challenge was encountered

Analyze the screenshot and determine the next action to take. Return the JSON action object."""

        try:
            # Call GPT-4o with vision
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=300  # Reduced for faster responses
            )
            
            # Parse the response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from the response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            action_data = json.loads(content)
            reasoning = action_data.get("reasoning", "No reasoning provided")
            
            # Log the reasoning
            self.reasoning_logs.append({
                "step": len(self.reasoning_logs) + 1,
                "reasoning": reasoning,
                "action": action_data.get("action"),
                "url": current_url
            })
            
            # Execute the action
            await self._execute_action(action_data, current_url)
            
            return {
                "action": action_data.get("action"),
                "reasoning": reasoning,
                "url": current_url
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse AI response: {str(e)}"
            self.reasoning_logs.append({
                "step": len(self.reasoning_logs) + 1,
                "reasoning": error_msg,
                "action": "error",
                "url": current_url
            })
            return {
                "action": "error",
                "reasoning": error_msg,
                "url": current_url
            }
        except Exception as e:
            error_msg = f"Error during action execution: {str(e)}"
            self.reasoning_logs.append({
                "step": len(self.reasoning_logs) + 1,
                "reasoning": error_msg,
                "action": "error",
                "url": current_url
            })
            return {
                "action": "error",
                "reasoning": error_msg,
                "url": current_url
            }
    
    async def _execute_action(self, action_data: Dict, current_url: str):
        """Execute the action returned by the AI."""
        action = action_data.get("action", "").lower()
        
        def _execute():
            if action == "navigate":
                url = action_data.get("url", "")
                if url:
                    # Ensure URL has protocol
                    if not url.startswith("http://") and not url.startswith("https://"):
                        url = "https://" + url
                    self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    self.page.wait_for_timeout(1000)  # Wait for page to load
            elif action == "click":
                selector = action_data.get("selector", "")
                if selector:
                    try:
                        # Try to click by selector first
                        self.page.click(selector, timeout=5000)
                    except:
                        # If selector fails, try to click by text
                        try:
                            self.page.click(f"text={selector}", timeout=5000)
                        except:
                            # Try get_by_text
                            try:
                                self.page.get_by_text(selector, exact=False).first.click(timeout=5000)
                            except:
                                # Try clicking by role (for checkboxes like CAPTCHA)
                                if "robot" in selector.lower() or "captcha" in selector.lower() or "verify" in selector.lower():
                                    try:
                                        self.page.get_by_role("checkbox").click(timeout=5000)
                                    except:
                                        # Try to find Continue or Verify button
                                        try:
                                            self.page.get_by_role("button", name="Continue").click(timeout=5000)
                                        except:
                                            self.page.get_by_role("button", name="Verify").click(timeout=5000)
                    # Wait for page to update (reduced wait times for speed)
                    if any(keyword in selector.lower() for keyword in ["robot", "captcha", "verify", "continue", "unusual", "traffic"]):
                        self.page.wait_for_timeout(2000)  # Wait for security checks
                    else:
                        self.page.wait_for_timeout(500)  # Reduced wait time
                
            elif action == "type":
                selector = action_data.get("selector", "")
                text = action_data.get("text", "")
                if selector and text:
                    try:
                        # Try direct selector first (CSS selector or XPath)
                        if selector.startswith("//") or selector.startswith("xpath="):
                            # XPath
                            self.page.locator(selector).fill(text, timeout=5000)
                        elif selector.startswith("/"):
                            # XPath without prefix
                            self.page.locator(f"xpath={selector}").fill(text, timeout=5000)
                        else:
                            # CSS selector
                            self.page.fill(selector, text, timeout=5000)
                    except:
                        try:
                            # Try by placeholder text
                            self.page.get_by_placeholder(selector).fill(text, timeout=5000)
                        except:
                            try:
                                # Try by label text
                                self.page.get_by_label(selector).fill(text, timeout=5000)
                            except:
                                try:
                                    # Try by role (searchbox)
                                    self.page.get_by_role("searchbox").fill(text, timeout=5000)
                                except:
                                    try:
                                        # Try common Google search input selectors
                                        self.page.fill("input[name='q']", text, timeout=5000)
                                    except:
                                        try:
                                            # Try textarea
                                            self.page.fill("textarea[name='q']", text, timeout=5000)
                                        except:
                                            # Last resort: try to find any input field
                                            self.page.locator("input[type='text'], input[type='search'], textarea").first.fill(text, timeout=5000)
                    self.page.wait_for_timeout(300)  # Reduced wait time
                    # Press Enter after typing
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_timeout(800)  # Reduced wait time
                    
            elif action == "scroll":
                direction = action_data.get("direction", "down").lower()
                if direction == "down":
                    self.page.evaluate("window.scrollBy(0, 500)")
                elif direction == "up":
                    self.page.evaluate("window.scrollBy(0, -500)")
                elif direction == "left":
                    self.page.evaluate("window.scrollBy(-500, 0)")
                elif direction == "right":
                    self.page.evaluate("window.scrollBy(500, 0)")
                self.page.wait_for_timeout(500)  # Reduced wait time
                
            elif action == "finish":
                # Task is complete, no action needed
                pass
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _execute)
    
    async def get_state(self) -> Tuple[str, str, str]:
        """
        Return the current state: screenshot, reasoning logs, and extracted content.
        
        Returns:
            Tuple of (screenshot_base64, logs_text, extracted_content)
        """
        screenshot_base64 = await self.capture_screenshot()
        logs_text = "\n".join([
            f"[Step {log['step']}] {log['reasoning']}"
            for log in self.reasoning_logs
        ])
        
        # Extract text content from the page
        def _extract_content():
            try:
                # Try to extract main content
                content = self.page.evaluate("""
                    () => {
                        // Extract post titles and links (for Reddit)
                        const posts = Array.from(document.querySelectorAll('h3, [data-testid="post-title"], .Post a[data-click-id="body"]'))
                            .slice(0, 10)
                            .map(el => {
                                const title = el.textContent?.trim();
                                const link = el.closest('a')?.href || '';
                                return title ? `• ${title}${link ? ' - ' + link : ''}` : null;
                            })
                            .filter(Boolean);
                        
                        // If no posts found, extract main headings
                        if (posts.length === 0) {
                            const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
                                .slice(0, 10)
                                .map(el => el.textContent?.trim())
                                .filter(Boolean);
                            return headings.join('\\n');
                        }
                        
                        return posts.join('\\n');
                    }
                """)
                return content or "Content extraction in progress..."
            except:
                return "Unable to extract content"
        
        loop = asyncio.get_event_loop()
        extracted_content = await loop.run_in_executor(self.executor, _extract_content)
        
        return screenshot_base64, logs_text, extracted_content
    
    async def cleanup(self):
        """Clean up browser resources."""
        def _cleanup():
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        
        if self.page or self.context or self.browser or self.playwright:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, _cleanup)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
