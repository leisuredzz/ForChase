# Windows → Linux：使用 uv 部署 Python 项目与每日定时任务

> **先修**：[[Python环境与依赖]]、[[Python模块导入与包管理]]；[[API到MySQL数据采集实战]] 只是本篇使用的项目实例。
> **建议阅读**：[[uv项目管理与Windows配置]]，理解声明、锁文件与项目环境；本篇负责服务器迁移与定时执行。
> 面向服务器与 Python 初学者的操作、理解和排查手册。
>
> 案例：将 Windows 上的 V1 库存同步项目迁移到 Linux 服务器，每天北京时间 08:00 执行一次。
>
> 本手册根据本次真实部署过程整理。案例中的路径可以直接用于本次 V1；迁移其他项目时，请先替换路径、用户名和启动命令。
> **核验状态**：部分实测——按一次真实部署过程整理；本机没有相同的服务器环境，步骤未能复跑验证。详见 [[知识库质量审计]]。

## 1. 先理解：我们到底部署了什么？

部署不是“把电脑上的所有文件原样搬到服务器”。本次迁移分为四件事：

1. **搬代码与配置**：上传源代码、依赖记录和必要的数据配置。
2. **重建运行环境**：在 Linux 上安装 uv，创建 Linux 的 Python 虚拟环境。
3. **验证业务运行**：先手动执行一次，确认接口访问和数据库写入正常。
4. **交给系统定时执行**：用 systemd 配置“执行什么”和“什么时候执行”。

```text
Windows 项目
  │ 打包代码、依赖记录、必要配置，不包含 Windows 虚拟环境
  ▼
上传到 Linux → 解压 → uv sync → 手动验证
                                 │
                                 ▼
每天北京时间 08:00 → systemd 定时器 → V1 同步库存 → 结束并记录日志
```

### 本次案例信息

| 项目 | 本次值 |
|---|---|
| 本地项目 | `C:\Users\NOTO-财务经理\Desktop\VS\V1` |
| 服务器系统 | Alibaba Cloud Linux 3，x86_64 |
| 服务器服务管理器 | systemd |
| 当前部署用户 | root |
| 服务器项目路径 | `/root/apps/V1` |
| 服务器 uv 路径 | `/root/.local/bin/uv` |
| 项目 Python 版本约束 | `.python-version` 为 `3.13` |
| 实际验证的 Python | Python 3.13.15 |
| 本地启动命令 | `uv run v1` |
| 服务器启动命令 | `/root/.local/bin/uv run --locked v1` |
| 任务类型 | 执行一次后退出 |
| 计划时间 | 每天北京时间 08:00 |

> **安全说明：本次沿用 root 完成部署，便于先跑通。正式长期运行建议使用专用普通用户。** 不要只把服务中的 `User=root` 改掉：还需要迁移出 `/root`、配置该用户的 uv/Python，并调整项目及令牌文件的所有权。

## 2. 最重要的基础概念

### 2.1 本地 PowerShell 与 SSH 终端不是同一台机器

| 终端 | 命令在哪执行 | 典型提示符 | 主要操作 |
|---|---|---|---|
| Windows 本地 PowerShell | 你的电脑 | `PS C:\Users\...>` | 打包、上传 |
| SSH 终端 | Linux 服务器 | `[root@服务器 V1]#` | 解压、安装依赖、运行项目、配置定时任务 |

**SSH 终端可能也开在 VS Code 的 PowerShell 标签里。判断时看当前连接和提示符，不要只看标签名称。**

从 Windows 执行 `ssh 用户名@服务器地址` 后，这个终端接下来操作的是远程服务器。需要本地打包时，应另外打开一个本地 PowerShell。

### 2.2 uv、Python、虚拟环境、项目依赖各是什么？

| 名称 | 含义 |
|---|---|
| uv | 管理 Python、依赖和运行命令的工具 |
| Python | 真正执行 Python 代码的解释器 |
| `.venv` | 当前项目的虚拟环境目录 |
| `pyproject.toml` | 项目配置：名称、Python 要求、依赖、命令入口等 |
| `uv.lock` | 锁定依赖解析结果，用于可重复安装 |
| `.python-version` | 给 uv 的 Python 版本选择提示，例如 `3.13` |
| `.env` | 常见的环境变量配置文件，可能包含密码和密钥 |
| `.lingxing_token.json` | 本案例的令牌缓存文件，应按敏感信息保护 |

