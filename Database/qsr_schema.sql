-- =====================================================================
-- CSDL QSR Demand Forecasting  (MySQL 8.0+)
-- Chạy:  mysql -u root -p < Database/qsr_schema.sql   (hoặc python -m Tests.AppPrepareData)
--
-- 5 bảng nghiệp vụ : stores, products, daily_sales, promotions, weather_events
-- 1 bảng kết quả   : forecasts (lưu dự báo + tồn kho an toàn cho web Django)
--
-- Độ chi tiết (đã kiểm tra trên dữ liệu):
--   - Thời tiết theo (thành phố, ngày); ngày lễ chung toàn quốc;
--     sự kiện đặc biệt theo (nhà hàng, ngày)  -> weather_events theo (restaurant, date)
--   - Khuyến mãi theo (nhà hàng, món, ngày)   -> promotions chỉ lưu ngày có khuyến mãi
-- =====================================================================

CREATE DATABASE IF NOT EXISTS qsr_db
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE qsr_db;

DROP TABLE IF EXISTS forecasts;
DROP TABLE IF EXISTS daily_sales;
DROP TABLE IF EXISTS promotions;
DROP TABLE IF EXISTS weather_events;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS stores;

-- 1. Nhà hàng (15 dòng)
CREATE TABLE stores (
    restaurant_id    VARCHAR(10)  NOT NULL,
    restaurant_name  VARCHAR(100) NOT NULL,
    city             VARCHAR(50)  NOT NULL,
    state            CHAR(2)      NOT NULL,
    PRIMARY KEY (restaurant_id)
) ENGINE=InnoDB;

-- 2. Sản phẩm / món ăn (50 dòng)
CREATE TABLE products (
    menu_item_id     VARCHAR(10)   NOT NULL,
    menu_item_name   VARCHAR(100)  NOT NULL,
    category         VARCHAR(30)   NOT NULL,
    unit_price       DECIMAL(6,2)  NOT NULL,
    PRIMARY KEY (menu_item_id)
) ENGINE=InnoDB;

-- 3. Thời tiết & sự kiện theo ngày của từng nhà hàng (15 x 1826 = 27.390 dòng)
CREATE TABLE weather_events (
    restaurant_id       VARCHAR(10)  NOT NULL,
    event_date          DATE         NOT NULL,
    avg_temp_f          DECIMAL(5,1) NOT NULL,
    precip_inches       DECIMAL(5,2) NOT NULL DEFAULT 0,
    precip_type         ENUM('None','Rain','Snow') NOT NULL DEFAULT 'None',
    is_holiday          TINYINT(1)   NOT NULL DEFAULT 0,
    holiday_name        VARCHAR(60)  NULL,
    is_special_event    TINYINT(1)   NOT NULL DEFAULT 0,
    special_event_name  VARCHAR(60)  NULL,
    PRIMARY KEY (restaurant_id, event_date),
    CONSTRAINT fk_we_store FOREIGN KEY (restaurant_id) REFERENCES stores (restaurant_id)
) ENGINE=InnoDB;

-- 4. Khuyến mãi - chỉ lưu các ngày có khuyến mãi (~15.582 dòng)
CREATE TABLE promotions (
    promotion_id     INT          NOT NULL AUTO_INCREMENT,
    restaurant_id    VARCHAR(10)  NOT NULL,
    menu_item_id     VARCHAR(10)  NOT NULL,
    promo_date       DATE         NOT NULL,
    PRIMARY KEY (promotion_id),
    UNIQUE KEY uq_promo (restaurant_id, menu_item_id, promo_date),
    CONSTRAINT fk_promo_store   FOREIGN KEY (restaurant_id) REFERENCES stores (restaurant_id),
    CONSTRAINT fk_promo_product FOREIGN KEY (menu_item_id)  REFERENCES products (menu_item_id)
) ENGINE=InnoDB;

-- 5. Doanh số theo ngày (1.369.500 dòng) - bảng fact chính
CREATE TABLE daily_sales (
    sale_id          INT          NOT NULL,
    sale_date        DATE         NOT NULL,
    restaurant_id    VARCHAR(10)  NOT NULL,
    menu_item_id     VARCHAR(10)  NOT NULL,
    quantity         INT          NOT NULL COMMENT 'đã làm sạch (dùng cho mô hình)',
    quantity_raw     INT          NULL     COMMENT 'giá trị gốc, NULL nếu bị thiếu',
    is_imputed       TINYINT(1)   NOT NULL DEFAULT 0,
    is_outlier       TINYINT(1)   NOT NULL DEFAULT 0,
    PRIMARY KEY (sale_id),
    UNIQUE KEY uq_sale (sale_date, restaurant_id, menu_item_id),
    KEY idx_store_date (restaurant_id, sale_date),
    CONSTRAINT fk_sales_store   FOREIGN KEY (restaurant_id) REFERENCES stores (restaurant_id),
    CONSTRAINT fk_sales_product FOREIGN KEY (menu_item_id)  REFERENCES products (menu_item_id)
) ENGINE=InnoDB;

-- 6. Kết quả dự báo & đề xuất tồn kho (web ghi vào sau mỗi lần bấm "Chạy dự báo")
CREATE TABLE forecasts (
    forecast_id         INT           NOT NULL AUTO_INCREMENT,
    forecast_date       DATE          NOT NULL,
    restaurant_id       VARCHAR(10)   NOT NULL,
    menu_item_id        VARCHAR(10)   NOT NULL,
    predicted_qty       DECIMAL(8,2)  NOT NULL,
    safety_stock        DECIMAL(8,2)  NULL,
    current_stock       INT           NULL,
    recommended_order   INT           NULL,
    model_name          VARCHAR(30)   NOT NULL,
    created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (forecast_id),
    UNIQUE KEY uq_forecast (forecast_date, restaurant_id, menu_item_id, model_name),
    CONSTRAINT fk_fc_store   FOREIGN KEY (restaurant_id) REFERENCES stores (restaurant_id),
    CONSTRAINT fk_fc_product FOREIGN KEY (menu_item_id)  REFERENCES products (menu_item_id)
) ENGINE=InnoDB;
