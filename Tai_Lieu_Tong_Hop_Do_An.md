# QSR Forecast – Tài liệu tổng hợp đồ án

> Tài liệu này dành cho **mọi thành viên** trong nhóm (kể cả người không viết code): đọc xong phải hiểu dự án giải quyết việc gì, dữ liệu từ đâu, mô hình dự đoán thế nào, web hoạt động ra sao, ai làm được gì, chạy và kiểm thử bằng cách nào. Mục 0 dành cho người cần hiểu nhanh; các mục sau đi sâu.

## 0. Đọc nhanh (5 phút)

**Dự án làm gì?** Một chuỗi 15 cửa hàng thức ăn nhanh (QSR) mỗi tối phải quyết định ngày mai chuẩn bị bao nhiêu phần của từng món (50 món). Chuẩn bị thiếu thì hết hàng, mất khách; chuẩn bị thừa thì lãng phí. Hệ thống **dự báo lượng bán từng món cho một ngày** bằng học máy, trừ đi hàng đang còn trong kho, cộng một lượng dự phòng, rồi cho ra **danh sách "ngày mai bếp cần chuẩn bị gì, bao nhiêu"**.

**Ai dùng và làm gì?**

| Vai trò | Việc chính |
|---|---|
| Nhân viên bếp/kho | Cuối ca **kiểm kho** (đếm còn bao nhiêu mỗi món); sáng hôm sau mở **Danh sách chuẩn bị** và đánh dấu từng món "xong" |
| Quản lý cửa hàng | Xem dự báo, **chỉnh** theo hiểu biết riêng (khuyến mãi, sự kiện), **duyệt** để gửi bếp, xem báo cáo độ chính xác |
| Quản trị viên | Quản lý dữ liệu, cửa hàng, tài khoản, cấu hình hệ thống; chạy dự báo cho một hoặc mọi cửa hàng |

**Một vòng làm việc trong một câu:** Nhân viên kiểm kho → hệ thống dự báo và tự lập đề xuất → quản lý chỉnh/duyệt → bếp làm và đánh dấu xong → quản lý nhận thông báo hoàn thành.

**Điểm mới nhất – dự báo cho mọi ngày.** Trước đây hệ thống chỉ dự báo ngày vận hành + 1 (30/10/2025 → 31/10/2025). Nay quản lý hay quản trị **chọn ngày nào cũng bấm dự báo được**, miễn DB có dữ liệu đầu vào của ngày đó (01/01/2021 – 31/12/2025). Ngày ngoài kỳ dữ liệu báo "Không có dữ liệu đầu vào cho ngày đã chọn". Chi tiết ở mục 2.3.

**Các con số cần nhớ**

| Mục | Giá trị |
|---|---|
| Quy mô dữ liệu | 15 cửa hàng × 50 món × 1.826 ngày (2021–2025) ≈ 1,32 triệu dòng |
| Mô hình tốt nhất | CatBoost, wMAPE trên tập test ≈ **14,5 %** (hai baseline đơn giản: 19,9 % và 22,9 %) |
| Ngày vận hành mặc định | 30/10/2025 (ngày phục vụ kế tiếp 31/10/2025 – Halloween) |
| Mức an toàn mặc định | 95 % (z = 1,65) |
| Kiểm thử tự động | 38 bài (`python manage.py test forecast`) |
| Tài khoản thử | 31 tài khoản: mỗi cửa hàng 1 quản lý + 1 nhân viên, cộng `admin` (mục 3.1) |

**Thuật ngữ**

| Từ | Nghĩa |
|---|---|
| Ngày vận hành | "Hôm nay" trong hệ thống (cấu hình, mặc định 30/10/2025). Số bán thật sau ngày này bị ẩn trên giao diện |
| Ngày phục vụ | Ngày cần chuẩn bị hàng; mặc định = ngày vận hành + 1, nhưng nay chọn tự do |
| Đề xuất (PrepPlan) | Danh sách chuẩn bị của 1 cửa hàng cho 1 ngày, có phiên bản (v1, v2…) và trạng thái |
| Tồn an toàn / dự phòng | Lượng hàng thêm phòng khi bán nhiều hơn dự báo: `z × RMSE` |
| RMSE | Độ lệch trung bình (căn bậc hai của bình phương sai số) giữa dự báo và thực tế của từng món tại từng cửa hàng; món càng khó đoán thì dự phòng càng lớn |
| wMAPE | Sai số phần trăm có trọng số = tổng |dự báo − thực tế| ÷ tổng thực tế; càng thấp càng tốt |
| Baseline | Cách dự báo đơn giản (lặp lại tuần trước, trung bình 7 ngày) dùng làm mốc để chứng minh mô hình tốt hơn |
| Lag / rolling | Đặc trưng lấy từ lượng bán các ngày trước (hôm qua, 7/14/28 ngày trước; trung bình trượt 7/28 ngày) |

