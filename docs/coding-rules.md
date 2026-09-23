# Coding Rules - Hidden Link Checker

Tài liệu này áp dụng cho mã Python của Hidden Link Checker. Các rule phải hỗ trợ
mục tiêu của sản phẩm: phát hiện URL ẩn có thể giải thích, bảo vệ an toàn khi
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
- Tách biệt rõ extractor, rule evaluator, persistence, API và UI contract như
  specification yêu cầu.
- Không dùng biến trạng thái toàn cục có thể thay đổi. Cấu hình rule và giới
  hạn vận hành phải được truyền vào hoặc quản lý tập trung.
- Không hard-code danh sách hoặc điều kiện rule kiểm tra lừa đảo trong source
  code. Rule phải nằm trong file cấu hình theo schema/version đã xác định;
  evaluator chỉ đọc và áp dụng cấu hình hợp lệ.

## 2. Quy ước Python

- Tuân thủ PEP 8 và cấu hình Ruff của dự án; giới hạn dòng là 100 ký tự.
- Dùng `snake_case` cho module, function, method và biến; `PascalCase` cho
  class; `UPPER_SNAKE_CASE` cho hằng số.
- Tên phải mô tả đúng nghiệp vụ, ví dụ `normalized_url`, `matched_rules` và
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
- Cập nhật documentation khi thay đổi contract của finding, severity, scan
  lifecycle hoặc giới hạn bảo mật.

## 5. URL và an toàn khi scan

- Chỉ chấp nhận scheme `http` và `https` ở boundary nhận request.
- Mọi URL phải được parse và chuẩn hóa bằng logic dùng chung; không tự nối URL
  bằng phép cộng chuỗi.
- Kiểm tra SSRF trước khi worker truy cập URL và kiểm tra lại sau mỗi redirect.
  Chặn localhost, loopback, private, link-local, multicast và cloud metadata
  endpoint.
- Áp dụng timeout, giới hạn redirect, response size, CPU, RAM và số scan đồng
  thời từ cấu hình tập trung.
- Không gửi cookie, authorization header hoặc application secret tới trang đích.
- Không log password, secret hoặc query string nhạy cảm. Lỗi network, timeout,
  403 và 429 phải được chuyển thành lỗi có kiểm soát, không làm API crash.

## 6. Finding và rule evaluation

- Mỗi finding phải giữ `element_type`, `source_url`, `normalized_url` và bằng
  chứng liên quan như visible text, alt text hoặc matched content.
- `severity` chỉ nhận `safe`, `warning` hoặc `critical`; mỗi finding nhận đúng
  một severity.
- Rule phải được cấu hình tập trung, có tên ổn định và trả về `matched_rules`
  cùng evidence/reason khi cần giải thích.
- Rule configuration phải có thể được cập nhật qua web app với quyền
  administrator và có chức năng import file theo mẫu được kiểm tra schema,
  version, severity và nội dung điều kiện trước khi publish.
- Lưu version rule được dùng cho mỗi scan để kết quả lịch sử vẫn giải thích và
  tái lập được sau khi cấu hình thay đổi.
- Rule gambling hoặc tín hiệu tương đương có thể tạo `critical`; destination
  ngoài origin, redirect bất thường hoặc dữ liệu thiếu có thể tạo tối thiểu
  `warning`.
- Không diễn đạt `safe` như chứng nhận website an toàn. Đây chỉ là kết quả chưa
  có rule rủi ro nào khớp trong phạm vi scan.
- Khi không thể đọc đầy đủ nội dung do JavaScript, iframe, CAPTCHA, login,
  timeout hoặc resource limit, ghi nhận `partial` và limitation thay vì đoán.

## 7. Bảo mật dữ liệu và ownership

- Mọi truy vấn scan, finding và snapshot phải kiểm tra `authenticated user_id`.
- Không trả hoặc xóa dữ liệu của user khác chỉ dựa trên `scan_id` do client gửi.
- Password phải được hash; không lưu hoặc log password dạng plain text.
- Snapshot, URL và finding phải tuân thủ retention policy; việc xóa scan phải
  xử lý dữ liệu liên quan theo cùng policy.
- Error response phải đủ hữu ích cho client nhưng không làm lộ secret, thông tin
  nội bộ hoặc dữ liệu của tài khoản khác.

## 8. Kiểm thử và chất lượng

- Viết unit test riêng cho extractor, URL normalization, rule evaluator,
  severity precedence và các policy bảo mật.
- Viết integration test cho các lát dọc chính: scan an toàn một URL, trích xuất
  text/image/background, đánh giá rule và chuyển trạng thái scan.
- Kiểm thử cả trường hợp lỗi: URL không hợp lệ, redirect nguy hiểm, timeout,
  response lỗi, dữ liệu thiếu và kết quả `partial`.
- Mỗi bug bảo mật hoặc regression của contract phải có test tái hiện trước hoặc
  cùng lúc với bản sửa.
- Trước khi hoàn tất thay đổi, chạy formatter/linter và test phù hợp; không bỏ
  qua test chỉ vì kết quả vẫn hiển thị được.
