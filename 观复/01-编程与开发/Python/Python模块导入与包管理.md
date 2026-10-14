# Python `import`、`module`、`package` 与包管理

> **先修**：[[Python语言核心]]。
> 视频：[【Python】一个视频弄明白 import、package、module 包管理](https://b23.tv/06pMibp)  
> 作者：隔壁的程序员老王  
> 发布日期：2024-08-16  
> 时长：约 15 分 40 秒  
> 整理方式：依据视频音频识别，并对术语、代码拼写和层级结构进行了校正。
> **核验状态**：未核验——依视频音频识别整理，未与原始视频逐句比对，导入机制未逐条对照官方文档。2026-10-02 新增第13节按 Python、PowerShell 与 uv 官方资料文档核对；前12节的视频来源仍未逐句核对。详见 [[知识库质量审计]]。

## 一句话总结

Python 的导入过程可以理解为：**查找模块 → 必要时执行模块代码并创建模块对象 → 缓存模块对象 → 在当前命名空间绑定一个名字**。包则是一种可以包含子模块、子包的模块组织形式。

## 1. 模块是什么

一个普通的 `.py` 文件可以作为模块。例如：

```python
# mymath.py
PI = 3.14

def add(a, b):
    return a + b
```

在同一目录的 `main.py` 中导入：

```python
import mymath

print(mymath.add(1, 2))  # 3
print(mymath.PI)         # 3.14
```

`mymath` 不是一个特殊关键字，而是当前命名空间中的一个变量；它指向 Python 创建的模块对象：

```python
print(type(mymath))
# <class 'module'>
```

模块对象保存了该模块的全局命名空间。因此，`mymath.py` 中定义的函数、常量等，可以通过 `mymath.add`、`mymath.PI` 访问。

```python
print(dir(mymath))
```

`dir()` 可以查看模块命名空间中已有的名称。

## 2. `import` 做了什么

执行下面的语句时：

```python
import mymath
```

可以用四步理解：

1. Python 查找名为 `mymath` 的模块或包。
2. 检查它是否已经被导入并缓存。
3. 若尚未导入，则创建模块对象，并执行模块中的顶层代码。
4. 在当前命名空间中，将名称 `mymath` 绑定到该模块对象。

> 更严谨地说，已导入的模块通常缓存在 `sys.modules` 中。再次导入时，一般会复用已有模块对象，而不会重新执行模块的顶层代码。

### 验证：同一模块通常只执行一次

```python
# mymath.py
print("mymath is running")
```

```python
# main.py
import mymath as mm1
import mymath as mm2

print(id(mm1) == id(mm2))  # True
```

现象：

- `mymath is running` 只打印一次；
- `mm1` 和 `mm2` 指向同一个模块对象。

如果确实需要重新执行模块，可使用 `importlib.reload()`；普通的重复 `import` 不会这样做。

## 3. 导入别名：`as`

```python
import mymath as mm

print(mm.add(1, 2))
```

这里当前命名空间中得到的是 `mm`，而不是 `mymath`：

```python
print(type(mm))      # <class 'module'>
# print(mymath.PI)   # NameError
```

`as` 只是改变当前绑定的名称，不会创建另一份模块，也不会复制模块内容。

## 4. `import module` 与 `from module import name`

### 导入模块对象

```python
import mymath
print(mymath.PI)
```

当前命名空间中绑定的是模块名 `mymath`。

### 从模块中导入名称

```python
from mymath import PI
print(PI)
```

Python 仍然需要加载 `mymath`，但当前命名空间直接绑定了 `PI`，不必写 `mymath.PI`。

### 为什么重新赋值互不影响

```python
from mymath import PI
import mymath

PI = 9999

print(PI)         # 9999
print(mymath.PI)  # 3.14
```

`from mymath import PI` 将当前名称 `PI` 绑定到导入时取得的对象。后续让当前名称 `PI` 指向另一个对象，不会改动 `mymath.PI`。

再次执行：

```python
from mymath import PI
```

会重新取得当前的 `mymath.PI`，并让当前名称 `PI` 再次指向它。

> 视频用“复制”帮助理解。更准确的 Python 表述是“名称绑定”：复制的是对象引用关系，并不一定复制对象本身。

## 5. 模块的全局命名空间

模块对象可视为模块代码运行时使用的全局命名空间。

如果模块在运行过程中新增全局名称，该名称也会出现在模块对象上：

```python
# mymath.py
def add_global(name, value):
    globals()[name] = value
```

```python
import mymath

mymath.add_global("foo", "bar")
print(mymath.foo)  # bar
```

这说明模块中的全局状态会保存在模块对象里，并被所有引用该模块对象的地方共享。

## 6. Python 从哪里查找模块

Python 会依据导入系统的规则，在搜索路径中查找模块。常用的观察入口是：

```python
import sys
print(sys.path)
```

`sys.path` 通常包含：

- 启动脚本所在目录，或当前执行环境对应的首项；
- 标准库目录；
- 第三方包目录，例如 `site-packages`；
- 环境或启动配置追加的目录。

因为 `sys.path` 是列表，所以可以在运行时修改：

```python
import sys
sys.path.append("/path/to/modules")
```

也可以通过环境变量 `PYTHONPATH` 向模块搜索路径追加目录。

### 实践建议

- 临时实验可以修改 `sys.path`；
- 正式项目更适合使用规范的包结构、虚拟环境和可安装项目配置；
- 避免在业务代码中到处手动拼接搜索路径，否则代码会依赖具体机器的目录结构。

## 7. 包是什么

包（package）是组织模块和子包的目录结构。例如：

```text
mydir/
├── __init__.py
├── a.py
└── subdir/
    ├── __init__.py
    └── b.py
```

导入包时：

```python
import mydir
```

`mydir` 同样是模块对象。如果存在 `mydir/__init__.py`，其顶层代码会在包首次加载时执行。

### `__init__.py` 是否必需

- 对传统的普通包，通常使用 `__init__.py`；
- Python 3.3 起支持隐式命名空间包，因此目录即使没有 `__init__.py`，在满足导入路径条件时也可能被导入；
- 没有 `__init__.py` 时，不会有该初始化文件可执行，但仍会创建相应的包模块对象。

实际项目中，是否省略 `__init__.py` 应是有意识的结构设计，而不只是为了少写一个空文件。

### 同名模块文件与包目录

若同一搜索路径位置同时存在：

```text
mymath.py
mymath/
└── __init__.py
```

导入解析可能优先命中普通包目录。不要依赖这种同名竞争关系；项目中应避免模块文件与包目录同名。

## 8. 子包导入

### 完整导入路径

```python
import mydir.subdir

print(mydir)
print(mydir.subdir)
```

可以理解为：

1. 当前命名空间中绑定 `mydir`；
2. `subdir` 作为属性绑定到 `mydir` 包对象上。

### 直接导入子包名称

```python
from mydir import subdir

print(subdir)
```

这会把 `subdir` 直接绑定到当前命名空间；与此同时，加载后的子包通常也可通过 `mydir.subdir` 关联到父包。

两种写法的主要差异是当前代码中使用的名称：

| 写法 | 当前命名空间中的主要名称 | 使用方式 |
|---|---|---|
| `import mydir.subdir` | `mydir` | `mydir.subdir` |
| `from mydir import subdir` | `subdir` | `subdir` |

## 9. 绝对导入与相对导入

假设目录结构如下：

```text
mydir/
├── __init__.py
├── a.py
└── subdir/
    └── __init__.py
```

在 `mydir/a.py` 中导入同一包下的 `subdir`：

### 绝对导入

```python
import mydir.subdir
```

绝对导入从顶层包名开始书写，路径直观、全局含义明确。

### 相对导入

```python
from . import subdir
```

相对导入中的点按当前模块所属的包来解释：

- `.`：当前包；
- `..`：父包；
- `...`：再上一层。

示例：

```python
from . import subdir
from .. import sibling_package
```

相对导入依赖“包上下文”，因此包内模块通常应通过模块方式运行：

```bash
python -m mydir.a
```

直接执行包内文件（如 `python mydir/a.py`）时，可能因缺失正确的包上下文而导致相对导入失败。

## 10. 概念对照表

| 概念 | 本质 | 典型形式 |
|---|---|---|
| 模块（module） | 运行后对应一个模块对象及其全局命名空间 | `mymath.py` |
| 包（package） | 能容纳子模块、子包的模块组织形式 | `mydir/` |
| 普通包 | 通常具有 `__init__.py` | `mydir/__init__.py` |
| 命名空间包 | 可不含 `__init__.py`，可跨多个路径组成 | 多个同名目录共同形成包 |
| `import x` | 将名称 `x` 绑定到模块或顶层包 | `import mymath` |
| `import x as y` | 将模块绑定为别名 `y` | `import numpy as np` |
| `from x import y` | 将模块 `x` 中的名称 `y` 绑定到当前命名空间 | `from math import pi` |
| `sys.path` | 导入系统使用的重要搜索路径列表 | 脚本目录、标准库、`site-packages` 等 |
| `PYTHONPATH` | 向模块搜索路径追加目录的环境变量 | 临时配置额外模块目录 |
| `sys.modules` | 已加载模块的缓存映射 | 避免普通重复导入时再次执行模块 |

## 11. 常见误区

### 误区 1：`import` 只是把源码文本粘贴进当前文件

不是。模块拥有独立的模块对象和全局命名空间，当前代码只是绑定并使用相应名称。

### 误区 2：重复 `import` 会重复运行模块全部代码

通常不会。已加载模块会从 `sys.modules` 复用。

### 误区 3：`from x import y` 会让 `y` 永远和 `x.y` 同步

不会。两边是不同命名空间中的名称绑定；任一边重新赋值，不会自动让另一边同步。

### 误区 4：目录没有 `__init__.py` 就绝对不是包

对现代 Python 不准确。Python 3.3+ 支持隐式命名空间包。

### 误区 5：修改 `sys.path` 是组织大型项目的首选方案

不建议。它适合调试或特殊启动场景，正式项目应优先采用清晰的包结构和标准安装方式。

## 12. 复习清单

- [ ] 我能解释模块对象与模块全局命名空间的关系。
- [ ] 我知道普通重复导入为什么不会重复执行模块代码。
- [ ] 我能区分 `import x`、`import x as y` 和 `from x import y`。
- [ ] 我知道 `sys.path`、`PYTHONPATH` 和 `sys.modules` 分别解决什么问题。
- [ ] 我能区分普通包与命名空间包。
- [ ] 我能正确使用子包导入、绝对导入和相对导入。
- [ ] 我知道包内相对导入失败时，应检查模块的启动方式与包上下文。

## 13. PATH、sys.path 与包位置：三张不同的地图

### 找工具、找解释器、找代码库

`PATH` 是 Shell 找可执行命令的目录表；`sys.path` 是**已经启动的 Python** 导入模块时使用的路径列表。它们处于不同阶段：先通过 PATH 等规则找到 Python，再由这个 Python 的导入系统找模块。

在 PowerShell：

~~~powershell
Get-Command uv -All
where.exe python
python -c "import sys; print(sys.executable)"
python -m pip show pandas
python -c "import pandas; print(pandas.__file__)"
~~~

`where.exe` 明确运行 Windows 外部程序，避免 PowerShell 的 `where` 别名被解释成 `Where-Object`。在 CMD 里可写 `where python`。即便 PATH 查找结果没错，PowerShell 的别名或函数也可能优先，`Get-Command` 与实际启动后的 `sys.executable` 更直接。

`pip show pandas` 的 `Location` 是分发安装目录；`pandas.__file__` 通常是这次导入的模块文件。它们回答的问题不同：当前目录里有同名 `pandas.py` 时，导入可能被遮蔽。`where pandas` 没找到 CLI 也不能证明没装 pandas。

需要核对项目环境时，将以上 Python 调用换成 `uv run python ...`；uv 的默认环境没有 pip，可用：

~~~powershell
uv pip show --python .\.venv\Scripts\python.exe pandas
uv run python -c "import pandas; print(pandas.__file__)"
~~~

`__file__` 两侧各有**两个下划线**；原稿的 `pandas.file`、`uv.file` 不是等价属性。有些内置模块、命名空间包没有通常意义上的 `__file__`，不能要求所有模块都具备它。

### 逐项读懂 Anaconda 的 sys.path 样例

在 Python 交互解释器或脚本里输入：

~~~python
import sys
import pprint
from pathlib import Path

print(sys.executable)
print(sys.prefix)
print(sys.base_prefix)
pprint.pp(sys.path)
print(Path.cwd())
~~~

`pprint.pp` 自 Python 3.8 引入，默认保留字典插入顺序；`pprint.pprint` 默认对字典键排序。要得到字符串而不立即打印，用 `pprint.pformat(sys.path)`。[pprint 官方文档](https://docs.python.org/3/library/pprint.html)

以原稿中的 `C:\Anaconda` 为例，路径须按当前机器实况解读：

| 路径项 | 可能的用途 | 不应推出的结论 |
| --- | --- | --- |
| `''` | 常见交互模式或 `-c` 的当前工作目录搜索入口 | 不等于永远是脚本目录，也不保证永远第一项 |
| `C:\Anaconda\python313.zip` | 标准库 zip 的候选搜索位置 | 列入路径不证明文件存在或标准库都已打包 |
| `C:\Anaconda\DLLs` | Windows Python 扩展模块等搜索位置 | 不是 PATH，也不能由此列出所有 DLL 的加载来源 |
| `C:\Anaconda\Lib` | 常见标准库目录 | 不是项目第三方包的同义词 |
| `C:\Anaconda` | 该发行版启动时纳入的根搜索位置 | 不代表所有全局配置都从这里导入 |
| `...\Lib\site-packages` | 第三方分发常见安装位置 | 仅适用于这个实际解释器和它的站点配置 |
| `...\site-packages\win32`、`win32\lib`、`Pythonwin` | 可能由 pywin32 的安装或站点配置追加 | 不代表所有 Anaconda 都必带这些项 |

直接执行 `python path/to/main.py` 时，常见首项是脚本目录；交互模式的空字符串代表当前工作目录；`-I`、`-P`、`._pth`、站点配置等可改变初始化。PATH 查到的解释器列表与此列表不是一回事。[sys.path 初始化规则](https://docs.python.org/3/library/sys_path_init.html)

“从列表第一项一直找”是理解常见文件模块的近似；真实导入还涉及 `sys.modules`、内置／冻结模块、`sys.meta_path` 查找器等。已经缓存的模块不必再完整遍历目录。

### 为什么 Scripts 里有 uv.exe，却没有 pandas.exe

`Scripts`／`bin` 放环境的可执行入口；`site-packages` 放可导入分发。一个分发可以既提供 Python 模块，又提供 CLI；两者名称不一定相同。pandas 常用方式是代码中的 `import pandas`，找库应让目标 Python 定位它。

也不能把所有 CLI 都概括为“EXE 调 Python 源码”：black 常见安装有 Python 命令入口，uv 的核心则是 Rust 编译的原生工具，pip 分发可以携带二进制与包装模块。`import uv` 存在时，不能据此把它认定为稳定的 Python 环境管理库 API。独立安装 uv 不需要在项目里再 `pip install uv`。

路径也依发行形式变化：Windows venv 的 Python 入口常在 `Scripts\python.exe`；官方基础安装、Conda 环境的 `python.exe` 常在其环境根目录。`Scripts` 并不是所有 Python 解释器的统一住所。

~~~powershell
python -m pip show uv
Get-Command uv -All
~~~

这两条分别定位这个 Python 下的 pip 分发与 Shell 找到的工具，结果可能来自不同安装。想移除 pip 安装的 uv，必须对准原安装解释器，而不是凭一个目录名直接删文件。参看 [[uv项目管理与Windows配置#从 pip 安装的 uv 切换到独立安装]]。

