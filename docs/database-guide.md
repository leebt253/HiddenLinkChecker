# Hidden Link Checker - PostgreSQL Database Guide

## 1. Mục đích

Tài liệu này hướng dẫn xây dựng database PostgreSQL cho MVP Hidden Link Checker.
Database lưu dữ liệu theo quan hệ:

```text
User -> LinkCheck -> LinkResult
```

MVP hỗ trợ:

- Đăng nhập bằng Google OAuth/OIDC.
- Tạo một lần kiểm tra cho một URL đầu vào.
- Lấy DOM của URL đầu vào.
- Phát hiện mọi URL trong DOM dưới dạng `LinkResult`.
- Phân biệt visibility của kết quả:
  - `direct`: URL hiển thị trực tiếp, ví dụ anchor có text.
  - `indirect`: URL nằm sau image, background hoặc object khác.
- Lưu và tải lại lịch sử theo user.
- Cập nhật metadata được phép và xóa một lần kiểm tra.

Database không lưu hoặc đánh giá risk rule, severity hay verdict bảo mật.
`actual_url` chỉ là dữ liệu được parse và resolve; worker không dùng nó để tạo
request mới.

## 2. Vì sao dùng PostgreSQL

PostgreSQL phù hợp với MVP vì:

- `users`, `link_checks` và `link_results` có quan hệ rõ ràng.
- Foreign key bảo vệ ownership và toàn vẹn dữ liệu.
- Transaction cho phép lưu một `LinkCheck` cùng toàn bộ `LinkResult` nguyên tử.
- Index hỗ trợ dashboard và lịch sử theo user.
- `jsonb` phù hợp cho bounding box, limitation và metadata mở rộng.
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

### 3.2 `link_checks`

Đại diện một lần user gửi URL để xử lý.

| Cột | Ý nghĩa |
|---|---|
| `id` | UUID của lần kiểm tra |
| `user_id` | User sở hữu dữ liệu |
| `submitted_url` | URL nguyên bản từ request |
| `normalized_url` | URL sau chuẩn hóa đầu vào |
| `final_url` | URL cuối của navigation URL đầu vào |
| `status` | `queued`, `running`, `completed`, `partial`, `failed` |
| `http_status` | HTTP status của URL đầu vào nếu có |
| `error_code` | Mã lỗi ổn định, không lưu stack trace |
| `dom_reference` | Reference tới DOM lưu ngoài database nếu có |
| `limitations` | Các giới hạn xử lý dạng JSONB |
| `notes` | Metadata do user được phép cập nhật |
| `created_at` | Thời điểm tạo |
| `started_at` | Thời điểm processor bắt đầu |
| `completed_at` | Thời điểm kết thúc |
| `retention_expires_at` | Thời điểm hết hạn lưu |

### 3.3 `link_results`

Mọi URL được phát hiện trong DOM đều là một `LinkResult`/hidden link.

| Cột | Ý nghĩa |
|---|---|
| `id` | UUID của kết quả |
| `link_check_id` | Link check cha |
| `element_type` | `text`, `image`, `background` |
| `object_reference` | ID/selector nội bộ của object trong DOM |
| `source_url` | URL literal đọc được từ DOM |
| `actual_url` | URL đã resolve theo `final_url` |
| `visibility` | `direct` hoặc `indirect` |
| `visible_text` | Text liên quan, có thể null |
| `alt_text` | Alt text liên quan, có thể null |
| `position` | Bounding box dạng JSONB, có thể null |
| `created_at` | Thời điểm lưu |

`actual_url` không phải foreign key và không được dùng để fetch tiếp.

## 4. SQL tạo database objects

Chạy script sau trong database PostgreSQL đã được tạo riêng cho ứng dụng. Nên
chạy bằng migration tool, không chạy thủ công lặp lại trong production.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_status AS ENUM ('active', 'disabled');
CREATE TYPE link_check_status AS ENUM (
    'queued',
    'running',
    'completed',
    'partial',
    'failed'
);
CREATE TYPE link_element_type AS ENUM ('text', 'image', 'background');
CREATE TYPE link_visibility AS ENUM ('direct', 'indirect');

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

CREATE TABLE link_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    submitted_url TEXT NOT NULL,
    normalized_url TEXT,
    final_url TEXT,
    status link_check_status NOT NULL DEFAULT 'queued',
    http_status INTEGER,
    error_code TEXT,
    dom_reference TEXT,
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    retention_expires_at TIMESTAMPTZ,
    CONSTRAINT link_checks_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT link_checks_submitted_url_length CHECK (
        char_length(submitted_url) BETWEEN 1 AND 8192
    ),
    CONSTRAINT link_checks_http_status_valid CHECK (
        http_status IS NULL OR http_status BETWEEN 100 AND 599
    ),
    CONSTRAINT link_checks_limitations_array CHECK (
        jsonb_typeof(limitations) = 'array'
    ),
    CONSTRAINT link_checks_completed_time_consistent CHECK (
        completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at
    ),
    CONSTRAINT link_checks_retention_time_consistent CHECK (
        retention_expires_at IS NULL OR retention_expires_at >= created_at
    )
);

CREATE TABLE link_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    link_check_id UUID NOT NULL,
    element_type link_element_type NOT NULL,
    object_reference TEXT,
    source_url TEXT NOT NULL,
    actual_url TEXT NOT NULL,
    visibility link_visibility NOT NULL,
    visible_text TEXT,
    alt_text TEXT,
    position JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT link_results_check_fk
        FOREIGN KEY (link_check_id)
        REFERENCES link_checks (id)
        ON DELETE CASCADE,
    CONSTRAINT link_results_source_url_length CHECK (
        char_length(source_url) BETWEEN 1 AND 8192
    ),
    CONSTRAINT link_results_actual_url_length CHECK (
        char_length(actual_url) BETWEEN 1 AND 8192
    ),
    CONSTRAINT link_results_position_object CHECK (
        position IS NULL OR jsonb_typeof(position) = 'object'
    )
);

