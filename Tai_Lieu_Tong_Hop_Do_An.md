# QSR Forecast – Tài liệu tổng hợp đồ án

## 1. Tổng quan đồ án

**Bài toán:** dự báo nhu cầu *ngắn hạn (ngày kế tiếp)* theo từng món, từng cửa hàng của chuỗi thức ăn nhanh (QSR) để lập danh sách chuẩn bị hàng, giảm thiếu hụt/lãng phí trong chuỗi cung ứng và vận hành.

**Bối cảnh demo:** cửa hàng R01 · Downtown Chicago Grill, ngày vận hành **30/10/2025**, ngày phục vụ cần chuẩn bị **31/10/2025** (Halloween). Hệ thống chỉ dùng dữ liệu đến hết ngày vận hành; 15 cửa hàng × 50 món = 750 cặp.

**Công thức nghiệp vụ cốt lõi**

```
Dự phòng      = z × RMSE          (mức an toàn 90% → 1,28 · 95% → 1,65 · 99% → 2,33)
Cần chuẩn bị  = Dự kiến bán + Dự phòng − Đang có      (không nhỏ hơn 0)
Ví dụ French Fries Regular: 118 + 25 − 20 = 123 phần; quản lý sửa 130 → ghi "Đã sửa" + "Đề xuất gốc 123"

Mức độ món:  Thiếu hàng  = Đang có < Dự phòng                    (đỏ)
             Cần bổ sung = Đang có ≥ Dự phòng nhưng Cần chuẩn bị > 0 (vàng)
             Đủ hàng     = Cần chuẩn bị = 0
```

**Công nghệ**

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Web backend | Django 6.1 (MVT) | `views.py` (trang) + `api.py`/`api_admin.py` (JSON) |
| Cơ sở dữ liệu | MySQL `qsr_db` (`mysqlclient`) | Bảng ML (unmanaged) + bảng web (migration) |
| Máy học | CatBoost, LightGBM, Ridge + 2 baseline | Mô hình tốt nhất lưu `Assets/best_model.joblib` (wMAPE test ≈ 14,5 %) |
| Frontend | Django Template + Tailwind (CDN) + JS thuần | Dựng từ thiết kế Figma; popup dùng chung `modals.js` |
| Dữ liệu/Excel | pandas, openpyxl | Nhập CSV/Excel, xuất CSV |

---

## 2. Kiến trúc MVT + lớp máy học

```
 Trình duyệt (Template + Tailwind + modals.js)
        │  HTTP GET/POST (CSRF, JSON)
        ▼
 ML_QSR/urls.py ─► forecast/urls.py ─► views.py (trang)  |  api.py / api_admin.py (JSON)
                                              │ kiểm quyền: permissions.role_required
                                              ▼
                              forecast/services/   (nghiệp vụ, KHÔNG nằm trong view)
                 ┌──────────────┬───────────────┼───────────────┬───────────────┐
              plans.py      engine.py      notifications.py   insights.py     adminops.py
          (vòng đời đề xuất) (cầu nối ML)  (thông báo)     (lý do/yếu tố)  (dữ liệu, cửa hàng,
                 │              │                                            tài khoản, cấu hình)
                 │              ▼
                 │     Models/ (QSRMLModel · processFeatures · forecastDate · QSRInventory.calcSafetyStock)
                 │              │  nạp 1 lần/tiến trình
                 │              ▼
                 │     Assets/best_model.joblib ──► predict()
                 ▼              ▲
          MySQL qsr_db ◄────────┘  (daily_sales, weather_events, promotions, forecasts … + bảng web)
```

**Luồng dữ liệu tuần tự (ví dụ "Chạy dự báo")**

