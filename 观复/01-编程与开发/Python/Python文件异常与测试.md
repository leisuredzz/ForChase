# Python 文件、异常与测试

> **先修**：[[Python语言核心]]。
> **核验状态**：未核验——示例未在本机复跑，结论未与 Python 官方文档逐条比对。详见 [[知识库质量审计]]。

## 背景：数据程序面对不可靠输入

教学例子常把数据写死在代码里。真实任务要读文件、解析格式、处理缺字段和重试失败。可靠性来自明确的边界：读取失败、格式错误、业务校验失败分别处理。

## 路径与编码

```python
from pathlib import Path

source = Path("data") / "orders.csv"
text = source.read_text(encoding="utf-8-sig")
```

相对路径相对于**当前工作目录**，不一定是脚本文件所在目录。部署时要选择稳定的基准路径，例如配置项或 `Path(__file__).resolve().parent`。`utf-8-sig` 可兼容某些 CSV 文件开头的 BOM；若数据源约定普通 UTF-8，就直接用 `utf-8`。

## 解析与校验分开

```python
import csv
from pathlib import Path

def load_quantities(path: Path) -> list[int]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = csv.DictReader(file)
        if rows.fieldnames is None or "quantity" not in rows.fieldnames:
            raise ValueError("缺少 quantity 列")
        result = []
        for line_no, row in enumerate(rows, start=2):
            try:
                value = int(row["quantity"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"第 {line_no} 行 quantity 无效") from exc
            if value < 0:
                raise ValueError(f"第 {line_no} 行 quantity 不能为负")
            result.append(value)
        return result
```

`with` 保证离开代码块时关闭文件；它不保证文件内容有效。`newline=""` 交给 `csv` 模块处理换行。解析错误附上行号，远比返回空列表更方便定位。

## 异常处理原则

- 只捕获能够解释或处理的异常，避免 `except Exception: pass` 吞掉程序缺陷。
- 在边界处补充上下文，例如文件名、行号、请求 ID；需要保留原异常链时用 `raise ... from exc`。
- 不要把失败伪装成成功。对批处理要明确选择：单行跳过、整批回滚，还是隔离错误记录。

## 最小有效测试

测试要覆盖真实失败路径，而不只是把实现抄一遍。

```python
from pathlib import Path
from tempfile import TemporaryDirectory

def test_load_quantities() -> None:
    with TemporaryDirectory() as directory:
        path = Path(directory) / "orders.csv"
        path.write_text("quantity\n2\n3\n", encoding="utf-8")
        assert load_quantities(path) == [2, 3]

        path.write_text("quantity\n-1\n", encoding="utf-8")
        try:
            load_quantities(path)
        except ValueError as exc:
            assert "第 2 行" in str(exc)
        else:
            raise AssertionError("负数应被拒绝")
```

上述测试与 `load_quantities` 放在同一文件可以直接运行；在项目中宜放入独立测试模块，再使用 `unittest` 或现有测试框架组织。

## 现阶段认知

文件路径、编码、数据结构和业务规则是四个不同问题。逐层验证能让错误停在最接近源头的位置。数据工程案例参见 [[API到MySQL数据采集实战]]。

## 依据

- [Python 官方文档：`pathlib`](https://docs.python.org/3/library/pathlib.html)
- [Python 官方文档：`csv`](https://docs.python.org/3/library/csv.html)
- [Python 官方教程：异常](https://docs.python.org/3/tutorial/errors.html)
