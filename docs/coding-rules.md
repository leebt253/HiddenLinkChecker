# Coding Rules - Hidden Link Checker

Tài liệu này áp dụng cho mã Python của Hidden Link Checker. MVP tập trung vào
phát hiện hidden link từ DOM của URL đầu vào, bảo vệ an toàn khi
render URL và giữ dữ liệu đúng phạm vi tài khoản.

## 1. Nguyên tắc thiết kế

- Tuân thủ các nguyên tắc clean code: tên rõ nghĩa, hàm nhỏ, trách nhiệm đơn
  nhất, ít phụ thuộc và dễ kiểm thử.
- Tổ chức ứng dụng theo mô hình MVC dễ đọc và dễ maintenance: Model chịu trách
  nhiệm domain và persistence contract, View chịu trách nhiệm trình bày/UI,
  Controller điều phối request và use case; không đưa business rule vào View
  hoặc truy cập database trực tiếp từ Controller.
- Giữ business logic trong service/domain layer ở giữa Controller và Model khi
  use case phức tạp; MVC là ranh giới tổ chức, không phải lý do để tạo thêm
  abstraction không cần thiết.
- Ưu tiên KISS và YAGNI; không thêm abstraction hoặc design pattern khi chưa có
  nhu cầu thực tế.
- Tránh lặp code theo DRY, nhưng không gộp các logic khác mục đích chỉ để giảm
  số dòng.
- Tách biệt rõ extractor, persistence, API và UI contract như specification yêu
  cầu.
- Không dùng biến trạng thái toàn cục có thể thay đổi. Giới hạn vận hành phải
  được truyền vào hoặc quản lý tập trung.
- Không thêm rule đánh giá rủi ro hoặc severity vào MVP khi chưa có quyết định
  scope mới.

## 2. Quy ước Python

- Tuân thủ PEP 8 và cấu hình Ruff của dự án; giới hạn dòng là 100 ký tự.
- Dùng `snake_case` cho module, function, method và biến; `PascalCase` cho
  class; `UPPER_SNAKE_CASE` cho hằng số.
- Tên phải mô tả đúng nghiệp vụ, ví dụ `normalized_url`, `actual_url` và
  `element_type`; không dùng tiền tố kiểu `g_` hoặc quy ước camelCase.
- Dùng type hints cho public function, method, thuộc tính quan trọng và giá
  trị trả về. Ưu tiên kiểu cụ thể thay cho `Any`.
- Dùng `dataclass`, `Enum` hoặc kiểu dữ liệu chuẩn khi chúng biểu diễn đúng
  domain model. Ưu tiên object bất biến cho dữ liệu kết quả.
- Dùng `pathlib`, `urllib.parse` và thư viện chuẩn phù hợp thay vì tự xử lý
  chuỗi cho các thao tác path, URL hoặc parsing đã có abstraction chuẩn.

## 3. Hàm và vòng lặp

- Mỗi hàm chỉ nên có một trách nhiệm và có thể mô tả mục đích bằng một câu.
- Giữ hàm ngắn, dễ đọc; khi logic có nhiều nhánh hoặc vượt quá khoảng 20-30
  dòng có ý nghĩa, xem xét tách thành hàm private có tên rõ ràng.
- Chỉ tạo biến trung gian khi tên biến giúp làm rõ ý nghĩa hoặc giá trị được
  dùng nhiều lần. Biến vòng lặp được khuyến khích khi giúp biểu diễn rõ từng
  phần tử; không nhồi biểu thức phức tạp vào vòng lặp chỉ để tránh khai báo
  biến.
- Không dùng list comprehension hoặc biểu thức tạo collection để thực hiện
  side effect. Dùng vòng lặp tường minh khi cần cập nhật trạng thái, gọi hàm
  có side effect hoặc xử lý lỗi riêng cho từng phần tử.
- Tránh lồng vòng lặp và điều kiện sâu; dùng early return, guard clause hoặc
  hàm hỗ trợ để làm phẳng control flow.