---

## 0.5 Hướng dẫn tải về và mở web (làm theo từng bước)

Mỗi thành viên chạy web **trên máy của mình**; không có link chung trên mạng. Làm lần lượt từ A đến G (lần đầu khoảng 20–30 phút, chủ yếu là chờ nạp dữ liệu).

```
Tải mã (GitHub) ─► Cài môi trường ─► Điền .env ─► Tạo CSDL + nạp dữ liệu ─► migrate ─► seed_demo ─► runserver ─► mở trình duyệt
```

**A. Cài sẵn trên máy** (một lần)

| Phần mềm | Phiên bản | Cài như thế nào |
|---|---|---|
| Git | bất kỳ | git-scm.com |
| Python | **3.12** (đã kiểm thử với bản này) | python.org |
| MySQL Server | 8.x | macOS: `brew install mysql pkg-config` · Windows: MySQL Installer (ghi nhớ mật khẩu `root`) |
| `libomp` (chỉ macOS) | – | `brew install libomp` (LightGBM cần) |

**B. Tải dự án**
```bash
git clone https://github.com/HUY56206/Machine-Learning-QSR-Demand-Forecasting.git
cd Machine-Learning-QSR-Demand-Forecasting
```
Repo đã có sẵn mô hình `Assets/best_model.joblib` và bảng kết quả `Assets/reports/metrics.csv`. **Không có** thư mục `data/` (nặng ~438 MB, bị chặn khi đẩy lên GitHub) – xem bước E.

