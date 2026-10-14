# uv 项目管理与 Windows 配置

> **先修**：[[Python环境与依赖]]；理解命令入口时参看 [[Python模块导入与包管理]]。
> **核验状态**：部分实测——2026-10-01 在 Windows x64、uv 0.12.12、Python 3.12.14 下离线验证初始化、环境路径、运行和锁文件检查；清洗示例用 pandas 3.0.1、pyarrow 25.0.1 完成 CSV/Parquet 往返。另实测：无 `pyproject.toml` 的目录执行 `uv export` 直接报错，不会退化为导出当前环境。uv 安装、完整项目的联网依赖流程、解释器镜像下载、ARM64 和服务器部署未在本轮实测。2026-10-02 对两份 Word 补充安装归属、现有 venv 接管、CLI 选择及导出／哈希排错，这些新增范围以官方文档核对为主。详见 [[知识库质量审计]]。

新电脑第一次上手，先照 [[新电脑用uv管理Python：逐步操作与原理]] 完成一个小项目。

第一次学习按“背景 → 管理路线 → 安装和项目 → 配置 → 实践”阅读；遇到故障直接查“排错速查”，查选项看对应操作表。镜像候选与系统设置不属于每个项目都要执行的初始化步骤。

## 背景：把项目声明与本地环境分开

uv 可以管理 Python 解释器、项目依赖、虚拟环境和命令行工具。先把 [[Python环境与依赖]] 中的三层分清，再用 uv 串起工作流。它像项目的配装清单与施工工具：声明需要什么、锁定采用什么、在本机装出可运行的环境。

| 文件或目录 | 职责 | 如何处理 |
| --- | --- | --- |
| `pyproject.toml` | 项目元数据、兼容 Python 范围、直接依赖、命令入口 | 随代码提交 |
| `uv.lock` | 依赖解析结果，包含版本、来源和文件哈希等信息 | 随代码提交，不手改 |
| `.python-version` | 本地解释器选择请求，如 `3.12` | 团队统一选择时提交；系列版本没有固定补丁号 |
| `.venv/` | 当前机器上实际安装的项目环境 | 不提交，不跨机器复制 |
| `uv.toml` | uv 的配置，如索引与缓存策略 | 按用户或项目需求配置；不代替项目依赖声明 |

跨平台锁文件可以表达平台差异，但不能保证每个平台都有适用 wheel、系统库或编译工具。uv 能安装含二进制扩展的 Python 包；CUDA 驱动、系统库和编译工具链等仍需单独准备。已有 Conda 项目应先理解其非 Python 依赖，避免多个管理器同时修改同一环境。

### 工具链为什么能合并，性能来自哪里

传统职责分散在 `pip`（安装包）、`venv`（环境隔离）、pyenv 或安装器（解释器）、pipx（独立 CLI）、Poetry 或 pip-tools（项目解析与锁定）中。uv 将这些常见任务收进一套命令，减少工具间的交接；这并不意味着它与每个旧工具语义完全等价。

1. **依赖解析**：uv 用 Rust 实现，解析器使用 PubGrub；它跟踪不兼容约束，并在冲突时回溯，帮助输出冲突链。速度还取决于元数据获取、缓存、依赖图与约束，不能仅由算法名称推断“快一个量级”。参看 [官方解析器机制](https://docs.astral.sh/uv/reference/internals/resolver/)。
2. **共享缓存与链接**：包可复用已下载或已构建的缓存。在 Windows 默认硬链接模式下，同卷可让缓存和环境共享文件数据；跨卷则需复制。目录项、元数据、不同版本和安装时生成的文件仍可能占空间，不能概括为十个环境总共只占一份完整磁盘。
3. **预构建解释器**：uv 管理的 CPython 通常从 `python-build-standalone` 获取预构建发行版，省去本机编译解释器的步骤；下载与解压时间仍受网络、平台和文件大小影响。
4. **声明与解析结果分离**：`pyproject.toml` 表达要求，锁文件记住解析选择；本地环境可以删除后重建。跨平台差异用版本约束和环境标记表达，目标平台依然要验收。

本轮没有性能基准测试。遇到慢，应分辨解析、网络、构建、安装和安全扫描，避免把所有延迟归因于 pip 或某种语言实现。

## 问题：先选择哪条管理路线

| 需求 | 工作流 |
| --- | --- |
| 多文件项目、协作、测试、部署 | `uv init` → `uv add` → `uv run` → `uv sync --locked` |
| 一个可独立分发的脚本 | 内联依赖 → `uv run script.py` |
| 已有 requirements 环境，暂不迁移项目声明 | `uv venv` → `uv pip install -r requirements.txt` |
| 独立 CLI 工具 | 临时用 `uvx`，长期用 `uv tool install` |

`uv add` 维护项目声明、锁文件和环境；`uv pip` 直接操作环境，不维护前两者。项目需要长期依赖时用 `uv add`，临时实验可用 `uv run --with`。不要把手动装进环境的包误当成已交付的项目依赖。

## 方案：从安装到协作

### 安装与定位

官方独立安装器不要求预先安装 Python。以下命令下载并执行官方脚本；需要审查时先打开该地址阅读脚本。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

也可使用已有的包管理器，例如 `winget install --id astral-sh.uv --exact`、`scoop install main/uv` 或 `python -m pip install uv`。选一种安装方式，再由同一方式管理升级：独立安装用 `uv self update`；winget、Scoop、pip、pipx 安装则用对应管理器升级。安装路径以实际日志为准，独立安装常见位置为 `$env:USERPROFILE\.local\bin`。

安装后重开终端及其宿主程序，检查：

```powershell
Get-Command uv
uv --version
uv help
```

新标签页可能继承旧环境变量。需要当前会话临时找到默认安装位置时：

```powershell
$env:Path += ";$env:USERPROFILE\.local\bin"
```

PowerShell 补全可将下列两行各写一次到 `$PROFILE`；先检查文件，避免反复追加：

```powershell
(& uv generate-shell-completion powershell) | Out-String | Invoke-Expression
(& uvx --generate-shell-completion powershell) | Out-String | Invoke-Expression
```

安装方式、平台与选项以 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/) 为准。本篇记录本机版本，不标榜某个版本为“最新”。

#### 安装方式与升级命令对照

| 安装渠道 | 安装示例 | 后续升级 |
| --- | --- | --- |
| 官方独立安装器 | 本节开头的安装脚本 | `uv self update` |
| winget | `winget install --id astral-sh.uv --exact` | `winget upgrade --id astral-sh.uv --exact` |
| Scoop | `scoop install main/uv` | `scoop update uv` |
| pipx | `pipx install uv` | `pipx upgrade uv` |
| pip | `python -m pip install uv` | 在相同安装环境用 `python -m pip install -U uv` |

需要复现特定工具版本时，独立安装脚本可指定版本，例如 `https://astral.sh/uv/0.12.12/install.ps1`。自定义可执行文件安装位置可在运行安装器前设置 `$env:UV_INSTALL_DIR = "D:\tools\uv"`；它不会同时迁移解释器、工具和缓存目录，后者各有设置。安装与卸载仍由同一渠道管理，避免 PATH 中多份 uv 交替生效。

#### 先下载、检查，再执行

