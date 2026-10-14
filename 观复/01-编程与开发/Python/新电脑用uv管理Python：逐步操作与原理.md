# 新电脑用uv管理Python：逐步操作与原理

> **核验状态**：部分实测——2026-10-02 在 Windows x64、uv 0.12.12、已有 Python 3.12.14 下，隔离验证项目初始化、pandas 安装、运行合计30、锁检查和依赖导出；安装、解释器下载与存储规则另对照 Astral 文档，范围见 [[知识库质量审计]]。未在一台没有 Python 的新电脑上运行安装器或完成首次下载。
> 场景：Windows 10/11，新电脑尚未安装 Python，使用 PowerShell。Python 3.12 是本例的选择，不代表所有项目必须用它或它是最新版本。

## 背景：先知道自己在安装什么

要跑 Python 代码，必须有 Python 解释器；但不必先去 Python 官网手动装它。uv 的独立安装器先装一个可执行工具，再由 uv 下载解释器、准备每个项目自己的环境。[官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)

把这一套想成厨房：

- **uv** 是采购和配装的管理员，负责安排工作。
- **Python 解释器** 是能真正做菜的炉具，3.12、3.13 是不同规格。
- **项目的 `.venv`** 是这道项目专用的工作台，有自己的依赖包。
- **`pyproject.toml`** 是需求单：项目要什么、允许哪些版本。
- **`uv.lock`** 是本次确定的采购明细：选了哪些包、版本和文件。
- **代码** 是做菜的步骤；**缓存** 是可复用的备料仓库。

管理员住在哪里，并不决定他把工作安排到哪个工作台。因此 uv 在用户目录里，项目仍可使用它自己的 Python 和 pandas。这个类比只说明职责：虚拟环境不是虚拟机，也不隔离文件访问、网络或恶意代码。完整概念见 [[Python环境与依赖]]。

## 问题：要达到什么结果

本例建一个 `uv-first-project` 项目，用 pandas 合计两笔金额。最后你应能确认：

1. 终端找得到 uv。
2. uv 找得到 Python 3.12。
3. 项目有声明、锁文件和 `.venv`。
4. 脚本实际使用项目内的 Python，输出合计 `30`。
5. 关闭终端后再打开，也知道如何继续。

下面每个代码块按顺序执行；不要把提示符 `PS C:\...>`、`>>>` 或输出内容一起复制。

## 方案：从空电脑到第一个项目

### 第0步：打开 PowerShell，确认当前层次

在开始菜单搜索“PowerShell”，打开普通用户窗口即可。Windows Terminal 中也可选 PowerShell 标签页；终端软件与 Shell 的区别见 [[终端与 Shell]]。

输入：

~~~powershell
$PSVersionTable.PSVersion
Get-Location
~~~

第一条显示 PowerShell 版本；第二条显示当前目录。`PS` 是当前窗口的提示符，不是要输入的命令。当前目录像你正站着的房间：`.\main.py` 指的是这个房间内的文件。

如果提示符是 `>>>`，先输入 `exit()` 回到 Shell。那里是 Python 交互解释器，不能直接输入 `uv add pandas`。

### 第1步：安装 uv 本身

在 PowerShell 输入：

~~~powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
~~~

逐段理解：

| 片段 | 作用 |
| --- | --- |
| `powershell` | 启动 Windows PowerShell 子进程来执行安装命令 |
| `-ExecutionPolicy ByPass` | 给这个进程指定执行策略；不永久修改整台机器策略，组织策略仍可能优先 |
| `-c` | `-Command` 的缩写，执行引号内的命令 |
| `irm` | `Invoke-RestMethod` 的别名，从官方 URL 获取安装脚本 |
| `|` | 管道，把前一个命令的结果交给下一个 |
| `iex` | `Invoke-Expression` 的别名，把脚本文本作为命令执行 |

