"""
VinFast Web & Network Image Scraper Package
A robust, senior-grade scraping toolkit for capturing structured text,
specifications, and network-intercepted image responses from VinFast pages.
"""

__version__ = "1.0.0"
__author__ = "Senior Python Tool Developer"

from .engine import VinFastScraper
from .config import ScraperConfig
from .models import ScrapedResult, SpecificationItem, FeatureSection, ImageInfo

__all__ = [
    "VinFastScraper",
    "ScraperConfig",
    "ScrapedResult",
    "SpecificationItem",
    "FeatureSection",
    "ImageInfo",
]
