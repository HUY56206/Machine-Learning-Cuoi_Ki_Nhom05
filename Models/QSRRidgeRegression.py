from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from Models.QSRMLModel import QSRMLModel
from Utils import Config


class QSRRidgeRegression(QSRMLModel):
    model_name = "ridge"
    categorical_mode = "str"
    ALPHAS = [0.1, 1.0, 10.0, 100.0]

    def buildPipeline(self, alpha):
        numeric = [c for c in self.trainedmodel.columns_input if c not in self.trainedmodel.categorical_columns]
        return Pipeline([
            ("prep", ColumnTransformer([
                ("cat", OneHotEncoder(handle_unknown="ignore"), self.trainedmodel.categorical_columns),
                ("num", StandardScaler(), numeric),
            ])),
            ("ridge", Ridge(alpha=alpha, random_state=Config.RANDOM_STATE)),
        ])

    def fitModel(self, X_train, y_train, X_val, y_val):
        best, best_alpha, best_score = None, None, float("inf")
        for alpha in self.ALPHAS:
            pipe = self.buildPipeline(alpha).fit(X_train, y_train)
            pred = pipe.predict(X_val).clip(0)
            score = abs(pred - y_val.to_numpy()).sum() / abs(y_val.to_numpy()).sum()
            print(f"Ridge alpha={alpha:<6} val wMAPE (trên quantity đã làm sạch)={score:.4f}")
            if score < best_score:
                best, best_alpha, best_score = pipe, alpha, score
        return best, {"alpha": best_alpha}
