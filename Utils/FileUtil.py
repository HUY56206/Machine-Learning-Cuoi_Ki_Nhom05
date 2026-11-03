import traceback
from pathlib import Path

import joblib

from Utils import Config


class FileUtil:
    @staticmethod
    def saveModel(model, filename):
        """Lưu mô hình vào thư mục Assets. Trả về True nếu thành công."""
        try:
            path = Path(filename)
            if not path.is_absolute():
                path = Config.ASSETS_DIR / path
            path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, path)
            return True
        except:
            traceback.print_exc()
            return False

    @staticmethod
    def loadModel(filename):
        try:
            path = Path(filename)
            if not path.is_absolute():
                path = Config.ASSETS_DIR / path
            return joblib.load(path)
        except:
            traceback.print_exc()
            return None
