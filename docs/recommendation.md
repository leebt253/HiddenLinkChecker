# Customer Recommendation

## 1. Executive recommendation

Khuyến nghị xây dựng **Hidden Link Checker** thành một API-first web application
hỗ trợ rà soát nhanh các URL được nhúng trong nội dung nhìn thấy của một trang
web. Sản phẩm nên tập trung vào việc giúp người dùng trả lời ba câu hỏi:

1. Trang đang hiển thị những object nào có URL phía sau?
2. URL thực tế được nhúng trong object đó là gì?
3. Hidden link được lấy từ thuộc tính DOM nào?

MVP chỉ tập trung vào việc lấy DOM, tìm hidden link và lưu kết quả theo user.
Trong domain này, hidden link là mọi URL được phát hiện; link hiển thị trực tiếp
chỉ là hidden link có `visibility = direct`, còn link không hiển thị trực tiếp có
`visibility = indirect`.

Luồng xử lý chỉ fetch/render **URL đầu vào** để lấy DOM. Hệ thống chỉ phân tích
`href`, `src`, `srcset`, CSS background và các thuộc tính liên quan trong DOM;
không tự động mở, fetch, redirect hoặc kiểm tra các hidden link được phát hiện.
Redirect của chính URL đầu vào chỉ được xử lý trong phạm vi cần thiết để lấy
DOM và vẫn phải qua SSRF policy.

Về nền tảng dữ liệu, khuyến nghị dùng **PostgreSQL làm database chính**. Domain
`User -> LinkCheck -> HiddenLink` có quan hệ và ownership rõ ràng, cần transaction khi
tạo/xóa dữ liệu liên quan, constraint để bảo vệ toàn vẹn và truy vấn đồng thời
cho dashboard/lịch sử. PostgreSQL cũng phù hợp để lưu các phần có cấu trúc linh
hoạt như `position`, evidence hoặc metadata dưới dạng JSONB trong khi vẫn giữ
các field nghiệp vụ quan trọng ở cột có kiểu và index rõ ràng. SQLite chỉ nên
dùng cho test hoặc prototype đơn tiến trình, không nên là database production
cho web app nhiều worker.

## 2. Customer problem

Một trang web có thể hiển thị text hoặc hình ảnh bình thường nhưng dẫn tới destination khác với kỳ vọng. URL còn có thể nằm trong CSS background hoặc nội dung được tạo sau khi JavaScript chạy. Nếu chỉ xem danh sách URL, người dùng thiếu ngữ cảnh để đối chiếu với vị trí và nội dung trên trang.

Khách hàng cần một quy trình ngắn:

```text
Google login -> nhập URL -> API lấy DOM -> xem hidden link -> tải lịch sử theo user
```

## 3. Recommended MVP value

MVP nên cung cấp:

- Phân tích URL từ text link, image và CSS background.
- Dashboard nhập một URL và gọi API để lấy kết quả DOM/hidden link.
- Lưu object chứa hidden link, visibility, loại element, URL nguồn và link thực tế
	đã resolve.
- Lịch sử các lần kiểm tra được phân quyền theo Google user.
- CRUD dữ liệu kiểm tra được thực hiện qua API; frontend không truy cập database.
- Chính sách bảo vệ SSRF và cô lập browser worker ngay từ phiên bản đầu.
- PostgreSQL là persistence chính; migration, transaction, foreign key và
	index phải được thiết kế cùng model User, LinkCheck và LinkResult.

## 4. Customer-facing recommendation

### Nên ưu tiên

1. **Độ tin cậy của kết quả:** mỗi hidden link phải chỉ rõ object, thuộc tính DOM,
   URL nguồn, actual URL và `visibility` là `direct` hay `indirect`.
2. **API contract rõ ràng:** dashboard chỉ gọi API; authentication và CRUD không được bypass API.
3. **Không mở hidden link:** dữ liệu phát hiện chỉ được parse và lưu, không được dùng để điều hướng hoặc request tiếp.
4. **API-first:** authentication, create/read/update/delete và history đều đi qua API contract rõ ràng.
5. **Quyền riêng tư:** kết quả và URL chỉ thuộc về Google user tạo ra chúng.

### Có thể để sau MVP

- Crawler nhiều trang hoặc kiểm tra đệ quy các hidden link.
- Phân tích malware/phishing toàn diện.
- Bypass CAPTCHA hoặc đăng nhập vào trang đích.
- Phân tích đầy đủ iframe cross-origin và shadow DOM.
- Đánh giá rủi ro, severity, machine learning hoặc threat intelligence.
- Tích hợp threat intelligence bên thứ ba.

## 5. Expected user outcome

Sau một lần kiểm tra thành công, khách hàng có thể:

- Biết URL đầu vào và trạng thái xử lý.
- Xem DOM hoặc dữ liệu DOM cần thiết cùng danh sách hidden link.
- Biết hidden link nằm dưới object nào, URL nguồn, URL thực tế và visibility của nó.
- Tải lại lịch sử các lần kiểm tra của chính mình.
- Xóa hoặc cập nhật metadata của lần kiểm tra qua API theo quyền sở hữu.

Kết quả chỉ phản ánh DOM đã lấy từ URL đầu vào trong phạm vi giới hạn. Sản phẩm
không được diễn đạt kết quả này như chứng nhận website an toàn.

## 6. Success criteria

MVP được xem là đạt khi:

- Google user có thể đăng nhập và chỉ truy cập dữ liệu của chính mình.
- API lấy được DOM của URL đầu vào và nhận diện hidden link trong text/image/background.
- Hidden link không gây ra request hoặc navigation tự động tới link đó.
- Kết quả lưu được user, URL kiểm tra, object chứa hidden link và link thực tế.
- API hỗ trợ create/read/update/delete theo ownership và dashboard tải được history.
- URL đầu vào, redirect của URL đầu vào và endpoint metadata được kiểm tra SSRF.

## 7. Product decisions requested

Các quyết định nên được chốt trước khi triển khai đầy đủ:

- Thời gian chờ, kích thước response và giới hạn tài nguyên của worker.
- Schema lưu DOM: raw DOM, sanitized DOM hay chỉ phần DOM cần thiết.
- Các field được phép cập nhật qua `PATCH` và các field kết quả immutable.
- Thời gian retention của DOM, URL và hidden link.
- Google OAuth callback, session/token, logout và account linking.
- PostgreSQL deployment, migration strategy, backup/restore và retention purge.
- Cách hiển thị URL có query string nhạy cảm.
- Chính sách xử lý trang yêu cầu login, CAPTCHA hoặc trả lỗi mạng.
- Contract chính thức cho trạng thái link check và link result.

## 8. Recommendation conclusion

Nên triển khai theo từng lát dọc: Google OAuth, API tạo một `LinkCheck`, fetch
URL đầu vào an toàn, parse DOM mà không mở hidden link, lưu kết quả theo user,
API history/CRUD và dashboard. PostgreSQL phù hợp vì cần liên kết user, lần
kiểm tra và nhiều hidden link trong transaction, cùng ownership query và
cascade deletion rõ ràng. Mỗi lát cần test bảo mật, test non-navigation, test
API ownership và test migration.
