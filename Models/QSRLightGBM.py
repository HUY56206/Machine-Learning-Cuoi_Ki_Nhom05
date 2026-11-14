import lightgbm as lgb

from Models.QSRMLModel import QSRMLModel
from Utils import Config


class QSRLightGBM(QSRMLModel):
    model_name = "lightgbm"
    categorical_mode = "category"

    PARAMS = dict(
        objective="tweedie", tweedie_variance_power=1.2,
        n_estimators=3000, learning_rate=0.05, num_leaves=127, min_child_samples=50,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
        random_state=Config.RANDOM_STATE, n_jobs=-1, verbose=-1,
    )
    EARLY_STOPPING = 100

    def __init__(self, connector=None, fast=False):
        super().__init__(connector)
        self.fast = fast

    def fitModel(self, X_train, y_train, X_val, y_val):
        params = {**self.PARAMS, **({"n_estimators": 300} if self.fast else {})}
        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], eval_metric="l1",
                  callbacks=[lgb.early_stopping(self.EARLY_STOPPING), lgb.log_evaluation(200)])
        return model, {**params, "best_iteration": model.best_iteration_}
