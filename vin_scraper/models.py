"""
Data models for structured VinFast web scraped data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class ImageInfo(BaseModel):
    """Represents an intercepted or extracted image."""
    url: str
    filename: str
    content_type: str = ""
    size_bytes: int = 0
    sha256: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    alt: Optional[str] = None
    local_path: Optional[str] = None


class SpecificationItem(BaseModel):
    """Represents a single specification item (e.g. Dimensions, Power, Range)."""
    name: str
    value: str
    unit: Optional[str] = None
    category: Optional[str] = "General"


class FeatureSection(BaseModel):
    """Represents a content section or feature block on the page."""
    index: int
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    items: List[str] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None


class KeyStat(BaseModel):
    """Key highlight stat (e.g. 100 kW, 326 km)."""
    label: str
    value: str
    unit: Optional[str] = None


class PageMetadata(BaseModel):
    """Meta header information of the scraped page."""
    title: str = ""
    meta_description: str = ""
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    canonical_url: Optional[str] = None
    language: str = "vi"
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ScrapedResult(BaseModel):
    """Root model aggregating all extracted data from a page."""
    url: str
    metadata: PageMetadata
    key_stats: List[KeyStat] = Field(default_factory=list)
    specifications: List[SpecificationItem] = Field(default_factory=list)
    sections: List[FeatureSection] = Field(default_factory=list)
    text_blocks: List[str] = Field(default_factory=list)
    images: List[ImageInfo] = Field(default_factory=list)