CREATE INDEX link_checks_user_history_idx
    ON link_checks (user_id, created_at DESC);

CREATE INDEX link_checks_status_idx
    ON link_checks (status, created_at DESC);

CREATE INDEX link_checks_retention_idx
    ON link_checks (retention_expires_at)
    WHERE retention_expires_at IS NOT NULL;

CREATE INDEX link_results_check_idx
    ON link_results (link_check_id, created_at);

CREATE INDEX link_results_visibility_idx
    ON link_results (visibility);

CREATE INDEX link_results_actual_url_idx
    ON link_results (actual_url);
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

CREATE TRIGGER link_checks_set_updated_at
BEFORE UPDATE ON link_checks
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

## 6. Transaction lưu một lần kiểm tra

Processor phải lưu `link_checks` và các `link_results` trong cùng transaction.
Không chèn kết quả dựa trên `link_check_id` mà không kiểm tra ownership ở tầng
service/API.

```sql
BEGIN;

INSERT INTO link_checks (
    user_id,
    submitted_url,
    normalized_url,
    status
)
VALUES (
    $1,
    $2,
    $3,
    'queued'
)
RETURNING id;

-- Dùng id trả về ở trên cho các INSERT link_results.

COMMIT;
```

Khi processor hoàn thành:

```sql
UPDATE link_checks
SET status = $2,
    final_url = $3,
    http_status = $4,
    error_code = $5,
    dom_reference = $6,
    limitations = $7::jsonb,
    started_at = COALESCE(started_at, $8::timestamptz),
    completed_at = $9::timestamptz
WHERE id = $1
  AND user_id = $10;
```

Worker nội bộ có thể cập nhật theo `id` sau khi đã nhận job hợp lệ; API public
luôn phải thêm điều kiện `user_id` để chống truy cập chéo tài khoản.

## 7. Query cho API CRUD và dashboard

### 7.1 Tạo link check theo user

```sql
INSERT INTO link_checks (user_id, submitted_url, normalized_url)
VALUES ($1, $2, $3)
RETURNING id, status, created_at;
```

### 7.2 Lấy chi tiết một link check và kết quả

```sql
SELECT
    lc.id,
    lc.submitted_url,
    lc.normalized_url,
    lc.final_url,
    lc.status,
    lc.http_status,
    lc.error_code,
    lc.dom_reference,
    lc.limitations,
    lc.notes,
    lc.created_at,
    lc.started_at,
    lc.completed_at,
    lr.id AS result_id,
    lr.element_type,
    lr.object_reference,
    lr.source_url,
    lr.actual_url,
    lr.visibility,
    lr.visible_text,
    lr.alt_text,
    lr.position
FROM link_checks AS lc
LEFT JOIN link_results AS lr ON lr.link_check_id = lc.id
WHERE lc.id = $1
  AND lc.user_id = $2
ORDER BY lr.created_at, lr.id;
```

### 7.3 Lấy lịch sử của user

```sql
SELECT
    lc.id,
    lc.submitted_url,
    lc.final_url,
    lc.status,
    lc.created_at,
    lc.completed_at,
    COUNT(lr.id)::integer AS result_count
FROM link_checks AS lc
LEFT JOIN link_results AS lr ON lr.link_check_id = lc.id
WHERE lc.user_id = $1
GROUP BY lc.id
ORDER BY lc.created_at DESC
LIMIT $2
OFFSET $3;
```

### 7.4 Lọc kết quả theo visibility

```sql
SELECT
    lr.id,
    lr.element_type,
    lr.object_reference,
    lr.source_url,
    lr.actual_url,
    lr.visibility,
    lr.visible_text,
    lr.alt_text,
    lr.position
FROM link_results AS lr
JOIN link_checks AS lc ON lc.id = lr.link_check_id
WHERE lc.id = $1
  AND lc.user_id = $2
  AND ($3::link_visibility IS NULL OR lr.visibility = $3)
ORDER BY lr.created_at, lr.id;
```

### 7.5 Cập nhật metadata được phép

```sql
UPDATE link_checks
SET notes = $3
WHERE id = $1
  AND user_id = $2
RETURNING id, notes, updated_at;
```

### 7.6 Xóa link check

`ON DELETE CASCADE` sẽ xóa các `link_results` liên quan.

```sql
DELETE FROM link_checks
WHERE id = $1
  AND user_id = $2
RETURNING id;
```

### 7.7 Purge dữ liệu hết retention

Purge phải chạy trong job vận hành có quyền database phù hợp và nên xóa DOM
artifact ngoài database trước hoặc theo transaction nghiệp vụ tương ứng.

```sql
DELETE FROM link_checks
WHERE retention_expires_at IS NOT NULL
  AND retention_expires_at <= now();
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
- Không cấp quyền database cho browser worker nếu worker chỉ gọi API/queue.

## 10. Thứ tự triển khai migration

1. Bật extension `pgcrypto`.
2. Tạo enum types.
3. Tạo `users`.
4. Tạo `link_checks`.
5. Tạo `link_results`.
6. Tạo foreign key, index và trigger.
7. Chạy migration kiểm tra constraint và ownership query.
8. Nếu dùng server-side session, tạo `user_sessions`.
9. Tạo migration seed/config cho môi trường development, không seed user thật.

Mỗi migration cần có version, checksum và được chạy trong CI/staging trước khi
áp dụng production.
