class TrainedModel:
    """Gói mô hình đã train cùng thông tin cần để tái sử dụng (bước 9 - lưu mô hình).

    Không lưu X_train / X_test vào file vì dữ liệu hơn 1 triệu dòng - khi cần thì
    nạp lại từ MySQL.
    """

    def __init__(self, model=None, model_name=None, columns_input=None, column_target=None,
                 categorical_columns=None, categories=None, trained_until=None, params=None):
        self.model = model
        self.model_name = model_name
        self.columns_input = columns_input
        self.column_target = column_target
        self.categorical_columns = categorical_columns or []
        self.categories = categories or {}       # danh mục giá trị của từng biến phân loại
        self.categorical_mode = "str"            # "str" | "category" (LightGBM)
        self.trained_until = trained_until
        self.params = params or {}
        self.metrics = []                        # list MetricsResult (val, test)
        self.residual_rmse = None                # RMSE theo (nhà hàng, món) trên val -> Safety Stock
