# -*- coding: utf-8 -*-
"""utils 包的便捷导出。

项目里大量使用 ``from utils import MFileUtils`` 这类写法，而实际上
``MFileUtils`` / ``MFormUtils`` / ``MBezierUtils`` / ``MServiceUtils``
都是**子模块**的别名（例如 ``MFileUtils.read_history(...)``）。

这里采用 PEP 562 的模块级惰性 ``__getattr__`` 而不是在包初始化时直接 import，
原因是存在循环依赖：
    utils.MServiceUtils -> module.MOptions -> utils.MFileUtils
若在包初始化阶段就 import MServiceUtils，而外部又先从 module.MOptions 进入，
就会因为 module.MOptions 尚未初始化完成而 ImportError。
惰性导入把解析推迟到真正访问属性时，从而打破循环。
"""

__all__ = ["MFileUtils", "MFormUtils", "MBezierUtils", "MServiceUtils"]

# 属性名 -> 实际子模块名
_LAZY_MODULES = {
    "MFileUtils": "utils.MFileutils",       # 注意：文件名是 MFileutils（小写 u）
    "MFormUtils": "utils.MFormUtils",
    "MBezierUtils": "utils.MBezierUtils",
    "MServiceUtils": "utils.MServiceUtils",
}


def __getattr__(name):
    if name in _LAZY_MODULES:
        import importlib

        return importlib.import_module(_LAZY_MODULES[name])

    raise AttributeError("module {0!r} has no attribute {1!r}".format(__name__, name))