| # | Bước | Nơi thực hiện |
|---|---|---|
| 1 | Quản lý bấm **Chạy dự báo** → `POST /api/forecast/run` | `modals.js` → `api.run_forecast` |
| 2 | Kiểm quyền + cửa hàng + chỉ cho ngày vận hành + 1 | `permissions.py`, `plans.create_plan` |
| 3 | Lấy kiểm kho đã lưu (tồn hiện tại) | `plans.latest_saved_inventory` |
| 4 | Đọc lịch sử bán/thời tiết/khuyến mãi từ MySQL → Feature Engineering | `engine.forecast_store` → `QSRMLModel.execQSRHistory/processFeatures` |
| 5 | Nạp `best_model.joblib` (1 lần) và `predict()` | `engine.trained_model`, `forecastDate` |
| 6 | Tính tồn an toàn `z × RMSE`, `Cần chuẩn bị`, mức độ | `QSRInventory.calcSafetyStock`, `plans.compute_line` |
| 7 | Lưu `PrepPlan` + `PrepLine` (version +1), tạo thông báo | `plans`, `notifications.notify` |
| 8 | Trả `JsonResponse {ok, error, message}` → giao diện tải lại danh sách | `api.py` → `modals.js` |

> Ghi chú: mô hình lưu dạng **`.joblib`** (không phải `.pkl`) trong `Assets/`.

**Vòng đời đề xuất**

```
Nhân viên kiểm kho ─► (tự lập) đề xuất [pending] ─► Quản lý duyệt [approved] ─► Bếp "Đánh dấu xong"
                                  ▲                        │                          │
                                  └──── Mở lại + chạy lại ─┘ (phiên bản cũ → superseded)
                                                           └─ xong hết → thông báo quản lý
```

---

### Vòng nghiệp vụ 6 bước (quản trị viên đứng ngoài vòng)

```
①NV Kiểm kho cuối ca ─► ②Hệ thống dự báo & đề xuất ─► ③QL kiểm tra, chỉnh [Chờ duyệt]
   (50 món)               (tự lập sau khi lưu kiểm kho       │  ▲ Mở lại để chỉnh
                           hoặc QL/Admin bấm Chạy)            ▼  │
⑥Hoàn thành ◄── ⑤Bếp "Đánh dấu xong" ◄──────────── ④QL Duyệt, gửi bếp (xong trước hạn 10:00)
 (QL nhận thông báo)     từng món
```
- Kiểm kho chưa đủ 50 món → không tính lại đề xuất (chỉ Lưu nháp).
- Đã duyệt thì **không chạy lại dự báo**; muốn đổi phải **Mở lại**; trong lúc đó bếp vẫn thấy danh sách duyệt gần nhất.
- `require_approval` tắt → danh sách gửi bếp ngay khi tính xong.

### Quy tắc & trạng thái dùng xuyên suốt

| Khái niệm | Giá trị | Ý nghĩa |
|---|---|---|
| Mức độ món | Thiếu hàng · Cần bổ sung · Đủ hàng | Xem công thức ở mục 1 |
| Trạng thái đề xuất | Chờ duyệt · Đã duyệt · Hoàn thành · Đã sửa | Hoàn thành = bếp xong đủ việc; "Đã sửa" = quản lý chỉnh khác đề xuất gốc (DB: pending/approved/superseded + dòng `applied_qty ≠ need_qty`) |
| Trạng thái kiểm kho | Chưa nhập · Đã nhập · Cần xem lại | Cần xem lại: số nhập < 25 % kỳ trước, phải xác nhận trước khi lưu |
| Nguồn "Đang có" | Kiểm kho / ước tính | Món chưa kiểm hiển thị là ước tính |
| Lý do dự báo | Mức bán TB chung ± yếu tố | Yếu tố: lượng bán gần đây, thứ trong tuần, sự kiện, thời tiết, khuyến mãi (+ 4 ngày cùng thứ gần nhất) |
| Dự báo chỉ cho | Ngày vận hành + 1 | Ngày khác → "Chưa có dữ liệu" |

---

## 3. Phân quyền 3 vai trò

