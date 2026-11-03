class MetricsResult:
    """Kết quả đánh giá mô hình. wMAPE là chỉ số trọng tâm của đề tài."""

    def __init__(self, MAE=None, MSE=None, RMSE=None, R2_SCORE=None, WMAPE=None, BIAS=None,
                 model_name=None, split=None, n_rows=None):
        self.MAE = MAE
        self.MSE = MSE
        self.RMSE = RMSE
        self.R2_SCORE = R2_SCORE
        self.WMAPE = WMAPE
        self.BIAS = BIAS        # > 0: dự báo dư (thừa hàng) | < 0: dự báo thiếu (cháy hàng)
        self.model_name = model_name
        self.split = split
        self.n_rows = n_rows

    def toDict(self):
        return {"model": self.model_name, "split": self.split,
                "wMAPE": self.WMAPE, "MAE": self.MAE, "MSE": self.MSE, "RMSE": self.RMSE,
                "R2_SCORE": self.R2_SCORE, "Bias": self.BIAS, "n_rows": self.n_rows}

    def __str__(self):
        return (f"[{self.model_name} - {self.split}]\n"
                f"wMAPE={self.WMAPE}\nMAE={self.MAE}\nMSE={self.MSE}\nRMSE={self.RMSE}\n"
                f"R2_SCORE={self.R2_SCORE}\nBIAS={self.BIAS}")
