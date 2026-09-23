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
python -m pip install -e .
python -m pip install pytest
```

Google OAuth credentials và cấu hình PostgreSQL sẽ được cung cấp qua biến môi
trường khi web application được triển khai.

## Sử dụng

### Chạy test

```bash
python -m pytest -q
```

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
│   └── hidden_link_checker/
│       ├── models.py
│       └── scanner.py
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
- [Coding rules](docs/coding-rules.md)

## Giấy phép

Dự án hiện chưa chọn giấy phép. Cho đến khi có giấy phép chính thức, mọi quyền
đều thuộc về chủ sở hữu bản quyền.
