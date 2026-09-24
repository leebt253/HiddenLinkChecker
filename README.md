# Hidden Link Checker

Ứng dụng web giúp người dùng nhập một URL và tìm các hidden link trong DOM của
trang đó. Trong domain này, hidden link là mọi URL được phát hiện; link hiển thị
trực tiếp chỉ là một dạng hidden link có `visibility = direct`.

## Mục lục

- [Giới thiệu](#giới-thiệu)
- [Tính năng](#tính-năng)
- [Kiến trúc và công nghệ](#kiến-trúc-và-công-nghệ)
- [Cài đặt](#cài-đặt)
- [Tax Calculation](#tax-calculation)
- [Sử dụng](#sử-dụng)
- [Bảo mật](#bảo-mật)
- [Cấu trúc repository](#cấu-trúc-repository)
- [Đóng góp](#đóng-góp)
- [Giấy phép](#giấy-phép)

## Giới thiệu

Hidden Link Checker lấy DOM của URL do người dùng cung cấp, trích xuất các URL
được tham chiếu bởi text, hình ảnh và CSS background, sau đó hiển thị kết quả
trên dashboard. Mỗi kết quả cho biết object/thuộc tính DOM, URL nguồn, URL thực
tế sau khi resolve và visibility của hidden link.

Ứng dụng không tự động mở, fetch hoặc điều hướng tới các link được phát hiện.

Luồng sử dụng chính:

```text
Đăng nhập bằng Google
				|
				v
Nhập URL trên dashboard
				|
				v
API lấy DOM của URL đầu vào
				|
				v
Hiển thị và lưu hidden link theo user
```

## Tính năng

- Đăng nhập và đăng xuất bằng Google OAuth/OIDC.
- Nhập một URL trên dashboard để kiểm tra.
- Tìm hidden link từ text, image, `srcset`, CSS background hoặc object liên quan
	trong DOM.
- Phân biệt visibility của hidden link: `direct` nếu hiển thị trực tiếp và
	`indirect` nếu nằm sau image, background hoặc object khác.
- Resolve URL tương đối theo URL cuối cùng của trang đầu vào.
- Hiển thị URL nguồn, URL thực tế, loại object và thông tin element.
- Lưu kết quả theo user và tải lại lịch sử kiểm tra.
- API-first: authentication, tạo, đọc, cập nhật và xóa dữ liệu đều đi qua API.
- PostgreSQL làm database chính cho user, link check và link result.

## Kiến trúc và công nghệ

- **Backend:** Python.
- **Application structure:** MVC, với extractor/service nằm giữa controller và
	persistence khi use case cần điều phối.
- **Authentication:** Google OAuth/OIDC.
- **Database:** PostgreSQL với migration, foreign key, transaction và index cho
	ownership/lịch sử.
- **Processing:** browser worker cô lập chỉ truy cập URL đầu vào.
- **Frontend:** dashboard gọi API; không truy cập database trực tiếp.

## Cài đặt

### Yêu cầu

- Python 3.11 trở lên.
- `pip`.
- PostgreSQL khi chạy các thành phần persistence/web application.

### Thiết lập môi trường Python

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

Cài đặt project và công cụ test:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Tax Calculation

Build và cài thư viện tính thuế sibling project trước khi chạy module tích hợp:

```powershell
Push-Location ..\TaxCalculationLibrary
python -m pip install -e ".[test]"
Pop-Location
```

### Chạy test thư viện

Từ thư mục `HiddenLinkChecker`, chạy test của thư viện dùng chung:

```powershell
Push-Location ..\TaxCalculationLibrary
..\HiddenLinkChecker\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

Kết quả mong đợi hiện tại là `10 passed`.

Chạy test adapter JSON trong HiddenLinkChecker:

```powershell
.venv\Scripts\python.exe -m pytest -q tests\unit\api\test_tax_calculation.py
```

Chạy toàn bộ test của HiddenLinkChecker:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

### Input và output mẫu

Module `hidden_link_checker_api.services.tax_calculation` cung cấp
`calculate_tax(data, metadata)` và `calculate_tax_file(input_path, output_path)`. Mười input JSON mẫu
với tối thiểu 10 dòng mỗi file nằm trong [examples/tax_inputs](examples/tax_inputs/).
Output mẫu tương ứng nằm trong [examples/tax_outputs](examples/tax_outputs/).

Chạy một input JSON thực tế từ PowerShell:

```powershell
.venv\Scripts\python.exe scripts\run_tax_calculation.py `
	examples\tax_inputs\retail_order.json `
	examples\tax_outputs\retail_order.result.json
```

Kết quả được ghi vào file output JSON chỉ định. Có thể gọi trực tiếp trong Python:

```python
from hidden_link_checker_api.services.tax_calculation import calculate_tax_file

calculate_tax_file("input.json", "output.json")
```

Có thể chạy bằng CMD bằng file [scripts/run_tax_calculation.cmd](scripts/run_tax_calculation.cmd):

```cmd
scripts\run_tax_calculation.cmd
```

Khi được hỏi, nhập đường dẫn file input JSON, ví dụ:

```text
examples\tax_inputs\hotel_booking.json
```

Output sẽ tự động được tạo cùng thư mục với tên:

```text
hotel_booking.result.json
```

Output được tạo cùng thư mục với input và có hậu tố `.result.json`.

Tax Calculation không phụ thuộc Google OAuth, PostgreSQL hoặc web server.

## Sử dụng

### Chạy test

```bash
python -m pytest -q
```

### Chạy hai module độc lập

Để thử Google OAuth local mà chưa có PostgreSQL, mở terminal chạy API với
in-memory authentication:

```powershell
$env:HIDDEN_LINK_CHECKER_DATABASE_URL = ""
.venv\Scripts\python.exe -m uvicorn hidden_link_checker_api.main:app --host 127.0.0.1 --port 8000
```

Trong terminal khác, chạy Web module:

Khởi động API trước:

```bash
python -m uvicorn hidden_link_checker_api.main:app --host 127.0.0.1 --port 8000
```

Sau đó, trong terminal khác, khởi động Web module:

```bash
python -m uvicorn hidden_link_checker_web.main:app --host 127.0.0.1 --port 8001
```

Web module chỉ gọi HTTP API qua cấu hình runtime; không truy cập database hoặc
import repository của API. Khi được cấu hình database, API dùng PostgreSQL cho
user, transaction OIDC và session. Cookie chỉ chứa opaque session token; API
chỉ lưu hash token, không lưu Google access token hoặc refresh token.

Mở `http://127.0.0.1:8001/login`, chọn **Đăng nhập với Google**, rồi hoàn tất
Google sign-in. Callback sẽ tạo/cập nhật user theo `google_subject`, thiết lập
server-side session và chuyển tới `http://127.0.0.1:8001/welcome` để hiển thị
tên profile. API cung cấp `GET /v1/me` và `POST /v1/auth/logout` cho web module.

### Thử core trích xuất

```python
from hidden_link_checker import extract_findings

html = """
<a href="/about">About</a>
<img src="/banner.png" alt="Banner">
<div style="background-image: url('/promo.png')"></div>
"""

links = extract_findings(html, "https://example.test/home")

for link in links:
	print(link.element_type, link.normalized_url, link.visibility)
```

Kết quả cho biết loại object, URL nguồn, URL sau khi resolve và `visibility`.

## Bảo mật

Phần Tax Calculation không yêu cầu credential. Đối với phần Hidden Link Checker,
các giá trị OAuth, database URL và session secret phải được cấp qua secret
manager hoặc biến môi trường ở runtime. Không đưa client secret, mật khẩu,
database URL thật hoặc file cấu hình local vào repository, README, log hay
output JSON.

URL người dùng nhập là một ranh giới bảo mật quan trọng. Implementation phải:

- Chỉ cho phép scheme `http` và `https`.
- Chặn localhost, loopback, private IP, link-local, multicast và cloud metadata.
- Kiểm tra DNS/IP trước khi truy cập và sau mỗi redirect của URL đầu vào.
- Không fetch, mở hoặc điều hướng tới link được phát hiện trong DOM.
- Áp dụng timeout, giới hạn response size, CPU, memory, concurrency và redirect.
- Không gửi cookie, authorization header hoặc application secret tới URL đầu vào.
- Chạy browser worker trong sandbox cô lập.
- Kiểm tra Google authentication và ownership cho mọi thao tác dữ liệu.
- Không ghi OAuth credential, query string nhạy cảm hoặc DOM không cần thiết vào log.

## Cấu trúc repository

```text
.
├── docs/
│   ├── api-spec.md
│   ├── coding-rules.md
│   ├── database-guide.md
│   ├── domain-model.md
│   ├── recommendation.md
│   └── specification.md
├── src/
│   ├── hidden_link_checker_api/
│   │   ├── controllers/      # HTTP API
│   │   ├── domain/           # entities và lifecycle
│   │   ├── repositories/     # persistence ports/adapters
│   │   ├── scanner/          # URL policy, SSRF và extractor
│   │   ├── services/         # use cases
│   │   └── workers/          # queue/worker ports
│   ├── hidden_link_checker_web/
│   │   ├── controllers/      # dashboard routes
│   │   ├── services/         # HTTP API client
│   │   └── views/            # HTML rendering
│   └── shared_contracts/     # versioned API DTOs
├── tests/
│   ├── integration/
│   └── unit/
├── pyproject.toml
├── CONTRIBUTING.md
└── README.md
```

## Đóng góp

Đọc [CONTRIBUTING.md](CONTRIBUTING.md) trước khi tạo branch hoặc pull request.
Mọi thay đổi nên cập nhật test và tài liệu liên quan, đồng thời giữ đúng phạm
vi link extraction, ownership và security policy của MVP.

## Tài liệu tham khảo

- [Product recommendation](docs/recommendation.md)
- [Product specification](docs/specification.md)
- [API contract](docs/api-spec.md)
- [Domain model](docs/domain-model.md)
- [PostgreSQL database guide](docs/database-guide.md)
- [Database connection configuration](docs/database-connection.md)
- [Coding rules](docs/coding-rules.md)

## Giấy phép

Dự án hiện chưa chọn giấy phép. Cho đến khi có giấy phép chính thức, mọi quyền
đều thuộc về chủ sở hữu bản quyền.
