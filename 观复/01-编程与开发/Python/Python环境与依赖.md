# Python 环境与依赖

> 适用范围：Python 3.11 及以上的日常项目。命令以 PowerShell 为例；在服务器上应按 Linux 的路径和权限执行。
> **核验状态**：部分实测——2026-10-01 用 Windows x64、uv 0.12.12、Python 3.12.14 验证 uv 项目环境创建、解释器定位及锁一致性检查；另在 Python 3.13.14 确认 `pprint.pp` 存在、虚拟环境内 `pip --user` 被拒绝、本机未安装官方 `py` 启动器、`where python` 命中 WindowsApps 别名。2026-10-02 补回两份 Word 的概念和排错流程，并按 Python、pip、uv、Conda 官方资料修正；venv/pip 与 Conda 的其余步骤未逐条复跑。详见 [[知识库质量审计]]。

若不确定当前窗口运行的是 CMD、Windows PowerShell 还是 PowerShell 7，先看 [[终端与 Shell]]；同一个终端界面可以运行不同 Shell。

## 背景

一个 Python 项目至少有三层：**解释器**运行代码，**虚拟环境**隔离安装的包，**依赖清单**记录项目需要什么。把虚拟环境想成一间工作室：有自己的工具架，但仍借用大楼的基础设施。它并不是一份完全独立、可以跨系统复制的 Python 安装。

## 问题：到底调用了哪个 Python

遇到“已安装却无法导入”，先定位实际解释器，而不是反复安装。

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
Get-Command python
```

`python -m pip` 让当前解释器执行它对应的 pip，比单独输入 `pip` 更容易避免装错环境。检查 IDE 或 Notebook 时，也要查看其选中的解释器或内核；终端与编辑器未必相同。

### Windows 上到底装了几个 Python

同一台机器可以同时存在官方解释器、Conda 或 uv 管理的解释器，以及每个项目自己的虚拟环境。`python` 只是 PATH 中第一个被找到的入口，不能据它推断“本机只有一个 Python”。

```cmd
where python
python -V
py -0p
```

`where python` 按 PATH 顺序列出所有同名入口，排第一的就是当前实际调用的那个。`py -0p` 由官方的 Python 启动器提供，能列出已注册的解释器版本与路径；**没装官方启动器时该命令不存在**，会得到 `'py' 不是内部或外部命令`，这时改用 `where python` 与 `python -V`。本机 2026-10-01 实测没有 `C:\Windows\py.exe`，`py` 与 `py -0p` 均不可用。

命中 `python.exe` 也不等于命中解释器：Windows 会在 `%LOCALAPPDATA%\Microsoft\WindowsApps\` 放一个应用执行别名，它实际指向 `AppInstallerPythonRedirector.exe`，运行后会跳转微软应用商店。命令直接弹出商店，或版本与预期不符，就说明命中的是这个别名；此时按实际路径调用解释器，或调整 PATH 顺序。

### Shell 命令与 Python 交互解释器不是同一层

在 CMD 或 PowerShell 看到 `C:\...>`、`PS C:\...>` 时，输入的是 Shell 命令；执行 `python` 后看到 `>>>`，已经进入 Python 交互解释器，只能直接输入 Python 语句。`pip list`、`uv sync`、`where python` 等不是 Python 语法，放在 `>>>` 后会得到 `SyntaxError`。退出交互解释器可输入 `exit()`；Windows 控制台也可用 `Ctrl+Z` 后回车。

可以把 Shell 理解为前台调度员，`python` 是被调起的一台机器：在调度台上说“列出包”，应使用 `python -m pip list`；进入机器内部后，则使用 `import`、函数调用等 Python 语句。若确实要从 Python 中检查环境，使用解释器提供的对象，而不是把 Shell 命令原样搬进来：

```python
import importlib.metadata
import sys