**服务器安装好 uv，不代表项目代码已经上传，也不代表项目依赖已经安装。**

uv 本身可独立安装，不需要依靠 Conda 的 base。但已有虚拟环境的基础 Python 是否来自 Anaconda，是另一回事。本次 Linux 使用 `--managed-python`，让 uv 使用它自己管理的 Python。

### 2.3 为什么不上传 Windows 的 `.venv`？

虚拟环境包含平台相关的可执行文件、路径和二进制依赖。Windows 环境不能直接当作 Linux 环境运行。

正确方式：**传代码和依赖记录，到服务器重新创建 `.venv`。**

终端显示 `(v1)` 只是环境提示名称，不代表磁盘上的目录一定叫 `v1`。uv 项目通常使用 `.venv`，应按实际目录判断。

## 3. 迁移前检查清单

- [ ] 确认项目在 Windows 上能正常运行，记下完整启动命令。
- [ ] 确认任务是“一次执行后退出”还是“持续运行的服务”。本手册针对前者。
- [ ] 确认项目的依赖记录完整。仅存在于本地环境、未声明的包不会自动被迁移。
- [ ] 保留 `pyproject.toml`、`uv.lock` 和 `.python-version`（如果存在）。
- [ ] 检查是否存在 Windows 路径、Windows 专属依赖和本机文件。
- [ ] 明确一次试运行是否会写数据库、发送消息或产生其他业务效果。
- [ ] 确认服务器可以访问需要的 API、数据库及下载源。
- [ ] 核对本机是否已经有自动任务，避免本机和服务器重复同步。
- [ ] 密码、令牌不发到聊天、不提交到公共仓库。

**不要为了部署方便关闭整个防火墙，或把数据库向所有 IP 开放。** 如果数据库有访问白名单，只添加必要的服务器出口地址，并按实际网络需求排查。

## 4. 操作流程一：检查 Linux 服务器

**执行位置：SSH 终端。**

```bash
whoami
pwd
cat /etc/os-release
uname -m
date
ps -p 1 -o comm=
```

| 命令 | 用途 |
|---|---|
| `whoami` | 当前登录用户 |
| `pwd` | 当前目录的完整路径 |
| `cat /etc/os-release` | Linux 发行版和版本 |
| `uname -m` | CPU 架构 |
| `date` | 系统当前时间 |
| `ps -p 1 -o comm=` | 查看进程 1 是否是 systemd |

本次结果为 root、Alibaba Cloud Linux 3、x86_64、systemd，因此适合后面的 systemd 方案。

如果想进一步确认时区及时间同步状态：

```bash
timedatectl status
```

`CST` 缩写本身有歧义。本手册直接在定时器中写 `Asia/Shanghai`，不需要为了这个项目修改整台服务器的时区。服务器时钟仍需准确。

## 5. 操作流程二：在服务器安装独立版 uv

**执行位置：SSH 终端。**

如果当前显示 `(base)`，可以退出当前 Conda 环境：

```bash
conda deactivate
```

这不是卸载 Conda，也不会终止其他已经运行的程序。独立 uv 不要求激活 base。

先检查现有 uv：

```bash
command -v uv
```

如果没有独立版，使用官方安装命令：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

这会下载并执行官方安装脚本，应确认下载地址可信。安装日志显示的路径为准；本案例验证方式是：

```bash
/root/.local/bin/uv --version
```

**如果已安装成功，不必反复安装。** 自动任务中使用完整路径，可以避免非交互环境的 PATH 与 SSH 终端不一致。

安装命令默认获取当前版本。如果需要严格复现工具行为，应记录并固定 uv 版本，而不是在每次部署时无条件升级。

## 6. 操作流程三：Windows 打包和上传

### 6.1 打包项目

**执行位置：Windows 本地 PowerShell，不是 SSH 终端。**

```powershell
cd "C:\Users\NOTO-财务经理\Desktop\VS"
tar -czf V1-deploy.tar.gz --exclude=".venv" --exclude=".git" --exclude="__pycache__" V1
```

两步含义：先进入 V1 的上一级目录，再把 V1 打成一个压缩包。

