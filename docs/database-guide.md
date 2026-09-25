# Hidden Link Checker - PostgreSQL Database Guide

## 1. Mục đích

Tài liệu này hướng dẫn xây dựng database PostgreSQL cho MVP Hidden Link Checker.
Database chỉ lưu lịch sử URL đã kiểm tra theo quan hệ:

```text
User -> UrlCheck
```

MVP hỗ trợ:

- Đăng nhập bằng Google OAuth/OIDC.
- Kiểm tra một URL đầu vào và trả kết quả **đồng bộ** trong response (lấy DOM,
  phát hiện hidden link, phân biệt `visibility`).
- Lưu và tải lại lịch sử URL đã kiểm tra theo user (chỉ `url` và thời điểm).
- Xóa một mục lịch sử.

Database không lưu DOM, hidden link, `visibility`, risk rule, severity hay
verdict bảo mật. Hidden link chỉ tồn tại trong response của request tương ứng;
worker không dùng nó để tạo request mới và không có bảng nào lưu lại nó sau khi
phản hồi.

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

## 4. SQL tạo database objects

Chạy script sau trong database PostgreSQL đã được tạo riêng cho ứng dụng. Nên
chạy bằng migration tool, không chạy thủ công lặp lại trong production.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_status AS ENUM ('active', 'disabled');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_subject TEXT NOT NULL,
    email TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    status user_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    CONSTRAINT users_google_subject_unique UNIQUE (google_subject),
    CONSTRAINT users_email_length CHECK (char_length(email) BETWEEN 3 AND 320),
    CONSTRAINT users_display_name_length CHECK (
        display_name IS NULL OR char_length(display_name) <= 200
    )
);

CREATE TABLE url_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    url TEXT NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT url_checks_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT url_checks_url_length CHECK (
        char_length(url) BETWEEN 1 AND 8192
    )
);

CREATE INDEX url_checks_user_history_idx
    ON url_checks (user_id, checked_at DESC);
```

## 5. `updated_at` trigger

Dùng trigger để `users.updated_at` luôn phản ánh lần cập nhật gần nhất.

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

## 6. Lưu một mục lịch sử sau khi kiểm tra đồng bộ

Sau khi API xử lý xong một request kiểm tra URL (thành công hay có giới hạn),
chỉ cần một câu lệnh `INSERT` duy nhất để ghi lịch sử; không cần transaction
nhiều bảng vì không còn `link_results` để lưu cùng lúc.

```sql
INSERT INTO url_checks (
    user_id,
    url
)
VALUES (
    $1,
    $2
)
RETURNING id, url, checked_at;
```

Ghi lịch sử là bước cuối cùng sau khi request đồng bộ đã xử lý xong (thành công
hay có giới hạn); API không cần cập nhật lại bản ghi này sau đó vì không có
trạng thái trung gian nào cần theo dõi.

## 7. Query cho API và dashboard

### 7.1 Lưu một mục lịch sử

```sql
INSERT INTO url_checks (user_id, url)
VALUES ($1, $2)
RETURNING id, url, checked_at;
```

### 7.2 Lấy lịch sử của user

```sql
SELECT id, url, checked_at
FROM url_checks
WHERE user_id = $1
ORDER BY checked_at DESC
LIMIT $2
OFFSET $3;
```

### 7.3 Xóa một mục lịch sử

```sql
DELETE FROM url_checks
WHERE id = $1
  AND user_id = $2
RETURNING id;
```

### 7.4 Purge dữ liệu hết retention

Purge phải chạy trong job vận hành có quyền database phù hợp, theo retention
policy đã chốt cho lịch sử URL.

```sql
DELETE FROM url_checks
WHERE checked_at <= now() - INTERVAL '90 days';
```

## 8. Google OAuth persistence

`users` chỉ lưu identity reference (`google_subject`) và thông tin profile cần
thiết. Không lưu password hoặc access token.

Nếu ứng dụng dùng server-side session, có thể thêm bảng sau. Nếu dùng bearer
token do một identity/session service quản lý, không cần bảng này trong database
ứng dụng.

```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    CONSTRAINT user_sessions_expiry_valid CHECK (expires_at > created_at)
);

CREATE INDEX user_sessions_user_idx
    ON user_sessions (user_id, expires_at);

CREATE INDEX user_sessions_active_idx
    ON user_sessions (expires_at)
    WHERE revoked_at IS NULL;
```

Ứng dụng phải lưu hash của session token, không lưu token plaintext.

## 9. Quy tắc truy cập database

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

## 10. Thứ tự triển khai migration

1. Chạy `migrations/0001_initial_schema.sql` (hoặc wrapper psql
   `scripts/initial_schema.sql`) để tạo extension, enum `user_status`, bảng
   `users`, bảng lịch sử tối giản `url_checks`, foreign key, index và trigger.
2. Chạy `migrations/0002_auth_sessions.sql` để tạo
   `user_sessions` và `oauth_login_transactions`; migration này phụ thuộc vào
   `users` từ bước 1.
3. Chạy `scripts/verify_schema.sql` và integration test để xác minh schema cùng
   ownership query.
4. Tạo migration seed/config riêng cho development; không seed user thật.

Mỗi migration cần có version, checksum và được chạy trong CI/staging trước khi
áp dụng production.
