"""
Core Scraping Engine orchestrating Playwright browser, stealth anti-bot bypass,
smart scrolling, network interception, body filtering, and link-specific folder storage.
"""

import asyncio
from typing import Optional, Callable, Set
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from rich.console import Console

from .config import ScraperConfig
from .models import ScrapedResult
from .network_interceptor import NetworkImageInterceptor
from .dom_parser import VinFastDOMParser
from .storage import StorageManager

console = Console()


class VinFastScraper:
    """
    Senior-level Web Scraper for VinFast pages combining Playwright browser automation,
    stealth bypass, DevTools network interception, body content isolation, and organized storage.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.interceptor = NetworkImageInterceptor(self.config)
        self.storage = StorageManager(self.config)

    async def _apply_stealth(self, context: BrowserContext, page: Page):
        """Injects stealth scripts into the browser to bypass Cloudflare/WAF detection."""
        stealth_js = """
            // Overwrite the 'webdriver' property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock Chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['vi-VN', 'vi', 'en-US', 'en']
            });
        """
        await page.add_init_script(stealth_js)

    async def _wait_for_cloudflare_clearance(self, page: Page, max_wait_sec: int = 15):
        """Waits if Cloudflare challenge screen is displayed until the actual page is loaded."""
        for _ in range(max_wait_sec):
            try:
                title = await page.title()
                if "chờ một chút" not in title.lower() and "just a moment" not in title.lower() and "attention required" not in title.lower():
                    return
            except Exception:
                pass
            await asyncio.sleep(1.0)

    async def _smart_scroll(self, page: Page, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Performs smooth incremental scrolling to trigger lazy-loaded images,
        animations, and dynamic section renders.
        """
        if progress_callback:
            progress_callback("Đang thực hiện cuộn trang (Smart Scroll) để kích hoạt lazy-loading images...")

        total_height = await page.evaluate("() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        step_size = max(500, total_height // max(1, self.config.scroll_steps))

        current_position = 0
        while current_position < total_height:
            current_position += step_size
            await page.evaluate(f"window.scrollTo(0, {current_position})")
            await asyncio.sleep(self.config.scroll_delay_sec)

            new_height = await page.evaluate("() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
            if new_height > total_height:
                total_height = new_height

        # Scroll to bottom fully and wait a moment
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.0)

        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

    async def _trigger_interactive_elements(self, page: Page):
        """
        Interacts with tabs or color swatches if present to trigger deferred assets.
        """
        try:
            swatches = await page.query_selector_all('[class*="color-item"], [class*="color-swatch"], [class*="color-picker"] button')
            for swatch in swatches[:6]:
                try:
                    await swatch.click(timeout=1000)
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

    async def _extract_body_image_urls_from_browser(self, page: Page) -> Set[str]:
        """Extracts all image URLs residing strictly within the body/main container in the browser."""
        try:
            urls = await page.evaluate('''() => {
                const mainEl = document.querySelector('.block-system-main-block') || 
                               document.querySelector('main') || 
                               document.querySelector('#main-content') ||
                               document.querySelector('.main-container') ||
                               document.body;
                               
                const ignoreSelectors = 'header, footer, .block-megamainmenu, #onetrust-consent-sdk, .livechat, #block-vinfast-saigon-footer, .header-container, .modal, .modal-dialog, #chat-box';
                const found = new Set();
                
                // 1. img tags
                mainEl.querySelectorAll('img').forEach(img => {
                    if (!img.closest(ignoreSelectors)) {
                        if (img.src) found.add(img.src);
                        if (img.dataset.src) found.add(img.dataset.src);
                        if (img.currentSrc) found.add(img.currentSrc);
                    }
                });
                
                // 2. picture source srcset
                mainEl.querySelectorAll('picture source').forEach(source => {
                    if (!source.closest(ignoreSelectors) && source.srcset) {
                        source.srcset.split(',').forEach(s => {
                            const u = s.trim().split(' ')[0];
                            if (u) found.add(u);
                        });
                    }
                });
                
                // 3. Computed background images
                mainEl.querySelectorAll('*').forEach(el => {
                    if (!el.closest(ignoreSelectors)) {
                        const bg = window.getComputedStyle(el).backgroundImage;
                        if (bg && bg !== 'none') {
                            const matches = bg.matchAll(/url\\(["']?([^"']+)["']?\\)/g);
                            for (const match of matches) {
                                if (match[1] && !match[1].startsWith('data:')) {
                                    found.add(match[1]);
                                }
                            }
                        }
                        if (el.dataset.background) found.add(el.dataset.background);
                        if (el.dataset.bg) found.add(el.dataset.bg);
                    }
                });
                
                return Array.from(found);
            }''')
            return set(urls)
        except Exception:
            return set()

    async def run(self, progress_callback: Optional[Callable[[str], None]] = None) -> ScrapedResult:
        """
        Executes the full scraping workflow:
        1. Launches browser context with stealth bypass
        2. Attaches network interceptor
        3. Navigates to target URL and resolves challenges
        4. Auto-scrolls & triggers dynamic assets
        5. Extracts body image references and isolates body content
        6. Filters captured network images to retain ONLY body images
        7. Parses DOM specifications & sections
        8. Persists all output into link-specific folder
        """
        if progress_callback:
            progress_callback(f"Khởi động trình duyệt Chromium (Headless: {self.config.headless})...")

        html_content = ""
        page_title = ""
        browser_body_image_urls: Set[str] = set()

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=self.config.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )

            context: BrowserContext = await browser.new_context(
                user_agent=self.config.user_agent,
                viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
                locale=self.config.locale,
                timezone_id="Asia/Ho_Chi_Minh",
            )

            page: Page = await context.new_page()

            # Apply stealth anti-detection
            await self._apply_stealth(context, page)

            # Attach Network Image Interceptor to DevTools stream
            self.interceptor.attach(page)

            if progress_callback:
                progress_callback(f"Đang điều hướng đến: {self.config.url} ...")

            await page.goto(
                self.config.url,
                wait_until="domcontentloaded",
                timeout=self.config.timeout_ms
            )

            # Wait for Cloudflare clearance if any challenge exists
            await self._wait_for_cloudflare_clearance(page)

            # Wait initial load time
            await asyncio.sleep(self.config.page_load_wait_sec)

            # Smart scroll to trigger lazy loading
            await self._smart_scroll(page, progress_callback)

            # Trigger interactive elements (color swatches, etc.)
            await self._trigger_interactive_elements(page)

            # Extra buffer time to allow network image responses to settle
            await asyncio.sleep(2.0)

            # Extract body images from the live browser DOM
            if self.config.body_only:
                browser_body_image_urls = await self._extract_body_image_urls_from_browser(page)

            # Wait for all pending image downloads to complete
            await self.interceptor.wait_all_pending()

            if progress_callback:
                progress_callback("Đang trích xuất DOM và phân tích cấu trúc body...")

            # Capture title & HTML snapshot
            page_title = await page.title()
            html_content = await page.content()

            await browser.close()

        # Step 1: Filter captured network images strictly for Body
        parser = VinFastDOMParser(html_content, self.config.url)
        dom_body_image_urls = parser.extract_body_image_urls()
        combined_body_urls = browser_body_image_urls.union(dom_body_image_urls)

        if self.config.body_only and combined_body_urls:
            captured_body_images = self.interceptor.filter_by_body_urls(combined_body_urls)
        else:
            captured_body_images = self.interceptor.get_captured_images()

        if progress_callback:
            progress_callback(f"Đang lưu {len(captured_body_images)} hình ảnh Body vào thư mục '{self.storage.output_dir.name}/images'...")

        saved_images = self.storage.save_images(captured_body_images)

        # Step 2: Parse DOM text, metadata, specs, sections strictly from Body
        result = parser.parse(images=saved_images)

        # Fallback title if DOM title was empty
        if not result.metadata.title and page_title:
            result.metadata.title = page_title

        # Step 3: Export files into link-specific folder
        if progress_callback:
            progress_callback(f"Đang xuất file dữ liệu vào thư mục '{self.storage.output_dir.name}'...")

        if self.config.save_json:
            self.storage.save_json(result)

        if self.config.save_markdown:
            self.storage.save_markdown(result)

        if self.config.save_txt:
            self.storage.save_raw_text(result)

        if self.config.save_raw_html:
            self.storage.save_html_snapshot(html_content)

        return result
