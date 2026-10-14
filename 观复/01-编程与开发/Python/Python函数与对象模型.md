# Python 函数与对象模型

> **先修**：[[Python语言核心]]。
> **核验状态**：未核验——示例未在本机复跑，结论未与 Python 官方文档逐条比对。详见 [[知识库质量审计]]。

## 背景：用函数划清输入和输出

函数把一个可重复的动作命名。适合做数据开发的函数应让调用者看出输入、输出和可能失败的条件；不是把所有代码藏进 `main()`。

```python
def normalize_sku(raw: str) -> str:
    sku = raw.strip().upper()
    if not sku:
        raise ValueError("SKU 不能为空")
    return sku

assert normalize_sku(" a-01 ") == "A-01"
```

这个函数不访问网络、不改数据库，也不依赖全局变量，因此易于验证。类型标注说明预期类型，但 Python 默认不会在运行时自动拦截传错类型。

## 参数与可变默认值

默认参数表达式在定义函数时求值一次。把可变容器作为默认值，后续调用可能共享状态。

```python
def append_event(event: str, history: list[str] | None = None) -> list[str]:
    if history is None:
        history = []
    history.append(event)
    return history

assert append_event("created") == ["created"]
assert append_event("updated") == ["updated"]
```

这里的 `None` 是“没有传入容器”的明确哨兵；如果空列表也是有意义的用户输入，就不能写 `history = history or []`，因为它会把用户传入的空列表替换掉。

## 作用域与闭包

函数读取名称时，会按局部、外层函数、模块全局和内置命名空间查找。`global` 与 `nonlocal` 会改变赋值指向的作用域，应少用。数据管道里更可控的办法是把依赖作为参数传入，再返回结果。

```python
def make_multiplier(factor: int):
    def multiply(value: int) -> int:
        return factor * value
    return multiply

double = make_multiplier(2)
assert double(5) == 10
```

返回的内部函数仍能读取创建它时的 `factor`，这就是闭包的一个常见用途。

## 什么时候使用类

类适合把**需要共同维护的不变条件与状态**放在一起；仅为复用一段计算逻辑时，函数更简单。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price_cents: int

    def __post_init__(self) -> None:
        if self.quantity < 0 or self.unit_price_cents < 0:
            raise ValueError("数量和单价不能为负")

    def amount_cents(self) -> int:
        return self.quantity * self.unit_price_cents

assert OrderLine("A-01", 2, 1990).amount_cents() == 3980
```

`frozen=True` 禁止通常的属性重新赋值，但不是对嵌套可变对象的递归冻结。继承用于真正的“是一种”关系；组合通常更适合连接数据库客户端、解析器和业务规则。

## 迭代器与生成器

迭代器按需给出下一个值，生成器函数通过 `yield` 创建迭代器。它适合流式读取，但“懒”不等于自动节省所有内存：如果最终调用 `list()` 收集全部结果，仍会占用相应内存。

```python
def positive_amounts(rows):
    for row in rows:
        if row["amount"] > 0:
            yield row["amount"]

assert sum(positive_amounts([{"amount": 3}, {"amount": 0}])) == 3
```

## 现阶段认知

先用函数明确边界，再按状态和不变条件决定是否引入类。了解对象可变性后再学习装饰器、闭包与继承，比先记高级语法更有效。模块与导入机制另见 [[Python模块导入与包管理]]。

## 依据

- [Python 官方教程：函数](https://docs.python.org/3/tutorial/controlflow.html#defining-functions)
- [Python 官方教程：类](https://docs.python.org/3/tutorial/classes.html)
