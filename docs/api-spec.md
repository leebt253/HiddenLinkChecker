# Hidden Link Checker - API Contract

## 1. Mục đích và phạm vi

API này mô tả contract MVP cho Hidden Link Checker: user xác thực, gửi một URL
để scan, xem kết quả/finding và quản lý lịch sử scan của chính mình.

API chỉ hỗ trợ phân tích một trang trong phạm vi text, image và background đọc
được. API không phải crawler, malware scanner, phishing verdict, CAPTCHA bypass
hoặc công cụ tự động đăng nhập trang đích.

Các endpoint trong contract:

| Method | Path | Mục đích |
|---|---|---|
| `POST` | `/v1/auth/register` | Đăng ký user |
| `POST` | `/v1/auth/login` | Đăng nhập |
| `POST` | `/v1/auth/logout` | Đăng xuất |
| `GET` | `/v1/me` | Lấy user hiện tại |
| `POST` | `/v1/scans` | Tạo scan bất đồng bộ |
| `GET` | `/v1/scans/{scan_id}` | Lấy trạng thái và tổng quan scan |
| `GET` | `/v1/scans/{scan_id}/findings` | Lấy finding của scan |
| `GET` | `/v1/me/scans` | Lấy lịch sử scan của user |
| `DELETE` | `/v1/scans/{scan_id}` | Xóa scan của user |

## 2. Quy ước đã xác nhận

### 2.1 JSON và thời gian

- Request và response dùng JSON, trừ khi endpoint có quy định khác.
- Tên field dùng `snake_case`.
- Timestamp dùng chuỗi ISO 8601 UTC, ví dụ `2026-09-22T10:00:00Z`.
- `null` được dùng khi dữ liệu không có hoặc không thể lấy được, không dùng
	chuỗi rỗng để thay thế cho mọi trường hợp.
- API không trả `password_hash`, secret, stack trace hoặc dữ liệu nội bộ.

### 2.2 Authentication

`[DECISION REQUIRED]` Cần Product Owner chọn cơ chế xác thực và thời hạn:

- session cookie server-side; hoặc
- bearer access token, kèm chính sách refresh/revocation.

Cho đến khi quyết định được chốt, các endpoint ghi `Authenticated user` có nghĩa
là request phải mang credential hợp lệ theo cơ chế được chọn. API phải từ chối
request thiếu hoặc không hợp lệ và không được tiết lộ credential nào hợp lệ.

`[DECISION REQUIRED]` Cần chọn tên header/cookie, thời hạn, CSRF policy nếu dùng
cookie, hành vi logout và mã HTTP cụ thể cho credential thiếu/hết hạn.

### 2.3 Error envelope

Hình dạng lỗi thống nhất chưa được chốt.

`[DECISION REQUIRED]` Cần Product Owner chọn một error envelope và status code
cho từng nhóm lỗi. Hình dạng đề xuất để review, chưa phải contract đã duyệt:

```json
{
	"error": {
		"code": "validation_error",
		"message": "Request validation failed",
		"details": [
			{
				"field": "url",
				"reason": "unsupported_scheme"
			}
		],
		"request_id": "req_123"
	}
}
```

`code` phải ổn định và không chứa stack trace, SQL, secret, internal hostname,
password hoặc nội dung nhạy cảm từ URL. `details` chỉ chứa dữ liệu cần cho client
sửa request.

### 2.4 Ownership và anti-enumeration

- Endpoint scan/history/finding yêu cầu authenticated user.
- Mọi truy vấn phải lọc theo `authenticated_user_id` trước khi lấy dữ liệu.
- Client không được đọc, lọc, xóa scan, finding hoặc snapshot thuộc user khác,
	kể cả khi biết `scan_id`.
- Khi scan không thuộc user hiện tại, API phải dùng hành vi thống nhất giữa
	`not found` và `forbidden` sau khi Product Owner quyết định; không tiết lộ
	việc ID có tồn tại hay không trước quyết định đó.
- `user_id` không nhận từ request body cho các thao tác user-scoped; server lấy
	từ credential đã xác thực.

### 2.5 URL và SSRF

- API boundary chỉ nhận URL có scheme `http` hoặc `https`.
- API validation không thay thế SSRF validation tại worker.
- Worker phải kiểm tra DNS/IP trước khi truy cập và kiểm tra lại sau mỗi redirect;
	chặn localhost, loopback, private IP, link-local, multicast và cloud metadata
	endpoint.
- API không gửi cookie, authorization header hoặc application secret tới URL
	đích.
