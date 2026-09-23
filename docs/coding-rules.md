# Coding Rules — Hidden Link Checker

Tài liệu này quy định cách AI và contributor thay đổi code trong Hidden Link Checker. Khi có mâu thuẫn, ưu tiên theo thứ tự: yêu cầu bảo mật và quyền riêng tư trong `docs/specification.md`, phạm vi sản phẩm trong `docs/recommendation.md`, các coding rule này, rồi mới đến lựa chọn triển khai cục bộ.

## 1. Nguyên tắc sản phẩm

- Xây công cụ rà soát URL trong **một trang**; MVP chỉ trích xuất `text`, `image` và `background`.
- Mỗi finding phải giúp người dùng đối chiếu element, URL nguồn, URL đã chuẩn hóa, ngữ cảnh hiển thị và lý do phân loại.
- `safe` chỉ có nghĩa là không có rule đã cấu hình khớp trong phạm vi scan. Không mô tả hoặc triển khai nó như chứng nhận trang an toàn.
- Rule là tín hiệu triage minh bạch, không phải kết luận malware, phishing hay đánh giá bảo mật toàn diện.
- Báo rõ scan `partial`, `failed`, giới hạn và nguyên nhân. Không biến lỗi hoặc dữ liệu thiếu thành kết quả `safe`.
- Không tự mở rộng thành crawler toàn website, CAPTCHA/login bypass, malware scanner, threat intelligence hoặc phân tích toàn diện iframe/shadow DOM.

## 2. Quy trình làm việc cho AI

Trước khi sửa code:

1. Đọc yêu cầu liên quan trong `docs/recommendation.md` và `docs/specification.md`; kiểm tra thêm `docs/context-engineering.md`, API contract hoặc domain model nếu thay đổi chạm tới chúng.
2. Xác định requirement/acceptance criterion đang giải quyết và các module, model, API hay dữ liệu bị ảnh hưởng.
3. Giữ thay đổi nhỏ, có thể review, và phù hợp với kiến trúc đang có. Không tự giả định những phần mới như database, browser worker hay API đã tồn tại.
4. Nếu tài liệu chưa chốt chính sách ảnh hưởng đến bảo mật, quyền riêng tư, retention hoặc contract công khai, không âm thầm chọn hành vi nguy hiểm; ghi rõ giả định hoặc nêu điểm cần quyết định.

Khi hoàn tất, tóm tắt file/hành vi đã đổi, requirement được đáp ứng và kiểm tra đã thực hiện. Không tuyên bố tính năng đã hoàn thành nếu mới chỉ có skeleton hoặc contract.

## 3. Python và chất lượng code

- Hỗ trợ Python 3.11 trở lên; giữ source package trong `src/hidden_link_checker`.
- Dùng tên biến, hàm, class và module bằng tiếng Anh, rõ nghĩa; nội dung giải thích cho người dùng có thể được bản địa hóa.
- Dùng type hint cho API công khai và các cấu trúc dữ liệu quan trọng. Chọn `dataclass`, `Enum`/`StrEnum` hoặc kiểu hiện có của dự án thay vì tạo abstraction không cần thiết.
- Ưu tiên hàm nhỏ, một trách nhiệm, dữ liệu vào/ra rõ ràng và dependency được truyền vào khi cần thay thế trong test.
- Tránh trạng thái toàn cục có thể thay đổi, side effect ẩn, lặp logic và phụ thuộc vòng giữa extractor, evaluator, persistence và API.
- Không tạo biến trung gian nếu không làm rõ ý nghĩa; cũng không nhồi logic vào một biểu thức chỉ để giảm số dòng. Biến trong vòng lặp là bình thường khi cần biểu diễn từng phần tử.
- Không nuốt exception bằng `except` rộng hoặc trả kết quả mặc định khiến lỗi trông như thành công. Bắt loại lỗi dự kiến, chuyển thành lỗi/trạng thái domain có kiểm soát và giữ nguyên nguyên nhân nội bộ phù hợp.
- Không đưa secret, password, cookie, authorization header, nội dung trang đầy đủ hoặc query string nhạy cảm vào log, exception trả về client hay fixture công khai.
- Giữ dòng code tối đa 100 ký tự theo `pyproject.toml`; dùng standard library nếu đáp ứng yêu cầu, chỉ thêm dependency khi có lý do rõ ràng.

