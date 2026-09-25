# Hướng dẫn đọc mã nguồn

Tài liệu này mô tả các ranh giới chính trong mã nguồn Python. API contract chi
tiết nằm trong [api-spec.md](api-spec.md); quy tắc đóng góp và docstring nằm
trong [coding-rules.md](coding-rules.md).

## Cấu trúc ứng dụng

- `hidden_link_checker_api/controllers`: nhận request, lấy user hiện tại và
  chuyển dữ liệu qua service.
- `hidden_link_checker_api/services`: điều phối use case kiểm tra URL, lịch sử
  và xác thực.
- `hidden_link_checker_api/scanner`: chuẩn hóa URL, kiểm tra SSRF, fetch trang,
  render DOM trong browser bị chặn mạng và trích xuất link.
- `hidden_link_checker_api/workers`: điều phối một lượt scan và chuyển lỗi kỹ
  thuật thành trạng thái/limitation có kiểm soát.
- `hidden_link_checker_api/repositories`: lưu user, session và URL history bằng
  repository in-memory hoặc PostgreSQL.
- `hidden_link_checker_api/domain`: kiểu dữ liệu và trạng thái nghiệp vụ.
- `shared_contracts`: model request/response dùng chung giữa API và web.
- `hidden_link_checker_web`: giao diện server-rendered, controller web và HTTP
  client gọi API.

## Luồng kiểm tra URL

1. Controller API lấy user đã xác thực và gọi `LinkCheckService.check`.
2. Service chuẩn hóa URL, tạo kết quả scan và gọi worker đồng bộ.
3. Worker dùng fetcher để tải URL đầu vào; mỗi redirect được kiểm tra lại theo
   SSRF policy và kết nối được pin vào địa chỉ DNS đã xác minh.
4. Renderer chạy JavaScript trong Chromium riêng, đồng thời chặn request mạng
   do trang tạo ra. Nếu render lỗi, HTML fetch được vẫn có thể được phân tích.
5. Extractor đọc các tham chiếu text, image và inline CSS background. URL phát
   hiện chỉ được trả về trong response, không được fetch tiếp.
6. Service lưu URL và thời điểm vào lịch sử thuộc user; findings không được lưu.

Giới hạn thời gian, redirect, kích thước response và số scan đồng thời được cấu
hình tại `hidden_link_checker_api/scan_limits.py` và truyền vào worker/fetcher.

## Docstring trong mã nguồn

Public module, class và function có contract đáng chú ý dùng Google-style
docstring. Type hints nằm trong chữ ký; docstring giải thích ý nghĩa, điều kiện,
exception và side effect quan trọng. Dùng `Args`, `Returns`, `Raises`, `Yields`
hoặc `Notes` khi có nội dung tương ứng; bỏ mục không cần thiết. Không lặp lại
điều hiển nhiên từ tên hàm hoặc code.

Ví dụ:

```python
def normalize_input_url(submitted_url: str) -> str:
    """Chuẩn hóa URL đầu vào thành URL HTTP(S) tuyệt đối.

    Args:
        submitted_url: URL người dùng gửi lên.

    Returns:
        URL đã chuẩn hóa, bỏ fragment và điền path mặc định nếu cần.

    Raises:
        InvalidInputUrlError: URL sai định dạng hoặc không dùng HTTP(S).
    """
```

## Tài liệu liên quan

- [API contract](api-spec.md)
- [Coding rules](coding-rules.md)
- [Domain model](domain-model.md)
- [Database guide](database-guide.md)
- [Traceability](traceability.md)