| 参数 | 含义 |
|---|---|
| `-c` | 创建归档 |
| `-z` | 使用 gzip 压缩 |
| `-f V1-deploy.tar.gz` | 指定输出文件 |
| `--exclude=".venv"` | 排除本地虚拟环境 |
| `--exclude=".git"` | 排除 Git 历史 |
| `--exclude="__pycache__"` | 排除 Python 缓存 |
| 最后的 `V1` | 要打包的目录 |

**打包不会删除源项目，但同名压缩包可能被覆盖。** 如果要保留旧包，换一个带日期的文件名。

如果实际环境目录另有名称，追加对应排除项。不要把代码目录误当环境目录排除。

本次命令会把 `.env` 和令牌文件也打进去，因此压缩包本身也是敏感文件。上传到可信服务器后应妥善保护，不公开分享。

### 6.2 上传压缩包

仍在本地 PowerShell：

```powershell
scp .\V1-deploy.tar.gz root@服务器公网IP:/root/
```

将 `服务器公网IP` 换成你实际使用的地址或 SSH 别名。不要把示例占位文字原样执行。

如果端口不是 22，例如 2222：

```powershell
scp -P 2222 .\V1-deploy.tar.gz root@服务器公网IP:/root/
```

- `scp` 的端口参数是大写 `-P`；`ssh` 通常用小写 `-p`。
- 首次连接应核对服务器主机指纹，不要在不明情况下盲目接受。
- 输入 SSH 密码时没有字符、星号或光标移动，通常是正常的安全行为。
- 本次显示 `100%` 表示压缩包传输完成，**不等于项目已安装或定时任务已配置**。

## 7. 操作流程四：解压并检查文件权限

**执行位置：SSH 终端。**

先检查收到的文件和包内路径：

```bash
ls -lh /root/V1-deploy.tar.gz
tar -tzf /root/V1-deploy.tar.gz | head -20
ls -ld /root/apps/V1
```

预期压缩包中的项目路径以 `V1/` 开头。如果目标目录已经存在，先确认是否有需要保留的代码、数据、配置和令牌，**不要直接解压覆盖**。

首次部署、目标目录不存在时：

```bash
mkdir -p /root/apps
tar -xzf /root/V1-deploy.tar.gz -C /root/apps
cd /root/apps/V1
ls -la
```

### 7.1 为什么刚上传的权限看起来很宽松？

Windows 打包后解压到 Linux，文件可能显示为 `-rw-rw-rw-`，目录可能是 `drwxrwxrwx`。这允许其他用户写入，不适合作为部署目录的长期状态。

本次在确认项目路径后执行：

```bash
chmod -R go-w /root/apps/V1
chmod 600 /root/apps/V1/.env /root/apps/V1/.lingxing_token.json
chmod 600 /root/V1-deploy.tar.gz
```

- `-R`：递归处理项目内容。
- `g`：所属组，`o`：其他用户，`-w`：取消写权限。
- `600`：仅文件所有者可读、可写，其他人无权限。
- 第一条并不等于“所有文件只有 root 可读”；敏感文件需要单独设为 `600`。

> **重点：chmod 成功时通常没有输出。没有输出不是卡住。不要为了看到变化而重复输入或放宽权限。**

验证：

```bash
pwd
ls -l /root/apps/V1/.env /root/apps/V1/.lingxing_token.json
```

本次正确结果：

```text
/root/apps/V1
-rw------- 1 root root ... .env
-rw------- 1 root root ... .lingxing_token.json
```

文件名直接写 `.lingxing_token.json`，下划线不需要添加反斜杠。也不要复制聊天转义字符，例如 `&#x20;`。

## 8. 操作流程五：检查项目并安装依赖

### 8.1 检查配置，不要猜入口

```bash
cd /root/apps/V1
cat pyproject.toml
cat .python-version
```

本次关键配置：

```toml
[project]
name = "v1"
requires-python = ">=3.13"

[project.scripts]
v1 = "v1.main:main"
```

解释：`uv run v1` 会调用 `v1.main` 模块中的 `main()` 函数。按照本项目的 src 布局，它通常位于 `src/v1/main.py`。

**不需要强行改成 `python main.py`。使用项目本来提供的命令入口即可。**

`.python-version` 为 `3.13` 表示选择 3.13 系列，并未固定补丁版本。本次实际安装的是 3.13.15，不代表以后部署一定还是这个补丁版本。