以下步骤在 PowerShell 执行，不是 CMD；`irm`、`iex`、两种 PowerShell 进程及策略作用范围见 [[终端与 Shell]]。

```powershell
Invoke-RestMethod https://astral.sh/uv/install.ps1 -OutFile install-uv.ps1
Get-Content -LiteralPath .\install-uv.ps1
# 确认脚本和来源后再执行下一条
.\install-uv.ps1
```

若执行脚本被阻止，先 `Get-ExecutionPolicy -List`；可继续使用已安装的包管理器，或在组织策略允许时设置所需范围。只为当前会话允许本地脚本的例子是 `Set-ExecutionPolicy -Scope Process RemoteSigned`；确实需要长期用户设置才考虑 `-Scope CurrentUser`。网络来源标记、签名与策略优先级须结合实际报错判断，不把 Bypass 当成企业限制的通行证。

永久 PATH 是否含默认安装目录可用 `[Environment]::GetEnvironmentVariable("Path", "User") -split ';'` 检查。补全前若 `$PROFILE` 不存在，可用下面步骤建立文件，再在编辑器写入上面的补全行：

```powershell
New-Item -ItemType Directory -Path (Split-Path $PROFILE) -Force | Out-Null
if (-not (Test-Path -LiteralPath $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE | Out-Null
}
```

这些代码是操作示例；本轮未安装 uv、改 PATH、写 profile 或改变执行策略。

### 从 pip 安装的 uv 切换到独立安装

先定位**哪个 Python 安装了 uv**，再切换。不能拿当前项目的 `python` 去卸载另一个环境的包：

~~~powershell
Get-Command uv -All
python -c "import sys; print(sys.executable)"
python -m pip show uv
~~~

如果查到原 uv 在 Conda base 中，可明确调用它：

~~~powershell
conda run -n base python -m pip show uv
~~~

按查到的路径记录旧工具版本、项目路径、`uv python dir` 和项目 `sys.base_prefix`。只卸载 uv 包通常不会删除项目代码、环境或 uv 下载的解释器；**卸载整个 Anaconda／基础 Python** 是另一种操作，依赖该基础解释器的环境可能失效，不论它由 venv 还是 uv 创建。

