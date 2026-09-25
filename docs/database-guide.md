# Hidden Link Checker - PostgreSQL Database Guide

## 1. Mục đích

Tài liệu này mô tả schema PostgreSQL hiện dùng cho MVP Hidden Link Checker.
Database lưu account/session/OIDC transaction và lịch sử URL tối giản theo quan hệ:

```text
User -> UrlCheck
```

MVP hỗ trợ:

- Đăng nhập bằng Google OAuth/OIDC.
- Kiểm tra một URL đầu vào và trả kết quả **đồng bộ** trong response (lấy DOM,
  phát hiện hidden link, phân biệt `visibility`).
- Lưu và tải lại lịch sử URL đã kiểm tra theo user (chỉ `url` và thời điểm).
- Xóa một mục lịch sử.

Database không lưu DOM, hidden link, `visibility`, scan status, risk rule,
severity hay verdict bảo mật. Hidden link chỉ tồn tại trong response của request
tương ứng; worker không dùng nó để tạo request mới và không có bảng nào lưu lại
nó sau khi xử lý.

## 2. Vì sao dùng PostgreSQL

PostgreSQL phù hợp với MVP vì:

- `users` và `url_checks` có quan hệ ownership rõ ràng.
- Foreign key bảo vệ ownership và toàn vẹn dữ liệu.
- Index hỗ trợ dashboard và lịch sử theo user.
- Migration có version, backup/restore và khả năng mở rộng tốt hơn SQLite cho
  web application nhiều worker.

## 3. Mô hình dữ liệu

### 3.1 `users`

| Cột | Ý nghĩa |
|---|---|
| `id` | UUID nội bộ của user |
| `google_subject` | Subject ổn định từ Google OIDC, duy nhất |
| `email` | Email hiện tại từ Google |
| `display_name` | Tên hiển thị tùy chọn |
| `avatar_url` | URL avatar tùy chọn, không dùng để xác thực |
| `status` | `active` hoặc `disabled` |
| `created_at` | Thời điểm tạo |
| `updated_at` | Thời điểm cập nhật |
| `last_login_at` | Lần đăng nhập Google gần nhất |

Không lưu password hoặc Google access token trong bảng này.

### 3.2 `url_checks`

Đại diện việc user đã yêu cầu kiểm tra một URL. Đây là bảng lưu trữ lâu dài duy
nhất cho lịch sử kiểm tra; hidden link không có bảng riêng vì chỉ tồn tại trong
response của request tương ứng.

| Cột | Ý nghĩa |
|---|---|
| `id` | UUID của mục lịch sử |
| `user_id` | User sở hữu dữ liệu |
| `url` | URL đã gửi để kiểm tra |
| `checked_at` | Thời điểm kiểm tra |

## 4. Migration là nguồn schema chuẩn

Không duy trì thêm một bản `CREATE TABLE` viết tay trong guide. Schema phải
được áp dụng từ các migration có trong repository, theo thứ tự:

1. `migrations/0001_initial_schema.sql` tạo `users`, `url_checks`, khóa ngoại,
   index ownership/history và trigger `users.updated_at`.
2. `migrations/0002_auth_sessions.sql` tạo `user_sessions` và
   `oauth_login_transactions`; migration này phụ thuộc bảng `users`.

`scripts/initial_schema.sql` chỉ là wrapper psql dùng `\ir` để gọi migration
`0001`; nó không phải một schema độc lập. Có thể kiểm tra objects sau khi áp dụng
bằng `scripts/verify_schema.sql`. Hai migration hiện chưa được điều phối bởi
migration runner và chưa có schema-version ledger; quy trình release phải chạy
từng file một lần theo thứ tự, rồi xác minh staging trước production.

## 5. Lưu một mục lịch sử sau khi kiểm tra đồng bộ

Sau khi processor trả `completed`, `partial` hoặc `failed` — hoặc validation
chặn request trước khi fetch — service ghi một mục history trước khi trả response.
Ghi lịch sử thất bại cũng theo policy này. Transaction cho mỗi câu lệnh do
context kết nối psycopg quản lý; không có transaction nhiều bảng cho scan vì
không persist DOM, status hoặc link results.

```sql
INSERT INTO url_checks (id, user_id, url, checked_at)
VALUES (%s, %s, %s, %s);
```