## 4. Ranh giới kiến trúc và dữ liệu

Giữ các trách nhiệm tách biệt:

- **Scanner/extractor:** đọc DOM/HTML/style trong phạm vi cho phép và tạo finding thô cho text, image, background; không quyết định chính sách persistence hoặc quyền truy cập.
- **URL policy/navigation:** xác thực URL, DNS/IP, redirect và giới hạn tài nguyên trước khi browser worker truy cập mạng.
- **Rule evaluator:** nhận finding và ngữ cảnh cần thiết, trả severity cùng rule khớp; không tự truy cập mạng hay database.
- **Persistence/API:** xác thực user, kiểm tra ownership, lưu và trả contract; không tự diễn giải lại rule.
- **Presentation:** trình bày đúng status, severity, matched rules, bằng chứng và giới hạn scan; không tự nâng/hạ severity.

Giữ contract Finding nhất quán với `docs/specification.md`: loại element; `source_url`; `normalized_url`; text/alt/content liên quan; position có thể `null`; đúng một severity; danh sách `matched_rules`. Không âm thầm đổi tên, kiểu hoặc ý nghĩa field công khai. Nếu cần đổi, cập nhật contract và các consumer cùng lúc.

URL tương đối phải được resolve theo URL trang cuối cùng đã được worker xác nhận. Luôn giữ URL nguồn để người dùng có thể so sánh với URL đã chuẩn hóa. Không tự loại bỏ bằng chứng cần thiết để giải thích finding.

## 5. Quy tắc severity và giải thích

- `critical`: rule keyword đã cấu hình khớp với URL hoặc nội dung finding theo specification.
- `warning`: tín hiệu cần người dùng kiểm tra, gồm destination khác origin, redirect bất thường, scheme cần xem xét hoặc dữ liệu thiếu theo policy.
- `safe`: không có rule rủi ro nào khớp; `matched_rules` rỗng.
- Nếu nhiều rule khớp, chọn severity cao nhất theo thứ tự `safe < warning < critical` nhưng vẫn trả về tất cả rule khớp cần giải thích.
- Mỗi rule phải có tên ổn định, severity, điều kiện khớp, lý do/evidence có thể trình bày và test riêng.
- Không dùng điểm rủi ro mơ hồ, ML hoặc kết luận tuyệt đối thay cho rule minh bạch nếu chưa có yêu cầu được chấp thuận trong đặc tả.

## 6. Bảo mật và SSRF — quy tắc bắt buộc

Mọi code khiến server hoặc worker truy cập URL do user cung cấp phải duy trì các kiểm soát sau:

- Chỉ cho phép scheme `http` và `https`; từ chối scheme, URL lỗi định dạng và địa chỉ không hợp lệ trước khi navigation.
- Chặn localhost, loopback, private, link-local, multicast, địa chỉ nội bộ và cloud metadata endpoint.
- Resolve DNS và kiểm tra **mọi** địa chỉ IP có thể được dùng để kết nối; chống DNS rebinding bằng cách gắn kiểm tra với kết nối thực tế hoặc dùng egress/network policy tương đương.
- Lặp lại kiểm tra policy sau **mỗi redirect**; giới hạn số redirect và từ chối redirect tới đích bị cấm.
- Đặt timeout và giới hạn kích thước response, CPU, RAM, thời gian browser và concurrency. Giới hạn phải được cấu hình tập trung, không rải magic number.
- Không gửi cookie, authorization header, thông tin xác thực hay application secret tới trang đích. Browser worker phải được cô lập và không có quyền truy cập trực tiếp database hoặc secret không cần thiết.
- Không tin `Content-Type`, DNS result, URL đã validate trước đó hoặc kiểm tra ở API là đủ để bỏ qua kiểm soát tại worker.
- Không bắt đầu network access nếu policy validation thất bại; trả lỗi có kiểm soát và không để lộ chi tiết hạ tầng.

