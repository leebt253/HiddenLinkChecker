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

Backend phát hành opaque server-side session cookie, đặt `HttpOnly` và
`SameSite=Lax`; `Secure` phụ thuộc `HIDDEN_LINK_CHECKER_SESSION_COOKIE_SECURE`.
Session token chỉ được lưu dưới dạng SHA-256 hash, mặc định hết hạn sau 7 ngày
và bị revoke khi logout. OIDC `state`/`nonce` cũng được lưu dạng hash trong
`oauth_login_transactions`. Không lưu Google access token.
Cookie dùng `SameSite=Lax`; ứng dụng chưa có CSRF token riêng. Cần rà lại origin
topology và CSRF controls khi cấu hình production.

Google OAuth credentials là cấu hình runtime tùy chọn trong code: nếu thiếu,
API vẫn có thể khởi động nhưng endpoint đăng nhập trả `503`. Deployment production
phải cung cấp đủ `HIDDEN_LINK_CHECKER_GOOGLE_CLIENT_ID`,
`HIDDEN_LINK_CHECKER_GOOGLE_CLIENT_SECRET` và
`HIDDEN_LINK_CHECKER_GOOGLE_REDIRECT_URI`.

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

Sau khi xử lý request và trước khi gửi response, API lưu một bản ghi lịch sử tối
giản (`id`, `user_id`, `url`, `checked_at`) cho user, kể cả khi kết quả là
`partial`/`failed` hoặc URL bị validation từ chối. Hidden link, DOM và scan status
không được lưu lại.

## 5. Link check response

```json
{
  "check_id": "check_123",
  "status": "completed",
  "submitted_url": "https://example.com",
  "normalized_url": "https://example.com/",
  "final_url": "https://example.com/home",
  "checked_at": "2026-09-25T10:00:00Z",
  "dom_excerpt": "<html>…</html>",
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

`status` là `completed`, `partial` hoặc `failed`. Lỗi URL/fetch/SSRF có kiểm soát
được trả trong cùng response với HTTP 200 và trường `error_code`/`limitations`;
request không hợp lệ ở mức JSON/schema vẫn dùng HTTP 422.
`dom_excerpt` được giới hạn độ dài, lấy sau khi Chromium render JavaScript, hiển
thị như văn bản đã escape trên dashboard và chỉ tồn tại trong response. Browser
chặn toàn bộ request do trang tạo ra (image, stylesheet, script ngoài, XHR/fetch,
iframe, navigation); chỉ HTTP fetcher truy cập URL đầu vào và redirect đã xác minh.
Bảng history không chứa DOM hoặc scan state.

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
- Chặn địa chỉ reserved/non-global; pin kết nối TCP vào IP đã xác minh, giữ
  hostname cho TLS và xác minh/pin lại sau từng redirect để ngăn DNS rebinding.
- Code áp dụng timeout, response-size, concurrency và redirect limits qua
  `HIDDEN_LINK_CHECKER_SCAN_*`. Hard CPU/RAM limit cho Chromium chưa được thực
  hiện trong ứng dụng; deployment phải bổ sung process/container limits trước
  khi tiêu chí tài nguyên này được xem là đáp ứng.
- Không gửi cookie, authorization header hoặc application secret tới URL đầu vào.
- Không log OAuth credential, raw query string nhạy cảm hoặc toàn bộ DOM nếu
  không cần thiết.

## 8. PostgreSQL persistence

PostgreSQL là database production chính. Production bắt buộc cấu hình
`HIDDEN_LINK_CHECKER_DATABASE_URL`; API không fallback sang in-memory history.
Migration có version là `migrations/0001_initial_schema.sql` rồi
`migrations/0002_auth_sessions.sql`. Hiện chưa có migration runner hoặc ledger
tự động; release phải áp dụng hai file đúng thứ tự. Web module chỉ gọi API và
không mở kết nối database.

Index tối thiểu:

- unique `users.google_subject`;
- `url_checks(user_id, checked_at)`.
