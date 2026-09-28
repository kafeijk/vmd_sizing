# VMD适配（VMDサイジング）

把某个 MMD 模型（源模型）的动作数据（VMD / VPD），转换适配到另一个模型（目标模型）上的工具。
本项目已由日文版汉化为**简体中文版**。

## 功能标签页

| 标签页 | 说明 |
| --- | --- |
| 文件 | 指定待适配 VMD / 源模型 PMX / 目标模型 PMX 与输出 VMD，执行适配 |
| 多个 | 多人动作同时适配 |
| 表情 | 表情（モーフ）替换设置 |
| 手臂 | 接触规避、手腕/手指/地面位置对齐 |
| 腿部 | 整体移动量修正、腿IK偏移 |
| 相机 | 相机动作适配、全长Y偏移 |
| 批量 | 用 CSV 批量连续执行 |
| CSV | VMD ⇄ CSV 相互转换 |
| VMD | CSV 转回 VMD |

## 运行环境

- Windows 64 位、Visual Studio 2022（需要 C++ 桌面开发工作负载，提供 cl.exe / rc.exe）
- 依赖：numpy、wxPython、numpy-quaternion、bezier、pywin32、PyInstaller
- 编译扩展需要 **Cython 0.29.x**（见下）

## 直接运行（已打包）

双击运行：

```
dist\VmdSizing_5.01.08_CN_1.0.0_64bit.exe
```

## 从源码运行

已提供 conda 环境 `vmdsizing_cn`（Python 3.10），批处理脚本如下：

```
run_gui.bat       启动图形界面
run_debug.bat     以调试模式启动（输出详细日志）
pyinstaller64.bat 编译 Cython 扩展并打包生成 exe
```

也可以手工执行：

```bash
conda activate vmdsizing_cn
python src/executor.py --out_log 1 --verbose 20 --is_saving 1
```

## 从源码打包 exe

完整流程分三步：**准备环境 → 编译 Cython 扩展 → PyInstaller 打包**。

### 第 1 步：准备环境（只需做一次）

```bat
conda create -n vmdsizing_cn python=3.10 pip
conda activate vmdsizing_cn

pip install "numpy<2" "cython==0.29.37" wxPython numpy-quaternion bezier pyinstaller pywin32
```

> ⚠️ **Cython 必须是 0.29.x，不能用 3.x。**
> Cython 3 默认开启 `annotation_typing`，会把 `qq4calc: MQuaternion` 这类注解当成
> 真实静态类型，导致传 `None` 时抛
> `TypeError: Argument 'qq4calc' has incorrect type (expected ...MQuaternion, got NoneType)`。
> 本项目大量回调正是这么用的，用 Cython 3 编译后**一读模型就崩**，且编译期无任何报错。
> （项目 `command.txt` 里原作者也 pin 了 `cython==0.29.21`。）

### 第 2 步：编译 Cython 扩展

必须在**已加载 MSVC 环境的命令行**里执行。最省事的做法是从开始菜单打开
**“x64 Native Tools Command Prompt for VS 2022”**，然后：

```bat
conda activate vmdsizing_cn
cd C:\Users\pan\PycharmProjects\vmd_sizing\src
python setup_install.py build_ext --inplace
```

若用的是普通命令行，需先手动加载编译环境：

```bat
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
conda activate vmdsizing_cn
cd src
python setup_install.py build_ext --inplace
```

成功后会在 `src` 下生成 15 个 `.pyd`（`module\MMath.*.pyd`、`mmd\PmxData.*.pyd` 等）。

> 改动过 `.pyx` 后如果想强制重新生成 C 代码，删掉 `src\build\` 下的对应 `.c` 再编译即可
> （或直接删掉整个 `src\build` 目录重新编译）。

### 第 3 步：打包

回到项目根目录执行：

```bat
cd ..
pyinstaller vmdising_np64.spec
```

产物：`dist\VmdSizing_5.01.08_CN_1.0.0_64bit.exe`（约 35 MB，单文件）。

### 修改版本号

界面左上角标题栏显示的版本号来自 `src/executor.py` 的常量：

```python
VERSION_NAME = "ver5.01.08_CN_1.0.0"
```

改这里即可（命令行模式另有一处同名常量在 `src/vmd_sizing_cli.py`，建议同步修改）。
该版本号同时会写入输出文件与日志的「exe版本」记录中，不只是显示用。

exe 文件名由 `vmdising_np64.spec` 里的 `name='VmdSizing_5.01.08_CN_1.0.0_64bit'` 决定，
改名后旧的同名 exe 会留在 `dist\` 里，需手动删除。

### 一步到位

也可以直接双击 `pyinstaller64.bat`（已包含上面第 2、3 步）。

### 打包常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| `KeyError: 'Data'` | spec 里 datas 的类型码必须大写 `DATA`（PyInstaller 6 起的要求） |
| 运行时 `ModuleNotFoundError: utils.MFileutils` | `utils/__init__.py` 用的是惰性导出，PyInstaller 静态分析不到，必须在 spec 的 `hiddenimports` 里显式列出 |
| `LNK1158: cannot run rc.exe` | PATH 里缺 Windows SDK 的 `bin\10.0.xxxxx.0\x64` |
| `np.float` 相关 AttributeError | NumPy ≥1.24 已移除该别名，代码里已改为内建 `float` / `int` |
| 启动时报 `utils` 导入错误 | `src\utils\__init__.py` 不能为空，它提供 `MFileUtils` 等子模块别名 |

## 汉化说明（重要）

本工具读取的 PMX/VMD 文件里，**骨骼名、表情名、刚体名一律是日文**，
属于与文件匹配的数据，不能翻译，因此：

- 骨骼名（センター、グルーブ、左足ＩＫ、つま先、左親指０ …）保持日文原样；
- 输出的 CSV 表头保持日文原样（文件以 cp932 编码写出，多数简体字无法编码）；
- 内部用于跨模块读写的处理名（如 スタンス追加補正、モーフ置換）也保持原样。

已翻译的部分：全部界面文字、日志与提示信息，以及绝大部分代码注释。

## 许可

见 `LICENCE`。