### 8.2 安装服务器环境

```bash
/root/.local/bin/uv sync --locked --managed-python
```

| 部分 | 含义 |
|---|---|
| `sync` | 根据项目记录同步环境，按需创建 `.venv` |
| `--locked` | 要求锁文件与项目配置一致，不允许自动改锁文件 |
| `--managed-python` | 使用 uv 管理的 Python |

注意：

- 已有部分依赖时，只安装发生变化的包是正常的。
- `Uninstalled 1 package` 随后 `Installed 1 package` 可能只是重装本地项目本身，不代表项目代码被删除。
- `uv sync` 默认会清理环境中未声明的多余包，因此依赖应写进项目记录。
- 文件修改时间不同不能单独证明锁文件过期，以命令实际校验为准。
- 没有 `pyproject.toml` 或 `uv.lock` 时，先确认项目原本的管理方式；不要随意 `uv init`。
- 锁文件不一致时，应在开发环境核对、更新并测试依赖，再部署，不要靠删除锁文件绕过问题。

验证 Python：

```bash
/root/.local/bin/uv run --locked python --version
```

## 9. 操作流程六：手动执行一次并验证业务

确认允许产生一次真实业务操作后运行：

```bash
cd /root/apps/V1
/root/.local/bin/uv run --locked v1
```

**本次命令会真正同步库存、写入数据库，不是演练或只读检查。** 不要为了“再确认一下”反复执行。

任务结束回到提示符后，立即执行：

```bash
echo $?
```

- `0`：程序报告成功。
- 非 `0`：程序报告失败。
- 必须立即查看，因为 `$?` 是“上一条命令”的退出码；中间插入其他命令会改变它。

本次实际结果：

```text
成功写入 11381 条数据到 ods_FBA_inventory
同步时间：2026-09-04 14:05:36.313886
同步完成
```

退出码为 `0`。这说明本次交互式试运行成功；仍应核对数据库实际内容和业务日期。

**手动成功与定时成功是两个检查点。** 定时任务的环境变量、工作目录可能不同，首次自动执行还需验证。

### Linux 迁移常见兼容问题

- Windows 的 `C:\...` 路径在 Linux 不存在。
- Linux 区分文件名大小写。
- Excel COM、`pywin32` 等 Windows 专属功能不能直接运行。
- 数据库可能只允许原电脑的 IP 访问。
- 安装 `python-dotenv` 不代表程序一定读取 `.env`，仍取决于代码是否调用加载逻辑。
- 在 SSH 手动 `export` 的变量，不会自然传入 systemd 服务。
- 不要把 `.env` 当作普通 Shell 脚本随意 `source`；先确认文件格式和内容可信。

## 10. 操作流程七：创建 systemd 任务与定时器

### 10.1 两个文件分别负责什么？

| 文件 | 作用 | 保存位置 |
|---|---|---|
| `v1-sync.service` | 定义“做什么、在哪做、以谁的身份做” | `/etc/systemd/system/v1-sync.service` |
| `v1-sync.timer` | 定义“什么时候启动任务” | `/etc/systemd/system/v1-sync.timer` |

它们是服务器上的普通文本配置文件，不在 Windows，也不在项目目录中。systemd 读取它们来管理任务。

### 10.2 创建 service 文件

**执行位置：SSH 终端。下面适用于首次创建；若文件已有内容，先查看并备份。**

```bash
vi /etc/systemd/system/v1-sync.service
```

按 `i` 进入输入模式，粘贴：

```ini
[Unit]
Description=V1 FBA inventory sync
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/root/apps/V1
ExecStart=/root/.local/bin/uv run --locked v1
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Asia/Shanghai
UMask=0077
StandardOutput=journal
StandardError=journal
```

按 `Esc`，输入 `:wq`，回车保存退出。