print(sys.executable)
print(sys.prefix)
print([(dist.metadata["Name"], dist.version) for dist in importlib.metadata.distributions()])
```

`sys.executable` 回答“当前 Python 在哪里”，`sys.prefix` 帮助判断是否位于虚拟环境；`pprint.pprint(...)` 能把 `sys.path` 这类嵌套结构按行打印，比 `print` 更易读，Python 3.8 起提供 `pprint.pp`，与 `pprint.pprint` 的字典排序默认值不同（`pp` 默认不排序，`pprint` 默认排序）；此前引入版本写成 3.11 的结论有误，已按官方文档修正。模块搜索路径与导入排查统一参看 [[Python模块导入与包管理]]，不要仅凭提示符中的环境名下结论。

### 在 Shell 与交互解释器分别练什么

Shell 指挥程序；进入 `>>>` 后运行 Python 表达式。不要把“进入 Python”理解为自动激活项目虚拟环境；你只是启动了一个解释器进程。

~~~powershell
python --version
python -m pip list
python -m pip show pandas
python -m pip install requests
python -m pip uninstall requests
python main.py
python -m http.server 8000 --bind 127.0.0.1
~~~

这些是普通 Python／pip 路线的独立示例，执行前确认目标环境；不是要在 base 全部执行的初始化清单。`-m` 表示以模块入口运行；HTTP 服务器在这里仅监听本机，服务当前目录文件，按 `Ctrl+C` 停止，不用于生产交付。uv 项目运行命令时在前面加 `uv run`，项目添加／删除依赖用 `uv add`／`uv remove`。

在项目中可输入 `uv run python` 进入交互解释器，再分别试：

~~~python
2 + 3 * 4
"Hello, " + "World"
help(print)
dir("hello")
import sys
print(sys.executable)
import importlib.metadata
print(importlib.metadata.version("pandas"))
exit()
~~~

`help` 看对象文档，`dir` 看名称，`importlib.metadata.version` 查看已安装分发版本。包未安装会报查找错误；它也不保证对应本次导入的源码版本，必要时核对模块 `__file__`。第三方包提供版本属性时，要用正确拼写，例如 `requests.__version__`，而不是 `requests.version`。


## 方案一：标准库 `venv` 与 pip

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pandas
.\.venv\Scripts\python.exe -c "import pandas; print(pandas.__version__)"
```

直接调用环境中的 `python.exe` 不依赖激活脚本。需要交互使用时，可执行 `.\.venv\Scripts\Activate.ps1`；Linux/macOS 的激活路径是 `.venv/bin/activate`。激活只是调整当前 shell 的环境变量，**不是使用虚拟环境的必要条件**。

若 PowerShell 禁止运行激活脚本，可以继续直接调用 `.venv\Scripts\python.exe`。确实需要改变执行策略时，先查看组织策略，再选择仅对当前进程生效的方式；不要为了安装包盲目放宽整台机器的策略。

### 全局环境与用户级安装

单独的 `pip` 由 Shell 定位，可能与 `python` 不对应；`python -m pip` 才明确绑定这个解释器。默认安装目标通常是它的 `site-packages`，`--user`、`--target`、`--prefix` 等会改变位置。所谓“全局”是相对于项目隔离而言，并不意味着所有用户、所有 Python 都共享。业务依赖放项目环境；跨项目 CLI 优先放按工具隔离的环境，避免多个项目的版本要求互相覆盖。想知道某个包装到了哪里，看 `python -m pip show <包名>` 的 `Location`。

只想给自己装一个工具、又不想写入系统目录时，可以用用户级安装：

```powershell
python -m pip install --user httpie
```

它写入当前用户的用户级 `site-packages`，路径通常与 Python 版本等因素有关；启用了该用户站点的解释器可能看到它，同版本的多个安装也可能共享这个位置，所以它只是缩小了影响范围，不等于项目隔离。另外它不能用来救虚拟环境——默认隔离的虚拟环境里执行通常会报 `Can not perform a '--user' install`（本机 3.13.14 实测）。要按工具隔离、又能从任意目录调用，用 `uv tool install`（见 [[uv项目管理与Windows配置]]）。

## 方案二：uv 项目

`pyproject.toml` 声明项目要求，`uv.lock` 记录依赖解析结果，`.venv` 是可重建的本地环境。`uv init` 创建项目声明，后续 `uv add`、`uv sync` 或 `uv run` 按需建立环境；不必把手动创建虚拟环境当成独立的必经步骤。