- Query string có thể chứa dữ liệu nhạy cảm. Không ghi raw URL vào log mặc định.

## 3. Data contract

### 3.1 User response

Public user object chỉ gồm các field sau:

```json
{
	"id": "user_123",
	"email": "user@example.com",
	"status": "active",
	"created_at": "2026-09-22T09:00:00Z",
	"last_login_at": "2026-09-22T10:00:00Z"
}
```

`password_hash` là field persistence-only và không được trả qua API.

`status` và các giá trị hợp lệ ngoài `active` chưa được chốt.

### 3.2 Finding

Finding phải giữ đúng contract sau:

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

Field và enum đã xác nhận:

- `element_type`: `text | image | background`.
- `source_url`: URL được đọc từ element nguồn.
- `normalized_url`: URL đã resolve theo final page URL.
- `visible_text`, `alt_text`, `matched_content`: bằng chứng có thể rỗng nếu
	không thu thập được.
- `position`: object gồm `x`, `y`, `width`, `height`, hoặc `null` nếu element
	không render được/không lấy được bounding box.
- `severity`: `safe | warning | critical`, đúng một giá trị.
- `matched_rules`: danh sách tên rule ổn định; không khớp rule thì là `[]`.

`safe` chỉ có nghĩa là chưa có rule rủi ro nào khớp trong phạm vi scan; không
được hiển thị hoặc mô tả như chứng nhận website an toàn.

### 3.3 Scan response

Scan có lifecycle:

```text
queued -> running -> completed
									-> partial
									-> failed
```

Các trạng thái có ý nghĩa:

- `queued`: đã nhận request và đang chờ worker.
- `running`: worker đang xử lý.
- `completed`: xử lý xong trong phạm vi dự kiến.
- `partial`: có kết quả nhưng một phần nội dung không đọc được hoặc bị giới
	hạn, ví dụ CAPTCHA, login, iframe cross-origin, timeout hoặc resource limit.
- `failed`: không tạo được kết quả usable do validation, network hoặc worker
	failure.

Scan summary dùng các field đã chốt trong specification:

```json
{
	"scan_id": "scan_123",
	"status": "completed",
	"submitted_url": "https://example.com",
	"normalized_url": "https://example.com/",
	"final_url": "https://example.com/home",
	"http_status": 200,
	"error_code": null,
	"snapshot_reference": "snapshot_123",
	"safe_count": 10,
	"warning_count": 2,
	"critical_count": 1,
	"created_at": "2026-09-22T10:00:00Z",
	"completed_at": "2026-09-22T10:00:08Z",
	"retention_expires_at": "2026-10-22T10:00:08Z",
	"limitations": []
}
```

`final_url`, `http_status`, `completed_at` và `retention_expires_at` có thể là
`null` khi scan chưa hoàn tất hoặc policy chưa tạo giá trị. `error_code` phải là
mã ổn định, không phải stack trace. `limitations` phải nêu giới hạn có kiểm
soát cho `partial`; cấu trúc chi tiết của phần tử limitation chưa được chốt.

`snapshot_reference` là reference nội bộ hoặc URL đã được cấp quyền; không được
trả storage credential hoặc đường dẫn nội bộ. Cách cấp quyền tải snapshot chưa
được chốt.

## 4. API endpoints

### 4.1 `POST /v1/auth/register`

**Mục đích:** tạo user chưa xác thực.

**Xác thực:** không yêu cầu credential.

**Request body:**

```json
{
	"email": "user@example.com",
	"password": "correct-horse-battery-staple"
}
```

- `email`: bắt buộc, kiểu string. Quy tắc format, normalization, phân biệt hoa
	thường và giới hạn độ dài: `[DECISION REQUIRED]`.
- `password`: bắt buộc, kiểu string. Chính sách độ dài/complexity, breached
	password check và giới hạn request: `[DECISION REQUIRED]`.
- Không chấp nhận `user_id`, `status`, `password_hash` hoặc field server-managed
	từ client.

**Success response:** tạo account với password được hash, không trả hash.

```json
{
	"user": {
		"id": "user_123",
		"email": "user@example.com",
		"status": "active",
		"created_at": "2026-09-22T09:00:00Z",
		"last_login_at": null
	}
}
```

HTTP status và việc register có tạo credential/session ngay hay không:
`[DECISION REQUIRED]`.

**Expected errors:**