| Chức năng | Nhân viên (`staff`) | Quản lý (`manager`) | Quản trị (`admin`) |
|---|:-:|:-:|:-:|
| Phạm vi | 1 cửa hàng được gán | 1 cửa hàng được gán | Toàn hệ thống |
| Kiểm kho (nháp / lưu) | ✅ | – | – |
| Danh sách chuẩn bị, "Đánh dấu xong" | ✅ | – | – |
| Tổng quan, chọn ngày phục vụ | – | ✅ | – |
| Chạy dự báo / chỉnh % / chỉnh từng món | – | ✅ (nếu `managers_can_run`) | – |
| Duyệt / mở lại đề xuất, tải danh sách (CSV, mở được bằng Excel) | – | ✅ | – |
| Báo cáo (xu hướng, độ chính xác, yếu tố) | – | ✅ | – |
| Thông báo (chuông), hồ sơ, đổi mật khẩu (≥ 8 ký tự), 3 tùy chọn thông báo¹ | ✅ | ✅ | ✅ |
| Dữ liệu: tổng quan, dòng thiếu, nhập CSV/Excel | – | – | ✅ |
| Dự báo & Mô hình: chạy 1 cửa hàng / toàn hệ thống | – | – | ✅ |
| Cửa hàng: thêm/sửa, gán quản lý | – | – | ✅ |
| Tài khoản: thêm, sửa, khóa/mở, cấp lại mật khẩu tạm | – | – | ✅ |
| Cấu hình: mức an toàn, hạn chuẩn bị, giờ nhắc, cảnh báo | – | – | ✅ |
| `require_approval`, ngày vận hành | – | – | Django Admin (`/admin`) |

¹ Email tóm tắt hằng tuần: công tắc có nhưng chưa có hạ tầng gửi mail.

Menu theo vai trò: **NV** Chuẩn bị hàng · Kiểm kho │ **QL** Tổng quan · Chuẩn bị hàng · Dự báo · Báo cáo │ **Admin** Dữ liệu · Dự báo & Mô hình · Cửa hàng · Tài khoản · Cấu hình. Trang ngoài quyền → màn "Không có quyền truy cập" + nút *Về trang của tôi*.

Bảo vệ: quản lý/nhân viên chưa có cửa hàng → 403; đăng nhập sai 5 lần → khóa 15 phút; không khóa được admin cuối cùng; mỗi cửa hàng một quản lý.
Tài khoản demo (mật khẩu mặc định `Qsr@2025!`, **đổi trước khi triển khai**): `minh.r01` (staff), `lan.r01` (manager), `admin`. "Cấp lại mật khẩu" ở màn đăng nhập chỉ ghi nhận yêu cầu (Chờ xử lý); admin cấp mật khẩu tạm một lần.

---

## 4. Giao diện và tương tác dữ liệu

