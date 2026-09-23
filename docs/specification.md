# Hidden Link Checker - Product Specification

## 1. Document status

- **Status:** MVP specification
- **Product guidance:** `docs/recommendation.md`
- **Product type:** authenticated web application
- **Primary user:** người dùng cần rà soát nhanh URL ẩn trong một trang web
- **Scope boundary:** phân tích một trang và các URL đọc được trong text, image, background; không phải malware scanner toàn diện

## 2. Product objective

Cho phép người dùng gửi một URL, render trang trong browser worker cô lập, phát hiện các URL không dễ nhìn thấy trên giao diện, đánh giá tín hiệu rủi ro bằng rule minh bạch và xem kết quả cùng ngữ cảnh trực quan.

## 3. Actors

| Actor | Quyền và trách nhiệm |
|---|---|
| Unauthenticated user | Đăng ký, đăng nhập |
| Authenticated user | Tạo scan, xem/xóa scan của mình, lọc findings |
| Scan worker | Render trang trong sandbox và phát hiện URL theo policy |
| Rule evaluator | Gán severity và matched rules |
| System administrator | Quản lý cấu hình rule, retention và giới hạn vận hành |

## 4. Functional requirements

### FR-001 Authentication

System phải hỗ trợ đăng ký, đăng nhập, đăng xuất và lấy thông tin user hiện tại. Password phải được hash; không lưu hoặc log password dạng plain text.

### FR-002 Create scan

Authenticated user có thể tạo scan bằng URL `http` hoặc `https`. Request tối thiểu:

```json
{
  "url": "https://example.com",
  "include_snapshot": true
}
```

System trả về scan ở trạng thái `queued` và không đồng bộ chờ browser hoàn tất.

### FR-003 Safe navigation

Trước và trong quá trình điều hướng, system phải:

- Chỉ cho phép scheme `http` và `https`.
- Chặn localhost, loopback, private IP, link-local, multicast và cloud metadata endpoint.
- Resolve và kiểm tra IP sau mỗi redirect.
- Giới hạn timeout, số redirect, response size, CPU, RAM và số scan đồng thời.
- Không gửi cookie, authorization header hoặc application secret tới trang đích.

### FR-004 Link extraction

Worker/extractor phải phát hiện các URL sau trong phạm vi DOM và style đọc được:

- `text`: `href` của anchor hoặc phần tử có hành vi điều hướng, kèm visible text.
- `image`: `src`, `srcset`, URL bao quanh ảnh và alt text liên quan.
- `background`: URL trong `background`, `background-image` hoặc style tương đương có thể đọc được.

URL tương đối phải được chuẩn hóa theo URL cuối cùng của trang. Mỗi finding phải giữ URL nguồn và URL chuẩn hóa.

### FR-005 Finding contract

```json
{
  "id": "finding_123",
  "scan_id": "scan_123",
  "element_type": "text",
  "source_url": "/offers/casino",
  "normalized_url": "https://example.com/offers/casino",
  "visible_text": "Claim reward",
  "alt_text": "",
  "matched_content": "casino",
  "position": {
    "x": 10,
    "y": 20,
    "width": 120,
    "height": 32
  },
  "severity": "critical",
  "matched_rules": ["gambling-keyword"]
}
```

`position` có thể là `null` nếu element không render được hoặc không lấy được bounding box.

### FR-006 Rule evaluation

Mỗi finding phải nhận đúng một severity:

| Severity | Điều kiện mặc định | Ý nghĩa |
|---|---|---|
| `critical` | URL, visible text, alt text hoặc content chứa keyword như `casino`, `bet`, `poker`, `slot`, `gambling` | Tín hiệu ưu tiên cao cần kiểm tra |
| `warning` | Destination ngoài origin, redirect bất thường, scheme cần xem xét hoặc dữ liệu thiếu | Cần kiểm tra thủ công |
| `safe` | Không có rule rủi ro nào khớp | Chưa phát hiện tín hiệu trong phạm vi scan |

Rule phải được cấu hình tập trung và trả về `matched_rules` cùng thông tin giải thích. Rule không được kết luận website là malware hoặc phishing.

### FR-007 Scan result and dashboard

Dashboard của scan hoàn tất phải hiển thị:

- Snapshot nếu user yêu cầu và snapshot tạo được.
- Tổng số findings.
- Số lượng `safe`, `warning`, `critical`.
- Grid finding gồm preview, element type, text/alt, URL và severity.
- Highlight hoặc dấu vị trí trên snapshot khi có bounding box.
- Bộ lọc theo severity, element type và domain.
- Danh sách giới hạn hoặc cảnh báo khi scan ở trạng thái `partial`.

### FR-008 Scan lifecycle

Scan phải hỗ trợ các trạng thái:

```text
queued -> running -> completed
                  -> partial
                  -> failed
```