| Tình huống | Error code đề xuất | HTTP status |
|---|---|---|
| JSON/body sai hoặc thiếu field | `validation_error` | `[DECISION REQUIRED]` |
| Email đã tồn tại | `email_already_registered` | `[DECISION REQUIRED]` |
| Rate limit/abuse protection | `rate_limited` | `[DECISION REQUIRED]` |
| Dependency/auth service lỗi | `service_unavailable` | `[DECISION REQUIRED]` |

Response dùng error envelope ở mục 2.3 sau khi được chốt. Không trả password
hoặc chi tiết cho phép user enumeration ngoài policy đã duyệt.

**Ownership và logging:** account mới thuộc credential/user vừa tạo. Không log
password; email và request body phải được xử lý theo privacy policy.

### 4.2 `POST /v1/auth/login`

**Mục đích:** xác thực credential của user.

**Xác thực:** không yêu cầu credential trước đó.

**Request body:**

```json
{
	"email": "user@example.com",
	"password": "correct-horse-battery-staple"
}
```

`email` và `password` bắt buộc là string. Validation format và giới hạn chi tiết
chưa được chốt: `[DECISION REQUIRED]`.

**Success response:** trả user public object và credential theo cơ chế auth đã
chọn. Dạng credential, field name, expiry và refresh behavior:
`[DECISION REQUIRED]`.

```json
{
	"user": {
		"id": "user_123",
		"email": "user@example.com",
		"status": "active",
		"created_at": "2026-09-22T09:00:00Z",
		"last_login_at": "2026-09-22T10:00:00Z"
	}
}
```

HTTP status: `[DECISION REQUIRED]`.

**Expected errors:**

| Tình huống | Error code đề xuất | HTTP status |
|---|---|---|
| Body không hợp lệ | `validation_error` | `[DECISION REQUIRED]` |
| Credential sai hoặc account không hoạt động | `invalid_credentials` | `[DECISION REQUIRED]` |
| Rate limit/lockout | `rate_limited` | `[DECISION REQUIRED]` |
| Auth service lỗi | `service_unavailable` | `[DECISION REQUIRED]` |

Không phân biệt email không tồn tại với password sai nếu policy chống user
enumeration yêu cầu gộp lỗi.

**Ownership và logging:** credential sau login chỉ cấp quyền cho user đã xác
thực. Không log password, token/session value hoặc raw request body.

### 4.3 `POST /v1/auth/logout`

**Mục đích:** hủy hoặc vô hiệu hóa credential hiện tại.

**Xác thực:** authenticated user; credential hiện tại phải được gửi theo cơ chế
đã chọn.

**Parameters/body:** không có path parameter. Request body không được dùng để
chỉ định user/session khác.

**Success response:** không trả credential hoặc password.

```json
{
	"logged_out": true
}
```

HTTP status và semantics khi credential đã hết hạn: `[DECISION REQUIRED]`.

**Expected errors:**

| Tình huống | Error code đề xuất | HTTP status |
|---|---|---|
| Credential thiếu/hết hạn/không hợp lệ | `authentication_required` | `[DECISION REQUIRED]` |
| Auth service lỗi | `service_unavailable` | `[DECISION REQUIRED]` |

**Ownership và logging:** chỉ hủy credential/session hiện tại; không log token,
cookie hoặc session identifier đầy đủ.

### 4.4 `GET /v1/me`

**Mục đích:** lấy public profile của user hiện tại.

**Xác thực:** authenticated user.

**Parameters/body:** không có.

**Success response:** user public object ở mục 3.1.

```json
{
	"user": {
		"id": "user_123",
		"email": "user@example.com",
		"status": "active",
		"created_at": "2026-09-22T09:00:00Z",
		"last_login_at": "2026-09-22T10:00:00Z"
	}
}
```

HTTP status: `[DECISION REQUIRED]`.

**Expected errors:** thiếu hoặc credential không hợp lệ: `authentication_required`
với HTTP status `[DECISION REQUIRED]`.

**Ownership và logging:** chỉ trả profile gắn với credential hiện tại; không trả
password hash, secret hoặc field nội bộ.

### 4.5 `POST /v1/scans`

**Mục đích:** tạo scan bất đồng bộ cho một URL.

**Xác thực:** authenticated user.

**Request body:**

```json
{
	"url": "https://example.com",
	"include_snapshot": true
}
```

- `url`: bắt buộc, string; chỉ scheme `http`/`https`. URL phải được parse và
	validate trước khi enqueue. Quy tắc về hostname, port, độ dài và credential
	trong URL: `[DECISION REQUIRED]`.
