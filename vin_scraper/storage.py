"""
Storage manager for persisting scraped text, specifications, and intercepted image files
into link-specific folders.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse
from rich.console import Console

from .config import ScraperConfig, get_slug_from_url
from .models import ScrapedResult, ImageInfo

console = Console()


class StorageManager:
    """Handles writing scraped data, markdown reports, and image binaries to link-specific folders."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.output_dir = config.resolve_output_dir()
        self.images_dir = self.output_dir / "images"

    def setup_directories(self):
        """Creates necessary output folders."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.config.download_images:
            self.images_dir.mkdir(parents=True, exist_ok=True)

    def save_images(self, captured_images: Dict[str, Tuple[ImageInfo, bytes]]) -> List[ImageInfo]:
        """Saves binary image buffers to the images directory and returns updated ImageInfo list."""
        self.setup_directories()
        saved_image_infos: List[ImageInfo] = []

        for url, (img_info, body) in captured_images.items():
            try:
                file_path = self.images_dir / img_info.filename
                with open(file_path, "wb") as f:
                    f.write(body)

                # Set relative local path
                rel_path = f"images/{img_info.filename}"
                img_info.local_path = rel_path
                saved_image_infos.append(img_info)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to save image {img_info.filename}: {e}[/yellow]")

        # Save manifest
        manifest_path = self.output_dir / "images_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump([img.model_dump() for img in saved_image_infos], f, ensure_ascii=False, indent=2)

        return saved_image_infos

    def save_json(self, result: ScrapedResult) -> Path:
        """Saves full structured data to data.json."""
        self.setup_directories()
        json_path = self.output_dir / "data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        return json_path

    def save_raw_text(self, result: ScrapedResult) -> Path:
        """Saves clean text blocks to data.txt."""
        self.setup_directories()
        txt_path = self.output_dir / "data.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {result.metadata.title}\n")
            f.write(f"URL: {result.url}\n")
            f.write(f"SCRAPED AT: {result.metadata.scraped_at}\n\n")
            
            if result.metadata.meta_description:
                f.write(f"DESCRIPTION:\n{result.metadata.meta_description}\n\n")

            if result.key_stats:
                f.write("--- KEY STATS ---\n")
                for stat in result.key_stats:
                    unit_str = f" {stat.unit}" if stat.unit else ""
                    f.write(f"- {stat.label}: {stat.value}{unit_str}\n")
                f.write("\n")

            if result.specifications:
                f.write("--- SPECIFICATIONS ---\n")
                for spec in result.specifications:
                    f.write(f"- {spec.name}: {spec.value}\n")
                f.write("\n")

            f.write("--- CONTENT TEXT BLOCKS (BODY) ---\n")
            for block in result.text_blocks:
                f.write(f"{block}\n\n")

        return txt_path

    def save_markdown(self, result: ScrapedResult) -> Path:
        """Generates a comprehensive, formatted Markdown report with embedded images and tables."""
        self.setup_directories()
        md_path = self.output_dir / "data.md"

        # Build url-to-local path lookup map supporting full URL, relative path, and filename base
        url_to_local = {}
        for img in result.images:
            if img.local_path:
                url_to_local[img.url] = img.local_path
                parsed = urlparse(img.url)
                if parsed.path:
                    url_to_local[parsed.path] = img.local_path
                    url_to_local[parsed.path.split("/")[-1]] = img.local_path

        def resolve_img_path(raw_url: str) -> str:
            if raw_url in url_to_local:
                return url_to_local[raw_url]
            path = urlparse(raw_url).path
            if path in url_to_local:
                return url_to_local[path]
            base = path.split("/")[-1] if path else ""
            if base in url_to_local:
                return url_to_local[base]
            return raw_url

        md_lines = []
        md_lines.append(f"# {result.metadata.title or 'VinFast Vehicle Report'}\n")
        md_lines.append(f"**URL:** [{result.url}]({result.url})  ")
        md_lines.append(f"**Thời gian cào:** `{result.metadata.scraped_at}`  ")
        md_lines.append(f"**Tổng số ảnh Body bắt qua Network Tab:** `{len(result.images)}`\n")

        if result.metadata.meta_description:
            md_lines.append(f"> {result.metadata.meta_description}\n")

        # Key Highlights / Stats
        if result.key_stats:
            md_lines.append("## ⚡ Thông số nổi bật (Key Highlights)\n")
            md_lines.append("| Thông số | Giá trị | Đơn vị |")
            md_lines.append("| :--- | :--- | :--- |")
            for stat in result.key_stats:
                unit_str = stat.unit or "-"
                md_lines.append(f"| **{stat.label}** | `{stat.value}` | {unit_str} |")
            md_lines.append("\n")

        # Technical Specifications Table
        if result.specifications:
            md_lines.append("## 📋 Bảng thông số kỹ thuật chi tiết\n")
            md_lines.append("| Hạng mục | Giá trị | Phân loại |")
            md_lines.append("| :--- | :--- | :--- |")
            for spec in result.specifications:
                cat = spec.category or "Kỹ thuật"
                md_lines.append(f"| **{spec.name}** | {spec.value} | {cat} |")
            md_lines.append("\n")

        # Main Feature Sections
        if result.sections:
            md_lines.append("## 🚀 Chi tiết các Section & Tính năng (Body)\n")
            for sec in result.sections:
                title = sec.title
                if len(title) > 80:
                    title = title[:80] + "..."
                md_lines.append(f"### {title}\n")
                if sec.description and sec.description != sec.title:
                    md_lines.append(f"{sec.description}\n")
                if sec.items:
                    for item in sec.items:
                        md_lines.append(f"- {item}")
                    md_lines.append("\n")

                if sec.image_urls:
                    md_lines.append("**Hình ảnh liên quan:**\n")
                    for img_url in sec.image_urls:
                        local = resolve_img_path(img_url)
                        md_lines.append(f"![{title}]({local})\n")

                md_lines.append("---\n")

        # Image Gallery
        if result.images:
            md_lines.append("## 🖼️ Bộ sưu tập hình ảnh Body (Network Captured Gallery)\n")
            md_lines.append(f"Toàn bộ `{len(result.images)}` hình ảnh Body được lưu trong thư mục `images/`:\n")
            md_lines.append("| STT | Tên file | Kích thước | Dung lượng | URL gốc |")
            md_lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for idx, img in enumerate(result.images, 1):
                dims = f"{img.width}x{img.height}" if img.width and img.height else "-"
                kb = f"{img.size_bytes / 1024:.1f} KB"
                md_lines.append(f"| {idx} | [{img.filename}]({img.local_path}) | {dims} | {kb} | [Link gốc]({img.url}) |")
            md_lines.append("\n")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        return md_path

    def save_html_snapshot(self, html: str) -> Path:
        """Saves full raw HTML for archival."""
        self.setup_directories()
        html_path = self.output_dir / "page_snapshot.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return html_path