| Trang | Vai trò | Nút chính | Tác dụng thực tế |
|---|---|---|---|
| Kiểm kho | Staff (8 nhóm món, 5 dòng/trang) | **Lưu nháp / Lưu** | Ghi `InventoryCount/Item`; cờ "cần xem lại" nếu < 25 % kỳ trước; tự lập đề xuất nếu bật `auto_plan_after_inventory` |
| Danh sách chuẩn bị | Staff | **Đánh dấu xong** | Ghi người/giờ hoàn thành; xong hết → báo quản lý |
| Tổng quan | Manager | **Xem dữ liệu**, **Chọn ngày**, **Xem** (lý do) | Biểu đồ 7 ngày, 3 thẻ Thiếu/Bổ sung/Đủ, việc cần xử lý |
| Chuẩn bị hàng | Manager | **Chạy dự báo** | Gọi pipeline ML (mục 2) cho ngày vận hành + 1 |
| | | **Duyệt / Mở lại** | Chuyển trạng thái, gửi bếp |
| | | **Tải Excel** | Xuất CSV danh sách của ngày đang xem |
| Dự báo | Manager | Thanh −30/−15/0/+15/+30 % + lý do (Sự kiện, Khuyến mãi, Đổi giờ phục vụ, Khác – bắt buộc nhập) → **Lưu điều chỉnh**; **Tạo đề xuất chuẩn bị** | Áp cùng tỷ lệ cho mọi món; tạo đề xuất Chờ duyệt |
| Báo cáo | Manager | Tab Xu hướng / Độ chính xác | So dự báo – thực tế, wMAPE theo ngày, tác động 6 yếu tố |
| Dữ liệu | Admin | **Dòng thiếu**, **Nhập dữ liệu** | Xem/bù dữ liệu thiếu; nhập CSV/Excel có xem trước, ghi sau khi xác nhận (Thêm mới / Cập nhật theo khóa) |
| Dự báo & Mô hình | Admin | **Chạy cửa hàng / Chạy tất cả** | Chạy tuần tự; bỏ qua cửa hàng chưa kiểm kho hoặc đã duyệt |
| Cửa hàng · Tài khoản · Cấu hình | Admin | Thêm/Sửa/Khóa/Lưu | Quản trị danh mục, người dùng, tham số hệ thống |

**Nguồn dữ liệu lịch sử – nói đúng thực tế**

```
data/raw/qsr_demand_dataset.csv ──(QSRDataCleaning: làm sạch, impute, đánh dấu outlier)──►
data/processed/qsr_clean 13.20.26.csv ──(nạp một lần bằng pipeline/Database/qsr_schema.sql)──► MySQL qsr_db
```

- **Web đang chạy KHÔNG đọc trực tiếp file `qsr_clean 13.20.26.csv`.** File này là sản phẩm của bước làm sạch (offline) và là nguồn nạp vào MySQL; sau đó mọi nút bấm của Manager/Admin đọc **bảng MySQL** (`daily_sales`, `weather_events`, `promotions`, `stores`, `products`).
- Lịch sử dùng để: (1) tạo đặc trưng cho mô hình (lag, trung bình trượt, thứ trong tuần, thời tiết, khuyến mãi, lễ/sự kiện); (2) biểu đồ 7 ngày và 4 ngày cùng thứ trong popup "Lý do"; (3) tính độ chính xác báo cáo; (4) Admin thống kê dòng thiếu (≈ 5.261 / 1,32 triệu dòng) và nhập bổ sung.
- Dữ liệu nhập qua trang Admin ghi thẳng vào MySQL (không sửa file CSV).

---

## 5. Cấu trúc thư mục

```
Project_ML_QSR/
├── manage.py                  # điểm vào Django
├── requirements.txt           # thư viện (mysqlclient, openpyxl, catboost, lightgbm…)
├── .env / .env.example        # DB + QSR_SECRET_KEY, QSR_DEBUG, QSR_ALLOWED_HOSTS
├── README.md
├── Tai_Lieu_Tong_Hop_Do_An.md # tài liệu này
├── ML_QSR/                    # cấu hình project Django (settings, urls, wsgi/asgi)
├── forecast/                  # app web duy nhất
│   ├── models.py              # bảng ML (unmanaged) + Profile, SystemConfig, Inventory*, Prep*, Notification
│   ├── views.py               # các trang HTML theo vai trò
│   ├── api.py · api_admin.py  # endpoint JSON (staff/manager · admin)
│   ├── urls.py · permissions.py · context_processors.py · admin.py
│   ├── services/              # nghiệp vụ: plans, engine, notifications, insights, units, adminops
│   ├── management/commands/   # seed_demo, send_reminders
│   ├── migrations/            # 0001–0003 (chỉ bảng của web)
│   ├── templatetags/qsr.py    # filter thousands, dm, initial
│   ├── templates/forecast/    # base + 15 trang (login, dashboard, prep, report, data, model…)
│   ├── static/forecast/       # js/modals.js (popup, gọi API), img/
│   └── tests.py               # 37 test
├── Models/                    # lớp ML: làm sạch, đặc trưng, CatBoost/LightGBM/Ridge/Baseline, tồn kho
├── Assets/                    # best_model.joblib, các model đã train, reports/metrics.csv, figures/
├── Database/qsr_schema.sql    # lược đồ MySQL của pipeline ML
├── Connectors/Connector.py    # kết nối MySQL cho pipeline ML
├── Utils/                     # Config.py (đường dẫn, DB, tham số), FileUtil.py
├── data/
│   ├── raw/qsr_demand_dataset.csv
│   ├── processed/qsr_clean 13.20.26.csv
│   └── splits/                # train/val/test.parquet
├── Tests/                     # script chạy pipeline ML & pytest cũ (AppXxx.py, test_*.py)
├── popup/                     # ảnh thiết kế popup (Figma) theo 4 nhóm vai trò
├── muctieu/                   # mục tiêu, tóm tắt đồ án
├── Slides/                    # slide môn học
├── notebooks/                 # (trống)
├── demo_quickstart.py         # chạy nhanh minh họa
└── db.sqlite3                 # DB mặc định của Django – không dùng (web dùng MySQL)
```

