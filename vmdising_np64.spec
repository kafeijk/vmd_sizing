# -*- coding: utf-8 -*-
# -*- mode: python -*-
# VMD适配 64bit版（PyInstaller 6.x 适配：Data 类型码需大写 DATA）

block_cipher = None


a = Analysis(['src\\executor.py'],
             pathex=[],
             binaries=[],
             datas=[],
             # utils 包使用惰性 __getattr__ 导出子模块别名，PyInstaller 静态分析不到，需显式声明
             hiddenimports=['pkg_resources', 'wx._adv', 'wx._html', 'bezier', 'quaternion', 'module.MParams', \
                            'utils.MFileutils', 'utils.MFormUtils', 'utils.MBezierUtils', 'utils.MServiceUtils', \
                            'utils.MLogger', 'utils.MException'],
             hookspath=[],
             runtime_hooks=[],
             # scipy 是 numpy-quaternion 的安装依赖，但本项目与 bezier 实际用到的路径
             # （Curve 构造/evaluate/intersect、四元数基本运算）都不需要它，排除可省约 20MB
             excludes=['mkl','libopenblas', 'tkinter', 'win32comgenpy', 'traitlets', 'PIL', 'IPython', 'pydoc', 'lib2to3', 'pygments', 'matplotlib', 'scipy'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
a.datas += [('src\\vmdsizing.ico', '.\\src\\vmdsizing.ico', 'DATA')]
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='VmdSizing_5.01.08_CN_1.0.0_64bit',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False,
          icon='.\\src\\vmdsizing.ico')

