# 终端与 Shell：CMD、Windows PowerShell 和 pwsh

> **核验状态**：文档核对——终端与 Shell 的分层、版本对应关系对照 Microsoft 官方文档；本机实际安装情况与 `PATH` 未检测。详见 [[知识库质量审计]]。

## 背景

运行 Python、Git 或部署脚本时，常会接触 Windows Terminal、VS Code 集成终端、CMD 和 PowerShell。它们不处于同一层：**终端**负责输入、显示和窗口交互；**Shell**解释命令并启动程序。可以把终端看作工作台，把 Shell 看作在工作台上理解指令的操作员。

## 问题：打开的是哪个程序

| 名称 | 角色 | 常见进程 | 主要特点 |
| --- | --- | --- | --- |
| Windows Terminal、VS Code 集成终端 | 终端界面 | 随宿主而异 | 展示文本、管理标签页；可以承载不同 Shell |
| 命令提示符（CMD） | Shell | `cmd.exe` | 执行 Windows 命令、外部程序和 `.bat`/`.cmd` 脚本 |
| Windows PowerShell | Shell 与脚本语言 | `powershell.exe` | 通常为 5.1，基于 .NET Framework，管道可传递对象 |
| PowerShell 7 及后续版本 | Shell 与脚本语言 | `pwsh.exe` | 基于现代 .NET，可在 Windows、Linux、macOS 运行 |

在 CMD 中输入 `powershell` 或 `pwsh`，是启动一个新的 Shell 进程；输入 `exit` 才返回之前的 CMD。**能在某个终端窗口打开两个 PowerShell，不等于电脑有两个终端窗口**；要区分界面、进程与安装的版本。`pwsh` 是新版 PowerShell 的可执行文件名，不是 PowerShell 之外的第三种产品。

## 方案：按任务选择并确认环境

- 简单启动 `python`、`git` 等外部程序，CMD 与 PowerShell 都可以；脚本语法和内建命令则须按当前 Shell 编写。
- 需要按属性筛选进程、服务等结构化结果时，用 PowerShell 的对象管道更直接。例如 `Get-Process | Where-Object WorkingSet64 -gt 500MB | Sort-Object WorkingSet64 -Descending | Select-Object ProcessName, Id, WorkingSet64`。这与 SQL 的筛选、排序、投影**思路相似**，并非 SQL 查询或数据库执行。
- 遇到旧版 Windows 管理模块或现成脚本时先核对兼容性；跨平台脚本可考虑 PowerShell 7。不能假设同一脚本在两个版本的模块、编码与外部命令行为完全一致。

在 **CMD** 中检查可找到的程序：

```cmd
where powershell
where pwsh
powershell -NoProfile -Command "$PSVersionTable.PSVersion.ToString()"
pwsh -NoProfile -Command "$PSVersionTable.PSVersion.ToString()"
```

`where pwsh` 或启动命令失败，说明当前环境无法通过该名称找到程序；不能仅凭此断言机器上绝对没有安装。进入 PowerShell 后还可用 `$PSVersionTable.PSVersion` 查看正在运行的版本。提示符常能提供线索，但不能代替版本检查。

## 原理：文本与对象管道

CMD 的管道主要传递文本。PowerShell **内部命令之间**的管道可传递带属性的 .NET 对象，因而能用 `Where-Object`、`Sort-Object`、`Select-Object` 处理属性；传入或传出 `python`、`git` 等外部程序时仍要考虑文本流、编码和参数解析。两种 Shell 都能做复杂自动化，差异在默认抽象与工具生态，不能简单理解为“CMD 命令少、PowerShell 命令多”。

命令找不到时，还需区分 Shell 是否识别该语法、程序是否安装、可执行文件是否在 `PATH` 中，以及当前工作目录是否正确。参见 [[Python环境与依赖]]、[[调试与排错方法]]。

## 命令解释与执行策略

### 下载脚本命令为何不能直接换一个 Shell 执行

以 uv 安装命令为例，`irm` 是 `Invoke-RestMethod` 的别名，负责取回响应；`iex` 是 `Invoke-Expression` 的别名，将字符串当成 PowerShell 代码执行。它们不是 PATH 中的独立程序，因此 CMD 不认识这两个名字。

```powershell
Get-Alias irm, iex
```

在 PowerShell 中可以执行内层语句 `irm https://astral.sh/uv/install.ps1 | iex`；在 CMD 中要用完整的 `powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"`，让 PowerShell 解释内层语法。在 pwsh 中调用 `powershell` 会再启动 Windows PowerShell 进程；不等于当前进程变成 5.1。`-c` 是 `-Command` 的常用简写，PowerShell 参数名称不区分大小写。

这个管道的作用是“下载文本 → 执行代码”，并不等于只下载软件。先下载为文件并阅读，再执行，可把审查与运行分开；uv 的完整步骤见 [[uv项目管理与Windows配置]]。

### 执行策略的作用范围

执行策略约束脚本、配置文件加载等行为，**不是安全边界**。命令行里的字符串执行不能等同于 `.ps1` 文件的策略检查；`-ExecutionPolicy Bypass` 也不能覆盖组策略、AppLocker、WDAC 或受限语言模式等更高层约束。

```powershell
Get-ExecutionPolicy -List
$ExecutionContext.SessionState.LanguageMode
```

进程参数或 `Set-ExecutionPolicy -Scope Process ...` 只影响当前进程范围；`-Scope CurrentUser` 是持续作用于当前用户的设置。`RemoteSigned` 对被标记为网络来源的脚本要求签名，已审查可信的文件可以按需要解除该文件的阻止；不是每种下载方式都会设置网络来源标记。看到禁止运行脚本时，先确认实际策略及组织要求，再选所需的最小作用范围。

依据：[Microsoft 执行策略](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies)、[PowerShell 安全功能](https://learn.microsoft.com/en-us/powershell/scripting/security/security-features)。本段为文档核对，未修改本机策略或测试企业应用控制。

## 现阶段认知：确认当前解释器

对话“比较终端区别”的核心结论是：终端是界面，Shell 是解释器；`powershell.exe` 与 `pwsh.exe` 通常对应两个可并存的 PowerShell 版本。**本笔记没有据此断言用户电脑实际安装了哪些版本**，应以上述本机检查结果为准。

## 依据

- [Microsoft：Windows Terminal FAQ](https://learn.microsoft.com/en-us/windows/terminal/faq)
- [Microsoft：Windows PowerShell 5.1 与 PowerShell 7 的差异](https://learn.microsoft.com/en-us/powershell/scripting/whats-new/differences-from-windows-powershell)
