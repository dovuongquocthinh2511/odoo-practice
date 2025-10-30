# Hướng dẫn Sử dụng Module Đội xe GPS - Odoo 18

**Phiên bản**: 18.0.9.0.0
**Công ty**: BESTMIX
**Ngày cập nhật**: Tháng 10/2025

---

## Mục lục

### [Phần I: Giới thiệu](#phần-i-giới-thiệu)
- [1.1 Tổng quan Module](#11-tổng-quan-module)
- [1.2 Tính năng chính](#12-tính-năng-chính)
- [1.3 Lợi ích cho doanh nghiệp](#13-lợi-ích-cho-doanh-nghiệp)
- [1.4 Đối tượng sử dụng](#14-đối-tượng-sử-dụng)

### [Phần II: Bắt đầu](#phần-ii-bắt-đầu)
- [2.1 Đăng nhập hệ thống](#21-đăng-nhập-hệ-thống)
- [2.2 Giao diện Bảng điều khiển](#22-giao-diện-dashboard)
- [2.3 Điều hướng cơ bản](#23-điều-hướng-cơ-bản)

### [Phần III: Hướng dẫn cho Nhân viên](#phần-iii-hướng-dẫn-cho-nhân-viên)
- [3.1 Truy cập Module Đội xe](#31-truy-cập-module-đội-xe)
- [3.2 Tạo đơn đặt xe mới](#32-tạo-đơn-đặt-xe-mới)
- [3.3 Quản lý đơn đặt xe](#33-quản-lý-đơn-đặt-xe)
- [3.4 Xem hành trình GPS](#34-xem-hành-trình-gps)

### [Phần IV: Hướng dẫn cho Quản lý](#phần-iv-hướng-dẫn-cho-quản-lý)
- [4.1 Bảng điều khiển Quản lý](#41-dashboard-quản-lý)
- [4.2 Xử lý đơn đặt xe chờ phê duyệt](#42-xử-lý-đơn-đặt-xe-chờ-phê-duyệt)
- [4.3 Tạo đơn đặt xe thay nhân viên](#43-tạo-đơn-đặt-xe-thay-nhân-viên)
- [4.4 Theo dõi đơn đã duyệt](#44-theo-dõi-đơn-đã-duyệt)

### [Phần V: Hướng dẫn cho Sale Admin](#phần-v-hướng-dẫn-cho-sale-admin)
- [5.1 Bảng điều khiển Sale Admin](#51-dashboard-sale-admin)
- [5.2 Quản lý Xe](#52-quản-lý-xe)
- [5.3 Điều xe](#53-điều-xe-vehicle-dispatch)
- [5.4 Theo dõi GPS và Bản đồ](#54-theo-dõi-gps-và-bản-đồ)

### [Phần VI: Quy trình Nghiệp vụ](#phần-vi-quy-trình-nghiệp-vụ)
- [6.1 Quy trình Đặt xe cơ bản](#61-quy-trình-đặt-xe-cơ-bản)
- [6.2 Quy trình Phê duyệt](#62-quy-trình-phê-duyệt)
- [6.3 Quy trình Điều xe](#63-quy-trình-điều-xe)
- [6.4 Các trường hợp đặc biệt](#64-các-trường-hợp-đặc-biệt)

### [Phần VII: Tính năng Nâng cao](#phần-vii-tính-năng-nâng-cao)
- [7.1 Tìm kiếm và Lọc](#71-tìm-kiếm-và-lọc)
- [7.2 Xuất báo cáo](#72-xuất-báo-cáo)
- [7.3 Thông báo và Hoạt động](#73-thông-báo-và-activities)
- [7.4 Mẹo và Thủ thuật](#74-tips--tricks)

### [Phần VIII: Câu hỏi thường gặp và Xử lý sự cố](#phần-viii-faq-và-troubleshooting)
- [8.1 Câu hỏi thường gặp](#81-câu-hỏi-thường-gặp)
- [8.2 Xử lý lỗi thường gặp](#82-xử-lý-lỗi-thường-gặp)

### [Phụ lục](#phụ-lục)
- [Phụ lục A: Bảng thuật ngữ](#phụ-lục-a-bảng-thuật-ngữ)
- [Phụ lục B: Bảng trạng thái và màu sắc](#phụ-lục-b-bảng-trạng-thái-và-màu-sắc)
- [Phụ lục C: Quyền truy cập theo vai trò](#phụ-lục-c-quyền-truy-cập-theo-vai-trò)
- [Phụ lục D: Cấu hình hệ thống](#phụ-lục-d-cấu-hình-hệ-thống)

---

# Phần I: Giới thiệu

## 1.1 Tổng quan Module

Module **Đội xe GPS** (BM Fleet GPS Tracking) là giải pháp quản lý đội xe toàn diện được tích hợp với hệ thống GPS ADSUN, giúp doanh nghiệp:

- **Theo dõi vị trí xe** theo thời gian thực
- **Quản lý yêu cầu đặt xe** với quy trình phê duyệt chặt chẽ
- **Điều phối xe** hiệu quả cho các công tác và giao nhận
- **Giám sát hành trình** với dữ liệu GPS chi tiết
- **Tối ưu hóa** việc sử dụng tài nguyên xe

Module được thiết kế theo tiêu chuẩn Odoo 18, tích hợp sâu với hệ thống Quản lý Đội xe và Mail Activity.

## 1.2 Tính năng chính

### 🚗 Quản lý Yêu cầu Đặt xe

- **Tạo đơn nhanh**: Cửa sổ tạo đơn với giao diện thân thiện
- **Gợi ý địa chỉ thông minh**: Tích hợp OpenMap.vn cho địa chỉ Việt Nam
- **Lịch sử địa chỉ**: Ghi nhớ và gợi ý địa chỉ thường dùng
- **Quy trình phê duyệt**: Workflow tự động với 6 trạng thái

### 📍 Theo dõi GPS Real-time

- **Vị trí hiện tại**: Cập nhật vị trí xe theo thời gian thực
- **Trạng thái xe**: Phân biệt Offline / Idle / Running
- **Hành trình chi tiết**: Waypoints với timestamp, tọa độ, tốc độ
- **Thống kê**: Tổng quãng đường, tốc độ trung bình, thời gian chạy

### 🗺️ Bản đồ Hành trình

- **Bản đồ tương tác**: Sử dụng Leaflet.js + OpenStreetMap
- **Hiển thị tuyến đường**: Đường đi với điểm bắt đầu/kết thúc
- **Clustering**: Nhóm xe theo khu vực khi zoom out
- **Lọc nâng cao**: Theo xe, ngày, booking

### ✅ Quy trình Phê duyệt

1. **Mới** - Nhân viên tạo đơn
2. **Quản lý phê duyệt** - Chờ Quản lý duyệt
3. **Đợi điều xe** (Chờ điều xe) - Chờ Sale Admin phân xe
4. **Đang chạy** - Xe đã được điều phối
5. **Hoàn tất** (Hoàn tất) - Công tác hoàn thành
6. **Đã hủy** (Đã hủy) - Đơn bị từ chối

### 🔔 Thông báo Tự động

- **Thông báo công việc**: Thông báo cho người phê duyệt
- **Mail tracking**: Ghi lại lịch sử thay đổi
- **Khu vực trao đổi**: Trao đổi và ghi chú trong đơn

## 1.3 Lợi ích cho doanh nghiệp

| Lợi ích | Mô tả |
|---------|-------|
| **Minh bạch** | Theo dõi toàn bộ quá trình từ yêu cầu đến hoàn thành |
| **Tiết kiệm** | Tối ưu hóa việc sử dụng xe, giảm chi phí vận hành |
| **An toàn** | Giám sát hành trình, kiểm soát tốc độ và vi phạm |
| **Hiệu quả** | Quy trình phê duyệt tự động, giảm thời gian xử lý |
| **Chính xác** | Dữ liệu GPS thời gian thực, báo cáo chi tiết |

## 1.4 Đối tượng sử dụng

Module được thiết kế cho 3 vai trò chính:

### 👤 Nhân viên

**Quyền hạn**:
- Tạo yêu cầu đặt xe cho công tác
- Xem đơn đặt xe của mình
- Theo dõi trạng thái phê duyệt
- Xem hành trình GPS sau khi xe được điều phối

**Nhóm quyền**: `Người dùng BM Fleet`

### 👔 Quản lý

**Quyền hạn**:
- Tất cả quyền của Nhân viên
- Phê duyệt/Từ chối đơn đặt xe của team
- Tạo đơn đặt xe thay nhân viên
- Xem đơn của toàn bộ team

**Nhóm quyền**: `Người dùng BM Fleet` (với quyền Manager)

### 🔧 Sale Admin

**Quyền hạn**:
- Tất cả quyền của Manager
- Điều phối xe và tài xế
- Cấu hình thiết bị GPS
- Xem bản đồ tất cả xe
- Quản lý xe và kiểm tra phạt nguội
- Hoàn thành đơn đặt xe

**Nhóm quyền**: `Sale Admin BM Fleet`

---

# Phần II: Bắt đầu

## 2.1 Đăng nhập hệ thống

### Các bước đăng nhập

1. Mở trình duyệt web và truy cập địa chỉ hệ thống Odoo
2. Nhập thông tin đăng nhập:
   - **Email/Login**: Tài khoản được cấp bởi Admin
   - **Password**: Mật khẩu của bạn
3. Nhấn nút **Đăng nhập**

![Màn hình đăng nhập](screenshots/01_login/annotated/00_login_screen_annotated.png)

**Các thành phần trên màn hình**:
- ❶ Trường **Email/Login**: Nhập tài khoản
- ❷ Trường **Password**: Nhập mật khẩu
- ❸ Nút **Đăng nhập**: Đăng nhập vào hệ thống

💡 **Mẹo**:
- Nếu quên mật khẩu, nhấn **Đặt lại mật khẩu** để nhận email khôi phục
- Hỗ trợ đăng nhập bằng Google/Microsoft nếu được cấu hình

⚠️ **Cảnh báo**:
- Không chia sẻ thông tin đăng nhập với người khác
- Sau 5 lần nhập sai, tài khoản sẽ bị khóa tạm thời

## 2.2 Giao diện Bảng điều khiển

Sau khi đăng nhập thành công, bạn sẽ thấy Bảng điều khiển chính của Odoo với các module được cài đặt.

### Bảng điều khiển theo vai trò

Giao diện Bảng điều khiển sẽ khác nhau tùy theo vai trò:

#### Nhân viên

- **Module hiển thị**: Đội xe, Discuss, Calendar
- **Menu chính**: Đội xe → Đặt xe
- **Truy cập**: Chỉ xem được đơn của mình

#### Quản lý

- **Module hiển thị**: Đội xe, Discuss, Calendar, Approvals
- **Menu chính**: Đội xe → Đặt xe, Phê duyệt
- **Truy cập**: Xem đơn của team và đơn cần phê duyệt

#### Sale Admin

- **Module hiển thị**: Đội xe, Xe, Hành trình, Cấu hình
- **Menu chính**: Tất cả menu trong module
- **Truy cập**: Toàn bộ dữ liệu

## 2.3 Điều hướng cơ bản

### Cấu trúc Menu Module Đội xe

```
📦 Đội xe
├── 📋 Đặt xe
│   ├── Tất cả đơn đặt xe
│   └── Tạo đơn mới (Nút "Mới")
├── 🚗 Xe (Sale Admin only)
│   ├── Danh sách xe
│   └── Cấu hình GPS
├── 🗺️ Hành trình (Sale Admin only)
│   ├── Bản đồ
│   ├── Danh sách Waypoints
│   └── Báo cáo
└── ⚙️ Cấu hình (Sale Admin only)
    ├── Loại dịch vụ
    └── Cài đặt API
```

### Các thành phần giao diện Odoo

| Thành phần | Vị trí | Chức năng |
|------------|--------|-----------|
| **Menu ứng dụng** | Góc trên bên trái | Chuyển đổi giữa các module |
| **Breadcrumb** | Trên cùng, giữa | Hiển thị vị trí hiện tại |
| **Thanh tìm kiếm** | Góc trên bên phải | Tìm kiếm nhanh |
| **Menu người dùng** | Góc trên bên phải | Thông tin user, đăng xuất |
| **Nút tạo mới** | Dưới breadcrumb | Tạo mới đơn (Nút "Mới") |
| **Bảng lọc** | Bên trái | Bộ lọc và nhóm dữ liệu |
| **Chuyển đổi giao diện** | Góc phải | Chuyển đổi giữa Giao diện thẻ/List/Form |

### Phím tắt hữu ích

| Phím tắt | Chức năng |
|----------|-----------|
| `Alt + N` hoặc `Ctrl + Alt + N` | Tạo mới đơn |
| `Alt + E` hoặc `Ctrl + Alt + E` | Chỉnh sửa đơn |
| `Alt + S` hoặc `Ctrl + Alt + S` | Lưu đơn |
| `Alt + D` hoặc `Ctrl + Alt + D` | Hủy chỉnh sửa |
| `Alt + J` | Mở khu vực trao đổi |
| `Ctrl + K` | Command palette (tìm kiếm nhanh) |

📝 **Lưu ý**: Phím tắt có thể khác nhau trên macOS (Cmd thay vì Ctrl)

---

# Phần III: Hướng dẫn cho Nhân viên

Phần này hướng dẫn chi tiết cho **Nhân viên** (Employee) cách sử dụng module để tạo và quản lý yêu cầu đặt xe.

## 3.1 Truy cập Module Đội xe

### Các bước truy cập

1. Từ Bảng điều khiển chính, click vào icon **Đội xe**
2. Hoặc sử dụng menu trên cùng: **Đội xe** → **Đặt xe**

![Bảng điều khiển Nhân viên](screenshots/02_fleet_user_employee/annotated/01_dashboard_annotated.png)

✅ **Kết quả**: Bạn sẽ thấy màn hình **Giao diện thẻ** với các đơn đặt xe

## 3.2 Tạo đơn đặt xe mới

Có 2 cách để tạo đơn đặt xe:

### Cách 1: Sử dụng Tạo nhanh (Khuyến nghị)

Đây là cách nhanh nhất để tạo đơn đặt xe mới.

#### Các bước thực hiện

1. Tại màn hình Giao diện thẻ, nhấn nút **Mới** (hoặc nhấn `Alt + N`)
2. Cửa sổ **Tạo nhanh** xuất hiện
3. Điền thông tin cần thiết:

![Cửa sổ tạo đơn nhanh](screenshots/02_fleet_user_employee/annotated/03_create_booking_wizard_annotated.png)

**Các trường thông tin**:

| Số | Trường | Bắt buộc | Mô tả |
|----|--------|----------|-------|
| ❶ | **Địa điểm đi** | ✅ Có | Nhập địa chỉ khởi hành (tối thiểu 3 ký tự để có gợi ý) |
| ❷ | **Địa điểm đến** | ✅ Có | Nhập địa chỉ đích đến (tối thiểu 3 ký tự để có gợi ý) |
| ❸ | **Mục đích công tác** | ✅ Có | Mô tả ngắn gọn mục đích chuyến đi |
| ❹ | **Ngày giờ bắt đầu công tác** | ✅ Có | Chọn ngày và giờ dự kiến khởi hành |
| ❺ | **Ngày giờ kết thúc dự kiến** | ✅ Có | Chọn ngày và giờ dự kiến kết thúc |
| ❻ | **Team yêu cầu** | ✅ Có | Chọn phòng ban/team của bạn |
| ❼ | **Người yêu cầu** | Auto | Tự động điền = người đang đăng nhập |
| ❽ | **Thành viên tham gia** | ⭕ Không | Chọn thêm người đi cùng (nếu có) |
| ❾ | **Nút Đăng ký** | - | Nhấn để tạo đơn |

4. Nhấn nút **Đăng ký** (Lưu)

✅ **Kết quả**: Đơn đặt xe được tạo với trạng thái **Mới**

### Tính năng Gợi ý Địa chỉ Thông minh

Module tích hợp OpenMap.vn API để hỗ trợ nhập địa chỉ:

💡 **Cách sử dụng**:
1. Nhập tối thiểu 3 ký tự vào trường địa chỉ
2. Hệ thống hiển thị danh sách gợi ý
3. Click chọn địa chỉ từ danh sách

**Ưu tiên gợi ý**:
- ⭐ **Địa chỉ thường dùng**: Địa chỉ bạn đã sử dụng trước đó
- 🌐 **Địa chỉ OpenMap**: Địa chỉ từ cơ sở dữ liệu quốc gia

⚠️ **Lưu ý**:
- Nên chọn từ danh sách gợi ý để có tọa độ GPS chính xác
- Nếu không tìm thấy, có thể nhập tự do nhưng có thể ảnh hưởng độ chính xác bản đồ

### Cách 2: Sử dụng Form đầy đủ

Nếu cần nhập thêm thông tin chi tiết:

1. Nhấn nút **Mới**
2. Tại Tạo nhanh, nhấn nút **Chỉnh sửa chi tiết** (hoặc `Alt + E`)
3. Màn hình chi tiết đầy đủ xuất hiện:

![Form đầy đủ](screenshots/02_fleet_user_employee/annotated/04_booking_form_view_annotated.png)

**Thông tin bổ sung có thể nhập**:
- **Ghi chú**: Thông tin thêm về chuyến đi
- **Tài liệu đính kèm**: Upload file liên quan

4. Nhấn **Lưu** khi hoàn tất

## 3.3 Quản lý đơn đặt xe

### Xem danh sách đơn đặt xe

Sau khi tạo đơn, bạn có thể xem và quản lý đơn qua **Giao diện thẻ**.

![Giao diện thẻ](screenshots/02_fleet_user_employee/annotated/02_booking_kanban_view_annotated.png)

### Các cột trạng thái

Đơn đặt xe sẽ di chuyển qua các cột theo quy trình:

| Cột | Trạng thái | Màu sắc | Mô tả |
|-----|------------|---------|-------|
| **Mới** | `new` | Xám | Đơn vừa tạo, chưa gửi phê duyệt |
| **Quản lý phê duyệt** | `pending_manager` | Xanh dương | Chờ Quản lý phê duyệt |
| **Đợi điều xe** | `pending_dispatch` | Cam | Quản lý đã duyệt, chờ Sale Admin điều xe |
| **Đang chạy** | `running` | Tím | Xe đã được điều phối, đang thực hiện |
| **Hoàn tất** | `done` | Xanh lá | Chuyến đi hoàn thành |

📝 **Lưu ý**: Cột **Đã hủy** (Đã hủy) không hiển thị mặc định. Sử dụng bộ lọc để xem.

### Gửi đơn để phê duyệt

Sau khi tạo đơn ở trạng thái **Mới**, bạn cần gửi đi phê duyệt:

1. Click vào đơn đặt xe để mở
2. Kiểm tra lại thông tin
3. Nhấn nút **Gửi phê duyệt** (Gửi phê duyệt)

✅ **Kết quả**:
- Đơn chuyển sang trạng thái **Quản lý phê duyệt**
- Hệ thống tự động tạo thông báo công việc cho Quản lý
- Quản lý nhận thông báo

### Theo dõi trạng thái đơn

Để biết đơn đang ở đâu trong quy trình:

**Cách 1: Xem trên Giao diện thẻ**
- Đơn của bạn xuất hiện ở cột tương ứng với trạng thái

**Cách 2: Xem chi tiết trong Form**
- Mở đơn → Xem **Thanh trạng thái** ở trên cùng
- Các trạng thái đã qua sẽ được highlight

**Cách 3: Theo dõi Thông báo công việc**
- Chuông thông báo ở góc phải trên
- Số đỏ hiển thị số thông báo chưa đọc

### Chỉnh sửa đơn đang chờ

⚠️ **Quan trọng**: Chỉ có thể chỉnh sửa đơn khi ở trạng thái **Mới**

Nếu cần sửa đơn đã gửi phê duyệt:
1. Liên hệ Quản lý để **Đặt lại** đơn về trạng thái **Mới**
2. Sau đó bạn có thể chỉnh sửa
3. Gửi lại phê duyệt

## 3.4 Xem hành trình GPS

Sau khi đơn ở trạng thái **Đang chạy** hoặc **Hoàn tất**, bạn có thể xem hành trình GPS.

### Xem danh sách Hành trình

1. Mở đơn đặt xe đã được điều xe
2. Click vào **Nút thông minh Hành trình**

![Nút thông minh Hành trình](screenshots/02_fleet_user_employee/annotated/06_booking_form_view_Journey_smart_button_summary_annotated.png)

✅ **Kết quả**: Danh sách các điểm GPS (waypoints) hiển thị với:
- Thời gian
- Tọa độ (Latitude/Longitude)
- Địa chỉ (nếu có)
- Tốc độ (km/h)
- Quãng đường (km)

### Xem Bản đồ Tuyến đường

1. Mở đơn đặt xe đã được điều xe
2. Click vào **Nút thông minh Tuyến đường**

![Nút thông minh Tuyến đường](screenshots/02_fleet_user_employee/annotated/07_booking_form_view_route_smart_button_annotated.png)

✅ **Kết quả**: Bản đồ hiển thị:
- **Đường đi thực tế**: Đường nối các waypoints GPS
- **Điểm bắt đầu**: Marker màu xanh lá
- **Điểm kết thúc**: Marker màu đỏ
- **Thông tin chi tiết**: Click vào marker để xem

💡 **Mẹo**:
- Zoom in/out để xem chi tiết
- Click vào các điểm trên đường để xem thời gian đi qua
- Sử dụng bộ lọc để xem theo khoảng thời gian

---

# Phần IV: Hướng dẫn cho Quản lý

Phần này hướng dẫn chi tiết cho **Quản lý** (Manager) cách xử lý phê duyệt đơn đặt xe và các chức năng quản lý.

## 4.1 Bảng điều khiển Quản lý

Với vai trò Quản lý, bạn có thêm quyền phê duyệt đơn đặt xe của team.

![Bảng điều khiển Quản lý](screenshots/03_fleet_user_manager/annotated/01_dashboard_annotated.png)

**Điểm khác biệt so với Nhân viên**:
- ✅ Xem được tất cả đơn của team
- ✅ Có nút Phê duyệt/Từ chối
- ✅ Nhận thông báo Hoạt động khi có đơn chờ duyệt

## 4.2 Xử lý đơn đặt xe chờ phê duyệt

### Xem danh sách đơn chờ duyệt

Có 3 cách để xem đơn cần phê duyệt:

**Cách 1: Từ Giao diện thẻ**
- Truy cập **Đội xe** → **Đặt xe**
- Xem cột **Quản lý phê duyệt**

![Giao diện thẻ Quản lý](screenshots/03_fleet_user_manager/annotated/02_booking_kaban_view_annotated.png)

**Cách 2: Từ Hoạt động**
- Click chuông thông báo ở góc phải trên
- Chọn thông báo "Yêu cầu phê duyệt"

**Cách 3: Sử dụng Bộ lọc**
- Tại màn hình Đặt xe
- Click **Bộ lọc** → **Chờ phê duyệt**

### Phê duyệt đơn đặt xe

Khi nhận được yêu cầu phê duyệt:

#### Các bước phê duyệt

1. Click vào đơn cần phê duyệt
2. Kiểm tra thông tin:
   - Mục đích công tác có hợp lý?
   - Thời gian có phù hợp?
   - Địa điểm đi/đến rõ ràng?

3. Click nút **Phê duyệt**

![Form Phê duyệt](screenshots/03_fleet_user_manager/annotated/05_booking_form_view_approved_stage_annotated.png)

**Các thành phần trên màn hình**:
- ❶ **Mã đơn đặt xe**: Mã tự động (FSB/2025/10/XXXX)
- ❷ **Thông tin công tác**: Địa điểm, mục đích, thời gian
- ❸ **Thông tin đặt xe**: Người yêu cầu, ngày đặt
- ❹ **Thông tin phê duyệt**: Người phê duyệt, ngày phê duyệt
- ❺ **Nút Phê duyệt/Từ chối**: Ở góc trên bên trái

✅ **Kết quả**:
- Đơn chuyển sang trạng thái **Đợi điều xe**
- Thông báo công việc được đóng
- Hệ thống tạo thông báo mới cho Sale Admin
- Nhân viên nhận thông báo đơn đã được duyệt

### Từ chối đơn đặt xe

Nếu đơn không hợp lý hoặc cần điều chỉnh:

#### Các bước từ chối

1. Mở đơn cần từ chối
2. Click nút **Từ chối** (Từ chối)
3. **Hộp thoại xác nhận từ chối** xuất hiện
4. Nhập **Lý do từ chối** (bắt buộc)
5. Click **Xác nhận**

✅ **Kết quả**:
- Đơn chuyển sang trạng thái **Đã hủy**
- Lý do từ chối được ghi lại
- Nhân viên nhận thông báo và lý do từ chối
- Nhân viên có thể Đặt lại đơn để chỉnh sửa và gửi lại

💡 **Mẹo**:
- Nên mô tả rõ lý do từ chối để nhân viên biết cần sửa gì
- Có thể chat trực tiếp trong khu vực trao đổi để trao đổi thêm

## 4.3 Tạo đơn đặt xe thay nhân viên

Quản lý có thể tạo đơn thay cho nhân viên trong team.

### Các bước thực hiện

1. Truy cập **Đội xe** → **Đặt xe**
2. Nhấn nút **Mới**
3. Điền thông tin như hướng dẫn ở [Phần 3.2](#32-tạo-đơn-đặt-xe-mới)

![Cửa sổ tạo đơn](screenshots/03_fleet_user_manager/annotated/03_create_booking_wizard_annotated.png)

**Lưu ý khi tạo thay**:
- Chọn đúng **Người yêu cầu** (không phải chính Quản lý)
- Chọn đúng **Team yêu cầu**
- Điền đầy đủ thông tin để Sale Admin dễ điều xe

4. Nhấn **Đăng ký**
5. Đơn được tạo ở trạng thái **Mới**
6. Quản lý có thể tự phê duyệt luôn nếu cần

💡 **Mẹo**:
- Nên thông báo cho nhân viên khi tạo đơn thay
- Sử dụng khu vực trao đổi để tag nhân viên và giải thích

## 4.4 Theo dõi đơn đã duyệt

Sau khi phê duyệt, Quản lý vẫn có thể theo dõi tiến trình đơn.

### Xem trạng thái điều xe

1. Truy cập **Đội xe** → **Đặt xe**
2. Xem cột **Đợi điều xe** và **Đang chạy**

![Đơn đã điều xe](screenshots/03_fleet_user_manager/annotated/06_booking_form_view_dispatched_annotated.png)

### Xem hành trình GPS

Quản lý có thể xem hành trình GPS giống như nhân viên:

1. Mở đơn đặt xe
2. Click **Nút thông minh Hành trình** hoặc **Route**

![Nút thông minh Hành trình](screenshots/03_fleet_user_manager/annotated/07_booking_form_view_Journey_smart_button_summary_annotated.png)

![Nút thông minh Tuyến đường](screenshots/03_fleet_user_manager/annotated/08_booking_form_view_route_smart_button_annotated.png)

💡 **Mẹo**:
- Sử dụng tính năng Nhóm theo để xem theo Team
- Xuất báo cáo định kỳ để review việc sử dụng xe

---

# Phần V: Hướng dẫn cho Sale Admin

Phần này hướng dẫn chi tiết cho **Sale Admin** các chức năng quản lý xe, điều xe, và theo dõi GPS toàn diện.

## 5.1 Bảng điều khiển Sale Admin

Với vai trò Sale Admin, bạn có toàn quyền quản lý module.

![Bảng điều khiển Sale Admin](screenshots/04_sale_admin/annotated/01_dashboard_annotated.png)

**Quyền hạn của Sale Admin**:
- ✅ Quản lý danh sách xe
- ✅ Cấu hình thiết bị GPS
- ✅ Điều phối xe và tài xế
- ✅ Xem bản đồ tất cả xe
- ✅ Hoàn thành đơn đặt xe
- ✅ Kiểm tra phạt nguội

## 5.2 Quản lý Xe

### Xem danh sách Xe

1. Truy cập **Đội xe** → **Xe** (hoặc từ menu trên: **Xe** → **Xe**)
2. Giao diện thẻ hiển thị danh sách xe

![Giao diện thẻ Xe](screenshots/04_sale_admin/annotated/02_vehicle_kanban_annotated.png)

**Thông tin hiển thị trên card**:
- Tên xe / Biển số
- Trạng thái GPS (Offline/Idle/Running)
- Vị trí hiện tại (nếu có)
- Tài xế được gán

### Xem và Chỉnh sửa Thông tin Xe

1. Click vào xe cần xem
2. Màn hình chi tiết hiển thị đầy đủ thông tin

![Form Xe](screenshots/04_sale_admin/annotated/03_vehicle_form_annotated.png)

**Các tab thông tin**:
- **Thông tin chung**: Thông tin cơ bản (tên, biển số, model, năm sản xuất)
- **Driver**: Tài xế được gán
- **GPS Tracking**: Cấu hình thiết bị GPS
- **Phạt nguội**: Kiểm tra phạt nguội
- **Contracts**: Hợp đồng bảo hiểm, đăng kiểm
- **Services**: Lịch sử bảo dưỡng

### Cấu hình Thiết bị GPS

Để xe có thể theo dõi GPS, cần cấu hình thiết bị:

#### Tab GPS Tracking

![Tab GPS Tracking](screenshots/04_sale_admin/annotated/04_gps_tracking_tab_annotated.png)

**Các trường cấu hình**:

| Trường | Bắt buộc | Mô tả |
|--------|----------|-------|
| **GPS Device Serial** | ✅ Có | Số serial thiết bị GPS (ví dụ: 579324495) |
| **GPS Company ID** | ✅ Có | Mã công ty trên hệ thống ADSUN (mặc định: 1136) |
| **Branch** | ⭕ Không | Chi nhánh quản lý xe |
| **Vị trí hiện tại** | Auto | Vị trí hiện tại (tự động cập nhật) |
| **Lần đồng bộ cuối** | Auto | Lần đồng bộ GPS cuối cùng |

#### Các bước cấu hình

1. Mở form xe cần cấu hình
2. Chuyển đến tab **GPS Tracking**
3. Nhập **GPS Device Serial**
   - Hoặc nhấn nút **Tìm số serial GPS** để tự động tìm (nếu biết thông tin xe)
4. Nhập **GPS Company ID** (thường là 1136 cho BESTMIX)
5. Click **Lưu**
6. Nhấn nút **Đồng bộ dữ liệu GPS** để thử đồng bộ

✅ **Kết quả**:
- Vị trí hiện tại được cập nhật
- Hành trình GPS bắt đầu được ghi lại
- Xe xuất hiện trên bản đồ

💡 **Mẹo**:
- Nếu không biết GPS Serial, liên hệ đơn vị lắp thiết bị GPS
- Có thể xem danh sách thiết bị GPS qua API ADSUN

⚠️ **Cảnh báo**:
- GPS Serial phải chính xác 100% mới đồng bộ được
- Không cấu hình GPS Serial của xe khác

### Kiểm tra Phạt nguội

#### Tab Phạt nguội

![Tab Phạt nguội](screenshots/04_sale_admin/annotated/05_traffic_violation_tab_annotated.png)

**Ảnh trên đã gán nhãn các phần tử giao diện (1-9)** để dễ dàng tra cứu.

##### Cấu trúc Tab

**1. TRẠNG THÁI VI PHẠM** (bên trái)

| Số | Trường thông tin | Mô tả |
|---|---|---|
| 2 | Trạng thái phạt nguội | Badge màu hiển thị trạng thái: "Không có vi phạm" (xanh) / "Có vi phạm" (đỏ) |
| 3 | Số lần vi phạm chưa xử lý | Số lượng vi phạm chưa được xử lý (chưa đóng phạt) |
| 4 | Lần kiểm tra cuối | Thời gian kiểm tra phạt nguội gần nhất qua API |

**2. THÔNG TIN VI PHẠM GẦN NHẤT** (bên phải)

| Số | Trường thông tin | Mô tả |
|---|---|---|
| 5 | Thời gian vi phạm | Ngày giờ xảy ra vi phạm giao thông |
| 6 | Địa điểm vi phạm | Vị trí địa lý nơi phát hiện vi phạm |
| 7 | Hành vi vi phạm | Mô tả chi tiết hành vi vi phạm (theo quy định) |
| 8 | Đơn vị phát hiện | Cơ quan CSGT phát hiện và lập biên bản |

**3. NÚT THAO TÁC**

| Số | Nút | Mô tả |
|---|---|---|
| 9 | Kiểm tra vi phạm | Kết nối API iphatnguoi.com để lấy dữ liệu phạt nguội mới nhất |

##### Cách sử dụng

1. Mở form xe cần kiểm tra
2. Chuyển đến tab **Vi phạm giao thông**
3. Nhấn nút **Kiểm tra vi phạm** (số 9)
4. Hệ thống kết nối API Cục CSGT và hiển thị kết quả sau vài giây

##### Màu sắc Badge Trạng thái

- 🟢 **Xanh** ("Không có vi phạm"): Xe không có vi phạm chưa xử lý
- 🔴 **Đỏ** ("Có vi phạm"): Xe có vi phạm chưa đóng phạt

##### Lưu ý quan trọng

- ✅ **Cần kết nối Internet**: API yêu cầu kết nối mạng ổn định
- ⏱️ **Thời gian phản hồi**: API có thể chậm vào giờ cao điểm (30-60s)
- 💾 **Cache 24 giờ**: Dữ liệu được lưu tạm 24 giờ, nhấn lại nút để cập nhật mới
- 🔄 **Tự động cập nhật**: Khi có vi phạm mới, badge và số lượng sẽ tự động cập nhật sau lần kiểm tra tiếp theo

## 5.3 Điều xe

Đây là nhiệm vụ quan trọng nhất của Sale Admin: điều phối xe cho các đơn đặt xe đã được phê duyệt.

### Xem danh sách đơn chờ điều xe

1. Truy cập **Đội xe** → **Đặt xe**
2. Xem toàn bộ các trạng thái

![Giao diện thẻ All States](screenshots/04_sale_admin/annotated/06_booking_kanban_all_states_annotated.png)

**Lưu ý**: Sale Admin thấy tất cả cột, bao gồm **Đợi điều xe** (Chờ điều xe)

### Phân công Xe và Tài xế

Khi có đơn ở cột **Đợi điều xe**:

#### Các bước điều xe

1. Click vào đơn cần điều xe
2. Màn hình chi tiết hiển thị đầy đủ thông tin

![Màn hình chi tiết - Tất cả trạng thái](screenshots/04_sale_admin/annotated/07_booking_formview_all_states_annotated.png)

3. Scroll xuống phần **Thông tin điều xe**
4. Chọn **Vehicle** (Xe)
   - Dropdown hiển thị danh sách xe có sẵn
   - Ưu tiên xe đang Idle (không chạy)
5. Chọn **Driver** (Tài xế)
   - Dropdown hiển thị danh sách tài xế
   - Hoặc để trống nếu chủ xe tự lái
6. Nhập **Ngày điều xe** (Ngày điều xe)
   - Mặc định là ngày hiện tại
   - Có thể điều chỉnh nếu điều trước
7. Nhập **Notes** (Ghi chú) nếu cần
8. Click nút **Điều xe**

![Form Dispatched](screenshots/04_sale_admin/annotated/08_booking_form_view_dispatched_annotated.png)

✅ **Kết quả**:
- Đơn chuyển sang trạng thái **Đang chạy**
- Thông báo công việc được đóng
- Nhân viên và Quản lý nhận thông báo
- Xe và tài xế được gán cho chuyến đi
- Bắt đầu ghi lại hành trình GPS

💡 **Mẹo**:
- Kiểm tra lịch xe trước khi điều để tránh trùng
- Ưu tiên xe gần địa điểm khởi hành
- Gọi điện xác nhận với tài xế trước khi dispatch

⚠️ **Cảnh báo**:
- Không dispatch xe đang chạy chuyến khác
- Không dispatch xe offline (không có GPS signal)

### Từ chối Điều xe

Nếu không thể điều xe (không có xe trống, điều kiện thời tiết...):

1. Mở đơn cần từ chối
2. Click nút **Từ chối** (Từ chối)
3. Nhập **Lý do từ chối**
4. Click **Xác nhận**

✅ **Kết quả**:
- Đơn chuyển sang trạng thái **Đã hủy**
- Nhân viên và Quản lý nhận thông báo với lý do

### Hoàn thành Đơn đặt xe

Sau khi chuyến đi hoàn tất:

1. Mở đơn đang ở trạng thái **Đang chạy**
2. Xác nhận công tác đã hoàn thành
3. Click nút **Hoàn tất**

✅ **Kết quả**:
- Đơn chuyển sang trạng thái **Hoàn tất**
- Xe và tài xế được giải phóng
- Hành trình GPS được khóa (không cập nhật nữa)
- Có thể xuất báo cáo

### Xem Tuyến đường đã điều xe

Sau khi dispatch, có thể xem tuyến đường:

1. Mở đơn đã điều xe
2. Click **Nút thông minh Tuyến đường**

![Nút thông minh Tuyến đường](screenshots/04_sale_admin/annotated/10_booking_form_view_route_smart_button_annotated.png)

## 5.4 Theo dõi GPS và Bản đồ

Sale Admin có quyền xem tất cả xe trên bản đồ.

### Truy cập Bản đồ Hành trình

1. Từ menu trên: **Đội xe** → **Hành trình** → **Bản đồ hành trình**

![Menu Bản đồ hành trình](screenshots/04_sale_admin/annotated/11_journey_map_menu_annotated.png)

2. Bản đồ hiển thị tất cả vị trí xe

![Map All Locations](screenshots/04_sale_admin/annotated/12_journey_map_all_location_annotated.png)

**Các thành phần trên bản đồ**:

| Số | Thành phần | Chức năng |
|----|-----------|-----------|
| ❶ | **Nút Xem từng xe** | Chuyển đổi giữa xem tất cả/từng xe |
| ❷ | **Điểm nhóm** | Nhóm xe theo khu vực (số hiển thị số lượng) |
| ❸ | **Điểm xe** | Vị trí xe riêng lẻ |

### Các tính năng Bản đồ

#### Zoom và Navigation

- **Phóng to/Thu nhỏ**: Nút +/- hoặc scroll chuột
- **Pan**: Click và kéo bản đồ
- **Center**: Double-click để center tại điểm đó

#### Xem chi tiết Xe

1. Click vào marker của xe
2. Popup hiển thị thông tin:
   - Tên xe / Biển số
   - Tài xế
   - Vị trí hiện tại
   - Thời gian cập nhật
   - Trạng thái (Idle/Running)
   - Tốc độ hiện tại

#### Xem Hành trình Chi tiết

1. Click vào xe trên bản đồ
2. Trong popup, click **Xem hành trình**
3. Bản đồ hiển thị tuyến đường chi tiết

![Map Detail](screenshots/04_sale_admin/annotated/13_journey_map_detail_annotated.png)

**Hiển thị**:
- **Đường đi**: Đường nối các waypoints
- **Marker xanh lá**: Điểm bắt đầu
- **Marker đỏ**: Điểm kết thúc
- **Markers dọc đường**: Các điểm dừng/chuyển hướng

#### Lọc và Tìm kiếm

Sử dụng panel bên trái để lọc:

**Lọc theo**:
- **Vehicle**: Chọn xe cụ thể
- **Khoảng thời gian**: Chọn khoảng thời gian
- **Trạng thái**: Đang chạy/Đang đỗ/Mất kết nối

💡 **Mẹo**:
- Sử dụng clustering để xem tổng quan nhanh
- Zoom in để xem chi tiết từng xe
- Lọc theo date range để phân tích xu hướng

### Danh sách Waypoints

Ngoài bản đồ, có thể xem dạng danh sách:

1. Từ menu: **Đội xe** → **Hành trình** → **Hành trình vận tải**
2. Giao diện danh sách hiển thị tất cả waypoints

**Thông tin hiển thị**:
- Xe
- Thời gian
- Vị trí (Lat/Long)
- Địa chỉ (nếu có geocoding)
- Tốc độ (km/h)
- Quãng đường tích lũy

**Sử dụng**:
- Xuất Excel để phân tích
- Tìm kiếm waypoint cụ thể
- So sánh giữa các xe

---

# Phần VI: Quy trình Nghiệp vụ

Phần này mô tả chi tiết các quy trình nghiệp vụ hoàn chỉnh của module.

## 6.1 Quy trình Đặt xe cơ bản

### Sơ đồ Quy trình Tổng quát

```
┌─────────────┐
│  Nhân viên  │
│  Tạo đơn    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Mới      │ ◄─── Đặt lại (nếu bị từ chối)
│   (New)     │
└──────┬──────┘
       │ Gửi phê duyệt
       ▼
┌─────────────┐
│ Quản lý phê │
│   duyệt     │
│(Pending Mgr)│
└──────┬──────┘
       │
       ├─── Phê duyệt ───┐
       │               ▼
       │         ┌─────────────┐
       │         │ Đợi điều xe │
       │         │(Pending     │
       │         │ Dispatch)   │
       │         └──────┬──────┘
       │                │
       │                ├─── Dispatch ──┐
       │                │                ▼
       │                │          ┌─────────────┐
       │                │          │ Đang chạy   │
       │                │          │  (Running)  │
       │                │          └──────┬──────┘
       │                │                 │ Hoàn tất
       │                │                 ▼
       │                │           ┌─────────────┐
       │                │           │  Hoàn tất   │
       │                │           │   (Hoàn tất)    │
       │                │           └─────────────┘
       │                │
       │                └─── Từ chối ──┐
       │                               │
       └─── Từ chối ────────────────────┤
                                       ▼
                                 ┌─────────────┐
                                 │   Đã hủy    │
                                 │ (Đã hủy) │
                                 └─────────────┘
```

### Chi tiết từng Giai đoạn

#### Giai đoạn 1: Tạo đơn

**Người thực hiện**: Nhân viên
**Thời gian**: 2-5 phút

**Các bước**:
1. Nhân viên đăng nhập hệ thống
2. Truy cập Module Đội xe
3. Tạo đơn đặt xe mới (Tạo nhanh hoặc Form đầy đủ)
4. Điền thông tin:
   - Địa điểm đi/đến
   - Mục đích công tác
   - Thời gian
   - Team và thành viên
5. Lưu đơn → Trạng thái **Mới**

**Kết quả**:
- Đơn được lưu nhưng chưa gửi phê duyệt
- Nhân viên có thể chỉnh sửa thoải mái

#### Giai đoạn 2: Gửi phê duyệt

**Người thực hiện**: Nhân viên
**Thời gian**: Vài giây

**Các bước**:
1. Nhân viên kiểm tra lại thông tin đơn
2. Nhấn nút **Gửi phê duyệt**
3. Đơn chuyển sang trạng thái **Quản lý phê duyệt**

**Kết quả**:
- Hệ thống tạo thông báo công việc cho Quản lý
- Quản lý nhận thông báo qua email và in-app
- Nhân viên không thể chỉnh sửa đơn nữa

**Thời gian chờ**: Tùy Quản lý, thường 1-24 giờ

#### Giai đoạn 3: Phê duyệt (Chờ điều xe)

**Người thực hiện**: Quản lý
**Thời gian**: 5-10 phút

**Các bước**:
1. Manager nhận thông báo
2. Mở đơn để xem chi tiết
3. Kiểm tra:
   - Mục đích có hợp lý?
   - Ngân sách có đủ?
   - Thời gian có phù hợp?
4. Quyết định:
   - **Phê duyệt**: Đơn chuyển sang **Đợi điều xe**
   - **Từ chối**: Đơn chuyển sang **Đã hủy** (với lý do)

**Kết quả (nếu phê duyệt)**:
- Thông báo cho Quản lý được đóng
- Hệ thống tạo thông báo mới cho Sale Admin
- Nhân viên nhận thông báo đơn đã được duyệt

**Kết quả (nếu từ chối)**:
- Đơn chuyển sang **Đã hủy**
- Nhân viên nhận thông báo với lý do từ chối
- Nhân viên có thể Đặt lại để sửa và gửi lại

#### Giai đoạn 4: Điều xe

**Người thực hiện**: Sale Admin
**Thời gian**: 10-30 phút

**Các bước**:
1. Sale Admin nhận thông báo
2. Xem danh sách xe khả dụng
3. Chọn xe phù hợp:
   - Gần địa điểm khởi hành
   - Không bận chuyến khác
   - Có GPS hoạt động
4. Chọn tài xế (nếu cần)
5. Nhập ngày điều xe
6. Nhấn **Điều xe**

**Kết quả**:
- Đơn chuyển sang trạng thái **Đang chạy**
- Xe và tài xế được gán cho chuyến đi
- Nhân viên và Quản lý nhận thông báo
- Hệ thống bắt đầu ghi lại hành trình GPS

**Trong quá trình chạy**:
- GPS cập nhật vị trí mỗi 5 phút
- Có thể xem real-time trên bản đồ
- Tốc độ và quãng đường được ghi lại

#### Giai đoạn 5: Hoàn thành (Hoàn tất)

**Người thực hiện**: Sale Admin
**Thời gian**: Vài giây

**Các bước**:
1. Sau khi nhân viên hoàn tất công tác
2. Sale Admin xác nhận
3. Nhấn nút **Hoàn tất**

**Kết quả**:
- Đơn chuyển sang trạng thái **Hoàn tất**
- Xe và tài xế được giải phóng
- Hành trình GPS được khóa
- Báo cáo có thể được xuất

## 6.2 Quy trình Phê duyệt

### Tiêu chí Phê duyệt

Manager cần xem xét các tiêu chí sau:

| Tiêu chí | Câu hỏi kiểm tra | Hành động nếu không đạt |
|----------|------------------|-------------------------|
| **Tính hợp lý** | Mục đích có phù hợp với công việc? | Từ chối, yêu cầu làm rõ |
| **Tính khẩn cấp** | Có cần xe ngay không? Có thể dùng phương tiện khác? | Đề xuất phương án thay thế |
| **Thời gian** | Thời gian có hợp lý? Có trùng lịch quan trọng khác? | Từ chối, yêu cầu điều chỉnh |
| **Ngân sách** | Chi phí dự kiến có trong ngân sách? | Từ chối nếu vượt ngân sách |
| **Thành viên** | Người tham gia có liên quan đến công tác? | Yêu cầu giải thích |

### Thời gian Phản hồi

**SLA (Service Level Agreement)**:
- **Khẩn cấp**: Phản hồi trong 2 giờ
- **Bình thường**: Phản hồi trong 1 ngày làm việc
- **Không khẩn**: Phản hồi trong 2 ngày làm việc

### Các trường hợp Từ chối

**Lý do từ chối phổ biến**:
1. **Mục đích không rõ ràng**
   - Ví dụ: "Đi công tác" → Cần cụ thể hơn
   - Đề xuất: "Từ chối - Vui lòng làm rõ nội dung công tác"

2. **Thời gian không hợp lý**
   - Ví dụ: Đặt xe vào 23h đêm cho công tác sáng hôm sau
   - Đề xuất: "Từ chối - Thời gian quá gấp, vui lòng đặt trước ít nhất 1 ngày"

3. **Có thể dùng phương tiện khác**
   - Ví dụ: Quãng đường ngắn, có xe bus
   - Đề xuất: "Từ chối - Đề nghị sử dụng phương tiện công cộng"

4. **Vượt ngân sách**
   - Ví dụ: Tổng chi phí xe tháng này đã đạt hạn mức
   - Đề xuất: "Từ chối - Hết ngân sách tháng này, vui lòng chờ tháng sau"

## 6.3 Quy trình Điều xe

### Nguyên tắc Điều xe

1. **Ưu tiên**:
   - Đơn khẩn cấp trước
   - Theo thứ tự thời gian phê duyệt
   - Ưu tiên ban lãnh đạo

2. **Tối ưu hóa**:
   - Chọn xe gần địa điểm khởi hành nhất
   - Gộp chuyến nếu có thể (cùng hướng, cùng thời gian)
   - Cân đối tải giữa các xe

3. **An toàn**:
   - Không dispatch xe offline
   - Không dispatch xe quá giờ làm việc tài xế
   - Kiểm tra đăng kiểm, bảo hiểm còn hạn

### Checklist Trước khi Điều xe

- [ ] Xe có GPS hoạt động?
- [ ] Xe không bận chuyến khác?
- [ ] Tài xế có sẵn sàng?
- [ ] Đăng kiểm, bảo hiểm còn hạn?
- [ ] Nhiên liệu đủ cho chuyến đi?
- [ ] Đã xác nhận với tài xế?

### Xử lý Xung đột

**Trường hợp**: 2 đơn cùng thời gian, chỉ có 1 xe

**Giải pháp**:
1. So sánh mức độ ưu tiên (khẩn cấp, quan trọng)
2. Liên hệ cả 2 bên để xem ai có thể dịch thời gian
3. Tìm xe thay thế (thuê ngoài, mượn chi nhánh khác)
4. Nếu không được, ưu tiên đơn được duyệt trước

## 6.4 Các trường hợp đặc biệt

### Đặt lại đơn đã Từ chối

**Khi nào**: Nhân viên muốn sửa đơn đã bị từ chối

**Các bước**:
1. Nhân viên mở đơn ở trạng thái **Đã hủy**
2. Nhấn nút **Đặt lại**
3. Đơn quay về trạng thái **Mới**
4. Nhân viên chỉnh sửa theo góp ý
5. Gửi lại phê duyệt

**Lưu ý**:
- Chỉ người tạo đơn hoặc Manager có thể Đặt lại
- Nên đọc kỹ lý do từ chối trước khi sửa

### Hủy đơn đang Chạy

**Khi nào**: Công tác bị hủy đột xuất

**Các bước**:
1. Liên hệ Sale Admin
2. Sale Admin mở đơn
3. Trong khu vực trao đổi, ghi lý do hủy
4. Sale Admin chuyển đơn sang **Đã hủy** thủ công (qua Chế độ Nhà phát triển)

**Hậu quả**:
- Hành trình GPS vẫn được ghi lại
- Xe và tài xế được giải phóng
- Có thể phát sinh chi phí hủy chuyến

### Thay đổi Xe/Tài xế Giữa chừng

**Khi nào**: Xe hỏng, tài xế bận đột xuất

**Các bước**:
1. Sale Admin mở đơn đang **Đang chạy**
2. Chỉnh sửa trường **Vehicle** hoặc **Driver**
3. Lưu thay đổi
4. Thông báo cho nhân viên

**Lưu ý**:
- Hành trình GPS mới sẽ ghi dưới xe mới
- Hành trình cũ vẫn giữ nguyên với xe cũ

---

# Phần VII: Tính năng Nâng cao

## 7.1 Tìm kiếm và Lọc

### Tìm kiếm Nhanh

Tại màn hình danh sách đơn đặt xe, sử dụng thanh tìm kiếm:

**Có thể tìm theo**:
- Mã đơn (FSB/2025/10/0001)
- Địa điểm đến
- Tên xe
- Tên tài xế
- Người yêu cầu

**Cú pháp**:
- Nhập từ khóa → Tự động tìm
- Dùng dấu ngoặc kép cho cụm từ: `"Hồ Chí Minh"`

### Bộ lọc

Click vào **Bộ lọc** để mở bảng lọc:

**Bộ lọc theo Trạng thái**:
- **Tất cả hoạt động**: Tất cả đơn đang hoạt động
- **Mới tạo**: Đơn mới tạo
- **Chờ phê duyệt**: Chờ phê duyệt
- **Chờ điều xe**: Chờ điều xe
- **Đang chạy**: Đang chạy
- **Hoàn tất**: Hoàn tất
- **Đã hủy**: Đã hủy

**Bộ lọc theo Thời gian**:
- **Hôm nay**: Hôm nay
- **Tuần này**: Tuần này
- **Tháng này**: Tháng này
- **7 ngày qua**: 7 ngày qua
- **30 ngày qua**: 30 ngày qua

**Bộ lọc theo Người**:
- **Đơn của tôi**: Đơn của tôi
- **Đơn của nhóm**: Đơn của team tôi
- **Được gán cho tôi**: Đơn được gán cho tôi (Quản lý/Sale Admin)

💡 **Mẹo**: Có thể kết hợp nhiều bộ lọc cùng lúc

### Nhóm theo

Sử dụng **Nhóm theo** để tổ chức dữ liệu:

**Nhóm theo**:
- **State**: Theo trạng thái
- **Team**: Theo phòng ban
- **Vehicle**: Theo xe
- **Requester**: Theo người yêu cầu
- **Date**: Theo ngày

**Ví dụ**:
- Nhóm theo State → Thấy rõ số đơn ở mỗi trạng thái
- Nhóm theo Team → So sánh usage giữa các team
- Nhóm theo Vehicle → Xem xe nào được dùng nhiều nhất

### Yêu thích

Lưu các bộ lọc thường dùng:

1. Thiết lập bộ lọc + group by
2. Click **Yêu thích** → **Lưu current search**
3. Đặt tên (ví dụ: "Đơn của tôi tháng này")
4. Click **Lưu**

✅ **Kết quả**: Lần sau chỉ cần click vào Favorite đã lưu

## 7.2 Xuất báo cáo

### Xuất danh sách

1. Tại màn hình danh sách
2. Chọn các đơn cần xuất (hoặc Chọn tất cả)
3. Click **Action** → **Xuất**
4. Chọn các trường cần xuất
5. Chọn định dạng: Excel (.xlsx) hoặc CSV
6. Click **Xuất**

**Các trường nên xuất**:
- Booking Code
- Date
- Requester
- Team
- Departure Location
- Destination
- Vehicle
- Driver
- State
- Distance (km)
- Duration (hours)

### Tạo Báo cáo Tùy chỉnh

Bạn có thể tạo các báo cáo tùy chỉnh bằng cách:

1. Tại danh sách đơn đặt xe, sử dụng bộ lọc và nhóm theo các tiêu chí cần thiết
2. Chuyển sang view **Pivot** (biểu tượng bảng) hoặc **Graph** (biểu tượng biểu đồ) để xem dữ liệu theo nhiều chiều
3. Click **Download** → Excel để xuất báo cáo

**Các báo cáo phổ biến**:
- Thống kê theo Team/Phòng ban
- Tỷ lệ sử dụng theo xe
- Xu hướng sử dụng theo tháng
- Top người dùng có nhiều chuyến đi nhất

## 7.3 Thông báo và Hoạt động

### Loại Thông báo

Module gửi 3 loại thông báo:

| Loại | Kênh | Đối tượng | Khi nào |
|------|------|-----------|---------|
| **Thông báo công việc** | In-app | Quản lý/Sale Admin | Có đơn cần xử lý |
| **Email** | Email | Tất cả người liên quan | Thay đổi trạng thái quan trọng |
| **Khu vực trao đổi** | In-app | Người theo dõi | Mọi thay đổi |

### Quản lý Hoạt động

#### Xem Hoạt động của mình

1. Click icon **Clock** (đồng hồ) ở góc phải trên
2. Danh sách activities hiển thị
3. Click vào thông báo công việc để xem chi tiết

#### Đánh dấu Hoàn tất

1. Mở thông báo công việc
2. Thực hiện hành động cần thiết (phê duyệt, điều xe...)
3. Thông báo tự động đóng

#### Tạm hoãn thông báo

Nếu chưa thể xử lý ngay:

1. Mở thông báo công việc
2. Click **Schedule**
3. Chọn thời gian nhắc lại
4. Click **Lưu**

### Theo dõi Đơn

Để nhận thông báo về đơn cụ thể:

1. Mở đơn đặt xe
2. Trong khu vực trao đổi, click **Theo dõi**
3. Chọn **Subtypes** (loại thông báo muốn nhận)
4. Click **Follow**

✅ **Kết quả**: Bạn nhận email mỗi khi đơn có thay đổi

## 7.4 Mẹo và Thủ thuật

### Cho Nhân viên

💡 **Đặt xe sớm**: Đặt trước ít nhất 1 ngày để đảm bảo có xe
💡 **Mô tả rõ ràng**: Mục đích càng chi tiết, càng dễ được duyệt
💡 **Dùng địa chỉ gợi ý**: Chọn từ danh sách để có GPS chính xác
💡 **Check status thường xuyên**: Kiểm tra notification để biết tiến độ
💡 **Lưu địa chỉ thường dùng**: Hệ thống sẽ gợi ý lần sau

### Cho Manager

💡 **Xử lý thông báo công việc hàng ngày**: Đừng để tồn đọng quá lâu
💡 **Phê duyệt theo batch**: Xử lý nhiều đơn cùng lúc nếu có thể
💡 **Communicate rõ ràng**: Nếu từ chối, giải thích cụ thể lý do
💡 **Set expectations**: Thông báo SLA xử lý với team
💡 **Review định kỳ**: Xem báo cáo usage hàng tháng

### Cho Sale Admin

💡 **Lên lịch trước**: Nhìn trước đơn sẽ đến để plan xe
💡 **Maintain GPS**: Kiểm tra GPS xe định kỳ
💡 **Optimize routing**: Gộp chuyến cùng hướng nếu được
💡 **Track fuel**: Ghi lại nhiên liệu để tính chi phí
💡 **Monitor real-time**: Mở bản đồ để theo dõi trong giờ cao điểm

### Phím tắt

📌 **Xem danh sách đầy đủ các phím tắt hữu ích tại Phần I, mục "Điều hướng cơ bản"**

---

# Phần VIII: Câu hỏi thường gặp và Xử lý sự cố

## 8.1 Câu hỏi thường gặp

### Câu hỏi chung

**Q1: Tôi có thể đặt xe cho người khác không?**

**A**:
- **Nhân viên**: Không, chỉ đặt cho mình
- **Manager**: Có, có thể tạo đơn thay cho nhân viên trong team
- **Sale Admin**: Có, có thể tạo cho bất kỳ ai

**Q2: Mất bao lâu để đơn được phê duyệt?**

**A**:
- **SLA chuẩn**: 1 ngày làm việc
- **Khẩn cấp**: Có thể trong 2 giờ (cần liên hệ Manager trực tiếp)
- **Thực tế**: Phụ thuộc vào Manager và workload

**Q3: Tôi có thể hủy đơn đã gửi không?**

**A**:
- **Trạng thái Mới**: Có, delete trực tiếp
- **Trạng thái Chờ duyệt**: Liên hệ Manager để reset
- **Trạng thái Đang chạy**: Liên hệ Sale Admin, có thể phát sinh phí

**Q4: GPS không cập nhật phải làm sao?**

**A**:
- Kiểm tra xe có GPS device không (xem tab GPS Tracking)
- Kiểm tra GPS Serial đã đúng chưa
- Đợi 5-10 phút (sync interval)
- Liên hệ Sale Admin nếu vẫn không được

**Q5: Tôi quên mật khẩu, làm thế nào?**

**A**:
- Tại màn hình login, click **Đặt lại mật khẩu**
- Nhập email đăng ký
- Check email để nhận link reset
- Click link và đặt mật khẩu mới

### Câu hỏi về Quy trình

**Q6: Tại sao đơn của tôi bị từ chối?**

**A**:
- Xem lý do trong khu vực trao đổi hoặc email thông báo
- Liên hệ Manager để làm rõ
- Sửa theo góp ý và gửi lại

**Q7: Tôi có thể thay đổi địa điểm sau khi Manager duyệt không?**

**A**:
- **Không trực tiếp**, vì đã qua giai đoạn phê duyệt
- **Giải pháp**: Liên hệ Sale Admin để note lại thay đổi
- **Hoặc**: Hủy đơn cũ và tạo đơn mới (nếu chưa dispatch)

**Q8: Xe đến muộn, tôi nên làm gì?**

**A**:
- Check GPS để xem xe đang ở đâu
- Liên hệ tài xế qua số điện thoại
- Thông báo cho Sale Admin nếu muộn quá 30 phút

**Q9: Tôi có thể gia hạn thời gian sử dụng xe không?**

**A**:
- Liên hệ Sale Admin trước khi hết giờ
- Sale Admin kiểm tra lịch xe
- Nếu xe không bận chuyến sau, có thể gia hạn

**Q10: Làm sao biết xe nào đang rảnh?**

**A**:
- **Sale Admin**: Xem bản đồ real-time
- **Nhân viên/Manager**: Không thấy, hãy để Sale Admin quyết định

### Câu hỏi Kỹ thuật

**Q11: Tôi không thấy module Đội xe?**

**A**:
- Kiểm tra quyền truy cập (liên hệ Admin)
- Refresh trình duyệt (`Ctrl + F5`)
- Đăng xuất và đăng nhập lại

**Q12: Gợi ý địa chỉ không hoạt động?**

**A**:
- Kiểm tra kết nối Internet
- Đảm bảo nhập ít nhất 3 ký tự
- Thử refresh trang
- Có thể nhập thủ công nếu gợi ý không khả dụng

**Q13: Bản đồ không load?**

**A**:
- Kiểm tra Internet connection
- Disable browser extensions (AdBlock, etc.)
- Thử trình duyệt khác (Chrome khuyến nghị)
- Clear browser cache

**Q14: Tôi muốn xuất báo cáo nhưng không thấy nút Xuất?**

**A**:
- Chuyển sang **Giao diện danh sách** (icon list)
- Chọn ít nhất 1 đơn
- Nút **Action** → **Xuất** sẽ xuất hiện

**Q15: Upload file đính kèm bị lỗi?**

**A**:
- Kiểm tra kích thước file (< 25MB)
- Kiểm tra định dạng (PDF, DOC, XLS, PNG, JPG allowed)
- Thử file khác để test

## 8.2 Xử lý lỗi thường gặp

### Lỗi Đăng nhập

#### Lỗi: "Invalid username or password"

**Nguyên nhân**:
- Sai email/username
- Sai mật khẩu
- Account bị khóa

**Giải pháp**:
1. Kiểm tra Caps Lock
2. Copy-paste username/password để tránh typo
3. Đặt lại password nếu quên
4. Liên hệ Admin nếu account bị khóa

#### Lỗi: "Database not found"

**Nguyên nhân**: URL sai hoặc database không tồn tại

**Giải pháp**:
1. Kiểm tra lại URL
2. Liên hệ Admin để xác nhận database name

### Lỗi Tạo đơn

#### Lỗi: "Required field missing"

**Nguyên nhân**: Chưa điền đủ thông tin bắt buộc

**Giải pháp**:
- Kiểm tra các trường có dấu `*` (bắt buộc)
- Điền đầy đủ thông tin
- Thử lại

#### Lỗi: "Validation Error: End date must be after start date"

**Nguyên nhân**: Ngày kết thúc trước ngày bắt đầu

**Giải pháp**:
- Kiểm tra lại **Ngày giờ bắt đầu** và **Ngày giờ kết thúc**
- Đảm bảo logic đúng
- Lưu lại

#### Lỗi: "You don't have permission to create"

**Nguyên nhân**: Không có quyền tạo đơn

**Giải pháp**:
- Kiểm tra vai trò của bạn
- Liên hệ Admin để cấp quyền `Người dùng BM Fleet`

### Lỗi GPS

#### Lỗi: "GPS data not available"

**Nguyên nhân**:
- GPS device chưa được cấu hình
- GPS Serial sai
- Xe đang offline

**Giải pháp**:
1. Kiểm tra **GPS Device Serial** trong tab GPS Tracking
2. Nhấn **Đồng bộ dữ liệu GPS** để force sync
3. Đợi 5-10 phút
4. Liên hệ Sale Admin nếu vẫn lỗi

#### Lỗi: "No journey data found"

**Nguyên nhân**:
- Xe chưa chạy (chưa có waypoints)
- Chưa đến thời gian bắt đầu
- GPS chưa sync

**Giải pháp**:
- Đợi đến khi xe bắt đầu chạy
- Check lại sau 10-15 phút
- Verify GPS đang hoạt động

### Lỗi Bản đồ

#### Lỗi: Map không hiển thị (blank screen)

**Nguyên nhân**:
- JavaScript error
- Browser không tương thích
- Extensions chặn

**Giải pháp**:
1. Mở **Bảng điều khiển nhà phát triển** (`F12`)
2. Xem tab **Console** có lỗi không
3. Disable extensions
4. Thử trình duyệt khác
5. Clear cache và refresh

#### Lỗi: Markers không hiển thị

**Nguyên nhân**:
- Không có dữ liệu GPS
- Bộ lọc quá hẹp
- Zoom level quá xa

**Giải pháp**:
- Bỏ tất cả bộ lọc
- Zoom out để xem toàn bộ
- Chọn date range rộng hơn

### Lỗi Performance

#### Lỗi: Trang load chậm

**Nguyên nhân**:
- Quá nhiều dữ liệu
- Internet chậm
- Server busy

**Giải pháp**:
1. Sử dụng bộ lọc để giảm số dữ liệu
2. Kiểm tra Internet speed
3. Thử vào giờ khác (tránh giờ cao điểm)
4. Liên hệ Admin nếu liên tục chậm

#### Lỗi: Timeout khi xuất báo cáo

**Nguyên nhân**: Quá nhiều dữ liệu

**Giải pháp**:
- Giảm số dữ liệu (sử dụng bộ lọc)
- Xuất theo từng tháng thay vì cả năm
- Chọn ít trường hơn để export

### Liên hệ Hỗ trợ

Nếu vẫn gặp lỗi sau khi thử các giải pháp trên:

**Thông tin cần cung cấp khi báo lỗi**:
- Username/Email
- Vai trò (Nhân viên/Manager/Sale Admin)
- Mô tả lỗi chi tiết
- Các bước tái hiện lỗi
- Screenshot (nếu có)
- Thời gian xảy ra lỗi

**Kênh liên hệ**:
- Email: support@bestmix.vn
- Hoặc tạo ticket trong hệ thống

---

# Phụ lục

## Phụ lục A: Bảng thuật ngữ

| Thuật ngữ Tiếng Việt | Thuật ngữ Tiếng Anh | Mô tả |
|---------------------|---------------------|-------|
| **Đội xe** | Fleet GPS | Tên module |
| **Đặt xe** | Booking | Tạo yêu cầu sử dụng xe |
| **Phê duyệt** | Approval | Xác nhận đồng ý yêu cầu |
| **Điều xe** | Dispatch | Phân công xe và tài xế |
| **Hành trình** | Journey | Tuyến đường xe đi |
| **Waypoint** | Waypoint | Điểm GPS trên hành trình |
| **Địa điểm đi** | Departure Location | Điểm khởi hành |
| **Địa điểm đến** | Destination | Điểm đích đến |
| **Mục đích công tác** | Work Purpose | Lý do sử dụng xe |
| **Người yêu cầu** | Requester | Người tạo đơn đặt xe |
| **Người phê duyệt** | Approver | Quản lý phê duyệt đơn |
| **Người điều xe** | Người điều xe | Sale Admin điều phối xe |
| **Tài xế** | Driver | Người lái xe |
| **Team yêu cầu** | Requesting Team | Phòng ban của người yêu cầu |
| **Thành viên tham gia** | Participants | Người đi cùng |
| **Trạng thái** | State/Status | Giai đoạn hiện tại của đơn |
| **Thông báo công việc** | Activity | Thông báo cần xử lý |
| **Khu vực trao đổi** | Chatter | Khu vực trao đổi, ghi chú |
| **Nút xem** | Nút thông minh | Nút thống kê/liên kết |
| **Giao diện thẻ** | Giao diện thẻ View | Giao diện dạng thẻ |
| **Giao diện danh sách** | Giao diện danh sách | Giao diện dạng bảng |
| **Màn hình chi tiết** | Giao diện biểu mẫu | Giao diện chi tiết |
| **GPS Serial** | GPS Device Serial | Số serial thiết bị GPS |
| **Company ID** | Company ID | Mã công ty trên hệ thống GPS |
| **Latitude** | Latitude | Vĩ độ |
| **Longitude** | Longitude | Kinh độ |
| **Geocoding** | Geocoding | Chuyển tọa độ thành địa chỉ |
| **Đồng bộ** | Đồng bộ | Đồng bộ dữ liệu |
| **Bộ lọc** | Bộ lọc | Bộ lọc |
| **Nhóm theo** | Nhóm theo | Nhóm theo |
| **Xuất** | Xuất | Xuất dữ liệu |

## Phụ lục B: Bảng trạng thái và màu sắc

### Trạng thái Đơn đặt xe

| Trạng thái (VI) | Trạng thái (EN) | Mã | Màu sắc | Biểu tượng | Mô tả |
|-----------------|-----------------|-----|---------|-----------| ------|
| **Mới** | New | `new` | Xám (secondary) | ⚪ | Đơn vừa tạo, chưa gửi |
| **Quản lý phê duyệt** | Pending Manager | `pending_manager` | Xanh dương (info) | 🔵 | Chờ Manager duyệt |
| **Đợi điều xe** | Chờ điều xe | `pending_dispatch` | Cam (warning) | 🟠 | Manager đã duyệt, chờ điều xe |
| **Đang chạy** | Running | `running` | Tím (primary) | 🟣 | Xe đang thực hiện |
| **Hoàn tất** | Hoàn tất | `done` | Xanh lá (success) | 🟢 | Hoàn thành |
| **Đã hủy** | Đã hủy | `cancelled` | Đỏ (danger) | 🔴 | Bị từ chối |

### Trạng thái GPS Xe

| Trạng thái | Điều kiện | Màu sắc | Ý nghĩa |
|------------|-----------|---------|---------|
| **Offline** | > 30 phút không có dữ liệu | Xám | Xe tắt máy hoặc GPS lỗi |
| **Idle** | Có dữ liệu, tốc độ = 0 | Vàng | Xe đang dừng |
| **Running** | Có dữ liệu, tốc độ > 0 | Xanh lá | Xe đang chạy |

### Màu sắc trong Giao diện thẻ/List

| Decoration | Trạng thái | Màu nền | Text color |
|------------|------------|---------|------------|
| `decoration-muted` | - | Xám nhạt | Xám đậm |
| `decoration-info` | pending_manager | Xanh dương nhạt | Xanh dương đậm |
| `decoration-warning` | pending_dispatch | Cam nhạt | Cam đậm |
| `decoration-primary` | running | Tím nhạt | Tím đậm |
| `decoration-success` | done | Xanh lá nhạt | Xanh lá đậm |
| `decoration-danger` | cancelled | Đỏ nhạt | Đỏ đậm |

## Phụ lục C: Quyền truy cập theo vai trò

### Ma trận Quyền hạn

| Chức năng | Nhân viên | Manager | Sale Admin |
|-----------|-----------|---------|------------|
| **Tạo đơn đặt xe** | ✅ Cho mình | ✅ Cho team | ✅ Cho tất cả |
| **Xem đơn đặt xe** | ✅ Của mình | ✅ Của team | ✅ Tất cả |
| **Chỉnh sửa đơn** | ✅ Khi ở trạng thái Mới | ✅ Khi ở trạng thái Mới | ✅ Mọi lúc |
| **Gửi phê duyệt** | ✅ Có | ✅ Có | ✅ Có |
| **Phê duyệt đơn** | ❌ Không | ✅ Đơn của team | ✅ Tất cả đơn |
| **Từ chối đơn** | ❌ Không | ✅ Đơn của team | ✅ Tất cả đơn |
| **Điều xe** | ❌ Không | ❌ Không | ✅ Có |
| **Hoàn thành đơn** | ❌ Không | ❌ Không | ✅ Có |
| **Xem hành trình GPS** | ✅ Đơn của mình | ✅ Đơn của team | ✅ Tất cả |
| **Xem bản đồ** | ❌ Không | ❌ Không | ✅ Có |
| **Quản lý xe** | ❌ Không | ❌ Không | ✅ Có |
| **Cấu hình GPS** | ❌ Không | ❌ Không | ✅ Có |
| **Kiểm tra phạt nguội** | ❌ Không | ❌ Không | ✅ Có |
| **Xuất báo cáo** | ✅ Đơn của mình | ✅ Đơn của team | ✅ Tất cả |


## Kết luận

Tài liệu này cung cấp hướng dẫn toàn diện về việc sử dụng Module **Đội xe GPS** trong Odoo 18.

**Các điểm chính**:
- ✅ Quy trình đặt xe rõ ràng, tự động
- ✅ Theo dõi GPS real-time chính xác
- ✅ Quyền hạn phân cấp hợp lý
- ✅ Giao diện thân thiện, dễ sử dụng
- ✅ Tích hợp sâu với workflow Odoo

Nếu có thắc mắc hoặc cần hỗ trợ thêm, vui lòng liên hệ:

📧 **Email**: support@bestmix.vn
🌐 **Website**: https://www.bestmix.vn

---

**Phát triển bởi**: BESTMIX IT Team
**Bản quyền**: © 2025 BESTMIX Company
**Giấy phép**: LGPL-3

---

*Cảm ơn bạn đã sử dụng Module Đội xe GPS!*
