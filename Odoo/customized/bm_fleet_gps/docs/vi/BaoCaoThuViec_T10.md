# BÁO CÁO THỬ VIỆC
## Hệ thống quản lý đội xe GPS BM Fleet Tracking

**Nhân viên:** Đỗ Vương Quốc Thịnh
**Công ty:** BESTMIX
**Thời gian:** 4 tuần
**Ngày báo cáo:** Tháng 11/2025

---

### QUÁ TRÌNH THỰC HIỆN DỰ ÁN (4 TUẦN)

#### 1. Giới thiệu dự án

Dự án xây dựng **Hệ thống quản lý đội xe GPS BM Fleet Tracking** được thực hiện trong 4 tuần với mục tiêu số hóa hoàn toàn quy trình quản lý xe của công ty.

**Vấn đề cần giải quyết:**
- Công ty đang quản lý đội xe thủ công qua giấy tờ
- Khó theo dõi vị trí xe trong thực tế
- Quy trình phê duyệt rườm rà, tốn thời gian
- Không có dữ liệu thống kê chi tiết

**Giải pháp thực hiện:**
- Xây dựng hệ thống đặt xe online trên nền tảng Odoo
- Kết nối GPS để theo dõi vị trí xe thời gian thực
- Tự động hóa quy trình phê duyệt
- Cung cấp báo cáo và thống kê tự động

#### 2. Các giai đoạn phát triển

**Tuần 1-2: Phân tích và Thiết kế**
- Nghiên cứu quy trình làm việc hiện tại của công ty
- Phỏng vấn các bộ phận liên quan: nhân viên, quản lý, admin
- Vẽ lưu đồ quy trình mới tối ưu hơn
- Lên kế hoạch chi tiết cho 10 tuần
- Chuẩn bị môi trường phát triển Odoo 18

**Tuần 1-2: Xây dựng chức năng Đặt xe**
- Thiết kế form đặt xe trực quan, dễ sử dụng
- Xây dựng quy trình phê duyệt 6 bước:
  1. Mới → 2. Chờ Manager duyệt → 3. Chờ điều xe → 4. Đang chạy → 5. Hoàn thành/Đã hủy
- Tích hợp hệ thống email thông báo tự động
- Xây dựng giao diện Kanban theo trạng thái
- Tạo wizard nhanh để tạo đơn

**Tuần 1-2: Kết nối GPS và Bản đồ**
- Nghiên cứu và kết nối API của nhà cung cấp GPS ADSUN
- Lấy dữ liệu vị trí xe tự động mỗi 30 phút
- Hiển thị vị trí xe trên bản đồ trực tuyến
- Vẽ hành trình di chuyển của xe
- Thống kê quãng đường, thời gian chạy, tốc độ
- Tối ưu hiệu suất truy vấn dữ liệu

**Tuần 3-4: Hoàn thiện chức năng bổ sung**
- Xây dựng tìm kiếm địa chỉ tự động
- Tích hợp bản đồ Việt Nam (OpenMap.vn)
- Xây dựng hệ thống phân quyền 3 cấp:
  - Nhân viên: Đặt xe và xem đơn của mình
  - Quản lý: Duyệt đơn của team
  - Sale Admin: Quản lý toàn bộ hệ thống
- Tạo báo cáo thống kê chi tiết

**Tuần 3-4: Kiểm tra và Hoàn tất**
- Test toàn bộ chức năng với dữ liệu thật
- Sửa các lỗi tìm được trong quá trình test
- Tối ưu tốc độ tải trang và truy vấn
- Viết tài liệu hướng dẫn sử dụng người dùng ở các cấp: nhân viên, quản lý, Sale Admin
- Chuẩn bị hệ thống sẵn sàng để triển khai

#### 3. Kết quả chính đạt được

**Về mặt hiệu quả:**
- **100% số hóa** quy trình đặt xe, không dùng giấy
- **Giảm 80% thời gian** xử lý đơn đặt xe
- **Tăng tốc độ truy vấn** từ 2.5 giây xuống 0.15 giây
- **Theo dõi 24/7** vị trí toàn bộ đội xe

**Về mặt hệ thống:**
- Hệ thống production sẵn sàng sử dụng
- Hỗ trợ điều phối xe và theo dõi hành trình xe 
- Báo cáo tự động và chi tiết
- Giao diện thân thiện, dễ sử dụng

**Về mặt quản lý:**
- Minh bạch hoàn toàn quy trình
- Dữ liệu thống kê để ra quyết định
- Phân quyền rõ ràng, bảo mật
- Lưu trữ lịch sử đầy đủ

---

### BÀI HỌC KINH NGHIỆM VÀ PHÁT TRIỂN CÁ NHÂN

#### 1. Kỹ năng đã học được và phát triển

**Quản lý dự án:**
- **Lập kế hoạch chi tiết:** Chia nhỏ công việc lớn thành từng task cụ thể
- **Quản lý thời gian:** Đảm bảo tiến độ 4 tuần đúng cam kết
- **Theo dõi tiến độ:** Báo cáo hàng tuần cho quản lý
- **Xử lý rủi ro:** Lường trước các vấn đề có thể xảy ra

**Kỹ năng giải quyết vấn đề:**
- **Phân tích vấn đề:** Tìm gốc rễ của từng khó khăn
- **Tìm kiếm giải pháp:** Nghiên cứu nhiều cách tiếp cận
- **Thử và sai:** Dũng cảm thử nghiệm các giải pháp mới
- **Tối ưu hóa:** Cải tiến liên tục để đạt kết quả tốt hơn

