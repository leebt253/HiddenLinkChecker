# Customer Recommendation

## 1. Executive recommendation

Khuyến nghị xây dựng **Hidden Link Checker** thành một công cụ web hỗ trợ rà soát nhanh các URL được nhúng trong nội dung nhìn thấy của một trang web. Sản phẩm nên tập trung vào việc giúp người dùng trả lời ba câu hỏi:

1. Trang đang hiển thị những element nào có URL phía sau?
2. URL thực tế sau khi chuẩn hóa là gì?
3. Vì sao một finding cần được ưu tiên kiểm tra?

Sản phẩm nên bắt đầu bằng MVP có khả năng giải thích kết quả, thay vì cố gắng trở thành hệ thống threat intelligence hoặc malware scanner toàn diện.

Về nền tảng dữ liệu, khuyến nghị dùng **PostgreSQL làm database chính**. Domain
`User -> Scan -> Finding` có quan hệ và ownership rõ ràng, cần transaction khi
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
Đăng nhập -> nhập URL -> quét an toàn -> xem snapshot và finding -> kiểm tra lịch sử
```

## 3. Recommended MVP value

MVP nên cung cấp:

- Phân tích URL từ text link, image và CSS background.
- Snapshot của trang cùng vị trí tương đối của từng finding.
- Dashboard dạng grid để đối chiếu preview, loại element, nội dung và destination.
- Phân loại minh bạch `safe`, `warning`, `critical`.
- Giải thích bằng `matched_rules`, không chỉ hiển thị màu hoặc điểm số.
- Lịch sử scan theo tài khoản và khả năng xóa dữ liệu.
- Chính sách bảo vệ SSRF và cô lập browser worker ngay từ phiên bản đầu.
- Bộ rule không hard-code trong evaluator; rule được quản lý như cấu hình có
	schema/version riêng, có thể chỉnh sửa trên web app bởi administrator và
	import từ file theo mẫu.
- PostgreSQL là persistence chính; migration, transaction, foreign key và
	index phải được thiết kế cùng model User, Scan, Finding và Rule.

## 4. Customer-facing recommendation

### Nên ưu tiên

1. **Độ tin cậy của finding:** mỗi kết quả phải chỉ rõ element, URL gốc, URL chuẩn hóa và bằng chứng liên quan.
2. **Khả năng giải thích:** người dùng phải biết rule nào tạo ra severity.
3. **An toàn khi render URL:** không đánh đổi SSRF protection để lấy tốc độ phát triển.
4. **Đối chiếu trực quan:** snapshot và bounding box nên giúp người dùng liên hệ finding với trang gốc.
5. **Quyền riêng tư:** scan, snapshot và URL chỉ thuộc về tài khoản tạo ra chúng.

### Có thể để sau MVP

- Crawler nhiều trang.
- Phân tích malware/phishing toàn diện.
- Bypass CAPTCHA hoặc đăng nhập vào trang đích.
- Phân tích đầy đủ iframe cross-origin và shadow DOM.
- Machine learning hoặc điểm rủi ro tổng hợp thay cho rule minh bạch.
- Tích hợp threat intelligence bên thứ ba.

## 5. Expected user outcome

Sau một lần scan thành công, khách hàng có thể:

- Biết tổng số URL được phát hiện.
- Xem số lượng theo từng mức `safe`, `warning`, `critical`.
- Lọc theo severity, loại element hoặc domain.
- Mở chi tiết một finding để xem text/alt, URL và rule khớp.
- Nhận biết rõ khi kết quả chỉ là `partial` vì CAPTCHA, login, timeout hoặc nội dung không truy cập được.

`safe` chỉ có nghĩa là chưa có rule rủi ro nào khớp trong phạm vi scan. Sản phẩm không được diễn đạt kết quả này như một chứng nhận website an toàn.

## 6. Success criteria

MVP được xem là đạt khi:

- Finding fixture cho text, image và background được nhận diện đúng loại và URL chuẩn hóa.
- Keyword rủi ro được gắn `critical` và có giải thích rule.
- Destination ngoài origin được gắn ít nhất `warning` nếu không có rule nghiêm trọng hơn.
- Người dùng không thể xem scan hoặc snapshot của tài khoản khác.
- URL nội bộ, redirect nguy hiểm và endpoint metadata bị chặn trước khi worker truy cập.
- Scan lỗi hoặc không đầy đủ được phân biệt rõ với scan hoàn tất.
- Người dùng có thể xóa lịch sử và dữ liệu liên quan theo chính sách retention.

## 7. Product decisions requested

Các quyết định nên được chốt trước khi triển khai đầy đủ:

- Thời gian chờ, kích thước response và giới hạn tài nguyên của worker.
- Thời gian retention của snapshot và finding.
- Bộ keyword/rule mặc định và cơ chế quản trị rule.
- Schema/version của file rule, quyền publish, lịch sử thay đổi và rule version
	được gắn vào kết quả scan.
- PostgreSQL deployment, migration strategy, backup/restore và retention purge.
- Cách hiển thị URL có query string nhạy cảm.
- Chính sách xử lý trang yêu cầu login, CAPTCHA hoặc trả lỗi mạng.
- Contract chính thức cho trạng thái scan và finding.

## 8. Recommendation conclusion

Nên triển khai theo từng lát dọc: scan an toàn một URL, trích xuất ba nhóm
finding, đánh giá rule từ file cấu hình, hiển thị kết quả và lưu theo user trong
PostgreSQL. Web app cần cho administrator chỉnh sửa rule hoặc import file theo
mẫu, validate trước khi publish và gắn version rule vào scan. Mỗi lát cần có
test bảo mật, test giải thích kết quả và test migration/ownership. Cách này tạo
ra giá trị sử dụng sớm mà vẫn giữ đúng ranh giới của sản phẩm.
