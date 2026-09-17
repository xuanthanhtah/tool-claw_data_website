"""
DOM Parser for extracting structured body content, metadata, specifications, and sections
across all VinFast vehicle PDP templates.
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from bs4 import BeautifulSoup, Tag

from .models import (
    PageMetadata,
    SpecificationItem,
    FeatureSection,
    KeyStat,
    ScrapedResult,
    ImageInfo,
)


class VinFastDOMParser:
    """
    Parses HTML content strictly from the main body of VinFast web pages,
    excluding headers, footers, mega-menus, modals, and cookie banners.
    """

    EXCLUDE_SELECTORS = (
        "header, footer, .block-megamainmenu, .header-container, "
        "#block-vinfast-saigon-footer, #onetrust-consent-sdk, .livechat, "
        ".vinbase, #chat-box, .modal, .modal-dialog, script, style, noscript, svg, nav"
    )

    def __init__(self, html: str, url: str):
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, "html.parser")
        self.body_container = self._get_main_body_node()

    def _get_main_body_node(self) -> Tag:
        """Finds and isolates the primary body container."""
        doc = BeautifulSoup(self.html, "html.parser")
        for el in doc.select(self.EXCLUDE_SELECTORS):
            el.decompose()

        main_node = (
            doc.select_one(".block-system-main-block")
            or doc.select_one("main")
            or doc.select_one("#main-content")
            or doc.select_one(".main-container")
            or doc.body
            or doc
        )
        return main_node

    def extract_metadata(self) -> PageMetadata:
        """Extracts page title, description, and OpenGraph metadata."""
        title_tag = self.soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        def get_meta_attr(name_or_prop: str, value: str) -> Optional[str]:
            tag = self.soup.find("meta", attrs={name_or_prop: value})
            if tag and "content" in tag.attrs:
                return tag["content"].strip()
            return None

        meta_desc = get_meta_attr("name", "description") or get_meta_attr("property", "og:description") or ""
        og_title = get_meta_attr("property", "og:title")
        og_desc = get_meta_attr("property", "og:description")
        og_image = get_meta_attr("property", "og:image")
        
        canonical_tag = self.soup.find("link", attrs={"rel": "canonical"})
        canonical_url = canonical_tag.get("href") if canonical_tag else None

        lang = "vi"
        if self.soup.html and self.soup.html.get("lang"):
            lang = self.soup.html.get("lang")

        return PageMetadata(
            title=title,
            meta_description=meta_desc,
            og_title=og_title,
            og_description=og_desc,
            og_image=og_image,
            canonical_url=canonical_url,
            language=lang
        )

    def extract_key_stats(self) -> List[KeyStat]:
        """Extracts high-level highlight stats across all PDP templates."""
        stats: List[KeyStat] = []
        
        # General selectors for highlight stats across Herio, Limo, Minio, Nerio, VF3, VF8 etc.
        stat_containers = self.body_container.select(
            '[class*="stat-item"], [class*="stat-row"], [class*="stats-grid"] > div, '
            '[class*="hero-stat"], [class*="-specs-list"] > [class*="-spec-row"], '
            '[class*="-section-1-footer"] > div, [class*="-section-2-wrapper"] [class*="stat"]'
        )
        
        for item in stat_containers:
            num_el = item.select_one('[class*="number"], [class*="value"], [class*="num"], h3, h4')
            unit_el = item.select_one('[class*="unit"], span.unit')
            label_el = item.select_one('[class*="label"], [class*="desc"], [class*="title"], p:last-child')

            if num_el and label_el and num_el != label_el:
                val = num_el.get_text(strip=True)
                unit = unit_el.get_text(strip=True) if unit_el else None
                label = label_el.get_text(strip=True)
                
                if unit and val.endswith(unit):
                    val = val[:-len(unit)].strip()

                if label and val:
                    stats.append(KeyStat(label=label, value=val, unit=unit))
            else:
                lines = [l.strip() for l in item.get_text(separator="\n").splitlines() if l.strip()]
                if len(lines) == 2:
                    val = lines[0]
                    label = lines[1]
                    stats.append(KeyStat(label=label, value=val, unit=None))
                elif len(lines) == 3:
                    val = lines[0]
                    unit = lines[1]
                    label = lines[2]
                    stats.append(KeyStat(label=label, value=val, unit=unit))

        # Deduplicate stats
        unique_stats: List[KeyStat] = []
        seen = set()
        for s in stats:
            # Skip noise or non-stat items
            if any(w in s.label.lower() for w in ["đặt cọc", "giá kèm pin", "dự toán"]):
                continue
            key = f"{s.label}:{s.value}"
            if key not in seen and s.label and s.value:
                seen.add(key)
                unique_stats.append(s)

        return unique_stats

    def extract_specifications(self) -> List[SpecificationItem]:
        """Extracts detailed technical specifications from grid cards and tables."""
        specs: List[SpecificationItem] = []
        seen_names = set()

        # Target specification cards across all PDP templates
        spec_items = self.body_container.select(
            '[class*="spec-item"], [class*="section-6-grid"] > div, '
            '[class*="spec-grid"] > div, [class*="specs-grid"] > div, '
            '[class*="-spec-item"]'
        )

        for card in spec_items:
            label_el = card.select_one('[class*="label"], [class*="title"], [class*="desc"], p:last-child')
            val_el = card.select_one('[class*="value"], [class*="num"], [class*="number"], p:first-child, h3, h4')

            name = ""
            value = ""

            if label_el and val_el and label_el != val_el:
                name = label_el.get_text(separator=" ", strip=True)
                value = val_el.get_text(separator=" ", strip=True)
            else:
                card_children = [c for c in card.children if isinstance(c, Tag) and c.get_text(strip=True)]
                if len(card_children) == 2:
                    t1 = card_children[0].get_text(separator=" ", strip=True)
                    t2 = card_children[1].get_text(separator=" ", strip=True)
                    value, name = t1, t2
                elif len(card_children) >= 3:
                    t_last = card_children[-1].get_text(separator=" ", strip=True)
                    t_rest = " ".join([c.get_text(separator=" ", strip=True) for c in card_children[:-1]])
                    value, name = t_rest, t_last
                else:
                    lines = [l.strip() for l in card.get_text(separator="\n").splitlines() if l.strip()]
                    if len(lines) == 2:
                        value, name = lines[0], lines[1]
                    elif len(lines) >= 3:
                        value, name = " ".join(lines[:-1]), lines[-1]

            if name and value and name not in ["ĐẶT CỌC", "Thông số tạo nên khác biệt", "ĐẶT CỌC NGAY"]:
                if name not in seen_names:
                    seen_names.add(name)
                    unit = None
                    unit_match = re.search(r'\(([^)]+)\)', name)
                    if unit_match:
                        unit = unit_match.group(1)
                    specs.append(SpecificationItem(name=name, value=value, unit=unit, category="Kỹ thuật"))

        return specs

    def extract_sections(self) -> List[FeatureSection]:
        """Extracts major feature sections strictly from body."""
        sections: List[FeatureSection] = []
        
        section_elements = self.body_container.select(
            '[class*="pdp-section-class"], [class*="-section-"], [class*="pdp-section"]'
        )
        
        if not section_elements:
            section_elements = [c for c in self.body_container.children if isinstance(c, Tag) and c.get_text(strip=True)]

        for idx, sec in enumerate(section_elements, 1):
            heading = sec.select_one('h1, h2, h3, [class*="title"], [class*="header-content"], [class*="header"]')
            title = heading.get_text(strip=True) if heading else ""

            desc_el = sec.select_one('[class*="description"], [class*="subtitle"], p')
            desc = desc_el.get_text(strip=True) if desc_el else ""

            items = [li.get_text(strip=True) for li in sec.select('ul li, ol li') if li.get_text(strip=True)]

            img_urls = []
            for img in sec.select('img'):
                src = img.get('src') or img.get('data-src') or img.get('srcset')
                if src:
                    img_urls.append(src.split()[0])

            raw_text = sec.get_text(separator="\n", strip=True)

            if title or desc or items or img_urls:
                sections.append(FeatureSection(
                    index=idx,
                    title=title or f"Section {idx}",
                    subtitle=None,
                    description=desc,
                    items=items,
                    image_urls=img_urls,
                    raw_text=raw_text
                ))

        return sections

    def extract_clean_text_blocks(self) -> List[str]:
        """Extracts cleaned, de-noised readable text blocks strictly from body."""
        lines = [line.strip() for line in self.body_container.get_text(separator="\n").splitlines() if line.strip()]

        ignore_list = {
            "tài khoản", "đăng ký lái thử", "đăng nhập / đăng ký", "xem chi tiết", "đặt cọc",
            "đặt cọc ngay", "tiếp tục", "quay lại", "đóng", "menu", "tìm kiếm"
        }
        
        filtered = []
        for line in lines:
            if line.lower() not in ignore_list and len(line) > 1:
                filtered.append(line)

        blocks = []
        current_block = []
        for line in filtered:
            if len(line) > 60:
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
                blocks.append(line)
            else:
                current_block.append(line)
                if len(current_block) >= 4:
                    blocks.append("\n".join(current_block))
                    current_block = []
                    
        if current_block:
            blocks.append("\n".join(current_block))

        return blocks

    def extract_body_image_urls(self) -> Set[str]:
        """Extracts all image URLs referenced in the body DOM."""
        urls: Set[str] = set()

        for img in self.body_container.select("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                urls.add(src)

        for source in self.body_container.select("picture source"):
            srcset = source.get("srcset")
            if srcset:
                for item in srcset.split(","):
                    u = item.strip().split(" ")[0]
                    if u:
                        urls.add(u)

        for el in self.body_container.find_all(style=True):
            style = el.get("style", "")
            matches = re.findall(r'url\(["\']?([^"\']+)["\']?\)', style)
            for m in matches:
                if not m.startswith("data:"):
                    urls.add(m)

        return urls

    def parse(self, images: List[ImageInfo] = None) -> ScrapedResult:
        """Executes full parsing pipeline strictly for body content."""
        return ScrapedResult(
            url=self.url,
            metadata=self.extract_metadata(),
            key_stats=self.extract_key_stats(),
            specifications=self.extract_specifications(),
            sections=self.extract_sections(),
            text_blocks=self.extract_clean_text_blocks(),
            images=images or []
        )
