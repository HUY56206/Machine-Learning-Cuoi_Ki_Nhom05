class TrainedModel:

    def __init__(self, model=None, model_name=None, columns_input=None, column_target=None,
                 categorical_columns=None, categories=None, trained_until=None, params=None):
        self.model = model
        self.model_name = model_name
        self.columns_input = columns_input
        self.column_target = column_target
        self.categorical_columns = categorical_columns or []
        self.categories = categories or {}
        self.categorical_mode = "str"
        self.trained_until = trained_until
        self.params = params or {}
        self.metrics = []
        self.residual_rmse = None