- Không dùng list comprehension chỉ để tạo side effect. Dùng vòng lặp rõ ràng
  hoặc các hàm built-in như `any`, `all`, `sum` khi phù hợp.

## 4. Comment và documentation

- Code phải tự giải thích bằng tên và cấu trúc; chỉ comment lý do nghiệp vụ,
  giới hạn kỹ thuật hoặc quyết định an toàn không hiển nhiên.
- Dùng docstring theo phong cách Python cho module, class và public function
  có contract hoặc hành vi không tầm thường; không dùng JSDoc hay JavaDoc.
- Docstring cần nêu input, output, exception và side effect quan trọng.
- Cập nhật documentation khi thay đổi contract của link result, vòng đời request
  kiểm tra URL hoặc giới hạn bảo mật.

## 5. URL và an toàn khi scan

- Chỉ chấp nhận scheme `http` và `https` ở boundary nhận request.
- Mọi URL phải được parse và chuẩn hóa bằng logic dùng chung; không tự nối URL
  bằng phép cộng chuỗi.
- Kiểm tra SSRF trước khi worker truy cập URL và kiểm tra lại sau mỗi redirect.
  Chặn localhost, loopback, private, link-local, multicast và cloud metadata
  endpoint.
- Transport phải kết nối tới IP thuộc tập DNS đã xác minh, không tự resolve
  hostname lần nữa tại bước TCP; xác minh lại và pin lại ở từng redirect.
- Áp dụng timeout, giới hạn redirect, response size, CPU, RAM và số scan đồng
  thời từ cấu hình tập trung.
- Không gửi cookie, authorization header hoặc application secret tới trang đích.
- Không log password, secret hoặc query string nhạy cảm. Lỗi network, timeout,
  403 và 429 phải được chuyển thành lỗi có kiểm soát, không làm API crash.

## 6. Link extraction và result

- Mỗi link result phải giữ `element_type`, `object_reference`, `source_url`,
  `actual_url` và `visibility`.
- URL tương đối phải được resolve theo final URL của trang đầu vào.
- `actual_url` chỉ là dữ liệu kết quả trả về trong response; không được fetch,
  mở, điều hướng tới hoặc lưu trữ lại link đã phát hiện sau khi phản hồi.
- Mọi kết quả đều là hidden link; phân biệt link hiển thị trực tiếp và không
  trực tiếp bằng `visibility = direct` hoặc `visibility = indirect`.
- Khi không thể đọc đầy đủ nội dung do JavaScript, iframe, CAPTCHA, login,
  timeout hoặc resource limit, trả về `partial` và limitation trong response
  thay vì đoán.

## 7. Bảo mật dữ liệu và ownership

- Mọi truy vấn lịch sử URL đã kiểm tra phải kiểm tra authenticated `user_id`.
- Không trả hoặc xóa dữ liệu của user khác chỉ dựa trên `check_id` do client gửi.
- Không lưu hoặc log Google OAuth credential/token.
- Lịch sử URL phải tuân thủ retention policy; hidden link không được lưu trữ
  sau khi response đã được trả về nên không cần retention riêng cho phần này.
- Error response phải đủ hữu ích cho client nhưng không làm lộ secret, thông tin
  nội bộ hoặc dữ liệu của tài khoản khác.

## 8. Kiểm thử và chất lượng

- Viết unit test riêng cho extractor, URL normalization, visibility direct/
  indirect và các policy bảo mật.
- Viết integration test cho các lát dọc chính: lấy DOM an toàn của một URL,
  trích xuất text/image/background trong cùng response đồng bộ và lưu lịch sử
  URL đã kiểm tra.
- Kiểm thử cả trường hợp lỗi: URL không hợp lệ, redirect nguy hiểm, timeout,
  response lỗi, dữ liệu thiếu và kết quả `partial`.
- Mỗi bug bảo mật hoặc regression của contract phải có test tái hiện trước hoặc
  cùng lúc với bản sửa.
- Trước khi hoàn tất thay đổi, chạy formatter/linter và test phù hợp; không bỏ
  qua test chỉ vì kết quả vẫn hiển thị được.
