"""
Command Line Interface with Rich formatting and interactive progress for VinFast Scraper.
Supports link-specific folder separation and body-only data extraction.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.status import Status
from rich.text import Text

from .config import ScraperConfig, get_slug_from_url
from .engine import VinFastScraper
from .models import ScrapedResult

console = Console()


def display_banner():
    """Displays a welcoming banner in the terminal."""
    banner = Text()
    banner.append("⚡ VINFAST WEB & NETWORK IMAGE SCRAPER ⚡\n", style="bold cyan")
    banner.append("Công cụ cào Body Data, Thông số kỹ thuật & Bắt ảnh từ Network Tab\n", style="italic white")
    banner.append("Tự động phân chia thư mục theo Link, loại bỏ Header/Footer/Tracking", style="dim white")
    console.print(Panel(banner, border_style="cyan", expand=False))


def display_summary(result: ScrapedResult, target_output_dir: Path):
    """Prints a beautiful summary table of scraped results."""
    console.print("\n[bold green]✔ Quá trình cào dữ liệu Body hoàn tất thành công![/bold green]\n")

    # Metadata Panel
    meta_table = Table(title="📌 Thông tin trang web", show_header=True, header_style="bold magenta")
    meta_table.add_column("Thuộc tính", style="cyan", width=25)
    meta_table.add_column("Nội dung", style="white")

    meta_table.add_row("Tiêu đề", result.metadata.title or "N/A")
    meta_table.add_row("URL", result.url)
    meta_table.add_row("Thư mục lưu", str(target_output_dir.resolve()))
    meta_table.add_row("Thời gian cào", result.metadata.scraped_at)
    console.print(meta_table)

    # Key Stats Table
    if result.key_stats:
        stats_table = Table(title="⚡ Thông số nổi bật (Highlights)", show_header=True, header_style="bold yellow")
        stats_table.add_column("Chỉ số", style="cyan")
        stats_table.add_column("Giá trị", style="green bold")
        stats_table.add_column("Đơn vị", style="dim white")

        for s in result.key_stats:
            stats_table.add_row(s.label, s.value, s.unit or "-")
        console.print(stats_table)

    # Specifications Table (preview)
    if result.specifications:
        spec_table = Table(title=f"📋 Thông số kỹ thuật ({len(result.specifications)} mục)", show_header=True, header_style="bold blue")
        spec_table.add_column("Hạng mục", style="cyan", width=35)
        spec_table.add_column("Thông số", style="green")

        for spec in result.specifications[:12]:
            spec_table.add_row(spec.name, spec.value)
        if len(result.specifications) > 12:
            spec_table.add_row("...", f"... và thêm {len(result.specifications) - 12} thông số khác (xem chi tiết trong data.json / data.md)")
        console.print(spec_table)

    # Image Stats
    img_table = Table(title="🖼️ Thống kê hình ảnh Body (Bắt từ Network Stream)", show_header=True, header_style="bold cyan")
    img_table.add_column("Mục", style="cyan")
    img_table.add_column("Số lượng / Kích thước", style="green bold")

    total_size_mb = sum(img.size_bytes for img in result.images) / (1024 * 1024)
    formats = {}
    for img in result.images:
        ext = img.filename.split(".")[-1].lower() if "." in img.filename else "other"
        formats[ext] = formats.get(ext, 0) + 1

    format_str = ", ".join([f"{k.upper()}: {v}" for k, v in formats.items()])

    img_table.add_row("Tổng số ảnh Body", str(len(result.images)))
    img_table.add_row("Tổng dung lượng", f"{total_size_mb:.2f} MB")
    img_table.add_row("Định dạng", format_str or "N/A")
    img_table.add_row("Thư mục lưu trữ", str(target_output_dir.resolve() / "images"))
    console.print(img_table)

    # Generated Files Table
    files_table = Table(title="📂 Danh sách file đầu ra đã tạo", show_header=True, header_style="bold green")
    files_table.add_column("File", style="cyan")
    files_table.add_column("Mô tả", style="white")
    files_table.add_column("Đường dẫn", style="dim underline")

    files_table.add_row("data.json", "Dữ liệu có cấu trúc JSON đầy đủ", str((target_output_dir / "data.json").resolve()))
    files_table.add_row("data.md", "Báo cáo Markdown hoàn chỉnh kèm bảng và ảnh", str((target_output_dir / "data.md").resolve()))
    files_table.add_row("data.txt", "Văn bản thuần sạch sẽ từ phần Body", str((target_output_dir / "data.txt").resolve()))
    files_table.add_row("images_manifest.json", "Bảng kê chi tiết ảnh Body và URL gốc", str((target_output_dir / "images_manifest.json").resolve()))
    files_table.add_row("images/", f"Thư mục chứa {len(result.images)} file hình ảnh Body", str((target_output_dir / "images").resolve()))
    console.print(files_table)


def parse_args() -> argparse.Namespace:
    """Parses CLI command arguments."""
    parser = argparse.ArgumentParser(
        description="VinFast Web & Network Image Scraper Tool (Body only & Link folder separation)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        default="https://vinfastauto.com/vn_vi/herio-green",
        help="Đường link trang web VinFast cần cào"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./output",
        help="Thư mục gốc chứa các folder kết quả (tự động tạo thư mục con theo tên link)"
    )
    parser.add_argument(
        "--all-content",
        action="store_true",
        help="Cào toàn bộ trang (bao gồm cả Header/Footer) thay vì chỉ Body"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Chạy trình duyệt có giao diện (mặc định là headless)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60000,
        help="Thời gian timeout tải trang (milliseconds)"
    )
    parser.add_argument(
        "--min-image-size",
        type=int,
        default=500,
        help="Kích thước ảnh tối thiểu tính bằng bytes"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Chỉ cào văn bản, không lưu file ảnh"
    )
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="Lưu snapshot HTML gốc"
    )

    return parser.parse_args()


async def async_main():
    """Main asynchronous execution flow."""
    args = parse_args()
    display_banner()

    base_out = Path(args.output)
    config = ScraperConfig(
        url=args.url,
        base_output_dir=base_out,
        body_only=not args.all_content,
        headless=not args.headed,
        timeout_ms=args.timeout,
        min_image_size_bytes=args.min_image_size,
        download_images=not args.no_images,
        save_raw_html=args.save_html
    )

    target_dir = config.resolve_output_dir()
    slug = get_slug_from_url(args.url)
    console.print(f"[bold cyan]🎯 Link mục tiêu:[/bold cyan] [underline]{args.url}[/underline]")
    console.print(f"[bold cyan]📁 Thư mục lưu kết quả:[/bold cyan] [green bold]{target_dir.resolve()}[/green bold] (Tên folder: [yellow]{slug}[/yellow])\n")

    scraper = VinFastScraper(config)

    with Status("[bold cyan]Đang chuẩn bị và khởi chạy trình duyệt...", console=console) as status:
        def update_status(msg: str):
            status.update(f"[bold cyan]{msg}")

        try:
            result = await scraper.run(progress_callback=update_status)
        except Exception as e:
            console.print(f"\n[bold red]❌ Đã xảy ra lỗi trong quá trình cào dữ liệu:[/bold red] {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    display_summary(result, target_dir)


def main():
    """Entry point for script or CLI command."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