日常运行用 `uv run`，需要拒绝锁文件自动变化时加 `--locked`。`uv sync` 默认精确同步，会移除锁中没有的额外包；不要把 `.venv` 当作长期存储位置。`uv pip` 操作环境而不维护项目声明与锁文件，不能与 `uv add` 混为一谈。从空电脑开始的完整操作见 [[新电脑用uv管理Python：逐步操作与原理]]；进阶版本选择、网络配置和交付见 [[uv项目管理与Windows配置]]。

**选择规则**：已有 pip 项目先用 `venv`，需要项目级锁定和统一命令时用 uv；若项目明确依赖 Conda 管理的非 Python 包或平台工具链，就沿用 Conda。不要因为工具流行而混用多个环境管理器。

## 常见故障按证据排查

| 现象 | 先检查 | 处理 |
| --- | --- | --- |
| `ModuleNotFoundError` | 解释器路径、包安装位置、模块名是否拼对 | 在目标解释器下安装并复查 |
| 项目搬家后 pip 启动失败 | `.venv` 是否仍指向旧路径 | 用依赖清单重建环境；不要复制旧 `.venv` |
| `Fatal error in launcher: Unable to create process` | 报错中的旧绝对路径、`python -m pip --version`、`.venv\Scripts\python.exe` 是否存在 | 这通常是启动器仍记录旧位置，不是包下载失败；从声明或锁文件重建 `.venv`，不要手改启动器或跨目录复制环境 |
| 提示符同时出现 `(.venv)` 与 `(base)`/`(Py3-12)` | `sys.executable`、`Get-Command python`、`$env:VIRTUAL_ENV` 与 `conda info --envs` | 两个名称只说明激活脚本叠加修改过当前 Shell；以实际解释器路径为准，先逐层退出不需要的环境，再只激活一种管理路线 |
| 在 `>>>` 中输入 `pip list` 报 `SyntaxError` | 当前提示符是否为 Python 交互解释器 | `exit()` 返回 Shell，再执行 `python -m pip list`；交互解释器里只运行 Python 语句 |
| `conda activate` 无效 | Conda 是否安装、shell 是否初始化 | 按 Conda 文档执行对应 shell 的初始化，再重开终端 |
| `'py' 不是内部或外部命令` | 是否安装了官方 Python 启动器（`C:\Windows\py.exe`） | 用 `where python`、`python -V` 代替；确实需要启动器时按实际 Python 安装渠道补装相应启动器或安装管理器，不把 Add to PATH 当成安装启动器的证明 |
| `python` 弹出微软商店或版本不符 | `where python` 的第一条是否为 `…\WindowsApps\` 下的应用执行别名 | 按实际路径调用解释器，或调整 PATH 顺序 |
| `pip freeze` 为空 | 当前环境是否真的装有包 | 查 `python -m pip list`；空清单本身不是错误 |
| 依赖清单含 `@ file:///...` | 是否记录了本机或构建机路径 | 回到项目声明或人工核定依赖，不能简单批量删除后假定完整 |

项目路径包含中文或空格**不是天然错误**；只有特定工具或脚本处理路径有缺陷时才需要调整。排错时看完整报错与实际路径，不要靠经验一概归因。

## 原理：解释器、环境和目录怎样关联

### .venv 里面有什么，没有它能说明什么

在 Windows 中，典型 venv 结构如下：

~~~text
项目/
├── main.py
└── .venv/
    ├── pyvenv.cfg
    ├── Scripts/
    │   ├── python.exe
    │   ├── Activate.ps1
    │   └── activate.bat
    └── Lib/
        └── site-packages/
~~~

