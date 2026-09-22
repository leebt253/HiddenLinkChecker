# Hidden Link Checker

Công cụ kiểm tra link trên web dựa trên rule, giúp phát hiện các URL ẩn phía sau text, hình ảnh và CSS background.

Hidden Link Checker giúp người dùng đối chiếu nội dung đang hiển thị trên một trang web với đích thực tế được nhúng bên dưới. Mỗi URL được chuẩn hóa, phân loại theo loại phần tử nguồn và đánh giá bằng các rule có thể giải thích với mức `safe`, `warning` hoặc `critical`.

> **Trạng thái dự án:** skeleton MVP đang được phát triển. Core trích xuất link và đánh giá rule đã có; dashboard có xác thực, browser worker và lưu database sẽ được triển khai ở các bước tiếp theo.

## Vì sao xây dựng dự án này?

Một link có thể trông vô hại nhưng lại dẫn tới một địa chỉ không như người dùng kỳ vọng. Việc kiểm tra càng khó hơn khi URL nằm trong hình ảnh, CSS background inline hoặc một phần tử trực quan không giống hyperlink thông thường.

Luồng sản phẩm dự kiến:

```text
Đăng ký / đăng nhập
	|
	v
Gửi URL của trang cần kiểm tra
	|
	v
Render an toàn -> phát hiện URL ẩn -> áp dụng rule
	|
	v
Dashboard snapshot + grid finding + lịch sử scan
```

Dự án hướng tới việc triage có thể giải thích. Kết quả `safe` chỉ có nghĩa là không có rule nào đã cấu hình khớp trong phạm vi scan; đây không phải cam kết website an toàn.

## Tính năng hiện có

Python core hiện tại có thể:

- Trích xuất URL từ:
  - text link như `<a href="...">`;
  - hình ảnh thông qua `src` và `srcset`;
  - CSS inline như `background-image: url(...)`.
- Resolve URL tương đối dựa trên URL của trang được scan.
- Giữ lại loại nguồn là `text`, `image` hoặc `background`.
- Áp dụng rule có thể cấu hình và trả về `matched_rules`.
- Đánh giá các keyword liên quan đến cờ bạc như `casino`, `poker`, `slot`, `betting` và `gambling` ở mức `critical`.
- Đánh giá destination ngoài origin của trang ở mức `warning`.
- Có unit test và integration test cho hành vi core.

## Phạm vi MVP dự kiến

- Đăng ký, đăng nhập, đăng xuất và lịch sử scan theo từng user.
- Browser worker cô lập để đọc DOM đã render, computed style, nội dung do JavaScript tạo và ảnh chụp trang.
- Bounding box liên kết mỗi finding với vị trí tương ứng trên snapshot.
- Dashboard có bộ đếm severity, bộ lọc, highlight trên snapshot và grid finding.
- Lưu user, scan, finding, severity, matched rule và metadata retention vào database.
- API cho authentication, tạo scan, lấy kết quả, findings, lịch sử và xóa dữ liệu.
- SSRF protection, kiểm tra lại redirect, giới hạn tài nguyên, sandbox và rate limit.

## Mô hình severity

| Mức độ | Rule ban đầu | Ý nghĩa |
|---|---|---|
| `critical` | Keyword gambling/casino/betting xuất hiện trong URL hoặc ngữ cảnh hiển thị của finding | Tín hiệu ưu tiên cao, cần kiểm tra |
| `warning` | Destination ngoài domain hoặc khớp một tín hiệu cần xem xét khác | Cần kiểm tra thủ công |
| `safe` | Không có rule nào đã cấu hình khớp | Chưa phát hiện tín hiệu trong phạm vi scan hiện tại |

Mọi kết quả khác `safe` nên hiển thị tên rule và evidence dẫn tới việc phân loại. Rule chỉ là tín hiệu hỗ trợ review, không phải kết luận tuyệt đối về malware hoặc phishing.

## Cấu trúc repository