- `include_snapshot`: bắt buộc theo request tối thiểu của specification, boolean.
	Giá trị mặc định nếu client bỏ field: `[DECISION REQUIRED]`.
- Không chấp nhận `user_id`, scan status, timestamps, rule set, headers,
	cookies, authorization hoặc worker limits từ client.

API validation scheme không thay thế worker SSRF validation. Worker phải chặn
localhost, loopback, private IP, link-local, multicast và metadata endpoint,
đồng thời revalidate redirect.

**Success response:** request được nhận để xử lý bất đồng bộ và scan bắt đầu ở
trạng thái `queued`; API không chờ browser worker hoàn tất.

```json
{
	"scan_id": "scan_123",
	"status": "queued",
	"created_at": "2026-09-22T10:00:00Z"
}
```

HTTP status: `[DECISION REQUIRED]`.

**Expected errors:**

| Tình huống | Error code đề xuất | HTTP status |
|---|---|---|
| Chưa xác thực | `authentication_required` | `[DECISION REQUIRED]` |
| Body/field sai | `validation_error` | `[DECISION REQUIRED]` |
| Scheme không phải HTTP(S) | `unsupported_scheme` | `[DECISION REQUIRED]` |
| URL bị policy an toàn từ chối | `url_not_allowed` | `[DECISION REQUIRED]` |
| Vượt concurrency/rate limit | `rate_limited` | `[DECISION REQUIRED]` |
| Queue/worker không khả dụng | `service_unavailable` | `[DECISION REQUIRED]` |

Không trả thông tin DNS/IP nội bộ hoặc chi tiết policy có thể hỗ trợ SSRF bypass.

**Ownership và logging:** scan mới gắn với authenticated user, không lấy
ownership từ body. Hạn chế log `url` và che query string nhạy cảm theo policy
chưa chốt.

### 4.6 `GET /v1/scans/{scan_id}`

**Mục đích:** lấy trạng thái, summary, counts, limitation và snapshot reference
của một scan.

**Xác thực:** authenticated user sở hữu scan.

**Path parameter:**

- `scan_id`: bắt buộc, string identifier do server cấp. Format và độ dài:
	`[DECISION REQUIRED]`.

**Query/body:** không có query parameter hoặc request body.

**Success response:** Scan response ở mục 3.3, bao gồm status hiện tại.

```json
{
	"scan": {
		"scan_id": "scan_123",
		"status": "partial",
		"submitted_url": "https://example.com",
		"normalized_url": "https://example.com/",
		"final_url": "https://example.com/home",
		"http_status": 200,
		"error_code": "content_partially_unavailable",
		"snapshot_reference": "snapshot_123",
		"safe_count": 10,
		"warning_count": 2,
		"critical_count": 1,
		"created_at": "2026-09-22T10:00:00Z",
		"completed_at": "2026-09-22T10:00:08Z",
		"retention_expires_at": "2026-10-22T10:00:08Z",
		"limitations": ["cross-origin iframe was not readable"]
	}
}
```

HTTP status: `[DECISION REQUIRED]`.

**Expected errors:**

| Tình huống | Error code đề xuất | HTTP status |
|---|---|---|
| Chưa xác thực | `authentication_required` | `[DECISION REQUIRED]` |
| ID sai format | `validation_error` | `[DECISION REQUIRED]` |
| Không thuộc user hiện tại hoặc không tồn tại | `scan_not_found` hoặc `access_denied` | `[DECISION REQUIRED]` |
| Scan đã hết retention | `scan_expired` | `[DECISION REQUIRED]` |

Response lỗi không được cho biết scan của user khác có tồn tại hay không nếu
policy anti-enumeration chọn cách gộp `not found`/`forbidden`.

**Ownership và logging:** chỉ trả scan có `user_id` bằng authenticated user;
không log raw URL, snapshot credential hoặc internal worker detail.

### 4.7 `GET /v1/scans/{scan_id}/findings`

**Mục đích:** lấy các finding thuộc một scan để dashboard hiển thị grid, evidence
và filter.

**Xác thực:** authenticated user sở hữu scan.

**Path parameter:** `scan_id` bắt buộc; format/độ dài chưa chốt:
`[DECISION REQUIRED]`.

**Query parameters đã xác nhận về nghiệp vụ:**

| Tên | Kiểu | Bắt buộc | Validation |
|---|---|---:|---|
| `severity` | enum hoặc danh sách enum | Không | `safe`, `warning`, `critical` |
| `element_type` | enum hoặc danh sách enum | Không | `text`, `image`, `background` |
| `domain` | string | Không | Lọc theo destination domain |