| 配置 | 含义和注意事项 |
|---|---|
| `Description` | 显示用的说明文字 |
| `Wants`、`After` | 协调网络就绪顺序，不保证外部 API 或数据库一定可达 |
| `Type=oneshot` | 执行一次，完成后退出 |
| `User=root` | 本次沿用 root，长期建议迁移到低权限账户 |
| `WorkingDirectory` | 相当于先 `cd` 到项目目录，对相对路径和配置查找很重要 |
| `ExecStart` | 指定真正执行的程序和参数；不是随意可写管道和重定向的 Shell 命令行 |
| `PYTHONUNBUFFERED=1` | Python 输出及时进入日志 |
| `TZ=Asia/Shanghai` | 设置任务进程的时区；调度时区由 timer 单独指定 |
| `UMask=0077` | 限制新建文件的默认权限，不修改既有文件 |
| `StandardOutput/StandardError=journal` | 正常输出和错误写入系统日志 |

本次不设置自动重试，避免业务写入失败后产生不受控的重复执行。可靠重试应结合程序的幂等性、事务和错误处理设计。

### 10.3 创建 timer 文件

```bash
vi /etc/systemd/system/v1-sync.timer
```

按 `i`，粘贴：

```ini
[Unit]
Description=Run V1 daily at 08:00 Asia/Shanghai

[Timer]
OnCalendar=*-*-* 08:00:00 Asia/Shanghai
AccuracySec=1s
RandomizedDelaySec=0
Persistent=false
Unit=v1-sync.service

[Install]
WantedBy=timers.target
```

按 `Esc` → 输入 `:wq` → 回车。

| 配置 | 含义 |
|---|---|
| `OnCalendar=*-*-* 08:00:00 Asia/Shanghai` | 每年、每月、每天，北京时间 08:00 |
| `AccuracySec=1s` | 将调度合并窗口设为 1 秒，不是硬实时保证 |
| `RandomizedDelaySec=0` | 不增加随机延迟 |
| `Persistent=false` | 服务器关机错过时间，开机不补跑 |
| `Unit=v1-sync.service` | 到时间后触发这个 service |
| `WantedBy=timers.target` | 配合 enable，设置系统启动时启用定时器 |

如果业务希望开机补一次漏跑任务，可评估 `Persistent=true`。**它不是按遗漏天数逐次重放，也可能在启用或恢复时很快触发补跑，应先确认业务允许。**

### 10.4 检查并启用

```bash
systemd-analyze verify /etc/systemd/system/v1-sync.service /etc/systemd/system/v1-sync.timer
```

正常通常无输出。若是未知配置项、时间格式错误、执行文件不存在等针对本服务的错误，应修正后再继续。

本次出现的警告：

```text
upower.service ... IPAddressDeny=any ... does not support BPF/cgroup based firewalling
Proceeding WITHOUT firewalling in effect!
```

它针对 `upower.service` 的 IP 防火墙限制不受本机支持，不是 V1 文件格式错误，也没有阻止本次 timer 启用。它不等于“整台服务器防火墙已经关闭”；不要因此关闭安全组或系统防火墙。

启用：

```bash
systemctl daemon-reload
systemctl enable --now v1-sync.timer
```

解释：

- `daemon-reload`：让 systemd 重新读取配置。
- `enable`：设置以后系统启动时也启用此定时器。
- `--now`：现在就启动定时器，进入等待状态。
- **启用的是 `.timer`，不是直接启动 `.service`。按本配置，在已过当日 08:00 的时间启用，会等待次日 08:00。**

### 10.5 验证定时器

```bash
systemctl status v1-sync.timer --no-pager
systemctl list-timers --all v1-sync.timer
```

本次已观察到：

```text
Loaded: loaded (...; enabled; ...)
Active: active (waiting)
Trigger: Sat 2026-09-05 08:00:00 CST
```

| 输出 | 含义 |
|---|---|
| `enabled` | 已设置开机启用 |
| `active (waiting)` | 定时器正在等待 |
| `Trigger` / `NEXT` | 下一次计划执行时间 |
| `LAST n/a` | 尚无这一定时器的执行记录，首次启用时正常 |

**到这里可断开 SSH、关闭本地电脑。服务器仍需保持运行。** SSH 只是你的操作通道，不是定时器的运行载体。

## 11. 首次自动运行后的验收

第二天 08:00 之后查看：

```bash
journalctl -u v1-sync.service -n 100 --no-pager
systemctl show v1-sync.service -p Result -p ExecMainStatus
```

在确认确实发生过一次运行的前提下，成功通常显示：

```text
Result=success
ExecMainStatus=0
```

**不能只看这两个值就判断“今天已经执行过”。** 要结合日志时间、timer 的上次触发时间和数据库更新时间；服务从未执行时也可能出现默认状态值。

