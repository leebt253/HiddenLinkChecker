# Contributing to Hidden Link Checker

## Quy trình

1. Tạo branch từ `main`: `feature/<short-name>`, `fix/<short-name>` hoặc `docs/<short-name>`.
2. Giữ thay đổi tập trung vào một mục tiêu và cập nhật test/tài liệu liên quan.
3. Chạy `python -m pytest -q` trước khi mở pull request.
4. Mở pull request vào `main`, mô tả requirement/issue được xử lý và giới hạn còn lại.
5. Chờ CI pass và ít nhất một maintainer review trước khi merge.

## Nguyên tắc riêng của dự án

- Không mở rộng scope khỏi finding text/image/background nếu chưa cập nhật `docs/recommendation.md`, `docs/specification.md` và BRD.
- Không mô tả `safe` là chứng nhận an toàn tuyệt đối.
- Mọi code nhận/render URL phải có SSRF và resource-limit consideration.
- Mọi finding quan trọng cần có evidence và `matched_rules` để giải thích.
- Không commit credential, snapshot nhạy cảm hoặc URL chứa token thật.

## Commit và review

Dùng commit message ngắn theo dạng `feat:`, `fix:`, `test:`, `docs:` hoặc `chore:`. Pull request cần nêu cách kiểm thử, ảnh hưởng tới API/domain và các rủi ro bảo mật liên quan.
