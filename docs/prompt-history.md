# Lịch sử prompt

Tài liệu này liệt kê nguyên văn các prompt người dùng đã gửi trong phiên làm việc hiện tại, kèm tóm tắt ngắn gọn kết quả/hành động đã thực hiện cho mỗi prompt.

## Prompt 1

Bạn là Senior Software Architect và Senior Python Developer trên dự án Hidden Link Checker.

Đọc README.md, CONTRIBUTING.md, Recommendation.md và toàn bộ docs/ hiện có.

Hãy báo cáo:

- Phạm vi sản phẩm và người dùng;

- Business requirements, functional requirements và acceptance criteria;

- Domain entities, lifecycle và invariant;

- API contract;

- Rủi ro bảo mật, đặc biệt SSRF, authentication, ownership và dữ liệu nhạy cảm.

Sau khi báo cáo, đề xuất danh sách tài liệu cần có và nội dung/file nào cần

tạo hoặc cập nhật. Chưa sửa file cho tới khi tôi duyệt danh sách.

## Prompt 2

Triển khai PostgreSQL persistence cho Hidden Link Checker theo quyết định

database-guide.md và domain/API contract đã duyệt.

Yêu cầu:

- SQLAlchemy models/repositories và Alembic migrations;

- lưu user, scan và findings theo contract;

- enforce ownership ở mọi thao tác đọc/xóa;

- transaction và unique/foreign-key constraints phù hợp;

- secrets chỉ lấy từ environment/configuration, không commit credential;

- không để browser worker truy cập database trực tiếp.

Thêm cấu hình PostgreSQL local qua Docker Compose nếu chưa có. Viết integration

test chạy trên PostgreSQL; Trước khi sửa, liệt kê file và migration dự kiến

## Prompt 3

Bạn là Senior PostgreSQL Database Architect và Senior Python Developer.

Hãy triển khai database PostgreSQL cho dự án Hidden Link Checker dựa trên tài liệu:

docs/database-guide.md

docs/domain-model.md

docs/specification.md

docs/api-spec.md

docs/recommendation.md

Thông tin kết nối:

Database đã tồn tại: hidden_link_checker

PostgreSQL host: localhost

Port: 5432

Username: postgres

Password: lấy từ biến môi trường .env

PGPASSWORD, không hard-code và không ghi password vào file/log

Lưu ý:

Không tạo lại hoặc xóa database hidden_link_checker.

Không chạy DROP DATABASE, DROP TABLE hoặc xóa dữ liệu hiện có.

Kiểm tra schema hiện tại trước khi migration.

Nếu object đã tồn tại, giữ nguyên dữ liệu và chỉ tạo/cập nhật phần còn thiếu.

Nếu schema hiện tại không tương thích, dừng lại và báo cáo, không tự ý phá dữ liệu.

Mục tiêu database MVP:

Tạo PostgreSQL extension cần thiết, tối thiểu pgcrypto.

Tạo các enum:

user_status: active, disabled

link_check_status: queued, running, completed, partial, failed

link_element_type: text, image, background

link_visibility: direct, indirect

Tạo các bảng:

users

link_checks

link_results

Tạo quan hệ:

users.id -> link_checks.user_id

link_checks.id -> link_results.link_check_id

Sử dụng foreign key và ON DELETE CASCADE phù hợp.

Tạo các cột đúng theo docs/database-guide.md:

users: google_subject, email, display_name, avatar_url, status,

created_at, updated_at, last_login_at

link_checks: submitted_url, normalized_url, final_url, status,

http_status, error_code, dom_reference, limitations, notes,

created_at, updated_at, started_at, completed_at,

retention_expires_at

link_results: element_type, object_reference, source_url, actual_url,

visibility, visible_text, alt_text, position, created_at

Tạo các constraint:

google_subject là duy nhất.

URL có giới hạn độ dài hợp lý.

HTTP status nằm trong khoảng 100-599.

limitations phải là JSON array.

position phải là JSON object hoặc NULL.

visibility chỉ nhận direct hoặc indirect.

actual_url chỉ là dữ liệu kết quả, không được dùng để tự động fetch.

Tạo index:

users.google_subject

link_checks(user_id, created_at DESC)

link_checks(status, created_at DESC)

link_checks(retention_expires_at)

link_results(link_check_id, created_at)

link_results(visibility)

link_results(actual_url)

Tạo trigger cập nhật updated_at cho users và link_checks.

Tạo migration/query mẫu cho:

Tạo link check theo authenticated user.

Lưu nhiều link result trong cùng transaction.

Lấy chi tiết link check theo user ownership.

Lấy lịch sử link check của user.

Lọc link result theo visibility.

Cập nhật notes theo user ownership.

Xóa link check theo user ownership.

Xóa dữ liệu hết retention.

Nếu ứng dụng dùng server-side session, tạo thêm user_sessions với:

user_id

token_hash

expires_at

revoked_at

Không lưu session token plaintext.

Yêu cầu bảo mật:

Không nhận user_id từ client để quyết định ownership.

Mọi query public phải kiểm tra authenticated_user_id.

