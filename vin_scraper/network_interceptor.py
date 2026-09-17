"""
Network response interception module for capturing image streams directly from DevTools Protocol.
"""

import asyncio
import hashlib
import io
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from PIL import Image
from playwright.async_api import Response, Page

from .config import ScraperConfig
from .models import ImageInfo


class NetworkImageInterceptor:
    """
    Intercepts network responses from the browser and captures image buffers in real-time.
    Supports filtering exclusively for body content images.
    """

    # Domains / assets to ignore (tracking, analytics, cookie banners, chat widgets)
    EXCLUDED_PATTERNS = [
        "cookielaw.org",
        "vinbase.ai",
        "recaptcha",
        "google-analytics",
        "googletagmanager",
        "facebook.net",
        "doubleclick.net",
        "hotjar",
    ]

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.captured_images: Dict[str, Tuple[ImageInfo, bytes]] = {}
        self.seen_hashes: Set[str] = set()
        self._counter: int = 1
        self._tasks: List[asyncio.Task] = []

    def is_image_response(self, response: Response) -> bool:
        """Determines if a response is an image based on Content-Type or URL extension."""
        ct = response.headers.get("content-type", "").lower()
        url = response.url.lower()

        # Check exclusions
        if any(p in url for p in self.EXCLUDED_PATTERNS):
            return False

        # Check content type
        if any(allowed in ct for allowed in self.config.allowed_mime_types) or "image/" in ct:
            return True

        # Check file extension
        parsed = urlparse(url)
        path = parsed.path
        if any(path.endswith(f".{ext}") for ext in ["webp", "png", "jpg", "jpeg", "svg", "gif", "avif"]):
            return True

        return False

    def _generate_filename(self, url: str, content_type: str, body: bytes) -> str:
        """Generates a clean, sanitized filename for the image."""
        parsed = urlparse(url)
        path = parsed.path
        base_name = path.split("/")[-1].split("?")[0] if path else ""

        # Clean filename characters
        clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base_name)

        # Detect extension
        ext = ""
        if "." in clean_name:
            ext = clean_name.split(".")[-1].lower()
            clean_stem = clean_name.rsplit(".", 1)[0]
        else:
            clean_stem = clean_name or f"image_{self._counter:03d}"

        if not ext or len(ext) > 5:
            if "webp" in content_type:
                ext = "webp"
            elif "png" in content_type:
                ext = "png"
            elif "jpeg" in content_type or "jpg" in content_type:
                ext = "jpg"
            elif "svg" in content_type:
                ext = "svg"
            elif "gif" in content_type:
                ext = "gif"
            elif "avif" in content_type:
                ext = "avif"
            else:
                ext = "png"

        if not clean_stem:
            clean_stem = f"image_{self._counter:03d}"

        filename = f"{self._counter:03d}_{clean_stem}.{ext}"
        self._counter += 1
        return filename

    async def on_response(self, response: Response):
        """Playwright response handler callback."""
        if not self.config.download_images:
            return

        try:
            if response.status != 200:
                return

            if not self.is_image_response(response):
                return

            url = response.url
            if url in self.captured_images:
                return

            # Read raw response binary body directly from network stream
            body = await response.body()
            if not body or len(body) < self.config.min_image_size_bytes:
                return

            # Compute sha256 to deduplicate exact identical binary payloads
            sha256 = hashlib.sha256(body).hexdigest()
            if sha256 in self.seen_hashes:
                return
            self.seen_hashes.add(sha256)

            ct = response.headers.get("content-type", "")
            filename = self._generate_filename(url, ct, body)

            # Extract dimensions if raster image
            width, height = None, None
            if "svg" not in ct and not filename.endswith(".svg"):
                try:
                    with Image.open(io.BytesIO(body)) as img:
                        width, height = img.size
                except Exception:
                    pass

            image_info = ImageInfo(
                url=url,
                filename=filename,
                content_type=ct,
                size_bytes=len(body),
                sha256=sha256,
                width=width,
                height=height
            )

            self.captured_images[url] = (image_info, body)

        except Exception:
            pass

    def attach(self, page: Page):
        """Attaches the interceptor listener to the page with async task tracking."""
        def handler(res: Response):
            task = asyncio.create_task(self.on_response(res))
            self._tasks.append(task)

        page.on("response", handler)

    async def wait_all_pending(self):
        """Awaits completion of all background response capture tasks."""
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    def filter_by_body_urls(self, body_urls: Set[str]) -> Dict[str, Tuple[ImageInfo, bytes]]:
        """
        Filters captured images to retain ONLY those that appear in the body content.
        Matches by full URL, path, or filename.
        """
        if not self.config.body_only or not body_urls:
            return self.captured_images

        # Build normalized lookups for body URLs
        normalized_body_urls = set()
        normalized_paths = set()
        normalized_basenames = set()

        for u in body_urls:
            u_clean = u.split("?")[0].strip()
            normalized_body_urls.add(u_clean)
            p = urlparse(u_clean).path
            if p:
                normalized_paths.add(p)
                base = p.split("/")[-1]
                if base:
                    normalized_basenames.add(base.lower())

        filtered: Dict[str, Tuple[ImageInfo, bytes]] = {}
        counter = 1

        for url, (img_info, body) in self.captured_images.items():
            url_clean = url.split("?")[0].strip()
            p = urlparse(url_clean).path
            base = p.split("/")[-1].lower() if p else ""

            # Check if this image matches any body image reference
            is_match = (
                url in body_urls
                or url_clean in normalized_body_urls
                or p in normalized_paths
                or base in normalized_basenames
            )

            if is_match:
                # Re-index filename cleanly
                stem = img_info.filename.split("_", 1)[-1] if "_" in img_info.filename else img_info.filename
                img_info.filename = f"{counter:03d}_{stem}"
                counter += 1
                filtered[url] = (img_info, body)

        return filtered

    def get_captured_images(self) -> Dict[str, Tuple[ImageInfo, bytes]]:
        """Returns all captured images."""
        return self.captured_images