这一步执行的是联网安装脚本，不是在安装项目的 pandas；应确认地址为官方地址。希望先读脚本时，使用 [[uv项目管理与Windows配置#先下载、检查，再执行]] 的分步方法。

安装日志会报告实际目录。常见默认位置为：

~~~text
C:\Users\你的用户名\.local\bin\uv.exe
~~~

`$env:USERPROFILE` 表示当前用户目录。默认按用户安装通常不需要管理员权限；如果组织策略阻止安装，按实际限制处理。[安装器配置](https://docs.astral.sh/uv/reference/installer/)

### 第2步：关闭终端宿主，再打开并验证

安装器可能修改用户 PATH。PATH 是“去哪些目录找命令”的地址簿；正在运行的程序通常拿着启动时的旧副本。因此关闭整个 Windows Terminal 后重开；若在 VS Code 内，也可能需要重开 VS Code。

输入：

~~~powershell
uv --version
Get-Command uv -All
~~~

第一条应显示 `uv` 和版本号；第二条显示可调用入口及其路径。版本号随安装时间变化，不要求与笔记完全相同。

如果找不到 uv，先看安装日志。仅当日志中的安装目录是默认目录时，可在当前窗口临时调用：

~~~powershell
& "$env:USERPROFILE\.local\bin\uv.exe" --version
~~~

`&` 是 PowerShell 调用运算符：告诉它把后面的字符串路径当作程序运行。若这条成功而 `uv --version` 失败，重点排查 PATH，不必重装 Python。可查看：

~~~powershell
[Environment]::GetEnvironmentVariable("Path", "User") -split ';'
~~~

不要把 `.venv` 的路径永久写进用户 PATH；项目之间会争抢默认入口。多份 uv 时看 `Get-Command uv -All`，选择一种安装渠道管理升级。

### 第3步：让 uv 安装 Python 3.12

~~~powershell
uv python install 3.12
uv python list --only-installed
uv python find 3.12 --managed-python
~~~

第一条安装 uv 管理的 Python 3.12；已安装时可复用。第二条列出本机可发现的已安装解释器，其中不一定全由 uv 安装。第三条限定查找 uv 管理的 3.12 并显示路径。

`3.12` 是一个系列请求，没有固定补丁版本；需要严格固定时使用经验证可用的完整版本号。下载失败先看完整报错，不把“未装 Python”当成故障根因；包索引和解释器下载是两条不同链路，配置见 [[uv项目管理与Windows配置#包索引和解释器下载分别配置]]。

此时拥有的是一份可被多个项目使用的基础解释器，还没创建本例项目的虚拟环境。[解释器版本与发现规则](https://docs.astral.sh/uv/concepts/python-versions/)

### 第4步：建立放代码的父目录

~~~powershell
New-Item -ItemType Directory -Path "$env:USERPROFILE\code" -Force | Out-Null
Set-Location -LiteralPath "$env:USERPROFILE\code"
Get-Location
~~~

- `New-Item` 创建一个东西，`-ItemType Directory` 指定创建文件夹。
- `-Force` 允许目录已经存在；这里不会清空目录。
- `Out-Null` 只隐藏创建目录的输出。
- `Set-Location` 切换当前目录，`-LiteralPath` 把路径按字面解释。
- 引号把整个路径当作一个参数，避免空格将其拆开。

本例选用户目录，不依赖机器有没有 D 盘。也可用你实际的代码目录。

### 第5步：初始化一个简单的脚本项目

先确认 `code` 下没有同名项目；已有项目不要重复初始化。

~~~powershell
uv init uv-first-project --no-package --python 3.12 --managed-python --vcs none
Set-Location -LiteralPath .\uv-first-project
Get-ChildItem -Force
Get-Content -LiteralPath .\pyproject.toml
~~~

| 参数 | 为什么加 |
| --- | --- |
| `uv-first-project` | 项目目录名 |
| `--no-package` | 本例用平铺脚本，不引入 `src` 包结构、构建系统和命令入口 |
| `--python 3.12` | 初始化时选择 Python 3.12，并影响模板中的版本要求 |
| `--managed-python` | 明确使用 uv 管理的解释器，避免已有 Conda 等安装参与选择 |
| `--vcs none` | 本例不初始化 Git，免去新电脑是否已装 Git 的变量 |

预期能看到 `pyproject.toml`、`.python-version`、`README.md` 和 `main.py`，具体模板以实际版本为准。**`uv init` 本身不建立 `.venv` 和 `uv.lock`**。它先画出项目蓝图，不等于已经把工作台装好。[初始化选项](https://docs.astral.sh/uv/concepts/projects/init/)

检查配置时重点看 `requires-python` 和 `dependencies`。例如 `requires-python = ">=3.12"` 说项目支持的范围，而 `.python-version` 中的 `3.12` 请求本机选这个系列，两者职责不同。TOML 的字符串用英文直引号，不用 Word 里的弯引号。

### 第6步：安装 pandas，并观察生成的文件

~~~powershell
uv add pandas
Get-Content -LiteralPath .\pyproject.toml
Get-ChildItem -Force
uv tree
~~~

`uv add pandas` 通常会连做三件事：

1. 把 pandas 作为直接依赖写进 `pyproject.toml`。
2. 解析 pandas 及其依赖，创建或更新 `uv.lock`。
3. 准备 `.venv`，把本次环境需要的包装进去。

这时应看到 `uv.lock` 和 `.venv`。`uv tree` 展示依赖关系：pandas 需要的其他包由解析器按约束补齐，不需要初学者逐个手动添加为直接依赖。

这也是 `uv add pandas` 与 `uv pip install pandas` 的关键差异：前者维护项目需求与锁，后者只操作目标环境。长期项目依赖优先走 `uv add`，不然下次同步可能移除未声明的包。[项目依赖管理](https://docs.astral.sh/uv/concepts/projects/dependencies/)

### 第7步：验证实际 Python 和 pandas

~~~powershell
uv run python -c "import sys, pandas; print(sys.executable); print(sys.version); print(pandas.__version__); print(pandas.__file__)"
~~~

`uv run` 先按项目准备运行环境，再执行后面的命令；`python -c` 让 Python 执行引号内的代码。`import sys, pandas` 加载这两个模块；分号将短语句分开。

判断依据：

- `sys.executable` 应指向本项目的 `.venv\Scripts\python.exe`。
- `sys.version` 应是 3.12 系列。
- pandas 版本以本次锁定结果为准。
- `pandas.__file__` 通常指向项目 `.venv\Lib\site-packages\pandas\__init__.py`。

不是只看提示符有没有 `(.venv)`。如路径不符合预期，先看 `Get-Location` 和 `Get-ChildItem Env:UV*` 是否有旧配置覆盖，再安装依赖。

### 第8步：在终端写入一个完整的小程序

以下块会覆盖**本例项目模板的** `main.py`；不要在别的已有项目里照抄覆盖。

~~~powershell
$demoCode = @'
import sys
import pandas as pd

amounts = pd.Series([10, 20], name="amount")
print("Python:", sys.executable)
print("pandas:", pd.__version__)
print("total:", amounts.sum())
'@
[System.IO.File]::WriteAllText(
    (Join-Path (Get-Location).Path "main.py"),
    $demoCode,
    [System.Text.UTF8Encoding]::new($false)
)
Get-Content -LiteralPath .\main.py
~~~

`@'` 与 `'@` 是 PowerShell 多行字符串边界；结尾 `'@` 单独顶格写一行。单引号形式不展开 Python 代码里的变量。`WriteAllText` 把字符串保存为文件；`$false` 表示不写 UTF-8 BOM，兼容 Windows PowerShell 5.1 与 PowerShell 7 的输出差异。

程序本身很简单：`pd.Series` 创建一列数，`sum()` 求和。`as pd` 只是给 pandas 绑定短名字，没装另一份包。

### 第9步：运行，并确认业务输出

~~~powershell
uv run python main.py
~~~

应看到 Python 路径、pandas 版本和：

~~~text
total: 30
~~~

另外两行包含实际路径与版本，不要求逐字相同。能导入 pandas 证明这个解释器找到了包；合计 30 证明本例给定输入执行成功，两者是不同检查。

不需要先运行激活脚本。`uv run` 为子进程选择项目环境，而不把整个当前窗口永久切换过去。之后直接输入 `python` 仍可能指向其他解释器或 Windows 应用执行别名；继续用 `uv run python` 即可。

### 第10步：关闭电脑之后，如何继续

下次打开 PowerShell：

~~~powershell
Set-Location -LiteralPath "$env:USERPROFILE\code\uv-first-project"
uv run python main.py
~~~

已经配置好的项目不用每次 `uv init`，也不用每次 `uv add pandas`。缺少环境时 uv 会按项目准备；缓存命中也不代表每次都重新下载。

依赖变化时，日常操作为：

~~~powershell
uv add requests
uv remove requests
uv lock --check
~~~

前两条分别添加、移除直接依赖；这里只作演示，不是 pandas 合计例子的必需步骤。`uv lock --check` 检查现有锁是否与声明一致，不安装包。

## 进一步理解：安装、选择、创建与同步

### 背景：安装新炉具，不等于更换项目工作台

`uv python install 3.14` 让电脑拥有一份 Python 3.14；它不自动把已用 3.12 的项目切到 3.14。基础解释器像仓库里的炉具，`.venv` 是项目工作台；添置一个型号，不等于替换每张工作台正在使用的型号。

| 操作 | 改变哪一层 |
| --- | --- |
| `uv python install 3.14` | 安装可供使用的基础解释器 |
| `uv init --python 3.14` | 初始化项目时明确选择，并形成模板版本配置 |
| `uv python pin 3.14` | 写入 `.python-version` 的版本请求，不自动修改 `requires-python` |
| `uv venv --python 3.14` | 明确用所选解释器创建虚拟环境，不自动统一项目声明 |
| `uv sync` | 根据项目配置、锁和选项准备本机项目环境 |
| `uv add pandas` | 添加项目依赖，通常也解析、锁定并同步环境 |

这里正确的参数是 `--python`，不是 `uv venv python 3.14`。`install` 往往可省略：后续命令需要的解释器不存在且允许自动下载时，uv 可按需下载。它仍适合提前准备版本、单独排查下载问题或为离线使用准备解释器；离线运行还需要包和构建资源，不能只安装 Python 就认为全部准备完成。[官方版本规则](https://docs.astral.sh/uv/concepts/python-versions/)

### 问题一：先 init，再 install，最后 venv，会用刚安装的版本吗

~~~powershell
uv init
uv python install 3.12
uv venv
~~~

**不能保证。** 最后一条没有显式指定版本，选择会受版本请求、配置及发现规则影响，不是“谁最后安装就选谁”。初始化可能已记录另一个版本；安装 3.12 不会把那个记录改掉。

只想创建指定版本的环境，可用 `uv venv --python 3.12`；想管理完整项目，则初始化时就指定版本，更容易避免声明和环境不一致。

### 方案：空文件夹中的两条路径

已经进入新建的空文件夹后，想用 3.14 且暂时不装业务包：

~~~powershell
uv init --no-package --python 3.14 --vcs none
uv sync
uv run python --version
uv run python -c "import sys; print(sys.executable)"
~~~

若需要 pandas，则把 `uv sync` 换成 `uv add pandas` 即可；默认情况下 `add` 已经准备环境，无须再重复 `venv` 和 `sync`。示例沿用平铺脚本模板，不要求新电脑已装 Git。3.14 只是选择示例，仍需 uv 支持下载且项目依赖支持这个版本。

### 问题二：已有 3.12 环境，再 install 3.14，为何仍是 3.12

安装新版本不会自动改项目的 `.python-version`、`requires-python` 或已有环境。先看：

~~~powershell
Get-Content -LiteralPath .\.python-version
Get-Content -LiteralPath .\pyproject.toml
uv run python --version
uv run python -c "import sys; print(sys.executable)"
~~~

例如 `.python-version` 仍是 `3.12`，项目继续请求 3.12；`requires-python = ">=3.12"` 只是允许 3.14，不要求自动采用它。`python --version` 查的是当前 Shell 找到的程序，`uv run python --version` 查的是项目运行时的程序，两者可能不同。

确实想切换已有项目时，先确认支持范围允许 3.14、依赖兼容，保存可靠声明和代码，再执行：

~~~powershell
uv python install 3.14
uv python pin 3.14
uv sync
uv run python --version
uv run python -c "import sys; print(sys.executable)"
~~~

`sync` 按新的版本请求准备环境，现有环境不相容时可能重建。不要把有价值的代码或数据放在 `.venv` 中；切换后需运行项目测试。现有声明若为 `>=3.12,<3.13`，必须先根据实际支持情况修改范围，不能靠 pin 越过它。这里不用 `--locked` 强行拒绝所有锁变化，因为这是主动迁移版本的开发操作；完成迁移后再检查锁和交付。

### 原理：一个项目会有多个 Python 吗

电脑可以有多个基础解释器，但默认项目的一个 `.venv` 使用一个基础解释器版本。它包含的入口程序和基础解释器关联，不是两个可任意切换的版本。

只有主动创建不同环境目录，才会在项目旁边出现多份环境，例如：

~~~powershell
uv venv .venv312 --python 3.12
uv venv .venv314 --python 3.14
~~~

这通常用于兼容性测试；uv 项目并不会自动将这两个目录都作为默认环境。日常开发先维护一份默认 `.venv` 即可。

### uv sync：把项目配方落实成本机环境

`pyproject.toml` 是需求单，`uv.lock` 是确定的采购明细，`.venv` 是实际工作台。有需求单不代表工具已装好；`sync` 负责让环境与本次项目要求一致。

在项目目录执行 `uv sync`，通常会：

1. 检查声明和锁；缺锁或需要更新时，创建或更新锁。
2. 按项目 Python 选择及兼容要求准备环境，必要时创建或重建 `.venv`。
3. 安装本次选择的依赖，默认精确同步，移除不属于本次同步集合的额外包。
4. 对配置为可安装包的项目，通常还安装项目自身；本教程的 `--no-package` 路线不做这一步。

这里的同步不上传云端，不自动把 Python 或所有包升级到最新。没有声明 pandas，普通 `sync` 不会凭空安装 pandas。依赖集合也受开发组、extras、平台标记与配置影响，具体选项见 [[uv项目管理与Windows配置#维护依赖与同步]]。

| 场景 | 常用操作 |
| --- | --- |
| 初始化后尚未准备环境 | `uv sync` |
| 新增项目依赖 | `uv add pandas`，通常已含同步 |
| 拿到别人交付的代码和锁 | `uv sync --locked` |
| 日常运行 | `uv run python main.py`，默认会按需检查和准备环境 |
| 只更新解析结果，不安装 | `uv lock` |

`uv sync --locked` 要求现有锁与声明一致且不允许更新，不一致或缺锁会失败；适合交付与 CI。`uv sync --frozen` 跳过锁新鲜度检查，是另一种策略，不能与 locked 混为一谈。[锁定与同步说明](https://docs.astral.sh/uv/concepts/projects/sync/)

### 现阶段认知

按职责记忆：**install 备解释器，init 建项目，pin 写选择，venv 建环境，add 改依赖，sync 配环境，run 执行。** 每次故障检查实际路径和项目配置，不按安装顺序猜测，也不将“版本允许”理解成“必须自动升级”。

以上 3.14 切换与双环境操作为文档核对示例，本轮未下载 3.14、切换真实项目或执行清理；此前 pandas 小项目的实测范围仍见 [[知识库质量审计]]。


## 原理：这些文件究竟放在哪里

~~~powershell
(Get-Command uv).Source
uv python dir
uv cache dir
uv tool dir
uv run python -c "import sys, site; print(sys.executable); print(sys.base_prefix); print(site.getsitepackages())"
~~~

| 要找什么 | 以上哪个入口回答 | 用途 |
| --- | --- | --- |
| uv 工具本体 | `Get-Command uv` | Shell 找到的管理员 |
| uv 管理的基础解释器目录 | `uv python dir` | 可供多个项目使用的 Python |
| 包缓存 | `uv cache dir` | 复用下载或构建结果 |
| 独立 CLI 工具环境 | `uv tool dir` | `uv tool install` 安装的工具，目录未必已产生 |
| 当前项目解释器和包目录 | 最后一条 | 本项目的工作台 |

Windows 常见默认缓存是 `%LOCALAPPDATA%\uv\cache`，uv 持久数据通常在 `%APPDATA%\uv\data` 下；**不能把解释器、缓存和工具一律写成同一个 LOCALAPPDATA 路径**。环境变量与配置可改位置，以查询结果为准。[官方存储规则](https://docs.astral.sh/uv/reference/storage/)

项目包的可导入位置在 `.venv` 中。uv 可通过硬链接等方式复用缓存的数据；硬链接是多个目录项共享同一份文件数据，并不是“快捷方式转到另一条路径”。不同版本、构建和生成文件、跨盘复制会影响空间占用，不能承诺十个项目总共只占一份完整环境。

## 可选：什么时候手动激活

想在当前窗口直接输入 `python` 时，先在项目根目录执行：

~~~powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
python main.py
deactivate
~~~

`.\` 表示从当前目录出发；`.venv` 是目录；`Scripts` 是 Windows 环境脚本目录；`Activate.ps1` 是 PowerShell 激活脚本。**`.venv.ps1` 不是标准激活命令**，也不是它的等价缩写。

若策略阻止激活，可继续用 `uv run` 或 `.\.venv\Scripts\python.exe`。添加 `.\` 解决路径定位，不绕过执行策略。

CMD 的激活命令是 `.venv\Scripts\activate.bat`；Bash 用 `source .venv/bin/activate`，Windows Git Bash 的 Windows 环境用 `source .venv/Scripts/activate`。不同 Shell 不互换语法。

## 迁移到另一台电脑

源电脑保留代码、`pyproject.toml`、`uv.lock`、需要的 `.python-version`、测试与必要配置；数据、密钥和系统依赖按项目约定另行准备。不传 `.venv`。

先在源项目验证：

~~~powershell
uv lock --check
uv run --locked python main.py
~~~

在目标电脑安装 uv 后，将上述项目文件放到实际目录，进入它，例如：

~~~powershell
Set-Location -LiteralPath "$env:USERPROFILE\code\uv-first-project"
uv sync --locked
uv run --locked python main.py
~~~

`--locked` 要求锁与声明一致且不允许自动改锁；不同步就失败，便于发现漏交或过期的锁。不要在收到的现成项目里重新 `uv init`。

锁文件像采购明细，能减少版本漂移，但不是整台电脑的克隆：操作系统、架构、Python 补丁、驱动、包下载可达性仍需验证。需要 requirements 格式时看 [[uv项目管理与Windows配置#迁移与交付]]。

## 排错：每一层失败，就查这一层

| 现象 | 下一步 |
| --- | --- |
| `uv` 不被识别 | 第2步检查实际可执行文件与 PATH |
| Python 下载失败 | 查 `uv python install 3.12 -v` 日志，区分网络、代理、证书与平台支持 |
| pandas 安装失败 | 查 `uv add pandas -v`，区分包源、版本约束、wheel/构建错误 |
| 找不到 `pyproject.toml` | `Get-Location`，进入实际项目根目录 |
| 找不到 `main.py` | `Get-ChildItem`，确认写文件步骤和运行路径 |
| 包已装却无法导入 | 第7步检查 `sys.executable` 与包文件位置 |
| `No module named pip` | uv 环境默认可没有 pip；用 `uv add` 或目标明确的 `uv pip`，不用为此重装整个环境 |
| `Fatal error in launcher` | 见 [[Python环境与依赖#项目搬家后 pip 启动器报错]]，不要把它当下载错误 |
| 在 `>>>` 输入 uv 命令报错 | `exit()` 回 Shell |
| 镜像配置后仍下载失败 | 包索引不改变解释器下载地址；分别验证两条链路 |

## 现阶段认知

你需要掌握的不是一串口令，而是每一步改变了哪一层：安装 uv → 准备基础 Python → 声明项目 → 同步环境 → 用项目 Python 执行。出错时先问“我在哪里、谁在执行、包装在哪里”，再按证据修复。

第一次上手读到这里即可；依赖组、包布局、工具管理、镜像与部署分别进入 [[uv项目管理与Windows配置]]、[[Python模块导入与包管理]] 和 [[Windows到Linux部署Python项目]]，无需在空电脑上一次设置完所有选项。