Không lưu password hoặc Google access token.

Không cấp quyền database trực tiếp cho browser worker.

Dùng parameterized query, không nối chuỗi SQL với user input.

Không log OAuth token, session token, raw query string nhạy cảm hoặc DOM đầy đủ.

Không tự động mở, redirect hoặc request tới actual_url trong link_results.

Quy trình thực hiện:

Kiểm tra PostgreSQL connection và role.

Kiểm tra database hidden_link_checker đã tồn tại.

Kiểm tra schema, table, enum, constraint, index và trigger hiện có.

Sinh migration SQL an toàn, có thể chạy nhiều lần mà không làm mất dữ liệu.

Chạy migration trong database hidden_link_checker.

Kiểm tra lại bằng catalog PostgreSQL:

information_schema.tables

pg_type

pg_constraint

pg_indexes

pg_trigger

Chạy các query smoke test không phá dữ liệu.

Báo cáo:

Objects đã tạo.

Objects đã tồn tại và được giữ nguyên.

Migration nào đã chạy.

Các lỗi hoặc khác biệt schema.

Cách rollback an toàn nếu cần.

Cập nhật rule tạo database vào docs/database-guide.md. Chuyển thư mục migrations vào git ignore.

## Prompt 4

Update tính năng Google OAuth cho Hidden Link Checker, follow

specification.md, api-spec.md, domain-model.md và coding-rules.md.

Yêu cầu cho tôi xác định các quyết định cần chốt: session hay token, cookie flags, OAuth state,

PKCE nếu phù hợp, account linking, email verification, logout/revocation,

CSRF, redirect URI và quản lý secrets. Không tự suy diễn account

linking hoặc authorization.

Đề xuất cập nhật tài liệu trước. Sau khi được duyệt,

triển khai OAuth callback, tạo / liên kết user an toàn, session lifecycle,

authorization và ownership checks.
Thêm test cho state mismatch, callback lỗi,

account conflict, session expiry và truy cập dữ liệu user khác. Không ghi

token, authorization code hoặc secret vào log.

## Prompt 5

Triển khai vertical slice UI/API cho Hidden Link Checker dựa trên API contract

đã duyệt.

Luồng:

1. Người dùng đăng nhập.

2. Nhập hoặc dán page URL.

3. Gửi scan và xem trạng thái queued/running/completed/partial/failed.

4. Xem findings, normalized URL, element type, severity, matched rules,

   counts và limitation.

5. Chỉ truy cập scan thuộc user hiện tại.

Tạo UI nhập URL bằng text field phù hợp, hỗ trợ URL dài mà không tràn layout.

Hiển thị lỗi validation và limitation rõ ràng. Không làm crawler, CAPTCHA

bypass hoặc tự động đăng nhập vào website đích.

Enforce authentication/ownership phía server; frontend không được xem là

ranh giới bảo mật. Trước khi triển khai, báo cáo các file cần thay đổi.

## Prompt 6

Trước khi làm tax_calculation, kiểm tra xem tính năng này có requirement hoặc

tài liệu nào trong repository không. Nếu không có, không gắn nó vào Hidden

Link Checker một cách mặc định.

Hãy hỏi/ghi nhận:

- đây là sản phẩm/module riêng hay tính năng mới của Hidden Link Checker;

- quốc gia và loại thuế;

- loại giao dịch, đầu vào/đầu ra, làm tròn và thời điểm áp dụng;

- nguồn dữ liệu và yêu cầu pháp lý;

- API/UI, quyền truy cập và lưu trữ dữ liệu.

Sau khi có scope được duyệt, viết specification và test cases trước khi

triển khai. Không tự đưa ra kết luận thuế pháp lý hoặc tự đặt công thức khi

thiếu quy tắc nghiệp vụ.

## Prompt 7

Tại repo HiddenLinkChecker: Bạn hãy ghi phần hướng dẫn chạy test thư viện tax_calculation và 1 mục riêng trong README

Có mẫu file JSON input và file mẫu output

## Prompt 8

Tôi có 1 code thư viện TaxCalculationLibrary. Tôi cần build thư viện theo hướng dẫn ở README.md của project này.

Tại Project HIddenLinkChecker, tạo 1 module riêng cho phép gọi thư viện đó.

Tạo 5 file input mẫu thực tế phù hợp với input của TaxCalculationLibrary, để chạy bên Project HIddenLinkChecker

## Prompt 9

Bạn tạo lại 10 input mẫu, mỗi input phải đạt tối thiểu 10 dòng

Xuất cả input và output tương ứng trong thư mục examples

## Prompt 10

Hoàn thiện các phần còn thiếu của dự án để đạt 100% như mô tả của recommendation, spec. Tuân thủ coding-rule và các tài liệu trong docs/

## Prompt 11

Tại trang kết quả inspection, bạn cần giới hạn độ dài của view không được vượt quá panel, nếu quá dài thì phải có thanh trượt. Và phải có padding với panel

Tạo thêm chức năng phân trang. Mặc định và tối thiểu là 20 dòng 1 trang. Tối đa là 100 dòng. Cần tính toán đến việc lưu dữ liệu đã check vào một nơi tạm để tính năng phân trang không khiến cho chương trình phải chạy lại, dẫn tới tăng thời gian tải

