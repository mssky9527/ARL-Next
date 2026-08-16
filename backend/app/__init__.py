import warnings

# 关闭警告
warnings.filterwarnings("ignore", category=UserWarning,
                        message="Python 3.6 is no longer supported by the Python core team")

# 关闭高权限使用celery警告
warnings.filterwarnings("ignore", category=UserWarning,
                        message="You're running the worker with superuser privileges")

# 修复高版本 Numpy 移除 float、int、object 等属性导致旧版 openpyxl 报错的问题
try:
    import numpy as np
    if not hasattr(np, 'float'):
        np.float = float
    if not hasattr(np, 'int'):
        np.int = int
    if not hasattr(np, 'object'):
        np.object = object
    if not hasattr(np, 'bool'):
        np.bool = bool
except ImportError:
    pass
