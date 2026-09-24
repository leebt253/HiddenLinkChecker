# Hidden Link Checker - Product Specification

## 1. Document status

- **Status:** MVP specification
- **Product guidance:** `docs/recommendation.md`
- **Product type:** authenticated web application
- **Primary user:** người dùng cần rà soát nhanh các URL được phát hiện trong một trang web
- **Scope boundary:** phân tích một trang và các URL đọc được trong text, image, background; không phải malware scanner toàn diện

## 2. Product objective

Cho phép người dùng đăng nhập bằng Google, gửi một URL qua API, lấy DOM trong
worker cô lập, phát hiện hidden link từ text/image/background và trả kết quả
trong thời gian xử lý. Database chỉ lưu URL và thời điểm check; không lưu DOM
hoặc hidden-link results. System không tự động mở hoặc request tới hidden link.

## 3. Actors

| Actor | Quyền và trách nhiệm |
|---|---|
| Unauthenticated user | Đăng nhập bằng Google |
| Authenticated user | Tạo, xem và xóa lịch sử URL của mình |
| Link processor | Fetch/render URL đầu vào trong sandbox, lấy DOM và parse hidden link |
| System administrator | Quản lý giới hạn vận hành và retention nếu cần |

## 4. Functional requirements

### FR-001 Google authentication

System phải hỗ trợ đăng nhập, đăng xuất và lấy thông tin user hiện tại thông qua
Google OAuth/OIDC. User được định danh bằng provider subject ổn định; system
không nhận password của user và không lưu Google access token nếu không cần cho
use case.

### FR-002 Create link check

Authenticated user có thể tạo một lần kiểm tra bằng URL `http` hoặc `https`.
Request tối thiểu:

```json
{
  "url": "https://example.com",
  "include_dom": true
}
```

System trả về link check ở trạng thái `queued` và không đồng bộ chờ processor
hoàn tất.

### FR-003 Secure input processing

Trước và trong quá trình điều hướng, system phải:

- Chỉ cho phép scheme `http` và `https`.
- Chặn localhost, loopback, private IP, link-local, multicast và cloud metadata endpoint.
- Resolve và kiểm tra IP sau mỗi redirect của **URL đầu vào**.
- Giới hạn timeout, số redirect, response size, CPU, RAM và số scan đồng thời.
- Không gửi cookie, authorization header hoặc application secret tới trang đích.
- Không fetch, mở, redirect hoặc điều hướng tới bất kỳ hidden link nào được
  phát hiện trong DOM. Hidden link chỉ được parse, chuẩn hóa theo base URL và
  lưu kết quả.

### FR-004 DOM link extraction

Processor phải trả về DOM hoặc phần DOM được phép lưu theo privacy policy và
phát hiện các URL sau trong phạm vi DOM/style đọc được:

- `text`: `href` của anchor hoặc phần tử có hành vi điều hướng, kèm visible text;
  có `visibility = direct` nếu hiển thị trực tiếp trên trang.
- `image`: `src`, `srcset`, URL bao quanh ảnh và alt text liên quan.
- `background`: URL trong `background`, `background-image` hoặc style tương đương có thể đọc được.

Mỗi kết quả phải có `visibility` để phân biệt hidden link hiển thị trực tiếp hay
không trực tiếp. Giá trị `direct` là link hiển thị trực tiếp; `indirect` là link
nằm sau image, background hoặc object khác. MVP không đánh giá rủi ro và không
chạy rule engine.

URL tương đối phải được chuẩn hóa theo URL cuối cùng của trang. Mỗi link result
phải giữ URL nguồn và URL thực tế.

### FR-005 Link result contract (ephemeral)

```json
{
  "id": "link_result_123",
  "link_check_id": "check_123",
  "element_type": "text",
  "object_reference": "img_42",
  "source_url": "/offers/casino",
  "actual_url": "https://example.com/offers/casino",
  "visibility": "indirect",
  "visible_text": "Claim reward",
  "alt_text": "",
  "position": null
}
```

`position` có thể là `null` nếu element không render được hoặc không lấy được bounding box.
Contract này chỉ phục vụ response/dashboard trong phiên xử lý; không có bảng
database lưu `LinkResult`.

### FR-006 Link check result and dashboard

Dashboard của link check hoàn tất phải hiển thị:

- Trạng thái xử lý và URL đầu vào.
- DOM hoặc phần DOM được phép lưu.
- Danh sách hidden link và visibility của từng kết quả.
- Object/thuộc tính DOM, URL nguồn và actual URL của từng kết quả.
- Bộ lọc theo `visibility`, element type hoặc domain nếu cần.

