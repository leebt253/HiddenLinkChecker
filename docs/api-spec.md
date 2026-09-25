# Hidden Link Checker - API Contract

## 1. Phạm vi

API MVP hỗ trợ Google OAuth, kiểm tra một URL đồng bộ, lấy hidden link từ DOM
của URL đầu vào ngay trong response và tải lịch sử URL đã kiểm tra. API không
fetch, mở hoặc điều hướng tới các link được phát hiện, và không lưu lại chi
tiết hidden link sau khi đã phản hồi.

## 2. Endpoints

| Method | Path | Mục đích |
|---|---|---|
| `GET` | `/v1/auth/google/start` | Bắt đầu Google OAuth |
| `GET` | `/v1/auth/google/callback` | Hoàn tất Google OAuth |
| `POST` | `/v1/auth/logout` | Đăng xuất |
| `GET` | `/v1/me` | Lấy user hiện tại |
| `POST` | `/v1/link-checks` | Kiểm tra một URL và trả kết quả đồng bộ |
| `DELETE` | `/v1/me/link-checks/{check_id}` | Xóa một mục lịch sử |
| `GET` | `/v1/me/link-checks` | Lấy lịch sử URL đã kiểm tra của user |

Mọi endpoint yêu cầu authenticated Google user, trừ hai endpoint OAuth. Frontend
không truy cập trực tiếp database.

## 3. Authentication

Google OAuth/OIDC là cơ chế đăng nhập duy nhất của MVP. Backend phải kiểm tra
`state`, `nonce`, redirect URI, issuer và chữ ký token theo cấu hình Google.
Google subject được map vào `users.google_subject` unique.

Backend phát hành session cookie server-side hoặc bearer token cho API. Cơ chế,
expiry, logout, revocation và CSRF policy phải được chốt trước triển khai.
Không lưu Google access token nếu API không gọi Google thay mặt user.

API không trả OAuth secret, token, stack trace hoặc thông tin nội bộ.

## 4. Kiểm tra một URL

`POST /v1/link-checks` yêu cầu:

```json
{
  "url": "https://example.com"
}
```

Chỉ nhận scheme `http` và `https`. Request được xử lý đồng bộ: API fetch/render
URL đầu vào, trích xuất hidden link và trả toàn bộ kết quả trong cùng response
(xem mục 5). Redirect của URL đầu vào phải được kiểm tra SSRF sau mỗi bước. API
không fetch, mở, redirect hoặc điều hướng tới URL nào được phát hiện trong DOM.

Sau khi phản hồi, API lưu một bản ghi lịch sử tối giản (`id`, `url`,
`checked_at`) cho user; hidden link phát hiện được không được lưu lại.

## 5. Link check response

```json
{
  "check_id": "check_123",
  "status": "completed",
  "submitted_url": "https://example.com",
  "normalized_url": "https://example.com/",
  "final_url": "https://example.com/home",
  "links": [
    {
      "element_type": "image",
      "object_reference": "img_42",
      "source_url": "/promo",
      "actual_url": "https://example.com/promo",
      "visibility": "indirect",
      "visible_text": "",
      "alt_text": "Promotion",
      "position": null
    }
  ]
}
```

Mọi kết quả trong response là hidden link. `visibility = direct` biểu thị link
hiển thị trực tiếp; `visibility = indirect` biểu thị link nằm sau image,
background hoặc object không hiển thị như link trực tiếp. `links` không có `id`
ổn định vì không được lưu trữ. MVP không có trường đánh giá rủi ro hoặc risk
verdict.

## 6. Ownership và lịch sử

- Server lấy `user_id` từ credential, không nhận `user_id` để gán ownership từ
  client.
- Mọi query lịch sử phải lọc theo authenticated `user_id` trước khi đọc/xóa.
- `DELETE /v1/me/link-checks/{check_id}` chỉ xóa bản ghi lịch sử (`url`,
  `checked_at`) của chính user; không có dữ liệu con nào khác cần xử lý vì
  hidden link không được lưu trữ.
- API không tiết lộ việc một `check_id` của user khác có tồn tại hay không.

## 7. URL và dữ liệu nhạy cảm

- Chặn localhost, loopback, private IP, link-local, multicast và cloud metadata.
- Áp dụng timeout, response-size, CPU, memory, concurrency và redirect limits.
- Không gửi cookie, authorization header hoặc application secret tới URL đầu vào.
- Không log OAuth credential, raw query string nhạy cảm hoặc toàn bộ DOM nếu
  không cần thiết.

## 8. PostgreSQL persistence

PostgreSQL là database production chính với các bảng tối thiểu `users` và
`url_checks`. Dùng foreign key, transaction và migration có version.

Index tối thiểu:

- unique `users.google_subject`;
- `url_checks(user_id, checked_at)`.
