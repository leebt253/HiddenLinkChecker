# Hidden Link Checker

Ứng dụng web giúp người dùng nhập một URL và tìm các hidden link trong DOM của
trang đó. Trong domain này, hidden link là mọi URL được phát hiện; link hiển thị
trực tiếp chỉ là một dạng hidden link có `visibility = direct`.

## Mục lục

- [Giới thiệu](#giới-thiệu)
- [Tính năng](#tính-năng)
- [Kiến trúc và công nghệ](#kiến-trúc-và-công-nghệ)
- [Cài đặt](#cài-đặt)
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
Hiển thị hidden link trong response của lần kiểm tra; chỉ lưu URL history theo user
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
- Lưu URL và thời điểm kiểm tra theo user để tải lại lịch sử.
- API-first: authentication, kiểm tra URL, đọc và xóa URL history đều đi qua API.
- PostgreSQL làm database chính cho user, auth session và URL history.
- Chromium render JavaScript trong browser context tách biệt cho từng lần kiểm tra.
- Mọi request mạng do trang tạo ra trong lúc render đều bị chặn; HTML fetcher chỉ
	truy cập URL đầu vào và redirect được kiểm tra SSRF.

## Kiến trúc và công nghệ

- **Backend:** Python.
- **Application structure:** MVC, với extractor/service nằm giữa controller và
	persistence khi use case cần điều phối.
- **Authentication:** Google OAuth/OIDC.
- **Database:** PostgreSQL với migration, foreign key, transaction và index cho
	ownership/lịch sử.
- **Processing:** HTTP fetcher kiểm tra SSRF lấy URL đầu vào; Chromium chạy JavaScript
	trong context sạch, chặn mọi request mạng do trang tạo ra.
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
python -m playwright install chromium
```

Ứng dụng tự dùng Edge/Chrome có sẵn trên Windows hoặc Chromium do Playwright cài.
Có thể đặt `HIDDEN_LINK_CHECKER_BROWSER_EXECUTABLE_PATH` để chỉ định executable trong
môi trường triển khai.

Sao chép `.env.example` thành `.env` để chạy local. Khi triển khai, đặt
`HIDDEN_LINK_CHECKER_ENVIRONMENT=production` và cấu hình PostgreSQL cùng Google
OAuth credentials; không commit tệp `.env`. Production sẽ từ chối khởi động nếu
thiếu `HIDDEN_LINK_CHECKER_DATABASE_URL`. In-memory URL history chỉ dùng khi
`HIDDEN_LINK_CHECKER_ENVIRONMENT` là `development` hoặc `test`.

Production cần cung cấp `HIDDEN_LINK_CHECKER_DATABASE_URL`, Google OAuth client
ID/secret/redirect URI, `HIDDEN_LINK_CHECKER_WEB_BASE_URL` và
`HIDDEN_LINK_CHECKER_API_BASE_URL`. Bật
`HIDDEN_LINK_CHECKER_SESSION_COOKIE_SECURE=true` khi dùng HTTPS. Cấu hình giới hạn
scan qua `HIDDEN_LINK_CHECKER_SCAN_TIMEOUT_SECONDS`,
`HIDDEN_LINK_CHECKER_SCAN_MAX_REDIRECTS`,
`HIDDEN_LINK_CHECKER_SCAN_MAX_RESPONSE_BYTES` và
`HIDDEN_LINK_CHECKER_SCAN_MAX_CONCURRENT` (mặc định lần lượt là 10 giây, 5,
2 MiB và 4). Google OAuth settings chưa được kiểm tra bắt buộc lúc khởi động;
thiếu cấu hình sẽ làm endpoint đăng nhập trả `503`.

Ứng dụng áp dụng timeout, redirect, kích thước response và concurrency limits.
Mã hiện chưa đặt hard limit CPU/RAM cho Chromium; cần cấu hình giới hạn process
hoặc container trước khi coi phần này là được kiểm soát trong production.

### Cấu hình Google OAuth

1. Tạo OAuth 2.0 Client ID loại Web application trong Google Cloud Console.
2. Đăng ký Authorized redirect URI đúng bằng
	`HIDDEN_LINK_CHECKER_GOOGLE_REDIRECT_URI`, mặc định là
	`http://127.0.0.1:8000/v1/auth/google/callback`.
3. Đặt `HIDDEN_LINK_CHECKER_GOOGLE_CLIENT_ID`,
   `HIDDEN_LINK_CHECKER_GOOGLE_CLIENT_SECRET`,
   `HIDDEN_LINK_CHECKER_DATABASE_URL` và `HIDDEN_LINK_CHECKER_WEB_BASE_URL`
   trong `.env`. `HIDDEN_LINK_CHECKER_DATABASE_URL` phải theo dạng
   `postgresql://user:password@localhost:5432/hidden_link_checker` vì ứng dụng
   dùng `psycopg` trực tiếp.
4. Khi deploy HTTPS, đặt `HIDDEN_LINK_CHECKER_SESSION_COOKIE_SECURE=true`.

Trong PowerShell, cung cấp URL cho lệnh `psql` (psql không đọc `.env`), rồi áp
dụng schema nền tảng trước migration session/OIDC:

```powershell
$env:HIDDEN_LINK_CHECKER_DATABASE_URL = "postgresql://user:password@localhost:5432/hidden_link_checker"
psql $env:HIDDEN_LINK_CHECKER_DATABASE_URL -v ON_ERROR_STOP=1 -f scripts/initial_schema.sql
psql $env:HIDDEN_LINK_CHECKER_DATABASE_URL -v ON_ERROR_STOP=1 -f migrations/0002_auth_sessions.sql
```

## Sử dụng

### Chạy test

```bash
python -m pytest -q
```

### Chạy hai module độc lập

Sau khi áp dụng migration theo hướng dẫn ở phần cấu hình, trong terminal thứ nhất chạy API:

```bash
python -m uvicorn hidden_link_checker_api.main:app --host 127.0.0.1 --port 8000
```

Trong terminal thứ hai, khởi động Web module:

```bash
python -m uvicorn hidden_link_checker_web.main:app --host 127.0.0.1 --port 8001
```

Web module chỉ gọi HTTP API qua `HIDDEN_LINK_CHECKER_API_BASE_URL`; không truy
cập database hoặc import repository của API. Khi có
`HIDDEN_LINK_CHECKER_DATABASE_URL`, API dùng PostgreSQL cho user, transaction
OIDC và session. Cookie chỉ chứa opaque session token; API chỉ lưu hash token,
không lưu Google access token hoặc refresh token.

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

URL người dùng nhập là một ranh giới bảo mật quan trọng. Implementation phải:

- Chỉ cho phép scheme `http` và `https`.
- Chặn localhost, loopback, private IP, link-local, multicast và cloud metadata.
- Kiểm tra DNS/IP trước khi truy cập và sau mỗi redirect của URL đầu vào.
- Kết nối TCP được pin vào một IP công khai trong đúng tập IP đã xác minh để
  tránh DNS rebinding; từ chối địa chỉ reserved và metadata.
- Không fetch, mở hoặc điều hướng tới link được phát hiện trong DOM.
- Áp dụng timeout, giới hạn response size, concurrency và redirect; hard limit
  CPU/RAM cần được cung cấp ở cấp process/container khi triển khai.
- Không gửi cookie, authorization header hoặc application secret tới URL đầu vào.
- JavaScript chạy trong browser; mọi network request của trang bị chặn. Trang phụ thuộc
	tài nguyên ngoài để render đầy đủ trả về trạng thái `partial`.
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
│   │   └── workers/          # bounded synchronous page fetcher
│   ├── hidden_link_checker_web/
│   │   ├── controllers/      # dashboard routes
│   │   ├── services/         # HTTP API client
│   │   └── views/            # HTML rendering
│   └── shared_contracts/     # versioned API DTOs
├── tests/
│   ├── integration/
│   └── unit/
├── .env.example
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
- [FR/AC traceability and evidence](docs/traceability.md)
- [API contract](docs/api-spec.md)
- [Domain model](docs/domain-model.md)
- [PostgreSQL database and production configuration](docs/database-guide.md)
- [Coding rules](docs/coding-rules.md)

## Giấy phép

Dự án hiện chưa chọn giấy phép. Cho đến khi có giấy phép chính thức, mọi quyền
đều thuộc về chủ sở hữu bản quyền.