**C. Tạo môi trường Python và cài thư viện**
```bash
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Lỗi khi cài `mysqlclient` thường do thiếu thư viện C của MySQL: macOS chạy `brew install mysql pkg-config` rồi cài lại; Windows dùng bản wheel (`pip install mysqlclient` sau khi cập nhật pip) hoặc báo trưởng nhóm.

**D. Điền thông tin MySQL vào `.env`**
```bash
cp .env.example .env                 # Windows: copy .env.example .env
```
Mở `.env`, điền mật khẩu MySQL của máy bạn:
```
QSR_DB_HOST=127.0.0.1
QSR_DB_PORT=3306
QSR_DB_USER=root
QSR_DB_PASSWORD=<mật khẩu MySQL của bạn>
QSR_DB_NAME=qsr_db
```
(`.env` không được đẩy lên GitHub nên mỗi người tự điền.) Bật MySQL trước khi làm tiếp: macOS `brew services run mysql`; Windows: dịch vụ MySQL đang chạy.

**E. Tạo cơ sở dữ liệu `qsr_db` và nạp dữ liệu** – chọn **một** trong hai cách:

| Cách | Khi nào dùng | Lệnh |
|---|---|---|
| E1. Nhận file `qsr_db.sql` từ trưởng nhóm (**nhanh, nên dùng**) | Trưởng nhóm đã xuất bằng `mysqldump` | `mysql -u root -p -e "CREATE DATABASE qsr_db CHARACTER SET utf8mb4"` rồi `mysql -u root -p qsr_db < qsr_db.sql` |
| E2. Tự dựng từ dữ liệu thô | Có file `qsr_demand_dataset.csv` | Đặt file vào `data/raw/qsr_demand_dataset.csv` rồi chạy `python -m Tests.AppPrepareData` (làm sạch → tạo schema → nạp 5 bảng; mất vài phút; **xóa và tạo lại** mọi bảng của `qsr_db`) |

Web **đọc dữ liệu từ MySQL**, không đọc trực tiếp file CSV khi chạy.

Kiểm tra nhanh: `python -m Tests.TestConnector` phải báo kết nối thành công.

**F. Tạo bảng của web và tài khoản mẫu**
```bash
python manage.py migrate        # tạo bảng của web (hồ sơ, kiểm kho, đề xuất, thông báo, cấu hình)
python manage.py seed_demo      # tài khoản mẫu + lịch sử kiểm kho + 1 đề xuất chờ duyệt
```
Cả nhóm nên dùng chung mật khẩu để dễ trao đổi: `python manage.py seed_demo --password "MatKhauNhom"`.

**G. Chạy web và đăng nhập**
```bash
python manage.py runserver
```
Mở trình duyệt: **http://127.0.0.1:8000/**. Đăng nhập bằng tài khoản ở mục 3.1 (VD một quản lý, một nhân viên, `admin`); hệ thống tự mở đúng trang theo vai trò. Dừng web: `Ctrl + C`.

**Mỗi lần mở lại web** chỉ cần: bật MySQL → `source .venv/bin/activate` → `python manage.py runserver`.

**Lỗi thường gặp**

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `Can't connect to MySQL server` | MySQL chưa chạy, hoặc sai host/cổng/mật khẩu trong `.env` |
| `Unknown database 'qsr_db'` | Chưa làm bước E |
| Trang đăng nhập báo sai tài khoản | Chưa chạy `seed_demo`, hoặc nhập sai mật khẩu (sai 5 lần bị khóa 15 phút) |
| "Không có dữ liệu đầu vào cho ngày đã chọn" | Ngày chọn ngoài 01/01/2021 – 31/12/2025, hoặc dữ liệu chưa nạp đủ |
| Chạy dự báo lần đầu rất chậm | Bình thường: mô hình được nạp một lần vào bộ nhớ, các lần sau nhanh hơn |
| Thiếu `Assets/best_model.joblib` | Kéo lại repo (`git pull`) hoặc chạy `python -m Tests.AppCatBoost` rồi `python -m Tests.AppCompareModels` để huấn luyện lại (cần bước E2) |
| Cổng 8000 đang bị dùng | `python manage.py runserver 8080` rồi mở `http://127.0.0.1:8080/` |

Chạy kiểm thử tự động (không bắt buộc): `python manage.py test forecast`. Kịch bản kiểm thử bằng tay cho cả nhóm: `Kich_Ban.md`.

---

## 1. Tổng quan đồ án

**Bài toán:** dự báo nhu cầu *ngắn hạn (một ngày)* theo từng món, từng cửa hàng của chuỗi QSR để lập danh sách chuẩn bị hàng, giảm thiếu hụt/lãng phí trong chuỗi cung ứng và vận hành.

**Bối cảnh demo:** cửa hàng R01 · Downtown Chicago Grill, ngày vận hành **30/10/2025**, ngày phục vụ cần chuẩn bị **31/10/2025** (Halloween); 15 cửa hàng × 50 món = 750 cặp (cửa hàng, món). Số bán thật sau ngày vận hành bị ẩn trên giao diện (nhưng vẫn nằm trong DB để dự báo thử và hậu kiểm).

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
| 2 | Kiểm quyền + cửa hàng; ngày chọn tùy ý (không còn giới hạn ngày vận hành + 1); cần có kiểm kho | `permissions.py`, `plans.create_plan` |
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
| Ngày dự báo | Bất kỳ ngày có dữ liệu đầu vào (01/01/2021 – 31/12/2025) | Ngoài kỳ → "Không có dữ liệu đầu vào"; ngày chưa chạy → "Chưa có dữ liệu cho ngày đã chọn" (chỉ là chưa bấm chạy) |

---

## 2.1 Dữ liệu