**Kỹ năng giao tiếp:**
- **Trình bày ý tưởng:** Demo sản phẩm cho các bộ phận
- **Lắng nghe phản hồi:** Hiểu nhu cầu thực tế của người dùng
- **Viết báo cáo:** Ghi nhận tiến độ và kết quả
- **Làm việc nhóm:** Phối hợp với các phòng ban liên quan

**Kỹ năng kỹ thuật:**
- **Học Odoo framework:** Nắm vững mô hình MVC của Odoo
- **Làm việc với API:** Kết nối hệ thống bên ngoài
- **Tối ưu hiệu năng:** Cải thiện tốc độ hệ thống
- **Testing:** Kiểm tra chất lượng sản phẩm

#### 2. Khó khăn đã vượt qua

**Thách thức công nghệ:**
- **Học các kiến thức từ Odoo framework:** Phải nghiên cứu tài liệu trong 2 tuần
- **Làm việc với GPS API:** Xử lý lỗi kết nối và đồng bộ dữ liệu
- **Tối ưu cơ sở dữ liệu:** Giải quyết vấn đề truy vấn chậm
- **Xây dựng giao diện bản đồ:** Học JavaScript và thư viện mới

**Thách thức về quy trình:**
- **Hiểu nghiệp vụ:** Phải học quy trình quản lý xe của công ty
- **Thỏa thuận yêu cầu:** Đàm phán với nhiều bộ phận khác nhau
- **Quản lý kỳ vọng:** Cân bằng giữa mong muốn và khả năng kỹ thuật
- **Thời gian áp lực:** Hoàn thành trong 10 tuần ngắn ngủi

**Thách thức cá nhân:**
- **Tự học:** Phải xem các tài liệu bằng tiếng Anh
- **Quyết định:** một số giải pháp kỹ thuật chưa thể tự đưa ra mà phải nhờ anh Tuấn hỗ trợ đưa ra hướng giải quyết
- **Trách nhiệm:** Chịu trách nhiệm toàn bộ dự án
- **Thích ứng:** Thay đổi kế hoạch khi cần thiết

#### 3. Đóng góp cho công ty

**Giải pháp hoàn chỉnh:**
- Hệ thống production sẵn sàng sử dụng
- Nền tảng vững chắc để phát triển thêm các tính năng
- Tiết kiệm chi phí vận hành hàng tháng
- Tăng hiệu quả quản lý đội xe

**Giá trị cho nhân viên:**
- Giao diện dễ sử dụng, không cần đào tạo nhiều
- Tiết kiệm thời gian trong công việc hàng ngày
- Minh bạch trong quy trình phê duyệt
- Dữ liệu để phục vụ công việc tốt hơn

**Nền tảng phát triển:**
- Code sạch, dễ bảo trì và mở rộng
- Tài liệu đầy đủ để người mới có thể tiếp cận
- Kiến trúc tốt để tích hợp thêm các module khác
- Kinh nghiệm để triển khai các dự án tương tự

#### 4. Bài học lớn nhất rút ra

**Về lập kế hoạch:**
- "Lập kế hoạch kỹ lưỡng là thành công của một nửa"
- Cần chia nhỏ công việc và có milestone rõ ràng
- Luôn có kế hoạch dự phòng cho các rủi ro

**Về kỹ thuật:**
- "Test sớm, test thường xuyên" là quy tắc vàng
- Hiệu năng phải được quan tâm ngay từ đầu
- Ghi chú và tài liệu là phần quan trọng của code

**Về làm việc:**
- Lắng nghe người dùng là chìa khóa thành công
- Không ngừng học hỏi và cập nhật công nghệ
- Sẵn sàng nhận lỗi và sửa chữa

**Về phát triển bản thân:**
- Ra khỏi vùng an toàn để học hỏi các kiến thức mới
- Chịu trách nhiệm với quyết định của mình

#### 5. Hướng phát triển tương lai

**Ngắn hạn (3-6 tháng):**
- Hỗ trợ triển khai hệ thống thực tế
- Thu thập phản hồi từ người dùng
- Sửa lỗi và cải thiện tính năng
- Training cho nhân viên mới

**Dài hạn (1-2 năm):**
- Phát triển mobile app cho tài xế
- Thêm tính năng phân tích thông minh
- Tối ưu lộ trình di chuyển
- Mở rộng cho các chi nhánh khác
- Tích hợp với các hệ thống khác của công ty

**Phát triển cá nhân:**
- Học thêm về phân tích dữ liệu
- Nâng cao kỹ năng quản lý dự án
- Chuyên sâu về Odoo và ERP
- Xây dựng tư duy kiến trúc hệ thống

---

### BÁO CÁO

Sau 10 tuần thử việc, dự án Hệ thống quản lý đội xe GPS đã hoàn thành thành công với đầy đủ chức năng cơ bản và sẵn sàng triển khai. Quá trình thử việc quý giá giúp em học hỏi rất nhiều về kỹ thuật, quy trình làm việc và phát triển bản thân.

Em xin chân thành cảm ơn công ty BESTMIX đã tạo điều kiện cho em được học hỏi và cống hiến trong suốt thời gian thử việc.

---
**Báo cáo thử việc kỳ tháng 10/2025**
**Tổng số trang: 2**
**Trạng thái: Hoàn thành**
