from Models.QSRMLModel import QSRMLModel


class ColumnModel:

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
