# VMD Sizing

本项目是一款用于将 MMD 模型的动作数据（VMD / VPD）从源模型转换并适配到目标模型的工具。

本项目基于原日文版进行汉化，现已提供简体中文版。

## 从源码打包 exe

完整流程分三步：**准备环境 → 编译 Cython 扩展 → PyInstaller 打包**。

### 第 1 步：准备环境

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

产物：`dist\VmdSizing_5.01.08_CN_1.0.0_64bit.exe`
