# Contributing to Hidden Link Checker

## Quy trình

1. Tạo branch từ `main`: `feature/<short-name>`, `fix/<short-name>` hoặc `docs/<short-name>`.
2. Giữ thay đổi tập trung vào một mục tiêu và cập nhật test/tài liệu liên quan.
3. Chạy `python -m pytest -q` trước khi mở pull request.
4. Mở pull request vào `main`, mô tả requirement/issue được xử lý và giới hạn còn lại.
5. Chờ CI pass và ít nhất một maintainer review trước khi merge.

## Nguyên tắc riêng của dự án

- Không mở rộng scope khỏi link thường và hidden link trong text/image/background
	nếu chưa cập nhật `docs/recommendation.md`, `docs/specification.md` và BRD.
- Không thêm rule đánh giá rủi ro, severity hoặc malware/phishing verdict vào MVP
	nếu chưa có quyết định scope mới và cập nhật tài liệu liên quan.
- Mọi code nhận/render URL phải có SSRF và resource-limit consideration.
- Không tự động mở, fetch hoặc điều hướng tới link được phát hiện; chỉ xử lý DOM
	của URL đầu vào.
- Mọi link result phải giữ được user ownership, URL kiểm tra, object nguồn và
	URL thực tế sau khi resolve.
- Không commit credential, snapshot nhạy cảm hoặc URL chứa token thật.

## Commit và review

Dùng commit message ngắn theo dạng `feat:`, `fix:`, `test:`, `docs:` hoặc `chore:`. Pull request cần nêu cách kiểm thử, ảnh hưởng tới API/domain và các rủi ro bảo mật liên quan.
