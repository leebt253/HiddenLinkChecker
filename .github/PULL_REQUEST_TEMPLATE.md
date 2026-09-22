## Mục tiêu

<!-- Issue/BR/AC mà pull request này xử lý. -->

## Thay đổi

-

## Kiểm thử

- [ ] `python -m pytest -q`
- [ ] Đã kiểm tra ownership/auth nếu thay đổi scan hoặc history
- [ ] Đã kiểm tra SSRF/resource limit nếu nhận hoặc render URL

## Scope và rủi ro

- Có thay đổi scope trong `docs/idea.md` hoặc `docs/br-analysis.md` không?
- Có dữ liệu snapshot/URL nhạy cảm đi vào log hoặc artifact không?

## Checklist

- [ ] Code/test/documentation đã cập nhật phù hợp
- [ ] Không commit secret hoặc dữ liệu website thật
- [ ] `safe` không bị mô tả như kết luận an toàn tuyệt đối