Filter kết hợp theo AND giữa nhóm filter; cách biểu diễn nhiều giá trị, domain
normalization và xử lý domain không hợp lệ: `[DECISION REQUIRED]`.

Pagination, sorting, page size tối đa, cursor/offset và thứ tự mặc định chưa có
quyết định trong specification: `[DECISION REQUIRED]`.

Để QA có thể kiểm tra contract sau khi quyết định được chốt, response phải chứa
list finding và metadata pagination đã chọn, ví dụ:

```json
{
	"scan_id": "scan_123",
	"items": [
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
	],
	"pagination": {
		"next_cursor": null
	}
}
```

`pagination` là placeholder contract và chưa được duyệt cho tới khi format được
chọn. HTTP status: `[DECISION REQUIRED]`.

**Expected errors:** authentication, invalid `scan_id`/filter, ownership denial,
expired scan và service failure. Error code/status cụ thể:
`[DECISION REQUIRED]`.

**Ownership và logging:** API phải lọc scan theo authenticated user trước khi
đọc findings. Không trả finding từ scan khác; không log `source_url` hoặc
`normalized_url` raw nếu có query string nhạy cảm.

### 4.8 `GET /v1/me/scans`

**Mục đích:** lấy lịch sử scan của authenticated user.

**Xác thực:** authenticated user.

**Query parameters:** Specification yêu cầu history nhưng chưa chốt pagination,
sorting hoặc filter cho endpoint này.

`[DECISION REQUIRED]` Cần Product Owner quyết định:

- Có hỗ trợ filter theo `status`, date range hoặc domain hay không.
- Format pagination, page size tối đa và thứ tự mặc định.
- Có trả snapshot reference và retention metadata trong list hay chỉ summary.

Cho tới khi chốt, không coi query parameter nào ngoài những field được duyệt là
hợp lệ.

Response phải chỉ chứa scan của user hiện tại, ví dụ:

```json
{
	"items": [
		{
			"scan_id": "scan_123",
			"status": "completed",
			"submitted_url": "https://example.com",
			"normalized_url": "https://example.com/",
			"final_url": "https://example.com/home",
			"http_status": 200,
			"error_code": null,
			"snapshot_reference": "snapshot_123",
			"safe_count": 10,
			"warning_count": 2,
			"critical_count": 1,
			"created_at": "2026-09-22T10:00:00Z",
			"completed_at": "2026-09-22T10:00:08Z",
			"retention_expires_at": "2026-10-22T10:00:08Z",
			"limitations": []
		}
	],
	"pagination": {
		"next_cursor": null
	}
}
```

`pagination` và field list chính thức cần được chốt trước implementation:
`[DECISION REQUIRED]`. HTTP status: `[DECISION REQUIRED]`.

**Expected errors:** authentication, query validation, rate limit và service
failure. Error code/status cụ thể: `[DECISION REQUIRED]`.

**Ownership và logging:** query bắt buộc scope theo authenticated user; không
nhận `user_id` từ query. Không log raw submitted URL.

### 4.9 `DELETE /v1/scans/{scan_id}`

**Mục đích:** user yêu cầu xóa scan của chính mình cùng findings và snapshot liên
quan theo retention policy.

**Xác thực:** authenticated user sở hữu scan.

**Path parameter:** `scan_id` bắt buộc, format/độ dài chưa chốt:
`[DECISION REQUIRED]`.

**Query/body:** không có. Client không được gửi `user_id` hoặc yêu cầu xóa dữ
liệu của user khác.

**Success response:** scan và dữ liệu liên quan được xóa hoặc đánh dấu xóa theo
retention policy. Cách xử lý bất đồng bộ, idempotency và response body:
`[DECISION REQUIRED]`.

Ví dụ response đề xuất, chưa duyệt:

```json
{
	"scan_id": "scan_123",
	"deleted": true
}
```

HTTP status: `[DECISION REQUIRED]`.

**Expected errors:**

| Tình huống | Error code đề xuất | HTTP status |
|---|---|---|
| Chưa xác thực | `authentication_required` | `[DECISION REQUIRED]` |
| ID sai format | `validation_error` | `[DECISION REQUIRED]` |
| Không thuộc user hiện tại hoặc không tồn tại | `scan_not_found` hoặc `access_denied` | `[DECISION REQUIRED]` |
| Scan đang được xử lý và policy không cho xóa ngay | `scan_deletion_conflict` | `[DECISION REQUIRED]` |
| Persistence/storage lỗi | `service_unavailable` | `[DECISION REQUIRED]` |