查看今天的日志：

```bash
journalctl -u v1-sync.service --since today --no-pager
```

验收清单：

- [ ] 日志里有当天运行的开始和完成记录。
- [ ] 程序报告成功，退出码为 0。
- [ ] 数据库中的同步时间和数据内容正确。
- [ ] 没有与本机或其他部署重复运行。
- [ ] 明天的 NEXT 时间仍正确。

`Type=oneshot` 任务执行完成后，service 显示 `inactive (dead)` 可以是正常现象；应结合退出结果判断，**不是要求任务永久显示 running**。timer 则应继续处于 waiting。

日志是否跨重启持久保存、保留多久，取决于服务器 journald 配置。当前方案不会自动给你发送失败通知，生产使用应补充监控或告警。

## 12. 重点答疑：为什么找不到 /etc？

### 12.1 `/` 与 `/root` 不一样

```text
/                              Linux 真正的根目录
├── etc/
│   └── systemd/system/
│       ├── v1-sync.service
│       └── v1-sync.timer
└── root/                      root 用户的个人目录
    ├── .ssh/
    ├── .local/
    └── apps/
        └── V1/
```

SSH 插件写着“根目录 /root”，通常表示插件把 `/root` 设为浏览起点，不代表 `/root` 是 Linux 根目录。

### 12.2 在终端进入根目录

```bash
cd /
pwd
ls
```

直接进入配置目录：

```bash
cd /etc/systemd/system
ls -l v1-sync.service v1-sync.timer
```

### 12.3 在文件面板进入根目录

不同 SSH 插件操作不同，可尝试：

- 在路径栏或“转到目录”中输入 `/`。
- 在连接或浏览起点上右键，寻找修改路径、编辑根目录等选项。
- 将浏览起点由 `/root` 改为 `/`，保存并刷新。

**不要凭空认定某个插件一定有某个菜单名称。** 找不到时应查看插件名称或右键菜单。

终端执行 `cd` 通常不会同步改变左侧文件面板。以 `.` 开头的文件需要面板启用“显示隐藏文件”；终端可用 `ls -la` 查看。

## 13. 重点答疑：vi 像“白板”一样，为什么动不了？

vi 是终端文本编辑器，不是普通命令提示符。它有不同模式。

| 操作 | 按键 |
|---|---|
| 开始输入文字 | `i` |
| 退出输入模式 | `Esc` |
| 保存并退出 | `Esc` → 输入 `:wq` → 回车 |
| 保存但不退出 | `Esc` → 输入 `:w` → 回车 |
| 放弃未保存修改并退出 | `Esc` → 输入 `:q!` → 回车，谨慎使用 |

**冒号 `:` 必须输入；不是直接输入 `wq`。**

如果键盘似乎完全没有反应：

1. 点击终端文字区域，确保获得键盘焦点。
2. 切换英文输入法。
3. 按 `Esc`，输入 `:wq`，回车。
4. 如果误按 `Ctrl+S` 暂停终端输出，可尝试 `Ctrl+Q` 恢复。
5. 仍不正常时，保留终端并记录画面，不要立刻强制关闭。

退出后用下面的命令确认保存内容，而不是只凭“退出成功”判断文件正确：

```bash
cat /etc/systemd/system/v1-sync.service
```

仅查看文件时优先用 `cat`，不需要进入 vi。

## 14. 日常维护与修改

### 14.1 改为每天 09:30

先备份原 timer，备份文件名要使用未存在的新名称：

```bash
cp -p /etc/systemd/system/v1-sync.timer /etc/systemd/system/v1-sync.timer.backup-20260904
vi /etc/systemd/system/v1-sync.timer
```

将时间行改为：

```ini
OnCalendar=*-*-* 09:30:00 Asia/Shanghai
```

保存后检查并生效：

```bash
systemd-analyze verify /etc/systemd/system/v1-sync.service /etc/systemd/system/v1-sync.timer
systemctl daemon-reload
systemctl restart v1-sync.timer
systemctl list-timers --all v1-sync.timer
```

这是更新定时安排，不是主动调用一次 service。靠近触发时间修改时，仍应检查 NEXT 和日志。

### 14.2 暂停和恢复定时任务