```text
.
├── docs/
│   ├── br-analysis.md             # Business requirements và acceptance criteria
│   ├── context-engineering.md     # Context pack cho AI/team
│   ├── idea.md                    # Ý tưởng sản phẩm và phạm vi MVP
│   └── project-scaffold.md        # Ghi chú scaffold của Lab 1.1
├── src/
│   └── hidden_link_checker/
│       ├── models.py              # Model Finding và severity
│       ├── rules.py               # Rule evaluator có thể giải thích
│       └── scanner.py             # Trích xuất URL từ HTML/CSS
├── tests/
│   ├── integration/
│   └── unit/
├── pyproject.toml
└── CONTRIBUTING.md
```

## Yêu cầu môi trường

- Python 3.11 trở lên
- `pip`

Core trích xuất hiện chỉ sử dụng standard library của Python. Bộ test cần thêm `pytest`.

## Bắt đầu nhanh

### 1. Tạo môi trường ảo

```bash
python -m venv .venv
```

Kích hoạt trên Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Kích hoạt trên macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Cài đặt project

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
```

### 3. Chạy test

```bash
python -m pytest -q
```

### 4. Thử core trích xuất

```python
from hidden_link_checker import extract_findings

html = """
<a href="/offers/casino">Claim reward</a>
<img src="/banner.png" alt="Welcome banner">
<div style="background-image: url('/promo.png')"></div>
"""

findings = extract_findings(html, "https://example.test/home")

for finding in findings:
    print(finding.element_type, finding.normalized_url, finding.severity)
```

Finding đầu tiên được đánh giá là `critical` vì destination chứa keyword cờ bạc đã cấu hình. Hình ảnh và background tạo ra các finding riêng để sau này hiển thị thành card trên dashboard.

## Ranh giới bảo mật

Service dự kiến nhận URL do user cung cấp và render các trang bên thứ ba. Đây là ranh giới bảo mật quan trọng liên quan đến SSRF và cô lập browser.

Trước khi expose việc scan qua API hoặc worker, implementation phải:

- chỉ cho phép `http` và `https`;
- từ chối localhost, loopback, private IP, link-local, multicast và cloud metadata address;
- resolve và kiểm tra destination sau mỗi redirect;
- giới hạn thời gian kết nối, thời gian browser, kích thước response, CPU, memory và concurrency;
- không forward cookie, authorization header hoặc application secret;
- chạy browser trong sandbox cô lập, không truy cập trực tiếp database;
- kiểm tra authentication và ownership cho scan, finding và snapshot;
- mặc định không ghi query string nhạy cảm hoặc nội dung trang vào log.

Xem [SECURITY.md](SECURITY.md) để biết chính sách báo cáo vấn đề bảo mật.

## Phát triển

Dùng branch riêng và gắn mỗi thay đổi với một requirement hoặc issue. Trước khi mở pull request:

```bash
python -m pytest -q
```

Pull request được kiểm tra bằng GitHub Actions và cần được review. Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết quy trình branch, review và các quy tắc riêng của dự án.

## Tài liệu

- [Ý tưởng sản phẩm và phạm vi MVP](docs/idea.md)
- [Business requirements và acceptance criteria](docs/br-analysis.md)
- [Context engineering pack](docs/context-engineering.md)
- [Project scaffold](docs/project-scaffold.md)

## Lộ trình

1. Mở rộng fixture cho text, image, background, URL tương đối và HTML không hợp lệ.
2. Thêm browser worker an toàn với snapshot đã render và bounding box của element.
3. Tách riêng extractor, rule evaluator, persistence và API contract.
4. Thêm authentication, lịch sử scan trong database và ownership enforcement.
5. Xây dashboard grid, bộ lọc, bộ đếm và highlight trên snapshot.
6. Bổ sung security control production, observability, retention và rate limit.

## License

Dự án hiện chưa chọn license. Cho đến khi có license chính thức, mọi quyền đều thuộc về chủ sở hữu bản quyền.