**Ownership và logging:** phải dùng điều kiện `scan_id` và authenticated
`user_id` trong cùng thao tác authorization/deletion. Không log snapshot path,
URL nhạy cảm hoặc storage credential.

## 5. Quy tắc bảo mật và privacy áp dụng toàn API

- Password chỉ được nhận qua kênh bảo mật, hash tại server và không bao giờ trả
	hoặc ghi log dạng plain text.
- Không trả password hash, access token ngoài response contract đã chốt, secret,
	cookie đích, stack trace, SQL, filesystem path hoặc worker internals.
- URL có query string nhạy cảm phải được redacted trong log. Cách redaction,
	danh sách key nhạy cảm và retention của URL/snapshot:
	`[DECISION REQUIRED]`.
- API phải giới hạn kích thước request/body và rate limit phù hợp; giá trị cụ
	thể chưa được chốt.
- SSRF protection phải tồn tại cả ở API boundary và worker; không coi URL scheme
	validation là đủ.
- Finding `critical` chỉ là tín hiệu rule cần kiểm tra, không phải kết luận
	malware/phishing. `safe` không phải chứng nhận an toàn.
- Với nội dung không đọc được đầy đủ, trả scan `partial` và limitation có kiểm
	soát; không suy đoán finding hoặc severity ngoài evidence có được.

## 6. Ma trận traceability

| Requirement | Endpoint hỗ trợ | Coverage |
|---|---|---|
| BR-001 / FR-001 / AC-01 Authentication | register, login, logout, me | Có contract cơ bản; cơ chế token/session và status lỗi còn mở |
| BR-002 / FR-002 | `POST /v1/scans` | Có URL HTTP(S), async `queued`; validation chi tiết còn mở |
| BR-003 / FR-004 / AC-01 | Scan result + findings | Có `text`, `image`, `background` và normalized URL |
| BR-004 / FR-005 | findings | Có đầy đủ field Finding và nullable `position` |
| BR-005/006 / FR-006 / AC-02 | scan summary + findings | Có severity, matched rules và explainability |
| BR-007 / AC-03 | scan detail + findings filters | Có counts, snapshot reference, filters; pagination còn mở |
| BR-008 / FR-009 / AC-04 | scan detail, findings, history, delete | Có ownership requirement |
| BR-009 / FR-003 / AC-05 | create scan + worker contract | Có scheme validation và yêu cầu worker SSRF revalidation |
| BR-010 / FR-008 | scan detail/history | Có timestamps, status, error code, retention metadata |
| BR-011 / AC-06 | scan detail | Có `partial`, `limitations`, controlled error requirement |
| BR-012 | Không có endpoint quản trị rule trong MVP | Đúng phạm vi; rule management API chưa được yêu cầu |

Requirement chưa có endpoint riêng:

- Snapshot binary/content download endpoint không nằm trong danh sách MVP; chỉ
	có `snapshot_reference` trong scan. Cách client truy cập snapshot:
	`[DECISION REQUIRED]` hoặc cần Product Owner xác nhận để bổ sung endpoint,
	nhưng không tự thêm endpoint trong contract này.
- Admin quản lý rule, retention và worker limits chưa có endpoint trong phạm vi
	được chốt; không mở rộng API MVP để thêm các endpoint đó.

## 7. Các quyết định cần Product Owner chốt

1. Cơ chế session/token, header/cookie, expiry, refresh, revocation và CSRF.
2. HTTP status chính xác cho success và từng nhóm lỗi.
3. Error envelope chính thức, danh sách error code và có dùng `request_id` hay
	 không.
4. Email normalization/validation và password policy.
5. URL validation chi tiết: hostname, port, credentials, độ dài và IDN.
6. Pagination format, page size tối đa, sorting mặc định và filter history.
7. Cách biểu diễn nhiều giá trị filter `severity`/`element_type` và domain
	 normalization.
8. Cách cấp quyền truy cập snapshot và có cần API tải snapshot riêng không.
9. Semantics delete: hard delete/soft delete, synchronous/asynchronous,
	 idempotency và behavior khi scan đang chạy.
10. Cấu trúc `limitations`, retention/URL redaction và policy log query string.
11. Rate limit, request/body size và worker concurrency limits được expose hay
		chỉ cấu hình nội bộ.

Các mục trên là điểm mở; không được triển khai như giả định đã được phê duyệt.