`pyvenv.cfg` 记录基础解释器关联和配置；`Scripts` 放环境的解释器入口、激活脚本和安装时产生的 CLI 入口；`site-packages` 是第三方包的安装位置。标准库通常仍来自基础 Python，不是把整个 Python 发行版都完整复制进来。uv 建立的环境默认可以没有 pip；`python -m venv` 的常见默认流程会引导安装 pip，二者不要混淆。[venv 官方说明](https://docs.python.org/3/library/venv.html)

`.venv` 是惯用目录名，不是 Python 的保留字；`venv`、`myenv` 或项目外的绝对路径同样可以作为环境。uv 项目默认在项目根目录用 `.venv`，这也是常见布局，不需要为了“目录干净”一律移到上级。

**项目中看不到 `.venv`，不能推出项目在用全局环境。** 它可能用项目外的 venv、Conda 环境、IDE 指定的解释器，或者尚未执行 uv 同步。反过来，文件夹里存在 `.venv`，也不代表这次 `python` 正在使用它。

确认普通 venv 时：

~~~powershell
python -c "import sys; print(sys.executable); print(sys.prefix); print(sys.base_prefix); print(sys.prefix != sys.base_prefix)"
~~~

`sys.executable` 给实际程序路径；`sys.prefix` 是当前环境前缀；`sys.base_prefix` 是基础 Python 前缀。普通 venv 中二者通常不同；**这项比较不是识别所有 Conda 环境的万能判据**。Conda 另看 `CONDA_PREFIX`、`conda info --envs` 和实际解释器路径。

虚拟环境像项目专用工具架，隔离的是依赖查找与安装位置，不是操作系统权限；它仍能访问你有权限访问的文件。`--system-site-packages`、手工 `PYTHONPATH` 等也可能改变包可见性，所以不能说“有 venv 就绝对不会看到外部包”。

### 为什么同一台电脑能有多个 Python

“官方安装”“Anaconda 安装”“uv 管理”描述的是发行和管理方式；“基础解释器”“项目虚拟环境”描述的是层级。两条轴不能混为“原生／非原生”。

假设已安装官方 Python 3.13、已安装 Anaconda，且 uv 项目的环境已创建：

| 对象 | 是否必然出现 |
| --- | --- |
| 官方 Python 3.13 | 题设已安装时存在；只是下载安装包不等于完成安装 |
| Anaconda base | Anaconda 安装后通常存在 |
| 项目虚拟环境 | 题设明确已创建时存在；仅 `uv init` 还不算 |
| uv 单独下载的解释器 | 不一定；可能复用了兼容的已有解释器 |

因此不能不检查就回答“至少四个”。`pip install uv` 添加的是工具，不额外创造一个 Python 环境。

看到 `packaged by Anaconda` 只说明**当前运行的这个 Python** 来自 Anaconda，不证明电脑没有其他 Python。像门口看到一辆车，只能证明这次来的是它，不能证明车库没有别的车。

基础解释器负责给环境提供运行基础，也可运行不需要第三方依赖的临时脚本。项目依赖放各自环境；跨项目工具可用隔离工具环境。uv 独立安装不要求先安装官方 Python，但最后执行代码仍然必须有解释器。

### 如何盘点环境：不同命令看不同清单

~~~powershell
Get-Command python -All
where.exe python
uv python list --only-installed
conda env list
conda env list --json
~~~

前两条看 Shell 可找到的入口；第三条看 uv 可发现的已安装解释器，可能含系统安装；后两条仅在已装 Conda 时使用，看 Conda 识别的环境。传统 `py -0p` 看启动器识别的解释器，不是全盘扫描所有 venv。

寻找已知代码目录内的普通 venv：

~~~powershell
$codeRoot = Join-Path $env:USERPROFILE "code"
Get-ChildItem -LiteralPath $codeRoot -Filter pyvenv.cfg -File -Recurse -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty DirectoryName
~~~

先把 `$codeRoot` 改成实际代码目录。搜索被权限限制、路径范围限制或文件格式限制，因此结果不是“本机所有环境”的证明。不要为了计数默认扫整个磁盘；一些目录慢、无权限，Conda 环境也不一定用这个标记。

若 `conda env list` 出现两个 `Py3-12`，先比**完整路径**：

~~~powershell
conda env list --json
conda info
Get-Content -LiteralPath "$env:USERPROFILE\.conda\environments.txt"
~~~

最后一条仅在文件存在时执行。同名不同路径可能是真正不同的环境；同一路径重复、大小写或链接差异才需要继续排查记录与版本。不能仅凭缺失路径的截图就认定是记录重复，也不能一上来清空 `environments.txt` 或删除环境。原稿的两个 Py3-12 路径已转写损坏，本轮无法确认是哪种情况。

## 环境切换：激活究竟改变了什么

### 激活是改当前 Shell，不是给整个电脑切换 Python

激活脚本通常在当前 Shell 的 PATH 前面加入环境目录，并设置相关变量、修改提示符。新开的另一个窗口、IDE 运行按钮、Notebook 内核，未必跟着切换。

| 当前 Shell 与环境平台 | 激活方式 | 退出方式 |
| --- | --- | --- |
| Windows PowerShell / pwsh，Windows venv | `.\.venv\Scripts\Activate.ps1` | `deactivate` |
| CMD，Windows venv | `.venv\Scripts\activate.bat` | `deactivate` |
| Windows Git Bash，Windows venv | `source .venv/Scripts/activate` | `deactivate` |
| Linux/macOS Bash、Zsh，Unix venv | `source .venv/bin/activate` | `deactivate` |
| 已初始化 Shell 的 Conda | `conda activate Py3-12` | `conda deactivate` |

`source` 在当前 Bash/Zsh 中执行脚本；若另开子进程执行，子进程改变的环境变量不会回写到父 Shell。PowerShell 的 `.\` 是路径前缀；`. <脚本路径>` 中单独的点加空格则是点源调用，两者不同。`.\` 不会解除策略限制，`.venv.ps1` 也不是标准目录结构里的激活脚本名称。[PowerShell 命令定位](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_command_precedence)

### 为什么激活后仍能用装在 base 里的 uv

寻找 `uv.exe` 与选择运行代码的 Python 是两件事。venv 激活通常**前置**自己的 Scripts 目录，不删除 PATH 中所有原有目录。因此原 base 的 Scripts 仍在 PATH 时，Shell 仍可能找到其中的 uv。

~~~powershell
Get-Command uv -All
Get-Command python -All
uv run python -c "import sys; print(sys.executable)"
~~~

第一条找工具，第二条找普通 `python`，第三条找 uv 项目执行时的 Python。可以是不同的目录。不能用“uv 运行成功”反推出用户仍激活 base；也不能说切到另一个环境后 uv 必然失踪。是否可调用由实际 PATH、别名和函数决定。

### Conda 在 CMD 可用，在 PowerShell 不生效

Conda 激活需要修改当前 Shell 的变量，仅找到 `conda.exe` 还不够。CMD 和 PowerShell 各有初始化方式；不是“CMD 默认一定能用、PowerShell 默认静默”。

先检查：

~~~powershell
Get-Command conda -All
$PROFILE
Get-ExecutionPolicy -List
conda init --dry-run powershell
~~~

`--dry-run` 先显示拟修改位置。确实需要初始化时：

~~~powershell
conda init powershell
~~~

它按 Shell 写初始化代码，通常需关闭并重开对应窗口。Windows PowerShell 与 pwsh 的 profile 可能不同；如果还不生效，要看实际修改了哪份 profile、是否以 `-NoProfile` 启动、是否被策略阻止。若当前找不到 conda，可先在安装附带的 Anaconda Prompt 中执行初始化，不需要把 Anaconda 的所有 DLL 路径永久塞进系统 PATH。[Conda 初始化](https://docs.conda.io/projects/conda/en/stable/commands/init.html)

### 同时出现 (.venv) 和 (Py3-12)，谁在执行

不能按括号排列顺序判断。先运行：

~~~powershell
python -c "import sys; print(sys.executable)"
Get-Command python -All
Get-Command pip -All
$env:VIRTUAL_ENV
$env:CONDA_PREFIX
$env:CONDA_SHLVL
~~~

`VIRTUAL_ENV` 与 `CONDA_PREFIX` 是线索，`sys.executable` 才是已经启动的 Python 的证据。普通 `pip` 也可能指向别处，继续用 `python -m pip --version` 核对。

`conda deactivate` 后出现 base，只说明本次 Conda 恢复到了它保存的状态，不能据此还原 VS Code 自动激活的完整历史。venv 的 `deactivate` 和 Conda 的 `conda deactivate` 各管自己的状态，不是一个统一的环境栈；连续退出的次数也不是恒定两次。

混合状态复杂时，最容易确认的方式是新开一个已知初始化状态的窗口，并核对路径。需要手动切换时，退出当前管理器的环境，确认剩余状态，再只激活目标路线。即便 `uv run` 不要求激活，仍可能继承代理、DLL 路径等 Shell 变量，不等于抹除所有 Conda 设置。

## 导出与迁移：把环境照片和项目配方分开

### pip freeze 与重定向每个符号是什么意思

在确认的项目环境中：

~~~powershell
python -m pip list
python -m pip freeze
~~~

`list` 用表格观察包；`freeze` 输出已安装分发的 requirements 表达，**包含已安装的传递依赖**，但不推断你的直接需求，也不是重新求解得到的锁。默认可能省略某些打包工具，具体以 pip 版本和 `--all` 为准。

CMD 的导出例子：

~~~cmd
python -m pip freeze > requirements.txt
~~~

`>` 把标准输出写入当前目录的文件，存在时覆盖；`>>` 追加。依赖快照通常不要追加，否则容易重复或出现相互冲突的版本。若命令先失败，文件仍可能已被清空，因此先在屏幕上检查命令成功，再输出到**新文件名**，不要覆盖唯一可靠清单。

PowerShell 5.1 文本重定向可能输出 UTF-16；跨版本更明确的方式是：

~~~powershell
$dependencyLines = python -m pip freeze
if ($LASTEXITCODE -ne 0) { throw "freeze 失败，未写入清单" }
[System.IO.File]::WriteAllLines(
    (Join-Path (Get-Location).Path "requirements-observed.txt"),
    [string[]]$dependencyLines,
    [System.Text.UTF8Encoding]::new($false)
)
~~~

先捕获输出并检查退出码，再写 UTF-8 新文件。这里仍会覆盖同名 `requirements-observed.txt`，因此名字也需按实际选择。

要导出某个 Python 3.12，先找到并确认**实际解释器**；已有传统 py 启动器时可在 CMD 用 `py -3.12 -m pip freeze > requirements-py312.txt`，没有启动器则调用实际路径。版本相同不代表环境相同，不要拿“3.12”替代“哪个环境”的检查。

反向安装是 `python -m pip install -r requirements-observed.txt`；`-r` 表示读取依赖文件。命令成功后还需 `python -m pip check` 和运行测试，不能承诺重现整台电脑。

### @ file:/// 为什么出现，如何处理

例如：

~~~text
pywin32 @ file:///D:/bld/some-build/work
~~~

`@` 表示依赖关联到直接来源；`file:///` 是本地文件 URL。它可能来自本地安装或构建记录，Conda 转出的包元数据也可能留下这类信息。**它不是 pip 看不懂 uv 硬链接的表现，也不是 pip 不知道版本号。** 检查实际环境和分发的 `direct_url.json`，才能解释这一条记录的来源。[直接 URL 元数据规范](https://packaging.python.org/en/latest/specifications/direct-url-data-structure/)

错误 `No such file or directory: D:\bld\...\work` 说明安装清单引用的源路径不可访问。解决目标是找回这个依赖的可交付来源，不是批量删包：

1. 判断项目是否用到了这个包。pywin32 是 Windows 包，但业务可能真的依赖它。
2. 查询已装版本和项目需求；确认能否从目标包索引获得合适版本。
3. 确认可替代时将该条改成经验证的 `包名==版本`；本地自研包则交付源码或 wheel。
4. 非 Python 依赖、平台不支持等另列迁移条件；不要删除记录后当作迁移成功。

pipreqs 可以通过源码导入扫描提供候选清单，例如在独立工具环境运行 `uvx pipreqs . --encoding=utf8 --force`。`--force` 会覆盖输出文件；它可能漏动态导入、插件、可选功能与配置驱动依赖，也需核对导入名到分发名的映射。它不是自动恢复完整依赖的保证，优先从项目声明、测试和真实运行路径确认。

### 从 Conda 的 Py3-12 迁到 venv 或 uv

先区分目标：**保持 Conda 工作流**与**转成 Python 包项目**不是同一个任务。

保持 Conda 时，可在 CMD 显式指定环境导出：

~~~cmd
conda env export -n Py3-12 > environment.yml
conda env create -f environment.yml
~~~

第一条在源机器执行，第二条在目标机器执行；导出里可能有机器路径、构建和平台约束，目标机仍需审查。`conda env export -n Py3-12 --from-history` 更接近显式请求的 Conda 依赖，但不保证包含完整 pip 需求，不是完整锁。[Conda 环境管理](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html)

转为 venv/uv 时，先保存 Conda 导出证据，再提取 Python 分发清单供人工核定：

~~~powershell
conda run -n Py3-12 python -c "import sys; print(sys.executable)"
conda run -n Py3-12 python -m pip list --format=json
conda run -n Py3-12 python -m pip freeze
~~~

`conda run -n` 指定环境执行，不必叠加激活。将实际项目所需包整理成可移植的 `requirements-reviewed.txt`，再在**单独目标目录**中选择一种路线：

~~~powershell
# 传统 venv：python 须已是核对过的目标版本
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-reviewed.txt
.\.venv\Scripts\python.exe -m pip check
~~~

~~~powershell
# uv 项目：没有 pyproject.toml 的目标代码目录才初始化
uv init --no-package --python 3.12 --vcs none
uv add -r requirements-reviewed.txt
uv run python -c "import sys; print(sys.executable)"
~~~

这两块是替代方案，不要在同一环境轮流用多个管理器修改。保留业务代码，运行导入验证和项目测试；Conda 提供的原生库、编译器、CUDA 运行库等需要另行准备。Conda 不负责替你安装所有系统驱动；pip/uv 也能安装含二进制扩展的 wheel，不能简单对比为“pip 只纯 Python、Conda 永不编译报错”。

| 工具 | 管理边界 | 基础解释器来源 |
| --- | --- | --- |
| venv | 标准库创建虚拟环境；安装包通常配合 pip | 使用已存在的 Python |
| uv | 可管理解释器、venv、Python 依赖、项目锁和 CLI 工具 | 发现系统解释器或下载管理的发行版 |
| Conda | 通过渠道管理 Python 与许多非 Python 环境包 | 可将 Python 作为环境内的包安装 |

选择依据是项目交付与依赖需求，不是哪个工具“永远更先进”；体积和耗时也取决于真实包集合，不能用固定秒数或 GB 数作规律。

## 项目搬家后 pip 启动器报错

遇到 `Fatal error in launcher: Unable to create process`，并且显示旧 D 盘 Python 路径、当前 C 盘 pip 路径时，“搬家后入口记录失效”是合理假设；仍需核对，不能把乱码本身当成中文路径不合法的证据。

先查：

~~~powershell
Get-Location
Get-Command python, pip -All
Test-Path -LiteralPath .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m pip --version
~~~

最后一条直接让目标 Python 加载 pip，绕过 `pip.exe` 入口。如果 Python 能运行而这条正常，问题可能只在 pip 启动器；如果提示缺少 pip，uv 默认环境没有 pip 也属正常。不是所有此类报错都只能通过删环境解决。

确认要重建且已有可靠声明／锁后，退出激活，确保 IDE 不再持有环境进程，在真实项目根目录先将旧环境改名保留，然后重建：

~~~powershell
Get-Location
Get-Content -LiteralPath .\pyproject.toml
Test-Path -LiteralPath .\.venv-old
# 仅在确认目录正确且 .venv-old 不存在后执行
Rename-Item -LiteralPath .\.venv -NewName .venv-old
uv sync --locked
uv run python -c "import sys; print(sys.executable)"
~~~

传统 venv 则用已核定解释器重建，再从已审查的 requirements 安装。旧环境改名后可能更不能运行，只用于取证与核对，不作为新环境继续使用。代码、数据不能放在环境目录中。

确认依赖、业务运行与文件保存完整后再清理 `.venv-old`。不要先执行 `freeze > requirements.txt` 覆盖唯一清单，也不要直接拷贝 `site-packages` 来“修好”环境。虚拟环境一般不可移植，迁移交付的是配方和代码，目标机重新配装。


## 现阶段认知

环境问题的首要问题是“**谁在执行，包装在哪里**”。先确认解释器和依赖，再考虑重建；部署时从声明文件重建环境，不复制 Windows 的 `.venv` 到 Linux。参见 [[Python模块导入与包管理]] 和 [[Windows到Linux部署Python项目]]。

## 依据

- [Python 官方文档：`venv`](https://docs.python.org/3/library/venv.html)
- [uv 官方文档：项目与同步](https://docs.astral.sh/uv/concepts/projects/sync/)