| Bảng MySQL | Nội dung | Khóa |
|---|---|---|
| `stores` | 15 cửa hàng (R01…R15), tên, thành phố | `restaurant_id` |
| `products` | 50 món, 8 nhóm (Đồ uống, Burger, Gà, Món phụ, Combo, Bữa sáng, Tráng miệng, Đặc biệt), giá | `menu_item_id` |
| `daily_sales` | Số bán mỗi (ngày, cửa hàng, món): `quantity` (đã làm sạch), `quantity_raw` (gốc), cờ `is_imputed` | `sale_id` |
| `weather_events` | Mỗi (ngày, cửa hàng): nhiệt độ TB, lượng mưa, loại mưa/tuyết, ngày lễ, sự kiện đặc biệt | `(restaurant_id, event_date)` |
| `promotions` | Khuyến mãi theo (ngày, cửa hàng, món) | `promotion_id` |
| `forecasts` | Kết quả dự báo thô do pipeline ghi (tương thích công cụ cũ) | `(forecast_date, restaurant_id, menu_item_id)` |
| Bảng web (migration) | `Profile`, `SystemConfig`, `InventoryCount/Item`, `PrepPlan/PrepLine`, `Notification`… | – |

Kỳ dữ liệu **01/01/2021 – 31/12/2025**. Dữ liệu thô (`data/raw`) được làm sạch (xử lý giá trị thiếu, đánh dấu ngoại lai theo MAD: `quantity > median + 8 × 1,4826 × MAD` cùng cửa hàng-món-thứ) rồi nạp vào MySQL. Web **chỉ đọc MySQL**, không đọc file CSV.

## 2.2 Mô hình học máy

**Chia dữ liệu theo thời gian (không xáo trộn):** train đến 30/06/2025 · validation 01/07–30/09/2025 · test 01/10–31/12/2025 (69.000 dòng).

**Đặc trưng (features)**

| Nhóm | Ví dụ |
|---|---|
| Phân loại | cửa hàng, món, nhóm món, thành phố, loại mưa |
| Lịch | thứ trong tuần, cuối tuần, tháng, tuần/ngày trong năm, năm |
| Biết trước ngày dự báo | giá, nhiệt độ, lượng mưa, ngày lễ, hôm trước/sau ngày lễ, sự kiện đặc biệt, khuyến mãi |
| Lịch sử bán (chỉ ≤ t−1) | `lag_1/7/14/28`, trung bình & độ lệch chuẩn trượt 7/28 ngày, trung bình 4 tuần cùng thứ |

Mọi đặc trưng lịch sử đều `shift` trước khi tính nên **không bao giờ chứa số bán của chính ngày được dự báo** (tránh rò rỉ dữ liệu).

**Kết quả (tập test, `Assets/reports/metrics.csv`)**

| Mô hình | wMAPE | MAE | RMSE | R² |
|---|---:|---:|---:|---:|
| CatBoost (tốt nhất, `best_model.joblib`) | **0,1454** | 3,37 | 6,62 | 0,789 |
| LightGBM | 0,1461 | 3,39 | 6,64 | 0,788 |
| Ridge | 0,1771 | 4,11 | 7,24 | 0,748 |
| Trung bình trượt 7 ngày (baseline) | 0,1992 | 4,62 | 7,90 | 0,700 |
| Lặp lại tuần trước (baseline) | 0,2288 | 5,31 | 8,92 | 0,617 |

**Từ dự báo thành danh sách chuẩn bị:** `Dự phòng = z × RMSE(cửa hàng, món)` (RMSE riêng từng cặp, lấy từ phần dư trên tập validation); `Cần chuẩn bị = max(0, Dự báo + Dự phòng − Đang có)`; `Đang có` lấy từ lần kiểm kho đã lưu gần nhất tính đến ngày vận hành.

## 2.3 Quy tắc ngày dự báo (cập nhật)

| Trường hợp | Hành vi |
|---|---|
| Ngày phục vụ mặc định (30/10 + 1 = 31/10) | Dự báo bình thường, là luồng vận hành thực |
| Ngày quá khứ (VD 15/09/2025) | Dự báo được; dùng lịch sử đến ngày hôm trước. Dùng để hậu kiểm so với số bán thật |
| Ngày sau 31/10 còn trong dữ liệu (VD 20/11/2025) | Dự báo được (dự báo thử). Đặc trưng lag lấy số bán thật có sẵn trong DB nên kết quả mang tính hậu kiểm, **không phải dự báo tương lai thật** |
| Ngày ngoài kỳ dữ liệu (VD 01/03/2026) | `no_data`: "Không có dữ liệu đầu vào cho ngày đã chọn", không tạo đề xuất rỗng |
| Tồn kho | Luôn dùng lần kiểm kho gần nhất ≤ ngày vận hành; với ngày xa ngày vận hành, số này chỉ tham khảo |
| Kiểm kho | Vẫn chỉ nhập cho ngày vận hành |
| Duyệt / khóa / phiên bản | Giống mọi ngày: mỗi (cửa hàng, ngày) có chuỗi phiên bản riêng |
| Giao diện | Lịch chọn 01/2021 – 12/2025; trang Dự báo hiện 3 thẻ (hôm trước · đang xem · hôm sau); nhân viên chọn ngày xem danh sách |