Thay đổi liên quan navigation, redirect, DNS, browser hoặc worker phải được review như thay đổi bảo mật. Không vô hiệu hóa SSRF control để làm test hay demo chạy được.

## 7. Authentication, quyền riêng tư và lưu trữ

- Không bao giờ lưu hoặc log password dạng rõ; dùng cơ chế hash password phù hợp khi triển khai authentication.
- Mọi truy vấn scan, finding và snapshot phải giới hạn theo `user_id` đã xác thực ở server. Không coi việc biết `scan_id` là quyền truy cập.
- Xóa scan phải xóa hoặc đánh dấu xóa finding và snapshot liên quan theo retention policy; không để bản sao mồ côi vượt qua chính sách.
- Hạn chế lưu và log query string nhạy cảm, HTML, snapshot và nội dung trang. Dùng thời hạn retention rõ ràng và hỗ trợ xóa dữ liệu.
- Không trả stack trace, secret, nội dung trang riêng tư hoặc thông tin tài khoản khác trong response lỗi.

## 8. Trạng thái scan và xử lý lỗi

- Tuân thủ lifecycle `queued -> running -> completed | partial | failed`.
- Chỉ dùng `completed` khi xử lý xong trong phạm vi dự kiến; dùng `partial` khi có kết quả nhưng nội dung/nguồn bị giới hạn; dùng `failed` khi không có kết quả usable.
- Lưu thời điểm và mã lỗi có kiểm soát cần thiết để giải thích kết quả. Phân biệt timeout, 403, 429, lỗi TLS/network, CAPTCHA/login và giới hạn tài nguyên khi có thể.
- Lỗi một phần không được xóa kết quả hợp lệ đã thu thập; đồng thời phải hiển thị limitation để người dùng không hiểu nhầm scan toàn diện.
- API không được crash vì lỗi URL hoặc worker dự kiến. Không retry vô hạn; retry phải có giới hạn và không bỏ qua policy bảo mật.

## 9. Quy tắc kiểm thử

Khi thay đổi hành vi, bổ sung hoặc cập nhật test tương ứng; test phải kiểm tra hành vi và contract thay vì chi tiết triển khai nội bộ.

### C0 bắt buộc cho test do AI tạo

- C0 được hiểu là **statement coverage**: mọi câu lệnh có thể thực thi trong phạm vi đo phải được chạy ít nhất một lần.
- Test case hoặc bộ test do AI tạo phải đạt **100% C0 cho toàn bộ module production được thêm hoặc thay đổi**. Không tính file test, mã sinh tự động và mã cấu hình vào phạm vi coverage.
- Phải đo coverage bằng công cụ coverage phù hợp và xem báo cáo theo từng file; không suy luận coverage từ việc test pass, không bỏ qua file chưa đạt và không sửa ngưỡng hoặc phạm vi đo để làm đẹp kết quả.
- Nếu còn câu lệnh chưa thể chạy (ví dụ code phụ thuộc nền tảng hoặc nhánh vận hành không thể tái hiện), nêu rõ từng dòng/lý do và xin quyết định trước khi xem thay đổi là hoàn tất; không tự đánh dấu ngoại lệ.
- 100% C0 không thay thế kiểm tra nhánh, điều kiện biên, lỗi bảo mật hoặc chất lượng assertion. Bổ sung test cho các nhánh quan trọng theo yêu cầu bên dưới.

