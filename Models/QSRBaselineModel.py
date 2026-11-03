"""Mô hình cơ sở (benchmark) - không cần học tham số.

- Seasonal Naive (m=7): y_hat(t) = y(t-7)              -> cột lag_7
- Moving Average 7   : y_hat(t) = mean(y(t-7..t-1))   -> cột roll_mean_7

Mọi mô hình học máy phải có wMAPE thấp hơn các mốc này mới có ý nghĩa.
"""
from Models.QSRMLModel import QSRMLModel


class ColumnModel:
    """'Mô hình' trả về nguyên một cột đặc trưng làm dự báo."""

    def __init__(self, column):
        self.column = column

    def predict(self, X):
        return X[self.column].to_numpy()


class QSRBaselineModel(QSRMLModel):
    METHODS = {"seasonal_naive": "lag_7", "moving_average": "roll_mean_7"}

    def __init__(self, connector=None, method="seasonal_naive"):
        super().__init__(connector)
        self.method = method
        self.model_name = {"seasonal_naive": "SeasonalNaive_7", "moving_average": "MovingAverage_7"}[method]

    def processTrain(self, columns_input=None, column_target=None):
        return super().processTrain(columns_input=[self.METHODS[self.method]])

    def fitModel(self, X_train, y_train, X_val, y_val):
        column = self.METHODS[self.method]
        return ColumnModel(column), {"column": column}
