# Customer Recommendation

## 1. Executive recommendation

Khuyến nghị xây dựng **Hidden Link Checker** thành một API-first web application
hỗ trợ rà soát nhanh các URL được nhúng trong nội dung nhìn thấy của một trang
web. Sản phẩm nên tập trung vào việc giúp người dùng trả lời ba câu hỏi:

1. Trang đang hiển thị những object nào có URL phía sau?
2. URL thực tế được nhúng trong object đó là gì?
3. Hidden link được lấy từ thuộc tính DOM nào?

MVP xử lý một URL theo kiểu đồng bộ: nhận request, lấy DOM, tìm hidden link và
trả toàn bộ kết quả ngay trong response. Trong domain này, hidden link là mọi
URL được phát hiện; link hiển thị trực tiếp chỉ là hidden link có
`visibility = direct`, còn link không hiển thị trực tiếp có `visibility = indirect`.
Kết quả hidden link chỉ tồn tại trong phạm vi một lần gọi API; hệ thống không
lưu lại chi tiết hidden link sau khi đã phản hồi.

Luồng xử lý chỉ fetch/render **URL đầu vào** để lấy DOM. Hệ thống chỉ phân tích
`href`, `src`, `srcset`, CSS background và các thuộc tính liên quan trong DOM;
không tự động mở, fetch, redirect hoặc kiểm tra các hidden link được phát hiện.
Redirect của chính URL đầu vào chỉ được xử lý trong phạm vi cần thiết để lấy
DOM và vẫn phải qua SSRF policy.

Về nền tảng dữ liệu, khuyến nghị dùng **PostgreSQL làm database chính**. Phạm vi
lưu trữ của MVP chỉ còn là lịch sử URL đã kiểm tra theo user (`User -> UrlCheck`),
không lưu lại chi tiết hidden link. Quan hệ và ownership vẫn cần rõ ràng, có
constraint bảo vệ toàn vẹn và index phục vụ truy vấn lịch sử. SQLite chỉ nên
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
- Dashboard nhập một URL và gọi API để lấy kết quả DOM/hidden link ngay trong
	response đồng bộ.
- Trả object chứa hidden link, visibility, loại element, URL nguồn và link thực tế
	đã resolve trong response; không lưu lại các object này sau khi phản hồi.
- Lịch sử URL đã kiểm tra (không kèm chi tiết hidden link) được phân quyền theo
	Google user.
- Đọc và xóa lịch sử kiểm tra được thực hiện qua API; frontend không truy cập
	database.
- Chính sách bảo vệ SSRF và cô lập browser worker ngay từ phiên bản đầu.
- PostgreSQL là persistence chính cho lịch sử URL; migration, transaction,
	foreign key và index phải được thiết kế cùng model User và UrlCheck.

## 4. Customer-facing recommendation

### Nên ưu tiên

1. **Độ tin cậy của kết quả:** mỗi hidden link trong response phải chỉ rõ object,
   thuộc tính DOM, URL nguồn, actual URL và `visibility` là `direct` hay `indirect`.
2. **API contract rõ ràng:** dashboard chỉ gọi API; authentication và truy cập
   lịch sử không được bypass API.
3. **Không mở hidden link:** dữ liệu phát hiện chỉ được parse và trả về, không
   được lưu lại và không được dùng để điều hướng hoặc request tiếp.
4. **API-first:** authentication, kiểm tra URL, đọc và xóa lịch sử đều đi qua
   API contract rõ ràng.
5. **Quyền riêng tư:** lịch sử URL chỉ thuộc về Google user tạo ra chúng; hidden
   link không được lưu trữ lâu dài.

### Có thể để sau MVP

- Crawler nhiều trang hoặc kiểm tra đệ quy các hidden link.
- Phân tích malware/phishing toàn diện.
- Bypass CAPTCHA hoặc đăng nhập vào trang đích.
- Phân tích đầy đủ iframe cross-origin và shadow DOM.
- Đánh giá rủi ro, severity, machine learning hoặc threat intelligence.
- Tích hợp threat intelligence bên thứ ba.

## 5. Expected user outcome

Sau một lần kiểm tra thành công, khách hàng có thể:

- Biết URL đầu vào và nhận toàn bộ danh sách hidden link ngay trong response.
- Biết hidden link nằm dưới object nào, URL nguồn, URL thực tế và visibility của nó.
- Tải lại lịch sử các URL đã kiểm tra của chính mình (chỉ gồm URL và thời điểm
	kiểm tra, không gồm chi tiết hidden link của lần đó).
- Xóa một mục lịch sử qua API theo quyền sở hữu.

Kết quả chỉ phản ánh DOM đã lấy từ URL đầu vào trong phạm vi giới hạn tại thời
điểm gọi API. Sản phẩm không được diễn đạt kết quả này như chứng nhận website
an toàn.

## 6. Success criteria

MVP được xem là đạt khi:

- Google user có thể đăng nhập và chỉ truy cập dữ liệu của chính mình.
- API lấy được DOM của URL đầu vào và nhận diện hidden link trong text/image/background,
  trả toàn bộ kết quả trong cùng response đồng bộ.
- Hidden link không gây ra request hoặc navigation tự động tới link đó.
- Hệ thống lưu được user và lịch sử URL đã kiểm tra (`url`, `checked_at`);
  chi tiết hidden link không được lưu lại sau khi phản hồi.
- API hỗ trợ đọc và xóa lịch sử theo ownership và dashboard tải được history.
- URL đầu vào và redirect của URL đầu vào được kiểm tra SSRF.

## 7. Product decisions requested

Các quyết định nên được chốt trước khi triển khai đầy đủ:

- Thời gian chờ, kích thước response và giới hạn tài nguyên khi xử lý đồng bộ.
- Thời gian retention của lịch sử URL đã kiểm tra.
- Google OAuth callback, session/token, logout và account linking.
- PostgreSQL deployment, migration strategy, backup/restore và retention purge.
- Cách hiển thị URL có query string nhạy cảm.
- Chính sách xử lý trang yêu cầu login, CAPTCHA hoặc trả lỗi mạng.
- Contract chính thức cho response đồng bộ và lỗi có kiểm soát.

## 8. Recommendation conclusion

Nên triển khai theo từng lát dọc: Google OAuth, API kiểm tra một URL đồng bộ,
fetch URL đầu vào an toàn, parse DOM mà không mở hidden link, trả kết quả trong
response, lưu lịch sử URL theo user, API đọc/xóa lịch sử và dashboard.
PostgreSQL phù hợp vì cần liên kết user và lịch sử URL với ownership query và
cascade deletion rõ ràng. Mỗi lát cần test bảo mật, test non-navigation, test
API ownership và test migration.
