"""
Configuration module for VinFast Scraper.
"""

import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field


def get_slug_from_url(url: str) -> str:
    """
    Extracts a clean, filesystem-safe folder slug from a URL.
    E.g. 'https://vinfastauto.com/vn_vi/herio-green' -> 'herio-green'
    E.g. 'https://vinfastauto.com/vn_vi/vf-3/?ref=1' -> 'vf-3'
    """
    parsed = urlparse(url.strip())
    path = parsed.path.strip("/")
    if not path:
        # Fallback to hostname if no path
        slug = parsed.netloc or "vinfast-data"
    else:
        # Get the last non-empty segment
        segments = [s for s in path.split("/") if s]
        slug = segments[-1] if segments else "vinfast-data"

    # Sanitize slug
    slug = re.sub(r'[^a-zA-Z0-9_\-]', '-', slug).strip("-")
    return slug or "vinfast-data"


class ScraperConfig(BaseModel):
    """Configuration options for the scraping process."""
    url: str = "https://vinfastauto.com/vn_vi/herio-green"
    base_output_dir: Path = Field(default_factory=lambda: Path("./output"))
    output_dir: Optional[Path] = None  # Will be resolved dynamically to base_output_dir / slug
    body_only: bool = True  # Only scrape data and images from body content
    headless: bool = True
    timeout_ms: int = 60000
    page_load_wait_sec: float = 3.0
    scroll_steps: int = 15
    scroll_delay_sec: float = 0.3
    min_image_size_bytes: int = 500  # Filter out tracking pixels / tiny icons
    allowed_mime_types: List[str] = Field(
        default_factory=lambda: [
            "image/webp",
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/svg+xml",
            "image/gif",
            "image/avif",
        ]
    )
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "vi-VN"
    save_json: bool = True
    save_markdown: bool = True
    save_txt: bool = True
    save_raw_html: bool = False
    download_images: bool = True

    def resolve_output_dir(self) -> Path:
        """Resolves output directory ensuring it is named after the URL slug."""
        slug = get_slug_from_url(self.url)
        if self.output_dir is not None:
            # If explicit output_dir passed
            out = Path(self.output_dir)
            if out.name == slug:
                return out
            return out / slug
        return self.base_output_dir / slug

    class Config:
        arbitrary_types_allowed = True