Mã liên quan: `forecast/services/plans.py` (`create_plan`), `forecast/views.py` (`forecast`, `staff_prep`), `forecast/static/forecast/js/modals.js` (lịch).

---

## 3. Phân quyền 3 vai trò

| Chức năng | Nhân viên (`staff`) | Quản lý (`manager`) | Quản trị (`admin`) |
|---|:-:|:-:|:-:|
| Phạm vi | 1 cửa hàng được gán | 1 cửa hàng được gán | Toàn hệ thống |
| Kiểm kho (nháp / lưu) | ✅ | – | – |
| Danh sách chuẩn bị (chọn ngày xem), "Đánh dấu xong" | ✅ | – | – |
| Tổng quan, chọn ngày phục vụ (mọi ngày) | – | ✅ | – |
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
Tài khoản demo: 31 tài khoản, **mỗi tài khoản có tên đăng nhập và mật khẩu riêng** (mục 3.1; **đổi trước khi triển khai**). "Cấp lại mật khẩu" ở màn đăng nhập chỉ ghi nhận yêu cầu (Chờ xử lý); admin cấp mật khẩu tạm một lần.

---

### 3.1 Danh sách tài khoản thử (toàn bộ 15 cửa hàng)

Tạo bằng `python manage.py seed_demo`; 31 tài khoản, tên đăng nhập và mật khẩu đều khác nhau, cố định trong `forecast/management/commands/seed_demo.py` (danh sách `ACCOUNTS`). **Chỉ dùng thử nghiệm nội bộ, đổi mật khẩu trước khi triển khai công khai.** R01, R02 có sẵn lịch sử kiểm kho; R03–R15 để trống cho kịch bản kiểm kho từ đầu.

| Cửa hàng | Quản lý (tên đăng nhập / mật khẩu) | Nhân viên (tên đăng nhập / mật khẩu) | Ghi chú |
|---|---|---|---|
| R01 · Downtown Chicago Grill | `lan.r01` / `vjtSKDEP%96` | `khanh.r01` / `UTxmJhkV!40` | Có lịch sử kiểm kho và đề xuất chờ duyệt |
| R02 · Wrigleyville Bites | `trang.r02` / `7AXSTTwM!86` | `nam.r02` / `ukYcs7PR#17` | Có lịch sử kiểm kho; dùng để kiểm tra không thấy dữ liệu R01 |
| R03 · Indianapolis Crossroads Eats | `yen.r03` / `jSS6k2tD%62` | `tuan.r03` / `52NVaJcu$51` | Chưa có kiểm kho |
| R04 · Detroit Motor City Diner | `chi.r04` / `QabyMfhC%65` | `kien.r04` / `4W7xd3t3$66` | Chưa có kiểm kho |
| R05 · Milwaukee Lakefront Kitchen | `huong.r05` / `nS722UFE#91` | `thao.r05` / `y6FHPP7w$63` | Chưa có kiểm kho |
| R06 · Columbus Campus Corner | `loan.r06` / `b9nNE2TG!21` | `hanh.r06` / `8bAfs2nm@74` | Chưa có kiểm kho |
| R07 · Minneapolis Uptown Cafe | `khoa.r07` / `TY6k93Dz@85` | `phong.r07` / `bt5sb78Q%43` | Chưa có kiểm kho |
| R08 · Kansas City BBQ Junction | `nhung.r08` / `psRm3uZr@29` | `tam.r08` / `DXekXKb8!65` | Chưa có kiểm kho |
| R09 · St. Louis Gateway Grub | `son.r09` / `aRgV4ayV$67` | `duc.r09` / `fKu4bMgf#54` | Chưa có kiểm kho |
| R10 · Cleveland Flats Eatery | `quan.r10` / `Mw7U87Ge#21` | `quyen.r10` / `Nz2HD8fK!81` | Chưa có kiểm kho |
| R11 · Cincinnati Riverfront Bites | `vy.r11` / `C2hR7eTs%61` | `hoa.r11` / `MJz2VcCf!60` | Chưa có kiểm kho |
| R12 · Des Moines Heartland Hub | `an.r12` / `fkjJCdLb!26` | `phuc.r12` / `MuMMFa2D$35` | Chưa có kiểm kho |
| R13 · Omaha Midtown Munch | `nhi.r13` / `uHGZqCKK@96` | `thu.r13` / `WNAXGwxB@36` | Chưa có kiểm kho |
| R14 · Madison State Street Snacks | `lam.r14` / `He7SdLBX@31` | `minh.r14` / `Uqr4qRF9%80` | Chưa có kiểm kho |
| R15 · Ann Arbor College Cravings | `long.r15` / `wWthbmTZ%24` | `ha.r15` / `Lf7h7KrC#37` | Chưa có kiểm kho |
| Toàn hệ thống (15 cửa hàng) | `admin` / `VaHhXjMc!75` (Quản trị viên) | – | Cũng đăng nhập được Django Admin `/admin/` |

