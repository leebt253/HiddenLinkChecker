# Hidden Link Checker - Ý tưởng sản phẩm

Web app giúp phát hiện các URL bị ẩn trong một trang web và đánh giá nhanh nguy cơ trang đó có dấu hiệu lừa đảo hay không. Người dùng đăng ký, đăng nhập, nhập URL cần kiểm tra và xem kết quả trực quan trên dashboard.

> **Trạng thái dự án:** đang ở giai đoạn đặc tả và chuẩn bị triển khai MVP.

## Ý tưởng sản phẩm

Hidden Link Checker mô phỏng một phần thao tác inspect trang web để tìm các URL không dễ nhìn thấy trên giao diện. Mỗi URL được gắn với phần tử hoặc vùng nội dung đã chứa nó, giúp người dùng đối chiếu giữa nội dung đang hiển thị và link thực tế bên dưới.

```text
Đăng nhập -> nhập URL -> tải trang an toàn -> phát hiện nội dung và URL ẩn
          -> áp dụng rule -> hiển thị trên dashboard grid -> lưu kết quả
```

Mục tiêu của MVP là hỗ trợ phân tích nhanh và giải thích được kết quả, không phải thay thế các hệ thống threat intelligence hoặc malware scanner chuyên dụng.

## Phạm vi MVP

### Các loại link cần phát hiện

Phân tích DOM và style của trang để tìm link gắn với:

- **Text:** `href` của các thẻ như `<a>` hoặc phần tử có hành vi điều hướng, kèm nội dung text hiển thị.
- **Image:** `src`, `srcset`, link bao quanh ảnh và các URL được khai báo trên phần tử hình ảnh.
- **Background:** URL trong `background`, `background-image` hoặc style tương đương của inline style và stylesheet có thể đọc được.
- **Nội dung hiển thị:** ảnh chụp hoặc snapshot của trang để người dùng xem vùng hiển thị cùng các điểm có URL ẩn.

Mỗi phát hiện nên lưu loại phần tử, nội dung hiển thị, URL gốc, URL đã chuẩn hóa, vị trí tương đối trên trang và rule đã kích hoạt.

### Dashboard

Dashboard cần trình bày kết quả theo cách dễ đối chiếu:

- Tổng số link được phát hiện.
- Số lượng kết quả `safe`, `warning` và `critical`.
- Grid các item phát hiện, mỗi item gồm preview nội dung hoặc ảnh, loại phần tử, text/alt liên quan, URL ẩn và mức đánh giá.
- Highlight hoặc đánh dấu vị trí của link trên snapshot trang.
- Bộ lọc theo mức độ, loại phần tử và domain.
- Trang chi tiết của một lần kiểm tra và lịch sử các lần kiểm tra.

Ví dụ một item trên grid:

| Preview nội dung | Thông tin phát hiện | Đánh giá |
|---|---|---|
| Text hoặc image trên trang | `href`, loại phần tử, text/alt, domain | `critical` / `warning` / `safe` |

## Rule đánh giá ban đầu

MVP dùng rule-based validation, ưu tiên tính minh bạch và khả năng giải thích. Rule không kết luận tuyệt đối rằng website là malware; nó chỉ đánh giá tín hiệu rủi ro trong nội dung và URL đã phát hiện.

| Mức | Điều kiện ví dụ | Ý nghĩa |
|---|---|---|
| `critical` | URL, text, alt text hoặc nội dung liên quan chứa từ khóa cờ bạc như `casino`, `bet`, `poker`, `slot`, `gambling` | Tín hiệu rủi ro cao theo rule hiện tại |
| `warning` | URL ngoài domain, redirect bất thường, scheme không phổ biến hoặc có dấu hiệu cần xem xét thêm | Cần người dùng kiểm tra thủ công |
| `safe` | Không kích hoạt rule rủi ro nào đã cấu hình | Chưa phát hiện tín hiệu đáng ngờ trong phạm vi scan |

Các keyword, mức độ và thông báo giải thích phải được cấu hình tập trung, không hard-code rải rác trong parser. Một kết quả nên trả cả `matched_rules` để người dùng biết vì sao item bị đánh giá ở mức đó.

## Cách phân tích

MVP nên dùng browser automation trong worker cô lập để có DOM và style gần với những gì người dùng thấy khi inspect trang:

1. Tải URL với chính sách network an toàn.
2. Chờ trang ổn định trong giới hạn thời gian.
3. Đọc DOM, thuộc tính của element và các style có thể truy cập.
4. Thu thập URL từ text link, image và background.
5. Chụp snapshot và ghi nhận bounding box của element.
6. Chuẩn hóa URL, chạy rule và tạo kết quả.
7. Lưu metadata, snapshot và kết quả theo user.

JavaScript động, iframe cross-origin, shadow DOM, nội dung cần đăng nhập hoặc bị CAPTCHA có thể khiến kết quả không đầy đủ. Hệ thống phải ghi rõ trạng thái và giới hạn này thay vì coi scan là toàn diện.

## Kiến trúc dự kiến

