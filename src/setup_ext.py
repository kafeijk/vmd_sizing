from setuptools import Extension
from numpy import get_include   # 为了使用 cimport numpy
import os
import site

# bezier 的 wheel 版本不附带 C 头文件（include 目录）。
# 本项目只使用 Python 层的 bezier.Curve API，因此只需把 site-packages 加入头文件搜索路径即可。
try:
    _sp = site.getsitepackages()
    bezier_path = next((p for p in _sp if os.path.isdir(os.path.join(p, "bezier"))), _sp[0])
except Exception:
    bezier_path = os.getcwd()

kwargs = {"output_dir": "./build/output", "build_dir": "./build/"}


def get_ext():
    ext = []
    sources = ["module\\MMath.pyx", "module\\MOptions.pyx", "module\\MParams.pyx", \
               "utils\\MLogger.py", "utils\\MBezierUtils.pyx", "utils\\MServiceUtils.pyx", \
               "mmd\\VmdData.pyx", "mmd\\VmdReader.py", "mmd\\PmxData.pyx", "mmd\\PmxReader.py", \
               "service\\parts\\StanceService.pyx", "service\\parts\\ArmAvoidanceService.pyx", "service\\parts\\ArmAlignmentService.pyx", \
               "service\\parts\\CameraService.py", "service\\parts\\MoveService.py"]
    # for path in glob.glob("*/**/*.pyx", recursive=True):
    #     if os.path.isfile(path):
    #         print(path)
    #         sources.append(path)
    # for path in glob.glob("*/**/*.py", recursive=True):
    #     if "__init__" not in path and os.path.isfile(path):
    #         sources.append(path)

    for source in sources:
        path = source.replace("\\", ".").replace(".pyx", "").replace(".py", "")
        print("%s -> %s" % (source, path))
        ext.append(Extension(path, sources=[source], include_dirs=['.', bezier_path, get_include()], define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]))
    
    return ext

# ext = [Extension("module.MMath", sources=["module/MMath.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("module.MMath", sources=["module/MMath.py"], include_dirs=['.', bezier_path, get_include()], define_macros=[('CYTHON_TRACE', '1')]), \
#        Extension("module.MParams", sources=["module/MParams.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("module.MOptions", sources=["module/MOptions.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("utils.MBezierUtils", sources=["utils/MBezierUtils.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("utils.MLogger", sources=["utils/MLogger.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("utils.MServiceUtils", sources=["utils/MServiceUtils.py"], include_dirs=['.', bezier_path, get_include()], define_macros=[('CYTHON_TRACE', '1')]), \
#        Extension("utils.MServiceUtils", sources=["utils/MServiceUtils.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("mmd.PmxData", sources=["mmd/PmxData.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("mmd.PmxReader", sources=["mmd/PmxReader.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("mmd.VmdData", sources=["mmd/VmdData.py"], include_dirs=['.', bezier_path, get_include()], define_macros=[('CYTHON_TRACE', '1')]), \
#        Extension("mmd.VmdData", sources=["mmd/VmdData.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("mmd.VmdReader", sources=["mmd/VmdReader.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("mmd.VpdReader", sources=["mmd/VpdReader.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("mmd.VmdWriter", sources=["mmd/VmdWriter.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("service.parts.MoveService", sources=["service/parts/MoveService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("service.parts.CameraService", sources=["service/parts/CameraService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("service.parts.MorphService", sources=["service/parts/MorphService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("service.parts.StanceService", sources=["service/parts/StanceService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("service.parts.ArmAvoidanceService", sources=["service/parts/ArmAvoidanceService.py"], include_dirs=['.', bezier_path, get_include()], define_macros=[('CYTHON_TRACE', '1')]), \
#        Extension("service.parts.ArmAvoidanceService", sources=["service/parts/ArmAvoidanceService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("service.parts.ArmAlignmentService", sources=["service/parts/ArmAlignmentService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        Extension("service.SizingService", sources=["service/SizingService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        # Extension("service.ConvertSmoothService", sources=["service/ConvertSmoothService.py"], include_dirs=['.', bezier_path, get_include()]), \
#        ]


