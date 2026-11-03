"""CatBoost Regressor - xử lý trực tiếp biến phân loại (nhà hàng, món, thời tiết)."""
from catboost import CatBoostRegressor

from Models.QSRMLModel import QSRMLModel
from Utils import Config


class QSRCatBoost(QSRMLModel):
    model_name = "catboost"
    categorical_mode = "str"

    PARAMS = dict(
        loss_function="RMSE", iterations=3000, learning_rate=0.08, depth=8,
        random_seed=Config.RANDOM_STATE, thread_count=-1, verbose=200,
        od_type="Iter", od_wait=100,
        train_dir=str(Config.ASSETS_DIR / "catboost_info"),
    )

    def __init__(self, connector=None, fast=False):
        super().__init__(connector)
        self.fast = fast        # True: 300 vòng để chạy thử nhanh

    def fitModel(self, X_train, y_train, X_val, y_val):
        params = {**self.PARAMS, **({"iterations": 300} if self.fast else {})}
        model = CatBoostRegressor(**params, cat_features=self.trainedmodel.categorical_columns)
        model.fit(X_train, y_train, eval_set=(X_val, y_val), use_best_model=True)
        return model, {**params, "best_iteration": model.get_best_iteration()}