Repository hiện cấp `id` và `checked_at` trong domain, rồi dùng parameterized
`INSERT` vào `url_checks`; `INSERT` thực tế không dùng `RETURNING`. Bản ghi chỉ
có `id`, `user_id`, `url`, `checked_at`.

## 6. Query của repository

### 6.1 Lưu một mục lịch sử

```sql
INSERT INTO url_checks (id, user_id, url, checked_at)
VALUES (%s, %s, %s, %s);
```

### 6.2 Lấy lịch sử của user

```sql
SELECT id, user_id, url, checked_at
FROM url_checks
WHERE user_id = %s
ORDER BY checked_at DESC;
```

### 6.3 Xóa một mục lịch sử

```sql
DELETE FROM url_checks
WHERE user_id = %s
  AND id = %s;
```

### 6.4 Retention

Thời hạn lưu history chưa được chốt và ứng dụng hiện không có purge job tự động.
Chỉ triển khai purge sau khi retention policy được thống nhất.

## 7. Google OAuth persistence

`users` chỉ lưu identity reference (`google_subject`) và thông tin profile cần
thiết. Không lưu password hoặc access token.

Ứng dụng hiện dùng server-side session cookie. Migration
`migrations/0002_auth_sessions.sql` tạo `user_sessions` và
`oauth_login_transactions`; cả hai lưu token/state/nonce dạng hash và có expiry.
Không tạo lại các bảng này bằng SQL riêng trong môi trường đã chạy migration.

## 8. Quy tắc truy cập database

- API không nhận `user_id` từ request body để xác định ownership.
- Query public phải dùng điều kiện `user_id = authenticated_user_id`.
- Foreign key và `ON DELETE CASCADE` bảo đảm kết quả không tồn tại mồ côi.
- Không đưa raw SQL có user input nối chuỗi; dùng parameterized query.
- Chỉ application role cần thiết mới được tạo/sửa dữ liệu; migration role nên
  tách khỏi runtime role.
- Dùng TLS cho kết nối production và lưu secret trong secret manager/environment.
- Không log `google_subject`, session token, raw query string nhạy cảm hoặc DOM
  đầy đủ nếu không cần.
- Không cấp quyền database cho tiến trình chỉ fetch/parse URL trong request nếu
  tiến trình đó chỉ cần ghi một dòng lịch sử sau cùng.

## 9. Cấu hình production và thứ tự triển khai

Đặt `HIDDEN_LINK_CHECKER_ENVIRONMENT=production` và cung cấp
`HIDDEN_LINK_CHECKER_DATABASE_URL` cùng Google OAuth client ID, client secret,
redirect URI, web base URL và API base URL. Đặt
`HIDDEN_LINK_CHECKER_SESSION_COOKIE_SECURE=true` khi chạy HTTPS; lưu secrets trong
secret manager/environment, không commit `.env`. Production từ chối khởi động
nếu thiếu database URL; thiếu Google OAuth config không chặn startup nhưng login
trả `503`.

Các giới hạn scan đang cấu hình được bằng `HIDDEN_LINK_CHECKER_SCAN_TIMEOUT_SECONDS`,
`HIDDEN_LINK_CHECKER_SCAN_MAX_REDIRECTS`,
`HIDDEN_LINK_CHECKER_SCAN_MAX_RESPONSE_BYTES` và
`HIDDEN_LINK_CHECKER_SCAN_MAX_CONCURRENT`. Hard CPU/RAM cap cho Chromium chưa có
trong code và phải được đặt ở process/container runtime.

1. Chạy `migrations/0001_initial_schema.sql` (hoặc wrapper psql
   `scripts/initial_schema.sql`) để tạo extension, enum `user_status`, bảng
   `users`, bảng lịch sử tối giản `url_checks`, foreign key, index và trigger.
2. Chạy `migrations/0002_auth_sessions.sql` để tạo
   `user_sessions` và `oauth_login_transactions`; migration này phụ thuộc vào
   `users` từ bước 1.
3. Chạy `scripts/verify_schema.sql` và PostgreSQL integration test để xác minh
   schema cùng ownership query.
4. Tạo migration seed/config riêng cho development; không seed user thật.

Migration file đã có version trong tên; repository chưa tự theo dõi checksum hay
trạng thái áp dụng. Ghi nhận việc chạy migration trong quy trình release/staging
trước khi áp dụng production.
