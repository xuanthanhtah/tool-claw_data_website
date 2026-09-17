# ⚡ VinFast Web & Network Image Scraper Tool

Bộ công cụ Python chuyên nghiệp (Senior-level) phục vụ việc cào **dữ liệu văn bản phần Body**, trích xuất **bảng thông số kỹ thuật chi tiết** và **bắt trực tiếp các luồng hình ảnh Body từ Network Tab** (DevTools Network Stream) của trình duyệt trên website VinFast (`https://vinfastauto.com/vn_vi/herio-green` và các dòng xe khác).

---

## 🌟 Điểm nổi bật & Tính năng kỹ thuật mới

1. **Phân chia thư mục tự động theo tên Link:**
   - Mỗi link gửi vào sẽ được trích xuất slug và tự động tạo thư mục tương ứng:
     `output/<tên-dòng-xe>/` (Ví dụ: `output/herio-green/`, `output/vf-8/`).
   - Giữ cho toàn bộ dữ liệu cào từ nhiều link khác nhau được tổ chức khoa học, tách biệt hoàn toàn.

2. **Chỉ cào dữ liệu & hình ảnh phần Body (Body Only):**
   - Loại bỏ triệt để các thành phần rác: Header, Mega-menu điều hướng xe, Footer, BCT logo, Livechat widget, Cookie consent banner (OneTrust), Popup đăng ký nhận tư vấn.
   - **Lọc ảnh Body:** Đối chiếu trực tiếp với DOM body (`img`, `picture source`, `background-image`, `data-src`) để chỉ lưu các hình ảnh thực sự thuộc về nội dung sản phẩm/xe (ảnh xe, nội thất, ngoại thất, bảng màu, biểu đồ chi phí).

3. **Bắt trực tiếp hình ảnh từ Network Stream (Network Interceptor):**
   - Lắng nghe sự kiện `page.on("response")` từ Chrome DevTools Protocol.
   - Bắt trọn vẹn binary buffer của tất cả định dạng ảnh (`WebP`, `PNG`, `JPG`, `SVG`, `AVIF`) ngay khi trình duyệt nhận từ CDN.
   - Không cần gửi request lần 2, chống bị Cloudflare chặn và tối ưu tốc độ tối đa.
   - Chống trùng lặp dữ liệu bằng mã băm SHA-256 (Deduplication).

4. **Trích xuất thông số kỹ thuật chuẩn xác (Structured Specs):**
   - Trích xuất 20/20 mục thông số kỹ thuật (Kích thước, Chiều dài cơ sở, Khoảng sáng gầm, Công suất, Mô-men xoắn, Quãng đường NEDC, Pin, Sạc, Treo, Phanh, Mâm xe, Màn hình, Ghế lái...).
   - Trích xuất các section tính năng, so sánh chi phí nhiên liệu.

5. **Đầu ra đa dạng (Multi-format Export):**
   - `output/<slug>/images/`: Toàn bộ các file ảnh Body chất lượng cao.
   - `output/<slug>/images_manifest.json`: Bảng kê khai chi tiết từng ảnh (Tên file, URL gốc, MIME Type, Kích thước WxH, Dung lượng, SHA256).
   - `output/<slug>/data.json`: Dữ liệu có cấu trúc JSON đầy đủ.
   - `output/<slug>/data.md`: Báo cáo Markdown định dạng đẹp với bảng thông số và liên kết ảnh cục bộ.
   - `output/<slug>/data.txt`: Văn bản thuần sạch chỉ từ phần Body.

---

## 📁 Cấu trúc thư mục

```
tool/
├── output/
│   └── herio-green/            # Thư mục được đặt tên theo Link
│       ├── images/             # 21 hình ảnh Body chất lượng cao
│       ├── data.json           # Dữ liệu cấu trúc JSON
│       ├── data.md             # Báo cáo Markdown
│       ├── data.txt            # Văn bản Body thuần sạch
│       └── images_manifest.json# Manifest toàn bộ ảnh Body
├── .venv/                      # Môi trường ảo Python
├── vin_scraper/                # Core Package
│   ├── __init__.py             # Module exports
│   ├── config.py               # Cấu hình ScraperConfig & Slug Extractor
│   ├── models.py               # Data models (Pydantic)
│   ├── network_interceptor.py  # Bộ bắt luồng ảnh từ Network Tab & Filter Body
│   ├── dom_parser.py           # Parser bóc tách DOM Body & Specs
│   ├── engine.py               # Playwright Engine & Anti-bot Stealth
│   ├── storage.py              # Quản lý lưu file theo thư mục link
│   └── cli.py                  # Giao diện CLI Rich
├── main.py                     # Entry point chính
├── run.sh                      # Script chạy nhanh 1 click
├── requirements.txt            # Danh sách thư viện cần thiết
└── README.md                   # Tài liệu hướng dẫn
```

---

## 🚀 Hướng dẫn sử dụng

### 1. Cài đặt môi trường (Lần đầu)

```bash
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Chạy cào dữ liệu theo link

```bash
# Cào link Herio Green (tự động tạo folder output/herio-green)
python main.py --url "https://vinfastauto.com/vn_vi/herio-green"

# Hoặc dùng run.sh
./run.sh --url "https://vinfastauto.com/vn_vi/herio-green"
```

### 3. Cào các dòng xe khác

Chỉ cần truyền đường link tương ứng, tool sẽ tự động tạo thư mục riêng:

```bash
# Cào link xe khác (tự động tạo folder output/vf-8)
python main.py --url "https://vinfastauto.com/vn_vi/o-to/vf-8"
```

---

## 📊 Cấu trúc file đầu ra mẫu (`output/herio-green/`)

- [`output/herio-green/data.json`](file:///Users/xuanthanh/Documents/vin/tool/output/herio-green/data.json)
- [`output/herio-green/data.md`](file:///Users/xuanthanh/Documents/vin/tool/output/herio-green/data.md)
- [`output/herio-green/data.txt`](file:///Users/xuanthanh/Documents/vin/tool/output/herio-green/data.txt)
- [`output/herio-green/images_manifest.json`](file:///Users/xuanthanh/Documents/vin/tool/output/herio-green/images_manifest.json)
- [`output/herio-green/images/`](file:///Users/xuanthanh/Documents/vin/tool/output/herio-green/images/) (21 ảnh Body)