暂停，并取消开机启用：

```bash
systemctl disable --now v1-sync.timer
```

恢复：

```bash
systemctl enable --now v1-sync.timer
```

**停止 timer 不会自动终止已经运行中的 service。** 如果正在写数据库，不要随意强行停止进程，应先了解事务和恢复方式。

### 14.3 通过 systemd 手动执行一次

只有确认允许再次执行真实业务时才使用：

```bash
systemctl start v1-sync.service
```

这不是检查命令，会立即启动同步。与 SSH 里直接 `uv run` 不同，这次运行会进入 service 的日志。

同一个 service 在已经运行时，timer 不会再启动一份同名服务实例。但你在 SSH 中直接执行 `uv run v1` 仍可能造成并行运行，因此不要把它当作所有场景下的防重机制。

### 14.4 后续更新代码

建议顺序：

1. 暂停 timer，确认当前任务已经结束。
2. 备份项目代码、配置和必要业务状态。
3. 更新代码与依赖记录，保留服务器专用 `.env` 和最新令牌。
4. 执行 `uv sync --locked --managed-python`。
5. 在允许的情况下验证运行，检查数据结果。
6. 如修改 service/timer，检查配置并执行 `daemon-reload`。
7. 恢复 timer，检查 NEXT。

**不要用 Windows 压缩包中的旧令牌覆盖服务器新生成的令牌。** 也不要默认把本机数据库、路径、密钥配置直接当成服务器配置。

## 15. 常见问题速查

| 现象 | 先检查什么 |
|---|---|
| chmod 没输出 | 通常成功，用 `ls -l` 验证 |
| scp 密码输入没显示 | 通常正常，输入后回车 |
| 上传显示 100% | 仅代表文件上传完成，还需解压和安装 |
| 找不到 V1 | `pwd`，再检查 `/root/apps/V1` |
| 文件面板没有 etc | 面板可能只显示 `/root`，应进入 `/` |
| 看不到 .env | 隐藏文件；用 `ls -la` |
| vi 无法像普通终端那样输入命令 | `Esc` → `:wq` → 回车，先保存退出 |
| uv: command not found | 检查安装路径，使用完整路径 |
| uv sync 报锁文件不一致 | 核对依赖声明，在开发环境修复后重新部署 |
| 手动成功但定时失败 | 工作目录、环境变量、权限、网络、依赖路径、日志 |
| timer waiting | 正常等待，不代表程序已经运行 |
| service inactive (dead) | 对一次性任务可能正常，查看结果和日志 |
| journal 没日志 | 可能还没通过 service 执行；SSH 手动运行不在这里 |
| 每天没有自动执行 | timer 是否 enabled/active、NEXT、系统时钟、服务器是否在线 |

## 16. 部署完成的四级判断

不要把不同阶段的“成功”混在一起：

1. **传输成功**：scp 显示 100%。
2. **手动执行成功**：程序完成、退出码 0、业务结果正确。
3. **调度配置成功**：timer enabled、active (waiting)、NEXT 正确。
4. **自动执行成功**：到了计划时间后，有实际日志与正确业务结果。

本次对话已经确认第 1～3 级；首次计划时间为 **2026-09-05 08:00（北京时间）**。第 4 级需根据实际自动运行日志与数据库结果验收，不能预先认定。

## 17. 官方资料

- [uv 安装方式](https://docs.astral.sh/uv/getting-started/installation/)
- [uv 项目结构与环境](https://docs.astral.sh/uv/concepts/projects/layout/)
- [uv 锁定与同步依赖](https://docs.astral.sh/uv/concepts/projects/sync/)
- [uv Python 版本管理](https://docs.astral.sh/uv/concepts/python-versions/)
- [uv 部署中的虚拟环境隔离说明](https://docs.astral.sh/uv/guides/integration/docker/)
- [systemd 定时器官方文档源文件](https://github.com/systemd/systemd/blob/main/man/systemd.timer.xml)

服务器本机文档与已安装版本最贴近，也可以执行 `man systemd.timer`、`man systemd.service`、`man systemd.time` 查看；阅读界面按 `q` 退出。

---

**复习时先记住这句话：代码上传只是开始，环境要重建，业务要验证，service 管“做什么”，timer 管“什么时候做”，日志和数据库共同证明任务是否真正成功。**