确定安装归属后，使用相同解释器执行 `python -m pip uninstall uv`；若源环境为 base，使用 `conda run -n base python -m pip uninstall uv`。然后按 [[新电脑用uv管理Python：逐步操作与原理#第1步：安装 uv 本身]] 安装独立版，重开终端检查 `Get-Command uv -All`、`uv --version`，再进入已有项目执行 `uv run --locked python -c "import sys; print(sys.executable)"` 和业务验证。

独立版 uv 可以管理已有项目，不需要重新 `uv init`；但不同版本的默认行为、配置和锁格式仍须核对，不能承诺“绝对无影响”。安装期间暂时不可调用工具与项目文件被删除是不同现象。

CMD 也可以执行完整的 `powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"`，不必仅因在 CMD 就手动下载。确实手动下载时，按机器架构从 [官方 Releases](https://github.com/astral-sh/uv/releases) 选择构建，把包含 `uv.exe` 的实际目录加入用户 PATH；x64 与 ARM64 不应混选。

### 已有 venv：接管安装与接管项目是两步

不必删除一个健康的普通 venv 才能用 uv。先直接指定目标，避免混合激活：

~~~powershell
uv pip list --python .\.venv\Scripts\python.exe
uv pip show --python .\.venv\Scripts\python.exe pandas
uv pip install --python .\.venv\Scripts\python.exe requests
uv pip check --python .\.venv\Scripts\python.exe
~~~

这是由 uv 的 pip 接口操作这个环境；**不会自动根据已安装包写 `pyproject.toml`**。清单没有相应包时 `show` 的失败也可以是正常的未安装。

要迁为 uv 项目，先保存原依赖信息并人工核定直接需求；已有 `pyproject.toml` 就在它上面修订，确实没有才初始化。随后 `uv add -r requirements-reviewed.txt`，审查直接／传递依赖与本机路径，再验证锁和运行。兼容的旧环境可能被复用，也可能因 Python 不相容需要重建。不要在确认需求前 `uv sync`：精确同步可能移除手工安装但未声明的包。[官方 pip 到项目迁移指南](https://docs.astral.sh/uv/guides/migration/pip-to-project/)

### CLI 工具放在全局还是项目中

“全局可调用”不等于“都往 base 的 site-packages 塞”。个人通用 CLI 可用每工具独立环境：

~~~powershell
uv tool install ruff
uv tool install black
uv tool list
uv tool dir --bin
uv tool update-shell
~~~

更新 Shell 路径后按日志重开终端；不必先将 uv 改装为独立版才能运行 `uv tool`，前提只是工具本身可调用。

团队希望格式化与 CI 一致时，用项目开发依赖：

~~~powershell
uv add --dev ruff black
uv run ruff check .
uv run black --check .
~~~

这不是“多余包污染项目”，而是声明开发所需工具并锁版本。选用 ruff、black 或二者要按项目规范，别同时采用相互冲突的格式化配置。`uvx ruff` 在独立工具环境运行，版本可能与项目锁不同；项目验收用 `uv run ruff`。


### 管理解释器，理解两种版本约束

```powershell
uv python list --only-installed
uv python install 3.12
uv python find 3.12
uv python pin 3.12
uv python dir
```

`uv python install` 明确安装解释器；`uv python pin` 写解释器选择请求，不能据此认定必然发生下载。后续 `uv sync` 或 `uv run` 在缺少合适解释器且允许下载时，可自动安装。需要确保采用 uv 管理的解释器时使用 `--managed-python`。

`requires-python = ">=3.12"` 表达项目支持的版本范围；`.python-version` 中的 `3.12` 表达本地选择。**先 `uv init` 再 `uv python pin 3.12` 与 `uv init -p 3.12` 不保证等价**：后者参与初始化版本要求，前者不会自动重写已存在的 `requires-python`。更改解释器前核对两者是否相容。要固定补丁版本，使用实际需要的完整版本号并验证可用性。

关于“刚安装的版本是否会成为项目版本”、已有3.12为何不自动变3.14以及一个项目多环境的完整例子，见 [[新电脑用uv管理Python：逐步操作与原理#进一步理解：安装、选择、创建与同步]]。

其他解释器操作：

```powershell
uv python list                  # 列可用与已安装的解释器
uv python install 3.11 3.12 3.13
uv python install 3.12 --default # 同时请求建立默认命名的可执行入口
uv python uninstall 3.12        # 只在确认没有环境仍依赖该解释器时执行
```

`--default` 不代表抹除其他 Python 安装；普通 `python` 最终指向谁仍由 PATH 和 Windows 执行别名共同决定。解释器通常在共享安装目录，虚拟环境可能仍依赖它；卸载前检查实际关联，而不是因为环境目录里有 `python.exe` 就认定可独立运行。

没有显式选择时，uv 的发现和偏好规则不等于“始终挑本机最高版本”。原稿报告过机器有 3.13.14 但项目选到 3.12 的情况；这属于来源观察，当前选择应使用 `uv python find` 与 `uv run python --version` 核对，再显式固定所需请求。

### 创建项目，选择布局

```powershell
uv init data-clean -p 3.12
cd data-clean
uv add pandas pyarrow
uv add --dev pytest ruff
uv run python -c "import sys, pandas; print(sys.executable); print(pandas.__version__)"
```

本机 uv 0.12.12 的默认模板是带构建系统的包项目：

```text
data-clean/
├── .python-version
├── pyproject.toml
├── README.md
└── src/data_clean/__init__.py
```

默认会尝试初始化 Git；上面的文件树未列出 Git 文件。已有仓库或关闭初始化时行为不同，显式关闭用 `--vcs none`。**`uv init` 不创建 `.venv` 与 `uv.lock`**；后续项目同步操作再生成它们。默认模板可能随版本变化，判断项目时读实际 `pyproject.toml`。

| 参数 | 意义 |
| --- | --- |
| 默认 / `--app` | 包应用，通常有 `src/`、构建系统和命令入口 |
| `--no-package` | 平铺脚本项目，有 `main.py`，不安装本项目为包 |
| `--lib` | 库模板，通常有类型标记，无默认 CLI 入口 |
| `--bare` | 最小元数据模板；通常只生成 `pyproject.toml`，不初始化 Git |
| `--script clean.py` | 单文件脚本的内联元数据 |

默认模板声明 `data-clean = "data_clean:main"`，因此可用 `uv run data-clean`。`uv run python -m data_clean` 要求包内有 `__main__.py`，不能把它当作这个入口的等价写法。单个模块有可执行入口时，可用 `uv run python -m data_clean.clean`。

#### 项目配置如何连到包和命令

本机 0.12.12 模板的关键结构如下；已有文件应编辑对应表，不重复追加同名表头：

```toml
[project]
name = "data-clean"
version = "0.1.0"
description = "Text table cleaning example"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
data-clean = "data_clean:main"

[build-system]
requires = ["uv_build>=0.12.12,<0.13.0"]
build-backend = "uv_build"
```

`project.name` 是分发名称，命令入口和导入包名是独立的名称。例如 `data-clean` 可对应 `data_clean` 包；`data_clean:main` 表示导入该模块并调用 `main()`。构建系统负责把项目构建、安装成包；没有构建系统的 `--no-package` 项目通常只安装依赖，不安装项目本身。后端版本范围是模板当时的约束，不是所有项目永远必须采用的版本。

初始化的其他选择：

```powershell
uv init --no-readme
uv init --no-pin-python
uv init --no-workspace
uv init --build-backend hatchling
```

前三个分别不生成 README、不固定本地 Python 请求、不自动加入上级工作区；最后一个更换构建后端。纯 Python 库可选 uv_build、Hatchling、Flit 或 setuptools 等；Rust 扩展、C/C++ 扩展可能选择 maturin、scikit-build-core 等，按项目的构建需求选择，无须把所有后端都装一遍。

### 维护依赖与同步

初学者先看 [[新电脑用uv管理Python：逐步操作与原理#uv sync：把项目配方落实成本机环境]]，理解同步的对象，再按本节选择依赖组、锁策略和升级操作。

```powershell
uv add "pandas>=2.2" "numpy<3"
uv add --dev pytest ruff
uv add --group docs mkdocs
uv add --optional plots matplotlib
uv remove numpy
uv tree
uv lock --upgrade-package pandas
```

普通依赖写入 `project.dependencies`；开发依赖写入 `dependency-groups.dev`，默认参与同步；自定义组用 `--group docs` 选择；可选依赖用 `--extra plots` 选择。默认组可以由项目配置改变。升级依赖后重新测试，不将“成功安装”视作兼容性证明。

| 依赖归属 | 声明命令 | 后续安装选择 |
| --- | --- | --- |
| 运行依赖 | `uv add requests` | 项目正常同步安装 |
| 开发组 dev | `uv add --dev pytest ruff` | 默认包含；`--no-dev` 排除 |
| 自定义组 docs | `uv add --group docs mkdocs` | 后续同步用 `--group docs`，或配置为默认组 |
| 可选功能 plots | `uv add --optional plots matplotlib` | 同步或运行时用 `--extra plots` |

`uv add` 通常完成“写声明 → 解析并更新锁 → 创建或同步环境”，但所选依赖组及 `--no-sync` 等参数会影响最后一步。自定义组并非必定永远不默认安装，需检查 `tool.uv.default-groups`。

```powershell
uv tree --depth 1
uv tree --outdated
uv lock --upgrade
uv sync --no-dev
uv sync --group docs
uv sync --extra plots
uv sync --all-extras --all-groups
uv sync --reinstall
```

`--all-extras` 与 `--all-groups` 用于确实需要全部功能和组的环境，互斥功能可能无法一起解析或安装。`--reinstall` 重装依赖，不能修复代码错误；`--upgrade` 在声明允许范围内升级，不能代替兼容性测试。

| 命令 | 锁文件处理 | 适用目的 |
| --- | --- | --- |
| `uv sync` | 必要时更新锁并同步环境 | 本地开发 |
| `uv sync --locked` | 校验锁与声明相容，不允许更新 | CI、部署前的一致性检查 |
| `uv sync --frozen` | 使用现有锁，跳过新鲜度检查 | 上游已验收锁文件后的受控安装 |
| `uv lock --check` | 检查锁是否需要更新 | 只检查，不安装环境 |
| `uv lock` | 创建或更新锁，不同步环境 | 先调整解析结果 |

本机实测：先锁定无依赖项目，再把 `requires-python` 从 `>=3.12` 改为 `>=3.11`，`--frozen` 退出码为 0；`--locked` 退出码为 1，提示锁需更新。**部署也可以优先用 `--locked`**，避免漏交锁文件；“生产必须 frozen”不是工具要求。

`uv sync` 默认精确同步，会移除锁中没有的包；`uv run` 默认保留额外包，同时补足需要的依赖，必要时会更新锁。需要运行时也拒绝锁变动，用 `uv run --locked ...`；`--no-sync` 跳过同步，不能用来验证环境完整。依据：[锁定与同步](https://docs.astral.sh/uv/concepts/projects/sync/)。

### 环境、脚本与工具各有入口

```powershell
uv venv --python 3.12
uv venv --seed
uv run python main.py
uv run --with rich python -c "from rich import print; print('hello')"
uv run --env-file .env python main.py
uv tool install ruff
uv tool list
uv tool upgrade --all
uv tool uninstall ruff
uvx ruff check .
```

项目通常不必先手动 `uv venv`；项目环境默认是 `.venv`。自定义名称或绝对路径都可用 `UV_PROJECT_ENVIRONMENT`，不要让多个项目共用一个会被精确同步的环境。uv 默认环境不依赖 pip；旧流程确实需要环境内的 pip 时才用 `--seed`。使用 `uv run` 不必激活环境。

本机验证 `uv venv list` 会创建 `list/`，并不会列环境。`uv python list` 列解释器，`uv tool list` 列工具。`uvx` 是 `uv tool run` 的别名，会在工具环境中安装或复用工具；它不是“完全不安装”。工具 PATH 可用 `uv tool update-shell` 配置，实际目录用 `uv tool dir --bin` 查询。

#### 项目初始化与手动环境是两种操作

| 操作 | 建立什么 | 不会自动替你做什么 |
| --- | --- | --- |
| `uv init` | 项目元数据、模板代码、可选版本请求 | 不立即建立项目环境 |
| `uv venv myenv` | 指定路径的环境 | 不声明项目依赖，不让所有项目自动改用它 |
| `uv add` / `uv sync` / 项目内 `uv run` | 按项目配置准备或更新环境 | 不把环境中所有手工安装都转成依赖声明 |

例如先 `uv venv myenv` 再创建默认 uv 项目，后续仍可能新建 `.venv`。要选用已有自定义环境，需要显式设置：

```powershell
$env:UV_PROJECT_ENVIRONMENT = "myenv"
uv sync --locked
# 切回默认项目环境，移除当前会话覆盖
Remove-Item Env:UV_PROJECT_ENVIRONMENT
```

绝对路径同样支持。切换后旧环境不会自动删除；确认不再使用后才清理。不要长期把一个全局环境路径用于多个项目。

已有环境需要重建时可使用 `uv venv --clear .venv`，**它会删除目标环境中的内容**，必须先确认 `.venv` 是可重建环境而非代码或数据目录；通常也可在确认后移除旧环境，再用项目同步重建。`--seed` 会按解释器版本和选项加入所需种子包，不承诺每个版本都同时含 pip、setuptools 与 wheel。`uv env` 不是虚拟环境管理入口。

可选的激活与退出方式：

```powershell
.\.venv\Scripts\Activate.ps1
deactivate
```

CMD 用 `.venv\Scripts\activate.bat`，Git Bash 用 `source .venv/Scripts/activate`；Linux 的 Bash 环境通常为 `source .venv/bin/activate`。激活是当前 Shell 的状态变化，`uv run` 和直接调用解释器都可不激活。

#### 执行形式与独立工具

```powershell
uv run main.py
uv run -m http.server 8000
uv run --no-sync python main.py
uv tool install --python 3.12 mypy
uv tool install httpie --with requests
uvx --from httpie http GET https://example.com
uvx --python 3.12 cowsay hello
```

`--from` 指定提供命令的分发包，适用于命令名和包名不同的情况；`--with` 给工具或这次运行补充依赖，不会因此成为业务项目的直接依赖。项目内的 ruff 应用 `uv run ruff`，它遵循项目锁；`uvx ruff` 在独立工具环境运行，版本可能不同。工具环境同样不是业务项目的 `.venv`。

单文件脚本可以声明自己的依赖：

```powershell
uv init --script clean.py -p 3.12
uv add --script clean.py pandas pyarrow
uv run clean.py
uv lock --script clean.py
```

前三步提供隔离的运行方式，但只声明依赖没有固定传递依赖版本。需要重复运行的确定性时，保留脚本锁文件并验证 `uv run --locked clean.py`。多人维护、多模块或复杂测试适合项目路线，判断依据是组织需求，无须规定“超过几个文件就必须建项目”。参看 [脚本指南](https://docs.astral.sh/uv/guides/scripts/)。

脚本头使用 PEP 723 内联元数据，形如：

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "rich"]
# ///
```

其作用是声明脚本运行要求，uv 可在独立环境中满足要求；它与项目的 `pyproject.toml` 是不同的管理入口。可手写合法元数据，也可用 `uv add --script` 维护，后者有助于减少语法差错。普通脚本在项目内运行时可能使用项目环境；带内联依赖的脚本不能简单视为与 `uv run python script.py` 在所有情形下都等价。

#### 保留已有 requirements 工作流

```powershell
uv venv --python 3.12
uv pip install -r requirements.txt
uv pip install -e .
uv pip list
uv pip show pandas
uv pip freeze
uv pip check
uv pip uninstall requests
uv pip compile requirements.in -o requirements.txt
uv pip sync requirements.txt
```

`uv pip compile` 解析输入声明并输出固定版本清单；`uv pip sync` 让所选环境精确匹配清单，而 `uv pip install` 通常保留无关已装包。它们可以服务于非 uv 项目，不必为使用 uv 的安装器强制迁移管理体系。默认应先准备目标虚拟环境；`--python <路径>` 可以明确目标，`--system` 请求操作系统解释器环境，会影响其他使用者，不能当成“找不到环境”的通用补救。

`uv pip check` 核对已安装依赖的兼容要求，不代替运行测试。将 requirements 导入 uv 项目时才用 `uv add -r ...`；原稿“不要用 uv pip 导入”应理解为不能靠它维护 uv 项目声明，而非该命令本身无用。

导出前先看清重定向符号：**`>` 覆盖目标文件，`>>` 才追加**。目录里已有 `requirements.txt` 时，`pip freeze > requirements.txt` 会先把它清空再写入；要保留手工维护的内容就别用导出覆盖它，而追加导出通常会产生重复条目，一般不如重新导出。另有按源码 `import` 反推依赖的第三方工具（如 pipreqs），清单更短，但只看静态导入，动态导入和不经过 `import` 的依赖会漏掉；本轮未在本机验证，采用前先与 `uv export` 的结果比对。

### 迁移与交付

已有项目先检查是否已有 `pyproject.toml` 与构建配置；不要盲目覆盖。只有确实缺少项目声明时才用 `uv init --bare`，随后将适合的运行依赖导入：

```powershell
uv add -r requirements.txt
uv sync --locked
```

导入固定版本清单后，检查直接依赖是否混入了大量传递依赖，以及本机路径、平台标记是否适合交付。`environment.yml` 中的 Conda 非 Python 包不能直接等同于 PyPI 包。旧 requirements 是否删除，取决于 CI、部署和其他消费者是否仍需要它。

uv 使用者交付代码、`pyproject.toml`、`uv.lock` 与必要的 `.python-version`，接收者执行 `uv sync --locked`。忽略 `.venv/`、缓存、敏感凭据与不应提交的业务数据。迁到 Linux 的具体案例参看 [[Windows到Linux部署Python项目]]。

只交付第三方依赖给 pip 消费者时：

```powershell
uv export --format requirements-txt --no-dev --no-emit-project -o requirements.txt
uv export --format pylock.toml -o pylock.toml
```

默认保留哈希；仅在消费者确实不支持时考虑 `--no-hashes`。`--no-emit-project` 排除项目自身，**不是所有导出都必须加**：消费者还需要安装项目时，应保留或单独交付项目。`uv pip freeze` 是当前环境快照，可能带本地可编辑路径；应检查实际输出，不能称其必定不可交付。`uv freeze` 不是本机有效命令。

| 接收到的材料 | 接入方式 | 需要额外核对 |
| --- | --- | --- |
| uv 项目代码、声明与锁 | `uv sync --locked` | 平台、Python 选择、源码与入口 |
| requirements 清单 | 继续 pip 接口，或 `uv add -r` 迁移 | 直接/传递依赖、本地路径、环境标记 |
| 包名与约束 | `uv add "pandas>=2.2"` 等 | 解析结果满足兼容范围，不保证选绝对最新版本 |
| Conda `environment.yml` | 按依赖性质迁移或继续 Conda | 渠道包名、系统库、CUDA 等非 PyPI 内容 |

常用 Git 忽略项：

```gitignore
.venv/
__pycache__/
*.pyc
.env
data/
```

最后两项按项目实际需求决定：敏感凭据应排除，测试夹具或需要协作的非敏感小数据可以单独保留。`uv build` 生成分发包，适用于正确配置构建系统的项目；打包与运行验收不同，也不意味着别人无需处理依赖。

#### 声明四个包，为何导出八个包

以原稿 v1 为例，声明 `requests`、`pymysql`、`python-dotenv`、`pycryptodome` 是**直接依赖**；requests 又需要 certifi、charset-normalizer、idna、urllib3 等**传递依赖**。导出多出这些条目是正常的依赖树展开，不能据此判断是另一个项目。具体依赖关系以实际版本元数据、`uv tree` 与锁为准。

| 内容 | 回答的问题 |
| --- | --- |
| `pyproject.toml` | 项目主动要求什么；通常是范围约束 |
| `uv.lock` | 解析选了哪些直接／传递依赖及平台条件 |
| `uv pip freeze` | 目标环境实际装了哪些分发；也包含已安装传递依赖 |
| `uv export` | 从项目锁导出指定组／extra／平台标记所表达的依赖 |

`uv export` 不要求预先激活；它定位项目与锁，不会在找不到项目时退化为“导出当前环境”。当前或父目录的项目发现、工作区和导出选项均可能影响结果。哈希和多平台标记让文本更长，长度不是正确性的标准。

要排查“导出和声明不对应”，在项目根目录依次看：

~~~powershell
Get-Location
Get-Content -LiteralPath .\pyproject.toml
uv lock --check
uv tree
uv export --locked --format requirements-txt --no-dev --no-emit-project -o requirements-exported.txt
Get-Content -LiteralPath .\requirements-exported.txt
~~~

先检查命令成功与退出码，再核对运行依赖、开发组、extras、项目本身、本地路径和标记。`-o` 指定输出文件，也会覆盖同名文件；本例使用另一名字，避免覆盖手写清单。导出缺少直接依赖时检查所选项目、组和条件，不能直接猜“pip 不认识 uv”。[导出说明](https://docs.astral.sh/uv/concepts/projects/export/)

原稿的外部 txt 链接没有随文档附带完整文件，本轮未据它们判断用户的真实 requirements 是否有错。原稿列出的具体版本也只是当时对话观察，不作为此刻的安装推荐。

#### hash 是文件指纹，不是安全或兼容性证明

`--hash=sha256:...` 记录某个分发文件的 SHA-256 摘要。同一包版本可能有多个平台 wheel 和源码归档，每个文件有不同摘要，导出出现多行 hash 很正常。

像交货时称重核对封条：下载文件按给定算法得到的摘要与可信明细相同，可以检查文件是否符合明细；**不能证明代码无恶意、没有漏洞或适合业务**。明细本身的来源也必须可信，哈希不是签名，亦不是数学上保证永不碰撞的身份证。

pip 消费者要求严格哈希校验时可用：

~~~powershell
python -m pip install --require-hashes -r requirements-exported.txt
~~~

该模式要求完整固定及哈希覆盖，编辑安装、本地源码、选项差异可能使清单不满足要求，不能对任意 export 输出承诺都成功。对 uv 的 pip 接口也可显式 `uv pip install --require-hashes -r requirements-exported.txt`；先准备并明确目标环境。业务项目本身若被 `--no-emit-project` 排除，要另行交付与安装。依据：[pip 安全安装与哈希检查](https://pip.pypa.io/en/stable/topics/secure-installs/)、[uv pip 接口](https://docs.astral.sh/uv/pip/).

#### pyproject.toml 由命令维护哪些部分

`uv add`／`uv remove` 管理依赖；`uv lock --upgrade-package requests` 更新解析结果，**不意味着重写所有兼容范围或已经同步环境**。随后按需 `uv sync --locked` 并测试。名称、描述、支持 Python 范围、`[project.scripts]` 和构建系统等可以且经常需要人工编辑，编辑后检查锁与运行。

原稿 `v1 = "v1.main:main"` 意味着安装项目后提供命令 v1，它导入 `v1.main` 并调用 `main` 函数。它不是在当前目录随便找 `main.py`；源码布局、构建配置和项目安装须匹配。`requires-python = ">=3.13"` 也意味着选择 3.12 时不相容，不能单靠 `uv python pin 3.12` 越过项目声明。


## 网络与 Windows 配置：按证据调整

### 包索引和解释器下载分别配置

网络正常可直接用默认源。包索引与解释器下载地址是两条链路；只有受影响的链路需要调整。镜像可能存在同步延迟、缺包或可用性变化，哈希匹配证明下载内容与记录一致，不能独立证明来源可信。

如选择清华 PyPI 镜像，可在用户级 `$env:APPDATA\uv\uv.toml` 合并以下内容，**先读已有文件，避免覆盖其他配置**：

```toml
[[index]]
name = "tuna"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

项目级 `pyproject.toml` 改用 `[[tool.uv.index]]`；单独的 `uv.toml` 不带 `tool.uv` 前缀。命令行优先于环境变量；文件配置通常是项目高于用户、高于系统，同目录 `uv.toml` 优先于 `pyproject.toml`。多层配置会合并，列表设置尤其不能当成简单覆盖。工具命令忽略项目配置，使用用户或系统配置。参看 [配置文件规则](https://docs.astral.sh/uv/concepts/configuration-files/) 和 [清华镜像使用帮助](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)。

`default = true` 替换隐含的 PyPI，且该默认索引优先级最低；多个索引默认按 `first-index` 选择第一个包含包的索引。**这不是网络故障时的主备切换承诺**。私有包可在项目中用 `tool.uv.sources` 指定命名索引，并按需用 `explicit = true` 限制索引用途，避免只靠顺序判断。依据：[包索引](https://docs.astral.sh/uv/concepts/indexes/)。

CPython 下载另由 `python-install-mirror` 或 `UV_PYTHON_INSTALL_MIRROR` 控制。该 URL 替换官方的 `https://github.com/astral-sh/python-build-standalone/releases/download` 前缀，镜像必须提供匹配的版本、文件名和路径；不要把任意 GitHub 代理直接当作可用镜像。原稿中的地址保留在下面作为待核验候选，并非保证可用的配置。参看 [镜像设置定义](https://docs.astral.sh/uv/reference/settings/#python-install-mirror)。

临时选择包源可用 `$env:UV_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"`；验证请求地址用 `-v` 日志。新配置写成无 BOM UTF-8，可跨 PowerShell 5.1 与 7 避免编码差异。本机没有 `uv config`，用 `Get-Content` 查看文件、检查相关环境变量，再用详细日志确认效果。

#### 把配置真正写到文件

首次建立用户配置的例子如下。选择清华源的 TOML 写法已经核对；本轮该镜像请求曾返回 403，因此先在自己的网络环境验证。已有配置时该例明确停止，应打开文件合并所需项，保留原有设置。

```powershell
$uvConfigDir = Join-Path $env:APPDATA "uv"
$uvConfigFile = Join-Path $uvConfigDir "uv.toml"
New-Item -ItemType Directory -Path $uvConfigDir -Force | Out-Null
if (Test-Path -LiteralPath $uvConfigFile) {
    throw "已有 uv.toml，请打开并合并配置，不直接覆盖"
}
$uvConfigText = @'
[[index]]
name = "tuna"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
'@
[System.IO.File]::WriteAllText(
    $uvConfigFile, $uvConfigText, [System.Text.UTF8Encoding]::new($false)
)
Get-Content -LiteralPath $uvConfigFile
```

`@' ... '@` 是单引号 here-string，不展开变量；起始标记后换行，结束标记置于行首。这两行是 PowerShell 语法，手动在编辑器创建 TOML 时不粘贴它们。`UTF8Encoding($false)` 表示不写 BOM；PowerShell 7 可用 `utf8NoBOM`，上面的 .NET 写法也适用于 5.1。

手动路径：`Win + R` 输入 `%APPDATA%` → `uv` 目录 → 创建 `uv.toml` → 粘贴 TOML 内容 → 用 UTF-8 无 BOM 保存。显示文件扩展名，确认不是 `uv.toml.txt`。

若已验证某个 CPython 镜像，需要同时设置两个链路，可采用如下结构；`python-install-mirror` 放在文件顶层、数组表头之前，替换占位地址后再使用：

```toml
python-install-mirror = "https://your-verified-mirror.example/python-build-standalone"

[[index]]
name = "tuna"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

相应项目级配置要保留命名空间：

```toml
[tool.uv]
python-install-mirror = "https://your-verified-mirror.example/python-build-standalone"

[[tool.uv.index]]
name = "tuna"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

用户级只影响当前用户；项目级配置可随代码交付统一行为。项目不需要 uv 专用配置时，只有 `pyproject.toml` 与锁文件就够，不为了完整目录树另建空 `uv.toml`。

#### 环境变量的临时、永久与撤销

```powershell
# 当前会话
$env:UV_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
# 后续进程的用户环境；不会自动更新当前会话中的变量
[Environment]::SetEnvironmentVariable(
    "UV_DEFAULT_INDEX", "https://pypi.tuna.tsinghua.edu.cn/simple", "User"
)
# 查看与撤销当前会话覆盖
Get-Item Env:UV_DEFAULT_INDEX -ErrorAction SilentlyContinue
Remove-Item Env:UV_DEFAULT_INDEX -ErrorAction SilentlyContinue
# 撤销用户级永久覆盖
[Environment]::SetEnvironmentVariable("UV_DEFAULT_INDEX", $null, "User")
```

这些操作分别示范不同作用范围，不是一套应无脑连续执行的安装步骤。配置文件看起来正确而结果不符时，先检查是否有环境变量覆盖，不反复重写文件。

#### 原材料提供的镜像候选

保留地址是为了可查询和复核；没有完成端到端下载验证的条目标为待核验。镜像的包同步、目标版本与网络可达性须分别判断。

| 类型 | 名称 | 原稿地址 | 当前依据 |
| --- | --- | --- | --- |
| PyPI | 清华 | `https://pypi.tuna.tsinghua.edu.cn/simple` | 官方使用帮助已核对；本轮下载请求返回 403 |
| PyPI | 阿里 | `https://mirrors.aliyun.com/pypi/simple/` | 原稿候选，待核验 |
| PyPI | 腾讯 | `https://mirrors.cloud.tencent.com/pypi/simple/` | 原稿候选，待核验 |
| PyPI | 华为 | `https://mirrors.huaweicloud.com/repository/pypi/simple` | 原稿候选，待核验 |
| CPython | 南京大学 | `https://mirror.nju.edu.cn/github-release/astral-sh/python-build-standalone/` | 原稿候选，未完成目标发行包下载测试 |
| CPython | 兰州大学 | `https://mirror.lzu.edu.cn/github-release/astral-sh/python-build-standalone/` | 原稿候选，待核验 |
| CPython | npmmirror | `https://registry.npmmirror.com/-/binary/python-build-standalone/` | 原稿候选，待核验 |
| GitHub 代理 | ghfast | `https://ghfast.top/https://github.com/astral-sh/python-build-standalone/releases/download` | 原稿候选；不是专门的 CPython 镜像，路径规则、信任与可用性均待核验 |

旧资料可能指向 `indygreg/python-build-standalone`；当前 uv 默认下载前缀是 `astral-sh/python-build-standalone`。镜像是否维护旧路径应单独验证，不能因默认仓库已迁移就认定所有旧镜像都返回 404。

验证配置时，下载命令本身会产生安装效果，应在确实需要的环境执行：

```powershell
uv python install 3.12 -v
uv add requests -v
```

前者检查解释器链路，后者检查项目包链路；已经安装或命中缓存时，可能根本不发下载请求，没有新 URL 日志不证明配置失效。`uv add` 会修改项目声明，不把它当成无副作用的配置查看器。

检查 BOM 可读取文件前三字节：

```powershell
$uvConfigBytes = [System.IO.File]::ReadAllBytes($uvConfigFile)
$hasBom = $uvConfigBytes.Length -ge 3 -and
    $uvConfigBytes[0] -eq 239 -and $uvConfigBytes[1] -eq 187 -and $uvConfigBytes[2] -eq 191
$hasBom
```

`True` 表示 UTF-8 BOM。无 BOM 并不要求前三字节必须是 `112,121,116`，那只是原稿恰以 `python-install-mirror` 开头；以注释或 `[[index]]` 开头的合法文件当然不同。

#### 多索引顺序与私有包

下面的用户配置中，阿里索引优先于标为 default 的清华索引，与“清华主源、阿里备用”的直觉相反：

```toml
[[index]]
name = "tuna"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true

[[index]]
name = "aliyun"
url = "https://mirrors.aliyun.com/pypi/simple/"
```

它说明默认索引的优先级，不保证两个镜像此刻的内容与可用性相同。若只是替换公网包源，选一个经验证的索引通常更易排错。

企业私有包可显式绑定项目索引，示意如下，域名和包名需替换为实际值：

```toml
[[tool.uv.index]]
name = "company"
url = "https://packages.example.com/simple"
explicit = true

[tool.uv.sources]
company-utils = { index = "company" }
```

这同时保留私有包的来源约束与默认公开索引。认证另按公司要求处理，凭据不写进公开配置。`first-index` 能减少同名包跨索引混用的风险，但没有私有源、命名策略和配置正确性的前提，就不能声称彻底避免依赖混淆。

### 排错速查

| 现象 | 证据与处理 |
| --- | --- |
| 找不到 uv | `Get-Command uv`、安装日志和用户 PATH；重开终端宿主 |
| 包装好了仍不能导入 | `uv run python -c "import sys; print(sys.executable)"`；检查 IDE 解释器 |
| PowerShell 激活受阻 | 优先 `uv run` 或直接解释器路径；需激活时核对组织执行策略 |
| `uv venv myenv` 后项目另建 `.venv` | 默认项目环境未更改；显式配置 `UV_PROJECT_ENVIRONMENT` |
| 跨盘硬链接警告 | 查询 `uv cache dir`；可设当前会话 `$env:UV_LINK_MODE = "copy"`，或按需求把缓存放同卷 |
| TOML 无法解析 | 核对结构、引号、编码与实际错误；PowerShell 5.1 的 UTF-8 输出可能带 BOM |
| 路径太长 | 检查实际出错工具；浅目录有帮助，系统长路径设置也需应用配合 |
| 中文、空格路径报错 | 先看完整报错和引号处理，不能一概认定路径不合法 |
| 安装慢或失败 | `-v` 分清索引、解释器下载、编译和扫描阶段；按实际原因处理 |
| Windows ARM64 | 检查 uv 架构与包的 wheel 支持；uv 可运行不代表依赖都可用 |

不把关闭安全软件或大范围排除项目目录作为默认优化。硬链接同卷才可用；退回复制影响取决于包大小和磁盘，不能给出固定的速度结论。

#### 常用环境变量与目录设置

| 变量 | 作用 | 使用边界 |
| --- | --- | --- |
| `UV_DEFAULT_INDEX` | 默认包索引 | 与额外索引、配置文件共同决定解析来源 |
| `UV_PYTHON_INSTALL_MIRROR` | uv 管理的 CPython 下载前缀 | 不影响 PyPI 包索引 |
| `UV_PYTHON_INSTALL_DIR` | uv 管理的解释器安装目录 | 改路径不自动迁移已有安装与环境关联 |
| `UV_CACHE_DIR` | 缓存位置 | 同卷有利于硬链接复用 |
| `UV_PROJECT_ENVIRONMENT` | 项目环境路径 | 相对或绝对路径均可，避免多项目共用 |
| `UV_LINK_MODE` | 安装链接模式 | Windows 默认 hardlink，可选 copy、clone、symlink；能力受文件系统约束 |
| `UV_NO_MODIFY_PATH` | 安装器不修改 PATH | 安装器选项，不是项目运行开关 |
| `UV_PYTHON` | 解释器选择请求 | 仍须满足项目版本约束 |
| `UV_OFFLINE` | 禁止联网 | 资源不足会失败，不代表资源已完整缓存 |
| `UV_NO_SYNC` | 运行时不进行环境同步 | 以现有环境运行，不检验其完整性 |
| `UV_ENV_FILE` | 运行时加载环境变量文件 | 与 `.venv` 路径或包依赖是不同概念 |
| `UV_VENV_CLEAR` | 允许清空重建环境目标 | 对应 venv 的 `--clear`，避免设为全局长期默认 |
| `UV_TORCH_BACKEND` | PyTorch 包后端选择 | 如 auto 或具体后端；不替你安装系统驱动 |
| `HTTP_PROXY` / `HTTPS_PROXY` | HTTP/HTTPS 代理 | 依组织网络和认证要求配置 |

变量名称与用途按 [官方环境变量表](https://docs.astral.sh/uv/reference/environment/) 核对，具体版本的选项以本机 `uv help` 为准，本轮没有逐项修改或执行。安装器的选项另看 [官方安装器配置](https://docs.astral.sh/uv/reference/installer/)。

原稿提到的 PyTorch 操作形如 `uv pip install torch --torch-backend=auto`。自动选择后端仍要匹配驱动、平台和包版本，不保证自动解决 CUDA 环境；本轮没有安装或测试 PyTorch。

例如项目在 D 盘、缓存默认在 C 盘，可按目的选择当前会话复制模式，或将缓存放到同卷：

```powershell
$env:UV_LINK_MODE = "copy"
# 或选择当前会话的缓存位置
$env:UV_CACHE_DIR = "D:\uv-cache"
```

长期采用某项设置才写用户环境变量，如 `[Environment]::SetEnvironmentVariable("UV_CACHE_DIR", "D:\uv-cache", "User")`，然后重开终端。不要仅为去掉一个警告就无条件给所有项目固定 copy。

#### 长路径、编码与安全扫描怎么排查

传统 Windows API 的 MAX_PATH 限制可能在深层依赖目录中出现。先用浅目录复现并确认出错工具；系统长路径支持还要求应用配合，不能称改一个注册表项就彻底解决所有程序。

```powershell
Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled
```

组织允许且确需修改时，可在管理员 PowerShell 将该值设为 1：

```powershell
New-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

这只是可选操作示例，本轮未执行。程序可能已缓存设置，需要重启相关进程或机器，应用仍需支持长路径。参看 [Microsoft 长路径条件](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)。

安全软件可能影响下载、文件创建或扩展模块扫描，证据应来自拦截记录或安装日志。中文用户名、空格路径也应先检查参数引用和构建工具报错；确认某个旧构建器不兼容后再换浅路径，不能把猜测写成一律避开中文的规则。

### 缓存、离线与卸载边界

```powershell
uv cache dir
uv cache prune
uv cache clean requests
uv tool dir
uv python dir
```

Windows 常见默认缓存位于 `%LOCALAPPDATA%\uv\cache`，以查询为准。`uv cache clean` 清缓存，不卸载项目依赖。硬链接仍有环境目录中的链接时，删除缓存链接不会使其失效；符号链接模式才可能因缓存目标删除而破坏环境。用 uv 的清理命令，不手动编辑缓存内部。依据：[缓存说明](https://docs.astral.sh/uv/concepts/cache/)。

`uv sync --offline` 只能使用已经可用的解释器、依赖与构建资源；联网执行一次 `uv sync` 不保证缓存覆盖另一平台或 Python 版本。离线交付需按目标系统准备资源，并在断网条件下演练。另一条路线是导出依赖，在匹配目标环境的联网机器用 `python -m pip download --only-binary=:all: -r requirements.txt -d wheels` 准备 wheel，然后在目标机器先 `uv venv`，再 `uv pip install --no-index --find-links ./wheels -r requirements.txt`。本项目代码须另行交付；没有对应 wheel 时不能假定此方案成立。

卸载 uv 与删除其解释器、工具、缓存是不同操作。先查询并记录实际路径，检查是否仍被其他项目使用，再由原安装方式卸载 uv；只有确定不再需要时才删除对应数据目录。不要复制“查询结果直接递归删除”的整套命令，也不要顺手清掉安装目录中不属于 uv 的工具。

完整清缓存用 `uv cache clean`，按包清理用 `uv cache clean requests`，常规回收用 `uv cache prune`。uvx 的临时工具环境可以存放在缓存中，清缓存后可能需重建；这与项目硬链接包文件的生命周期不同。`UV_PYTHON_INSTALL_DIR`、`uv tool dir` 和 `uv cache dir` 分别管不同数据，卸载 uv 二进制不等于这些数据全被移除。

有原安装管理器时可使用 `winget uninstall --id astral-sh.uv --exact`、`scoop uninstall uv`、`pipx uninstall uv`，或在原 Python 安装环境用 `python -m pip uninstall uv`。独立安装器对应的二进制与配置应逐路径确认后清理；需要保留解释器或工具时不删除相应目录。

独立安装的候选二进制包括 `uv.exe`、`uvx.exe` 和某些版本提供的 `uvw.exe`，以安装目录实际文件为准。先 `Get-Command uv` 定位，记录 `uv python dir`、`uv tool dir`、`uv cache dir`；确认对应文件后可逐个用 `Remove-Item -LiteralPath <已核对的完整文件路径>` 移除。配置目录常为 `%APPDATA%\uv`，是否清理取决于是否仍需保留配置；不要把 `.local\bin` 整个工具目录删除，也不要静默忽略所有清理失败。

## 实践：一个有明确边界的 CSV → Parquet 项目

本例只处理**全部按文本读取的表格**：规范列名和首尾空白、把空字符串转为缺失、删除全空行、按整行去重。`NA` 等业务字符串保留；不猜数字、日期或业务主键。只有业务确认整行重复可删除时才采用本策略。Parquet 会保留这里的文本类型，不会替你恢复数字类型。

### 建目录、初始化与安装依赖

若已经建立前文的 `data-clean` 项目，直接进入项目并继续，不重做初始化。首次建立时，在选定的代码父目录执行：

```powershell
uv init data-clean -p 3.12
cd data-clean
New-Item -ItemType Directory -Path data\raw, data\processed, tests -Force | Out-Null
uv add pandas pyarrow
uv add --dev pytest ruff
```

检查 `.gitignore` 是否已含环境、缓存和 `data/` 等需排除内容；测试输入不含秘密的小样本可放在测试夹具中。所选 Python 已存在时不会每次重新下载；缺少时才按允许的下载策略补齐。

预期结构：

```text
data-clean/
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── .venv/                     # 本机可重建，不提交
├── data/raw/input.csv         # 按业务确定是否可提交
├── src/data_clean/
│   ├── __init__.py
│   └── clean.py
└── tests/test_clean.py
```

### 清洗实现与命令入口

用前面的 `data-clean` 项目，在 `src/data_clean/clean.py` 写入：

```python
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def clean_text_table(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy().astype("string")
    names = pd.Index(result.columns).astype("string")
    names = names.str.strip().str.lower().str.replace(r"[\s-]+", "_", regex=True)
    if names.has_duplicates or names.isna().any() or (names == "").any():
        raise ValueError("规范化后列名为空或重复，请先处理字段映射")
    result.columns = names
    for column in result.columns:
        result[column] = result[column].str.strip().replace("", pd.NA)
    return result.dropna(how="all").drop_duplicates().reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="文本 CSV 规范化并输出 Parquet")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    frame = pd.read_csv(args.source, dtype="string", keep_default_na=False)
    result = clean_text_table(frame)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(args.destination, index=False)
    print(f"{len(frame)} -> {len(result)} 行：{args.destination}")


if __name__ == "__main__":
    main()
```

将 `pyproject.toml` 中该命令入口改为：

```toml
[project.scripts]
data-clean = "data_clean.clean:main"
```

```powershell
uv run data-clean data/raw/input.csv data/processed/output.parquet
uv run pytest
uv run ruff check .
```

后两条需要你已编写测试和安装相应工具；无测试文件时 `pytest` 不会证明代码正确。至少核对：`" x "` 与 `"x"` 规范后去重，全空白行被删除，`"NA"` 被保留，列名碰撞明确报错，输出 Parquet 可读。数据对齐与选择机制参看 [[Pandas索引与数据对齐]]，异常和测试设计参看 [[Python文件异常与测试]]。

入口有两种可选组织方式，任选一种：当前采用 `data_clean.clean:main`，直接绑定到实现模块；若保留默认 `data_clean:main`，则在 `src/data_clean/__init__.py` 显式导出函数：

```python
from data_clean.clean import main

__all__ = ["main"]
```

两者都需包正确安装。不要既改变配置又误以为必须在所有模块重复导出。带 `if __name__ == "__main__"` 的实现还可以用 `uv run python -m data_clean.clean ...` 执行，参数仍需传入。

### 可直接使用的测试

写入 `tests/test_clean.py`：

```python
from pathlib import Path

import pandas as pd
import pytest

from data_clean.clean import clean_text_table, main


def test_normalize_column_names():
    frame = pd.DataFrame({"User Name": ["a"], "Age-Group ": ["b"]})
    assert list(clean_text_table(frame).columns) == ["user_name", "age_group"]


def test_trim_then_deduplicate_and_drop_blank_rows():
    frame = pd.DataFrame({"a": [" x ", "x", " ", None], "b": ["1", "1", "", None]})
    assert clean_text_table(frame).to_dict("list") == {"a": ["x"], "b": ["1"]}


def test_preserve_codes_as_text():
    frame = pd.DataFrame({"code": ["NA", "001", 7]})
    assert clean_text_table(frame)["code"].tolist() == ["NA", "001", "7"]


@pytest.mark.parametrize("columns", [["A", " a "], [" "]])
def test_reject_invalid_normalized_columns(columns):
    frame = pd.DataFrame([["x"] * len(columns)], columns=columns)
    with pytest.raises(ValueError):
        clean_text_table(frame)


def test_csv_to_parquet(tmp_path: Path, monkeypatch):
    source = tmp_path / "input.csv"
    destination = tmp_path / "out" / "table.parquet"
    source.write_text("User Name,Code\n x ,NA\nx,NA\n , \ny,001\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["clean.py", str(source), str(destination)])
    main()
    assert pd.read_parquet(destination).to_dict("list") == {
        "user_name": ["x", "y"], "code": ["NA", "001"]
    }
```

```powershell
uv run pytest
uv run ruff check .
uv run ruff format .
```

pytest 验证行为，ruff check 检查静态问题，ruff format 统一格式；三者的成功含义不同。本例的断言是对明确定义的文本清洗策略验收，不是所有业务清洗项目的通用正确答案。

### 从运行到交付的一条完整路径

1. 把真实 CSV 放到 `data/raw/input.csv`，核对编码、分隔符和清洗策略，必要时调整读取选项。
2. 执行 `uv run data-clean data/raw/input.csv data/processed/output.parquet`，检查日志、实际输出和业务口径。
3. 跑上述测试及静态检查，确认代码与声明一致，再 `uv lock --check` 检查锁。
4. 交付代码、声明、锁、所需版本请求和测试；接收者从 `uv sync --locked` 重建，数据按约定另外准备，不能假设 clone 后已经有业务输入。
5. 需要 Linux 定时运行时，接 [[Windows到Linux部署Python项目]] 的服务器与调度验收流程，不复制 Windows `.venv`。

### 旧习惯到 uv 的对应关系

| 旧任务 | uv 路线 | 不是完全等价的地方 |
| --- | --- | --- |
| `python -m venv .venv` | `uv venv` | 默认种子包不同，uv 环境不必自带 pip |
| 激活后 `python script.py` | `uv run script.py` | 项目同步、内联脚本依赖等行为需按上下文判断 |
| `pip install X` | 项目用 `uv add X`；环境用 `uv pip install X` | 前者维护声明与锁，后者只操作环境 |
| `pip freeze` | 项目交付优先 `uv export` | 一个观察已装环境，一个读取项目解析结果 |
| `pip-compile` | requirements 路线用 `uv pip compile`；项目用 `uv lock` | 输出格式与管理边界不同 |
| `pipx install` / 临时工具 | `uv tool install` / `uvx` | 与业务项目环境分开 |
| pyenv 安装 / 本地选版本 | `uv python install` / `uv python pin` | 预构建来源、平台支持和选择规则不同 |
| Poetry 添加 / 同步 | `uv add` / `uv sync` | 迁移时核对配置、组和来源，不只替换命令名 |
| Conda 建环境 | Python 部分可用 `uv venv --python ...` | 不负责等价重建 Conda 系统级包集合 |

日常快速回忆依次查：`uv add/remove`（声明）、`uv lock`（解析）、`uv sync --locked`（验收环境）、`uv run`（执行）、`uv tree`（观察依赖）、`uv export/build`（交付）。上表集中表达对应关系，具体参数和示例在前文，避免重复维护多份流程。

## 现阶段认知

日常用“声明 → 锁定 → 同步 → 运行”理解项目，用“文件或环境 → 实际解释器”定位故障。工具版本、平台、包源和业务清洗规则分别验证；环境能重建、代码能运行与业务结果正确是三个检查点。