## Prompt 12

Có 1 lỗi khi phân trang. GIả sử hiển thị 20 thì dòng hidden link(s) found. Chỉ hiện 20 trong khi có tới 109 records. Bạn hãy fix lại để dòng này thống kê số tổng

## Prompt 13

Build 2 file cmd để start API và Server

Chưa thấy phần database được xử lý. Sau khi tắt trình duyệt và xóa section thì dữ liệu của user trả về 0 hết. Không có data nào được lưu vào database

Đối với các trang lỗi cần xây dựng 1 giao diện báo lỗi thay vì là để mặc định

## Prompt 14

Dựa trên docs/specification.md và docs/recommendation.md, chuyển endpoint POST /v1/link-checks sang xử lý đồng bộ: xác thực URL, fetch/render chỉ URL đầu vào, trích xuất link, trả kết quả cùng response và sau khi xử lý chỉ lưu lịch sử URL tối giản. Hidden link, DOM và trạng thái xử lý không được lưu lâu dài. Loại bỏ các đường đi queue/detail/history status chỉ khi không còn cần theo contract mới. Cập nhật shared API models, service, controller, web API client, dashboard và tài liệu để thống nhất. Đảm bảo hidden link không bao giờ được request hoặc điều hướng tới. Thêm kiểm thử unit và integration cho luồng thành công, lỗi và privacy.

## Prompt 15

Hãy xử lý các giới hạn còn lại: bộ xử lý hiện fetch HTML tĩnh, không chạy JavaScript hoặc render bằng browser; các trang có script được trả trạng thái partial. Test dùng mock HTTP và in-memory history, chưa chạy với PostgreSQL thật.

## Prompt 16

Xây dựng thành phần fetch URL đầu vào có giới hạn và tích hợp ensure_safe_navigation_url vào luồng kiểm tra đồng bộ. Chỉ cho phép HTTP/HTTPS; kiểm tra DNS/IP trước kết nối và sau từng redirect; chặn địa chỉ private, loopback, link-local, multicast, reserved và metadata. Giới hạn thời gian, redirect, kích thước response và concurrency; không chuyển cookie, authorization header hoặc application secret tới host đích. Xử lý DNS rebinding bằng cách bảo đảm IP được xác minh là IP dùng để kết nối. Trả lỗi có kiểm soát theo failed hoặc partial. Không truy cập bất kỳ URL phát hiện nào trong DOM. Thêm kiểm thử cho redirect tới IP nội bộ, timeout, response quá lớn và lỗi mạng.

## Prompt 17

Triển khai UrlCheckRepository PostgreSQL dùng bảng url_checks để ghi và đọc lịch sử (url, checked_at) theo authenticated user_id. Dùng parameterized query, transaction phù hợp, index truy vấn theo user và thao tác xóa có điều kiện ownership. Thay repository in-memory khỏi cấu hình mặc định production; chỉ giữ adapter in-memory cho test/dev. Kiểm tra chuỗi migration có tạo đầy đủ schema users trước các migration auth/history, và bổ sung migration khởi tạo nếu đang thiếu. Không lưu DOM hoặc link result. Thêm kiểm thử repository và API ownership.

## Prompt 18

Cập nhật dashboard để gửi URL tới API đồng bộ và hiển thị kết quả ngay sau response: URL đầu vào, trạng thái, limitations, danh sách link, element type, visibility, object reference, source URL, actual URL và các trường DOM được phép hiển thị. Thêm bộ lọc theo visibility và element type trên kết quả của lần gọi hiện tại. Hiển thị lỗi partial/failed rõ ràng. Giữ mọi thao tác dữ liệu qua API; không để frontend truy cập database. Thêm kiểm thử rendering và API client.

## Prompt 19

Rà soát luồng kiểm tra để các lỗi validation, DNS, TLS, HTTP 403/429, timeout, lỗi worker/parser và giới hạn tài nguyên đều trả response có kiểm soát, không làm API crash và không lộ secret. Ánh xạ kết quả phù hợp sang completed, partial hoặc failed; ghi limitations đủ để dashboard giải thích phần không đọc được. Đảm bảo kể cả scan lỗi cũng chỉ lưu lịch sử URL theo policy đã thống nhất, không lưu kết quả scan. Thêm test cho từng nhóm lỗi quan trọng.

## Prompt 20

Đối chiếu README, API spec, database guide, domain model, coding rules và migration với recommendation/spec hiện tại. Loại bỏ mô tả không còn đúng về queue, xử lý bất đồng bộ, lưu link result và trạng thái cũ; mô tả contract đồng bộ, dữ liệu lịch sử tối giản, giới hạn SSRF và cách cấu hình production. Lập bảng truy vết FR-001 đến FR-008 và AC-01 đến AC-06 tới module và test tương ứng; đánh dấu rõ mục nào đã đáp ứng, còn thiếu hoặc chưa được xác minh. Không tuyên bố tiêu chí đã đạt nếu chưa có bằng chứng.