- **Extractor:** text link, image `src`/`srcset`, link bao quanh ảnh khi hỗ trợ, inline/style background, URL tương đối theo final URL, HTML thiếu chuẩn và position có thể thiếu.
- **Rule evaluator:** từng rule, nhiều rule đồng thời và ưu tiên severity; `critical` có `matched_rules`; external destination ít nhất là `warning`; trường hợp không khớp là `safe` với danh sách rỗng.
- **SSRF/navigation:** scheme bị cấm, localhost/private/metadata, DNS trả nhiều IP, DNS rebinding phù hợp kiến trúc, redirect tới IP cấm và giới hạn timeout/response.
- **Authorization/privacy:** truy cập và xóa dữ liệu của user khác phải bị từ chối; kiểm tra xóa liên đới và không lộ secret trong log/response.
- **Lifecycle:** timeout, lỗi mạng và giới hạn tài nguyên cho trạng thái `partial` hoặc `failed` đúng contract.
- Dùng fixture HTML/URL tổng hợp; không phụ thuộc website bên ngoài, DNS công cộng hoặc thời điểm chạy.
- Với rule/config mới, test giải thích phải xác nhận tên rule/evidence được trả ra, không chỉ xác nhận màu hoặc severity.

## 10. Quy tắc thay đổi tài liệu và API

- Khi đổi endpoint, request/response, status, finding field hoặc ý nghĩa severity, đồng bộ `docs/specification.md`, `docs/api-spec.md` và các consumer có liên quan.
- Khi đổi phạm vi sản phẩm hoặc quyết định khách hàng, cập nhật `docs/recommendation.md` chỉ khi thay đổi đã được quyết định; không sửa tài liệu định hướng để hợp thức hóa việc mở rộng tùy ý.
- Tài liệu phải phân biệt rõ tính năng hiện có với tính năng dự kiến. Ví dụ: browser worker, dashboard, authentication và database không được mô tả như đã triển khai nếu repository chưa có.
- Không thêm dependency, dịch vụ bên ngoài hoặc schema lưu dữ liệu mới mà không giải thích nhu cầu, tác động bảo mật/quyền riêng tư và cách vận hành.

## 11. Definition of done

Một thay đổi được xem là hoàn tất khi:

1. Đáp ứng requirement/acceptance criterion đã nêu và không vượt ranh giới MVP.
2. Contract, phân quyền, trạng thái lỗi và giới hạn bảo mật liên quan được giữ đúng.
3. Có test cho hành vi thay đổi và tài liệu được đồng bộ khi contract/phạm vi đổi.
4. Không ghi nhận secret hoặc dữ liệu nhạy cảm ngoài policy.
5. Kết quả kiểm tra được báo trung thực; nêu rõ phần chưa triển khai hoặc limitation còn lại.

## 12. Mô tả code và comment

- Không thêm comment tràn lan hoặc dùng comment để diễn giải lại từng dòng code. Ưu tiên viết code và tên định danh đủ rõ để tự giải thích.
- Tập trung docstring vào hàm/method có API công khai, logic nghiệp vụ hoặc hành vi không hiển nhiên. Mô tả ngắn gọn mục đích và kết quả/hành vi của hàm.
- Giải thích tham số khi ý nghĩa, định dạng, đơn vị, giá trị mặc định hoặc ràng buộc của chúng không thể hiểu rõ từ tên và kiểu dữ liệu. Mô tả giá trị trả về hoặc exception quan trọng nếu người gọi cần biết.
- Ghi rõ lưu ý quan trọng khi gọi hàm, như thứ tự gọi, điều kiện tiên quyết, side effect, giới hạn bảo mật/tài nguyên hoặc cách xử lý lỗi. Đặt lưu ý gần định nghĩa hàm để người gọi dễ tìm.
- Không cần docstring cho hàm private đơn giản nếu tên và phần triển khai đã rõ. Không ghi comment lỗi thời, suy đoán hoặc TODO chung chung; cập nhật hoặc xóa comment khi hành vi code thay đổi.