| Thư mục / file | Vai trò kỹ thuật |
|---|---|
| `ML_QSR/` | Cấu hình Django, đọc `.env` qua `Utils.Config` |
| `forecast/views.py`, `api*.py` | Chỉ điều phối: kiểm quyền → gọi `services` → trả HTML/JSON |
| `forecast/services/engine.py` | Cầu nối duy nhất tới ML; cache model theo tiến trình |
| `forecast/services/plans.py` | Luật nghiệp vụ: duyệt, mở lại, chỉnh, hoàn thành, phiên bản |
| `Models/` | Huấn luyện/đánh giá/dự báo (không phụ thuộc Django) |
| `Assets/` | Mô hình đã huấn luyện + báo cáo metric (`metrics.csv`) |
| `Database/`, `Connectors/` | Tạo và truy cập bảng MySQL cho pipeline ML |
| `data/` | Dữ liệu thô → sạch → tách train/val/test |
| `Tests/` & `forecast/tests.py` | Kiểm thử pipeline ML (cũ, chưa chạy lại) & kiểm thử web (37 test, đạt) |

**Chạy nhanh:** bật MySQL → `python manage.py migrate` → `python manage.py seed_demo` → `python manage.py runserver`; nhắc kiểm kho: cron `python manage.py send_reminders`.

**Đối chiếu tài liệu thiết kế (PDF) và mã nguồn – điểm khác biệt đã biết**

| # | Thiết kế (PDF) | Mã nguồn hiện tại |
|---|---|---|
| 1 | Làm tròn dự báo/tồn an toàn *trước* khi cộng trừ | Cộng trước rồi `ceil` một lần (`plans.compute_line`); có thể lệch ±1 phần so với ví dụ PDF |
| 2 | Cửa hàng, Cấu hình dùng giao diện Django Admin | Có trang riêng cho admin; riêng `require_approval` và ngày vận hành chỉ sửa ở Django Admin |
| 3 | Nút "Tải Excel" | Xuất **CSV** (Excel mở được) |
| 4 | Email tóm tắt hằng tuần | Chỉ lưu công tắc, chưa gửi |
| 5 | Nhắc kiểm kho theo giờ cấu hình | Cần cron chạy `send_reminders` |
| 6 | Chạy toàn hệ thống 750 cặp | Chạy tuần tự đồng bộ, có thể chậm/timeout khi triển khai |

**Hạn chế đã biết:** "Chạy tất cả cửa hàng" chạy đồng bộ (có thể chậm); `weekly_email` chưa có hạ tầng gửi mail; `Tests/` (pytest cũ) chưa chạy lại; giao diện chưa đối chiếu thị giác đầy đủ với Figma.