- `completed`: xử lý xong trong phạm vi dự kiến.
- `partial`: có kết quả nhưng một phần nội dung không đọc được hoặc bị giới hạn.
- `failed`: không tạo được kết quả usable do lỗi validation, network hoặc worker.

Scan phải lưu `created_at`, `completed_at`, lỗi có kiểm soát và giới hạn gặp phải.

### FR-009 History and deletion

User có thể xem danh sách scan của chính mình, mở chi tiết và xóa scan. Mọi truy vấn scan, finding và snapshot phải lọc theo authenticated `user_id`. Xóa scan phải xóa hoặc đánh dấu xóa toàn bộ finding và snapshot liên quan theo retention policy.

## 5. API contract

| Method | Endpoint | Mục đích |
|---|---|---|
| `POST` | `/v1/auth/register` | Tạo tài khoản |
| `POST` | `/v1/auth/login` | Đăng nhập |
| `POST` | `/v1/auth/logout` | Đăng xuất |
| `GET` | `/v1/me` | Lấy user hiện tại |
| `POST` | `/v1/scans` | Tạo scan |
| `GET` | `/v1/scans/{scan_id}` | Lấy trạng thái và tổng quan scan |
| `GET` | `/v1/scans/{scan_id}/findings` | Lấy findings, có filter |
| `GET` | `/v1/me/scans` | Lấy lịch sử của user |
| `DELETE` | `/v1/scans/{scan_id}` | Xóa scan của user |

Response tạo scan tối thiểu:

```json
{
  "scan_id": "scan_123",
  "status": "queued",
  "created_at": "2026-09-22T10:00:00Z"
}
```

## 6. Data model

### User

`id`, `email`, `password_hash`, `status`, `created_at`, `last_login_at`

### Scan

`id`, `user_id`, `submitted_url`, `normalized_url`, `final_url`, `status`, `http_status`, `error_code`, `snapshot_reference`, `safe_count`, `warning_count`, `critical_count`, `created_at`, `completed_at`, `retention_expires_at`

### Finding

`id`, `scan_id`, `element_type`, `source_url`, `normalized_url`, `visible_text`, `alt_text`, `matched_content`, `position`, `severity`, `matched_rules`

## 7. Non-functional requirements

- **Security:** SSRF protection, sandbox worker, authentication và ownership checks.
- **Explainability:** mọi severity khác `safe` phải có rule và evidence; `safe` không được gọi là bảo đảm an toàn.
- **Privacy:** snapshot và URL có retention; hạn chế log query string nhạy cảm.
- **Reliability:** timeout, 403, 429, SSL error và HTML lỗi phải trả trạng thái có kiểm soát.
- **Performance:** static page nhỏ phải hoàn tất trong timeout cấu hình; dashboard không cần tải toàn bộ HTML.
- **Maintainability:** extractor, rule evaluator, persistence và UI contract phải tách biệt; rule có test riêng.

## 8. Known limitations

Kết quả có thể không đầy đủ khi trang dùng JavaScript động, iframe cross-origin, shadow DOM, yêu cầu đăng nhập, CAPTCHA, stylesheet không truy cập được hoặc vượt giới hạn tài nguyên. System phải ghi nhận limitation thay vì coi scan là toàn diện.

## 9. Acceptance criteria

### AC-01 Extraction

Với HTML có text link, image `src/srcset` và inline `background-image`, scan tạo finding tương ứng với `text`, `image` và `background`; URL tương đối được resolve theo final page URL.

### AC-02 Rule

Keyword gambling trong URL hoặc content tạo severity `critical` và `matched_rules` chứa rule tương ứng. External destination không khớp rule critical tạo tối thiểu `warning`. Không khớp rule tạo `safe` với `matched_rules` rỗng.

### AC-03 Dashboard

Scan completed hiển thị snapshot, counts và grid. Filter severity, type và domain chỉ trả findings phù hợp. Scan partial hiển thị giới hạn và lý do.

### AC-04 Ownership

User không thể đọc hoặc xóa scan, findings hay snapshot của user khác, kể cả khi biết `scan_id`.

### AC-05 SSRF

URL localhost/private IP/metadata bị từ chối trước khi worker truy cập. Redirect tới private IP được kiểm tra lại và bị chặn.

### AC-06 Controlled failure

Timeout, lỗi network hoặc vượt resource limit kết thúc scan bằng `partial` hoặc `failed` phù hợp, không làm lộ secret và không làm API crash.

## 10. Out of scope for MVP

- Quét toàn bộ website hoặc crawling không giới hạn.
- Malware detection, phishing verdict hoặc threat intelligence toàn diện.
- Bypass CAPTCHA hoặc tự động đăng nhập trang đích.
- Khẳng định `safe` là chứng nhận an toàn.
