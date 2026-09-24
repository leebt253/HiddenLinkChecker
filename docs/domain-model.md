# Hidden Link Checker - Domain Model

## Scope

MVP nhận một URL, lấy DOM của URL đầu vào, tìm hidden links và hiển thị kết quả
trong phiên xử lý. PostgreSQL chỉ lưu identity và URL history.

## Entities

### User

`id`, `google_subject`, `email`, `status`, `created_at`, `last_login_at`.

`google_subject` chỉ dùng nội bộ để liên kết Google identity. Mọi URL history
đều được truy vấn theo authenticated `user_id`.

### URL check history

`id`, `user_id`, `url`, `checked_at`.

Đây là entity duy nhất của một lần check được lưu vào PostgreSQL. Xóa user sẽ
cascade xóa URL history.

### LinkResult (memory only)

`id`, `element_type`, `object_reference`, `source_url`, `actual_url`,
`visibility`, `visible_text`, `alt_text`, `position`.

`LinkResult` được tạo bởi extractor để trả về dashboard trong process hiện tại.
Nó không có bảng database và mất khi process restart. `actual_url` chỉ là dữ
liệu kết quả; system không fetch, mở, redirect hoặc điều hướng tới URL đó.

## Invariants

1. Mỗi URL history thuộc đúng một `User`.
2. Client không được tự gửi `user_id`; server lấy từ authenticated session.
3. API phải lọc ownership trước mọi thao tác đọc hoặc xóa.
4. Không lưu hoặc log OAuth secret, token, raw query string nhạy cảm hoặc DOM.

## PostgreSQL mapping

Các bảng cần giữ:

- `users`.
- `user_sessions`.
- `oauth_login_transactions`.
- `url_checks`.

Index chính: unique `users.google_subject` và
`url_checks(user_id, checked_at DESC)`. Các bảng `link_checks` và `link_results`
không còn cần thiết và được loại bỏ bởi migration.
