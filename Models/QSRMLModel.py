"""Lớp cơ sở cho mọi mô hình dự báo nhu cầu (BUILD MODEL & USE MODEL - Slide 08).

    (5)  Filter & load data : execQSRHistory() -> processFeatures() -> splitTrainValTest()
    (6)  Select algorithm   : lớp con (QSRRidgeRegression, QSRLightGBM, QSRCatBoost, QSRBaselineModel)
    (7)  Train              : processTrain()
    (8)  Evaluate           : evaluate() -> MetricsResult
    (9)  Save model         : saveModel()
    (10) Load model         : loadModel()
    (11) Use model          : predict() / forecastDate()

Bài toán: dự báo ngày mai (one-step-ahead). Tại ngày t, đặc trưng lịch sử chỉ dùng
quantity đến ngày t-1; lịch, khuyến mãi, ngày lễ, sự kiện, thời tiết của ngày t
được coi là đã biết trước.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from Models.MetricsResult import MetricsResult
from Models.QSRStatistic import QSRStatistic
from Models.TrainedModel import TrainedModel
from Utils import Config
from Utils.FileUtil import FileUtil


class QSRMLModel(QSRStatistic):
    model_name = "base"
    categorical_mode = "str"     # "str" (Ridge, CatBoost) | "category" (LightGBM)

    def __init__(self, connector=None):
        super().__init__(connector)
        self.df_features = None
        self.train = self.val = self.test = None
        self.trainedmodel = None

    # ================================================================ (5) đặc trưng
    def processFeatures(self):
        df = self.df.copy()
        d = df[Config.DATE_COL]
        df["week_of_year"] = d.dt.isocalendar().week.astype("int16")
        df["day_of_month"] = d.dt.day.astype("int16")
        df["day_of_year"] = d.dt.day_of_year.astype("int16")

        # Ngày lễ chung toàn quốc -> hiệu ứng trước / sau lễ
        holidays = set(df.loc[df["is_holiday"] == 1, Config.DATE_COL].unique())
        df["is_holiday_tomorrow"] = (d + pd.Timedelta(days=1)).isin(holidays).astype("int8")
        df["is_holiday_yesterday"] = (d - pd.Timedelta(days=1)).isin(holidays).astype("int8")

        df = df.sort_values(Config.SERIES_KEYS + [Config.DATE_COL]).reset_index(drop=True)
        grp = df.groupby(Config.SERIES_KEYS, sort=False)[Config.TARGET]
        for k in Config.LAGS:
            df[f"lag_{k}"] = grp.shift(k)

        # shift(1) trước rồi mới rolling -> không bao giờ chứa giá trị của ngày t
        shifted_grp = grp.shift(1).groupby([df[k] for k in Config.SERIES_KEYS], sort=False)
        for w in Config.ROLL_WINDOWS:
            df[f"roll_mean_{w}"] = shifted_grp.transform(lambda s: s.rolling(w, min_periods=w).mean())
            df[f"roll_std_{w}"] = shifted_grp.transform(lambda s: s.rolling(w, min_periods=w).std())
        df["dow_mean_4w"] = pd.concat([grp.shift(k) for k in (7, 14, 21, 28)], axis=1).mean(axis=1)

        # Bỏ các ngày đầu chuỗi chưa đủ lịch sử (28 ngày)
        df = df.dropna(subset=[f"lag_{max(Config.LAGS)}", f"roll_std_{max(Config.ROLL_WINDOWS)}"])
        self.df_features = df.sort_values([Config.DATE_COL] + Config.SERIES_KEYS).reset_index(drop=True)
        return self.df_features

    def splitTrainValTest(self):
        """Chia theo trục thời gian - không xáo trộn ngẫu nhiên."""
        d = self.df_features[Config.DATE_COL]
        self.train = self.df_features[d <= Config.TRAIN_END]
        self.val = self.df_features[d.between(Config.VAL_START, Config.VAL_END)]
        self.test = self.df_features[d.between(Config.TEST_START, Config.TEST_END)]
        assert self.train[Config.DATE_COL].max() < self.val[Config.DATE_COL].min()
        assert self.val[Config.DATE_COL].max() < self.test[Config.DATE_COL].min()
        return self.train, self.val, self.test

    def saveDatasets(self, folder=Config.SPLIT_DIR):
        folder.mkdir(parents=True, exist_ok=True)
        for name, part in (("train", self.train), ("val", self.val), ("test", self.test)):
            part.to_parquet(folder / f"{name}.parquet", index=False)

    def printSplitInfo(self):
        for name, part in (("train", self.train), ("val", self.val), ("test", self.test)):
            d = part[Config.DATE_COL]
            print(f"{name:5s}: {d.min():%Y-%m-%d} -> {d.max():%Y-%m-%d} | {len(part):>9,} dòng")

    def prepareX(self, df):
        """Chọn đúng cột và kiểu dữ liệu mà mô hình đã thấy khi huấn luyện."""
        tm = self.trainedmodel
        X = df[tm.columns_input].copy()
        for col in tm.categorical_columns:
            if tm.categorical_mode == "category":
                X[col] = pd.Categorical(X[col].astype(str), categories=tm.categories[col])
            else:
                X[col] = X[col].astype(str)
        return X

    # ================================================================ (6)(7) train
    def fitModel(self, X_train, y_train, X_val, y_val):
        """Lớp con cài đặt: trả về (model, params)."""
        raise NotImplementedError

    def processTrain(self, columns_input=None, column_target=Config.TARGET):
        columns_input = columns_input or Config.FEATURES
        categorical = [c for c in Config.CATEGORICAL_FEATURES if c in columns_input]
        self.trainedmodel = TrainedModel(
            model_name=self.model_name, columns_input=columns_input, column_target=column_target,
            categorical_columns=categorical,
            categories={c: sorted(self.train[c].astype(str).unique()) for c in categorical},
            trained_until=str(self.train[Config.DATE_COL].max().date()),
        )
        self.trainedmodel.categorical_mode = self.categorical_mode
        model, params = self.fitModel(self.prepareX(self.train), self.train[column_target],
                                      self.prepareX(self.val), self.val[column_target])
        self.trainedmodel.model = model
        self.trainedmodel.params = params
        return self.trainedmodel

    # ================================================================ (8) đánh giá
    def predict(self, df):
        y_hat = self.trainedmodel.model.predict(self.prepareX(df))
        return np.clip(np.asarray(y_hat, dtype=float), 0, None)   # nhu cầu không âm

    def evaluate(self, split="test"):
        """Đánh giá trên giá trị gốc quantity_raw, bỏ các dòng do nhóm tự điền (imputed)."""
        df = {"train": self.train, "val": self.val, "test": self.test}[split]
        mask = (df["is_imputed"] == 0).to_numpy()
        y_true = df[Config.TARGET_RAW].to_numpy()[mask]
        y_pred_all = self.predict(df)
        y_pred = y_pred_all[mask]
        err = y_pred - y_true
        mse = float(np.mean(err ** 2))
        result = MetricsResult(
            MAE=round(float(np.mean(np.abs(err))), 4),
            MSE=round(mse, 4),
            RMSE=round(float(np.sqrt(mse)), 4),
            R2_SCORE=round(1 - mse / float(np.var(y_true)), 4),
            WMAPE=round(float(np.abs(err).sum() / np.abs(y_true).sum()), 4),
            BIAS=round(float(err.sum() / y_true.sum()), 4),
            model_name=self.model_name, split=split, n_rows=int(mask.sum()),
        )
        self.trainedmodel.metrics = [m for m in self.trainedmodel.metrics if m.split != split] + [result]
        if split == "val":
            self.trainedmodel.residual_rmse = self.processResidualRMSE(df, y_pred_all, mask)
        return result

    @staticmethod
    def processResidualRMSE(df, y_pred, mask):
        """RMSE theo từng (nhà hàng, món) trên validation -> đầu vào cho Safety Stock.

        Safety Stock phải phản ánh độ dao động của NHU CẦU, nên bỏ thêm:
        - outlier (lỗi ghi nhận, gấp ~5 lần bình thường)
        - ngày bán = 0: mọi món đều có trung vị > 2/ngày, số 0 rải rác 1-2 ngày
          -> dấu hiệu hết hàng (nhu cầu bị che khuất), không phải nhu cầu thật bằng 0.
        """
        mask = mask & (df["is_outlier"] == 0).to_numpy() & (df[Config.TARGET_RAW] > 0).to_numpy()
        y_pred = pd.Series(y_pred, index=df.index)[mask]
        res = df.loc[mask, Config.SERIES_KEYS].assign(sq_err=(df.loc[mask, Config.TARGET_RAW] - y_pred) ** 2)
        out = res.groupby(Config.SERIES_KEYS)["sq_err"].mean().pow(0.5).rename("residual_rmse")
        return out.reset_index()

    def visualizeActualAndPredictResult(self, restaurant_id, menu_item_id, split="test", savePath=None):
        df = {"val": self.val, "test": self.test}[split]
        part = df[(df["restaurant_id"] == restaurant_id) & (df["menu_item_id"] == menu_item_id)]
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(part[Config.DATE_COL], part[Config.TARGET_RAW], label="Thực tế", marker=".")
        ax.plot(part[Config.DATE_COL], self.predict(part), label=f"Dự báo ({self.model_name})", marker=".")
        name = part["menu_item_name"].iloc[0] if "menu_item_name" in part else menu_item_id
        ax.set_title(f"{restaurant_id} - {name}: thực tế vs dự báo ({split})")
        ax.legend()
        ax.grid(alpha=0.3)
        self._show(fig, savePath)

    def saveMetricsReport(self, path=Config.REPORTS_DIR / "metrics.csv"):
        """Ghi (hoặc cập nhật) kết quả của mô hình này vào bảng so sánh chung."""
        new = pd.DataFrame([m.toDict() for m in self.trainedmodel.metrics])
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            old = pd.read_csv(path)
            new = pd.concat([old[old["model"] != self.model_name], new], ignore_index=True)
        new.to_csv(path, index=False)
        return new

    # ================================================================ (9)(10) lưu / nạp
    def saveModel(self, fileName):
        return FileUtil.saveModel(self.trainedmodel, fileName)

    def loadModel(self, fileName):
        self.trainedmodel = FileUtil.loadModel(fileName)
        if self.trainedmodel is not None:
            self.model_name = self.trainedmodel.model_name
        return self.trainedmodel

    # ================================================================ (11) sử dụng
    def forecastDate(self, forecast_date, restaurant_id=None):
        """Dự báo nhu cầu của mọi món (của một / mọi nhà hàng) cho một ngày.

        Cần đã gọi execQSRHistory() với dữ liệu ít nhất 28 ngày trước forecast_date
        và processFeatures().
        """
        day = self.df_features[self.df_features[Config.DATE_COL] == pd.Timestamp(forecast_date)]
        if restaurant_id:
            day = day[day["restaurant_id"] == restaurant_id]
        if day.empty:
            raise ValueError(f"Không có dữ liệu đặc trưng cho ngày {forecast_date}")
        cols = [Config.DATE_COL, "restaurant_id", "restaurant_name", "menu_item_id", "menu_item_name",
                "category", Config.TARGET_RAW]
        out = day[cols].copy()
        out["predicted_qty"] = np.round(self.predict(day), 2)
        return out.reset_index(drop=True)