```text
Browser
   |
   v
Web App: Login, Scan Form, Dashboard, History
   |
   v
API + Authentication
   |
   +--> Scan API --> Queue --> Isolated Browser Worker
   |                               |
   |                               +--> Link Extractor
   |                               +--> Snapshot Builder
   |                               +--> Rule Evaluator
   |
   +--> Result and History API
   |
   v
Database + Snapshot/Object Storage
```

### Các thành phần chính

- **Authentication:** đăng ký, đăng nhập, logout, hash mật khẩu và quản lý session/token.
- **Scan API:** nhận URL, tạo scan job và trả trạng thái xử lý.
- **Browser worker:** render trang và thu thập link trong môi trường sandbox.
- **Link extractor:** phân tích text, image, background và vị trí hiển thị.
- **Rule evaluator:** áp keyword/rule để gắn `critical`, `warning` hoặc `safe`.
- **Dashboard:** hiển thị snapshot, grid phát hiện, thống kê và bộ lọc.
- **Database:** lưu user, scan, link finding, mức đánh giá và lịch sử.
- **Snapshot storage:** lưu ảnh hoặc artifact cần thiết theo retention policy.

## API dự kiến

### Authentication

```http
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/logout
GET  /v1/me
```

Đăng ký cần kiểm tra email, chính sách mật khẩu và không lưu password dạng plain text.

### Tạo scan

```http
POST /v1/scans
```

Request dự kiến:

```json
{
  "url": "https://example.com",
  "include_snapshot": true
}
```

Response ban đầu:

```json
{
  "scan_id": "scan_123",
  "status": "queued",
  "created_at": "2026-09-22T10:00:00Z"
}
```

### Lấy kết quả

```http
GET /v1/scans/{scan_id}
GET /v1/scans/{scan_id}/findings
```

Kết quả gồm snapshot, thống kê theo mức độ, danh sách finding, URL, loại phần tử, nội dung hiển thị, vị trí, rule đã khớp và giới hạn của lần scan.

### Lịch sử và xóa dữ liệu

```http
GET    /v1/me/scans
DELETE /v1/scans/{scan_id}
```

Mọi truy vấn phải giới hạn theo user đang đăng nhập. Không được để user đoán `scan_id` rồi đọc kết quả của user khác.

## Mô hình dữ liệu

### `User`

- `id`, `email`, `password_hash`
- `status`, `created_at`, `last_login_at`

### `Scan`

- `id`, `user_id`
- `submitted_url`, `normalized_url`, `final_url`
- `status`, `http_status`, `error_code`
- `snapshot_url` hoặc reference tới object storage
- `safe_count`, `warning_count`, `critical_count`
- `created_at`, `completed_at`, `retention_expires_at`

### `Finding`

- `id`, `scan_id`
- `element_type`: `text`, `image`, `background`
- `source_url`, `normalized_url`
- `visible_text`, `alt_text`, `matched_content`
- `position` hoặc bounding box trên snapshot
- `severity`: `safe`, `warning`, `critical`
- `matched_rules`

Snapshot và dữ liệu URL có thể chứa thông tin nhạy cảm, nên cần retention policy, quyền truy cập theo user và cơ chế xóa hoàn toàn.

## Bảo mật

Việc server nhận và render URL do user nhập có rủi ro **SSRF** và rủi ro từ JavaScript của trang đích. Worker cần:

- Chỉ cho phép URL `http` và `https`.
- Từ chối localhost, loopback, private IP, link-local, multicast và cloud metadata endpoint.
- Resolve DNS và kiểm tra IP sau mỗi redirect.
- Giới hạn timeout, số redirect, response size, CPU, RAM và thời gian browser.
- Không gửi cookie, authorization header hoặc secret nội bộ tới trang đích.
- Chạy browser worker trong sandbox/container không có quyền truy cập database trực tiếp.
- Rate limit theo user/IP và giới hạn số scan đồng thời.
- Che hoặc loại query string nhạy cảm khỏi log và giao diện khi cần.
- Không tuyên bố `safe` là bảo đảm website an toàn tuyệt đối.

## Lộ trình

1. Chốt schema finding và cách xác định text, image, background.
2. Xây browser worker proof of concept tạo snapshot và bounding box.
3. Xây extractor cho `href`, image URL và CSS background.
4. Implement rule engine với mức `critical`, `warning`, `safe` và matched rule.
5. Xây đăng ký, đăng nhập, phân quyền và database.
6. Xây dashboard grid, bộ lọc, thống kê và trang lịch sử.
7. Bổ sung SSRF test, worker sandbox, rate limit và retention policy.

## Quyết định hiện tại

Hidden Link Checker là công cụ phân tích trực quan các URL ẩn trong text, image và background của một trang web. MVP sẽ tập trung vào browser-rendered snapshot, dashboard dạng grid, rule-based severity và lưu lịch sử theo user có tài khoản. `critical`, `warning` và `safe` là kết quả của các rule minh bạch, không phải kết luận bảo mật tuyệt đối.
