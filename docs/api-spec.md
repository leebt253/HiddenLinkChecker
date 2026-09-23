# Hidden Link Checker - API Contract

## 1. Phạm vi

API MVP hỗ trợ Google OAuth, tạo một lần kiểm tra URL, lấy link thường và hidden
link từ DOM của URL đầu vào, lưu kết quả theo user và tải lịch sử. API không
fetch, mở hoặc điều hướng tới các link được phát hiện.

## 2. Endpoints

| Method | Path | Mục đích |
|---|---|---|
| `GET` | `/v1/auth/google/start` | Bắt đầu Google OAuth |
| `GET` | `/v1/auth/google/callback` | Hoàn tất Google OAuth |
| `POST` | `/v1/auth/logout` | Đăng xuất |
| `GET` | `/v1/me` | Lấy user hiện tại |
| `POST` | `/v1/link-checks` | Tạo link check bất đồng bộ |
| `GET` | `/v1/link-checks/{check_id}` | Lấy kết quả link check |
| `PATCH` | `/v1/link-checks/{check_id}` | Cập nhật metadata được phép |
| `DELETE` | `/v1/link-checks/{check_id}` | Xóa link check |
| `GET` | `/v1/me/link-checks` | Lấy lịch sử của user |

Mọi endpoint CRUD yêu cầu authenticated Google user. Frontend không truy cập
trực tiếp database.

## 3. Authentication

Google OAuth/OIDC là cơ chế đăng nhập duy nhất của MVP. Backend phải kiểm tra
`state`, `nonce`, redirect URI, issuer và chữ ký token theo cấu hình Google.
Google subject được map vào `users.google_subject` unique.

Backend phát hành session cookie server-side hoặc bearer token cho API. Cơ chế,
expiry, logout, revocation và CSRF policy phải được chốt trước triển khai.
Không lưu Google access token nếu API không gọi Google thay mặt user.

API không trả OAuth secret, token, stack trace hoặc thông tin nội bộ.

## 4. Tạo link check

`POST /v1/link-checks` yêu cầu:

```json
{
  "url": "https://example.com",
  "include_dom": true
}
```

Chỉ nhận scheme `http` và `https`. Response:

```json
{
  "check_id": "check_123",
  "status": "queued",
  "created_at": "2026-09-23T10:00:00Z"
}
```

Worker chỉ fetch/render URL đầu vào. Redirect của URL đầu vào phải được kiểm
tra SSRF sau mỗi bước. Worker không fetch, mở, redirect hoặc điều hướng tới URL
nào được phát hiện trong DOM.

## 5. Link check response

```json
{
  "check_id": "check_123",
  "status": "completed",
  "submitted_url": "https://example.com",
  "normalized_url": "https://example.com/",
  "final_url": "https://example.com/home",
  "dom_reference": "dom_123",
  "created_at": "2026-09-23T10:00:00Z",
  "completed_at": "2026-09-23T10:00:05Z",
  "links": [
    {
      "id": "link_result_123",
      "element_type": "image",
      "object_reference": "img_42",
      "source_url": "/promo",
      "actual_url": "https://example.com/promo",
      "is_hidden": true,
      "visible_text": "",
      "alt_text": "Promotion",
      "position": null
    }
  ]
}
```

`is_hidden = false` biểu thị link hiển thị trực tiếp; `is_hidden = true` biểu
thị link nằm sau image, background hoặc object không hiển thị như link trực tiếp.
MVP không có trường đánh giá rủi ro hoặc risk verdict.

## 6. Ownership và CRUD

- Server lấy `user_id` từ credential, không nhận `user_id` để gán ownership từ
  client.
- Mọi query phải lọc theo authenticated `user_id` trước khi đọc/cập nhật/xóa.
- `PATCH` chỉ cập nhật metadata được cho phép, không sửa `submitted_url`,
  `normalized_url`, `final_url` hoặc link results.
- `DELETE` xử lý `LinkCheck`, DOM reference và link results liên quan theo
  retention policy.
- API không tiết lộ việc một `check_id` của user khác có tồn tại hay không.

## 7. URL và dữ liệu nhạy cảm

- Chặn localhost, loopback, private IP, link-local, multicast và cloud metadata.
- Áp dụng timeout, response-size, CPU, memory, concurrency và redirect limits.
- Không gửi cookie, authorization header hoặc application secret tới URL đầu vào.
- Không log OAuth credential, raw query string nhạy cảm hoặc toàn bộ DOM nếu
  không cần thiết.

## 8. PostgreSQL persistence

PostgreSQL là database production chính với các bảng tối thiểu `users`,
`link_checks` và `link_results`. Dùng foreign key, transaction và migration có
version.

Index tối thiểu:

- unique `users.google_subject`;
- `link_checks(user_id, created_at)`;
- `link_results(link_check_id)`;
- `link_results(is_hidden)` khi dashboard cần filter.