### FR-007 Link check lifecycle

Link check phải hỗ trợ các trạng thái:

```text
queued -> running -> completed
                  -> partial
                  -> failed
```

- `completed`: xử lý xong trong phạm vi dự kiến.
- `partial`: có kết quả nhưng một phần nội dung không đọc được hoặc bị giới hạn.
- `failed`: không tạo được kết quả usable do lỗi validation, network hoặc worker.

Trạng thái và limitation chỉ tồn tại trong phiên xử lý; database chỉ lưu
`url_checks.checked_at`.

### FR-008 History and CRUD

User có thể xem và xóa lịch sử URL của chính mình. Mọi thao tác authentication
và history đều đi qua API; frontend không truy cập database. Mọi truy vấn URL
history phải lọc theo authenticated `user_id`.

## 5. API contract

| Method | Endpoint | Mục đích |
|---|---|---|
| `GET` | `/v1/auth/google/start` | Bắt đầu Google OAuth |
| `GET` | `/v1/auth/google/callback` | Hoàn tất Google OAuth |
| `POST` | `/v1/auth/logout` | Đăng xuất |
| `GET` | `/v1/me` | Lấy user hiện tại |
| `POST` | `/v1/link-checks` | Tạo link check |
| `GET` | `/v1/link-checks/{check_id}` | Lấy kết quả link check |
| `DELETE` | `/v1/link-checks/{check_id}` | Xóa link check |
| `GET` | `/v1/me/link-checks` | Lấy lịch sử của user |

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

`id`, `google_subject`, `email`, `status`, `created_at`, `last_login_at`

### URL check history

`id`, `user_id`, `url`, `checked_at`

### LinkResult (memory only)

`id`, `link_check_id`, `element_type`, `object_reference`, `source_url`, `actual_url`, `visibility`, `visible_text`, `alt_text`, `position`

## 7. Non-functional requirements

- **Security:** SSRF protection, sandbox worker, authentication và ownership checks.
- **Privacy:** chỉ URL history có retention; DOM và hidden links không được lưu.
- **Reliability:** timeout, 403, 429, SSL error và HTML lỗi phải trả trạng thái có kiểm soát.
- **Performance:** static page nhỏ phải hoàn tất trong timeout cấu hình; dashboard không cần tải toàn bộ HTML.
- **Maintainability:** ứng dụng tổ chức theo MVC dễ đọc và maintenance; extractor,
  persistence và API/UI contract phải tách biệt.
- **Persistence:** PostgreSQL lưu users, auth state và `url_checks` với migration,
  foreign key và index ownership. SQLite chỉ dành cho test/prototype.

## 8. Known limitations

Kết quả có thể không đầy đủ khi trang dùng JavaScript động, iframe cross-origin, shadow DOM, yêu cầu đăng nhập, CAPTCHA, stylesheet không truy cập được hoặc vượt giới hạn tài nguyên. System phải ghi nhận limitation thay vì coi scan là toàn diện.

## 9. Acceptance criteria

### AC-01 Extraction

Với HTML có text link, image `src/srcset` và inline `background-image`, link
check tạo link result tương ứng với `text`, `image` và `background`, đồng thời
phân biệt đúng `visibility`; URL tương đối được resolve theo final page URL.

### AC-02 Non-navigation

Hidden link được parse và lưu nhưng không làm phát sinh request, redirect hoặc
navigation tới actual URL.

### AC-03 Dashboard

Link check completed hiển thị URL đầu vào, DOM được phép lưu và danh sách hidden
link cùng visibility và object nguồn.

### AC-04 Ownership

User không thể đọc, cập nhật hoặc xóa link check/link result của user khác, kể
cả khi biết `check_id`.

### AC-05 SSRF

URL localhost/private IP/metadata bị từ chối trước khi worker truy cập. Redirect tới private IP được kiểm tra lại và bị chặn.

### AC-06 Controlled failure

Timeout, lỗi network hoặc vượt resource limit kết thúc link check bằng trạng thái
có kiểm soát, không làm lộ secret và không làm API crash.

## 10. Out of scope for MVP

- Quét toàn bộ website hoặc crawling không giới hạn.
- Malware detection, phishing verdict hoặc threat intelligence toàn diện.
- Bypass CAPTCHA hoặc tự động đăng nhập trang đích.
- Đánh giá rủi ro, severity, rule engine hoặc chứng nhận website an toàn.