---

## 4. Giao diện và tương tác dữ liệu

| Trang | Vai trò | Nút chính | Tác dụng thực tế |
|---|---|---|---|
| Kiểm kho | Staff (8 nhóm món, 5 dòng/trang) | **Lưu nháp / Lưu** | Ghi `InventoryCount/Item`; cờ "cần xem lại" nếu < 25 % kỳ trước; tự lập đề xuất nếu bật `auto_plan_after_inventory` |
| Danh sách chuẩn bị | Staff | **Đánh dấu xong** | Ghi người/giờ hoàn thành; xong hết → báo quản lý |
| Tổng quan | Manager | **Xem dữ liệu**, **Chọn ngày**, **Xem** (lý do) | Biểu đồ 7 ngày, 3 thẻ Thiếu/Bổ sung/Đủ, việc cần xử lý |
| Chuẩn bị hàng | Manager | **Chạy dự báo** | Gọi pipeline ML (mục 2) cho ngày đang chọn (mặc định ngày vận hành + 1) |
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
│   └── tests.py               # 38 test
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
| `Tests/` & `forecast/tests.py` | Kiểm thử pipeline ML (cũ, chưa chạy lại) & kiểm thử web (38 test, đạt) |

**Chạy nhanh:** `pip install -r requirements.txt` → bật MySQL → `python manage.py migrate` → `python manage.py seed_demo` → `python manage.py runserver`; nhắc kiểm kho: cron `python manage.py send_reminders`.

**Đối chiếu tài liệu thiết kế (PDF) và mã nguồn – điểm khác biệt đã biết**

| # | Thiết kế (PDF) | Mã nguồn hiện tại |
|---|---|---|
| 1 | Làm tròn dự báo/tồn an toàn *trước* khi cộng trừ | Cộng trước rồi `ceil` một lần (`plans.compute_line`); có thể lệch ±1 phần so với ví dụ PDF |
| 2 | Cửa hàng, Cấu hình dùng giao diện Django Admin | Có trang riêng cho admin; riêng `require_approval` và ngày vận hành chỉ sửa ở Django Admin |
| 3 | Nút "Tải Excel" | Xuất **CSV** (Excel mở được) |
| 4 | Email tóm tắt hằng tuần | Chỉ lưu công tắc, chưa gửi |
| 5 | Nhắc kiểm kho theo giờ cấu hình | Cần cron chạy `send_reminders` |
| 6 | Chạy toàn hệ thống 750 cặp | Chạy tuần tự đồng bộ, có thể chậm/timeout khi triển khai |
| 7 | Dự báo ngày vận hành + 1 | Mở rộng: dự báo mọi ngày có dữ liệu; ngày khác ngày phục vụ là dự báo thử (hậu kiểm) |

**Hạn chế đã biết:** "Chạy tất cả cửa hàng" chạy đồng bộ (có thể chậm); `weekly_email` chưa có hạ tầng gửi mail; `Tests/` (pytest cũ) chưa chạy lại; giao diện chưa đối chiếu thị giác đầy đủ với Figma.
