# Hidden Link Checker - PostgreSQL Database Guide

## Persistence scope

PostgreSQL chỉ lưu dữ liệu cần cho đăng nhập và lịch sử URL:

- `users`: Google identity và trạng thái tài khoản.
- `user_sessions`: session cookie dạng hash.
- `oauth_login_transactions`: state/nonce ngắn hạn của OAuth.
- `url_checks`: `id`, `user_id`, `url`, `checked_at`.

Worker giữ trạng thái scan và hidden-link results trong memory của process hiện
tại. Database không lưu raw DOM, `LinkResult`, visibility, actual URL, status
worker, limitation hay notes scan.

## Tables no longer required

Các bảng sau không còn cần cho yêu cầu mới và được loại bỏ bởi migration
`0004_remove_scan_result_storage.sql`:

- `link_checks`: trước đây lưu lifecycle, DOM reference, status và metadata scan.
- `link_results`: trước đây lưu toàn bộ hidden links và evidence.

Các enum/index/trigger chỉ phục vụ hai bảng trên cũng được loại bỏ trong migration.
URL history cũ được chuyển sang `url_checks` trước khi xóa bảng cũ.

## Ownership and indexes

`url_checks.user_id` tham chiếu `users.id` với `ON DELETE CASCADE`. Index chính là
`url_checks(user_id, checked_at DESC)` để tải history theo user.

Không có index cho hidden-link domain/visibility vì các thuộc tính này không còn
được lưu trong database.

## Apply schema

Từ thư mục project:

```powershell
.venv\Scripts\python.exe scripts\initialize_database.py
```

Script đọc `HIDDEN_LINK_CHECKER_DATABASE_URL` từ `.env`, tạo schema ban đầu và
chạy các migration chưa áp dụng qua bảng `schema_migrations`.
