# Pandas 索引与数据对齐

> **先修**：[[Python语言核心]]；理解行粒度时参见 [[数据认知框架]]。
> 适用范围：现代 pandas 的常用 Series/DataFrame 操作。示例可独立运行；生产数据还要检查类型、缺失值和重复键。
> **核验状态**：未核验——示例未在本机复跑，索引对齐的具体行为未与所用 pandas 版本文档逐条比对。详见 [[知识库质量审计]]。

## 背景：索引是标签，不是数据库主键

Series 有一条行索引，DataFrame 有行索引与列标签。索引让数据能按标签选取、自动对齐，也保存一定的语义。**索引默认允许重复**，因此不能直接当成 SQL 主键。

```python
import pandas as pd

sales = pd.DataFrame(
    {"sku": ["A", "B", "C"], "amount": [100, 80, 50]}
).set_index("sku")

assert sales.loc["B", "amount"] == 80
assert sales.iloc[1, 0] == 80
```

`.loc` 按**标签**，`.iloc` 按**整数位置**。若索引标签本身是整数，`.loc[1]` 仍指标签 `1`。标签切片的结束标签通常包含在内；位置切片的右边界不包含。

## 问题一：自动对齐改变了结果

```python
left = pd.Series({"A": 10, "B": 20})
right = pd.Series({"B": 3, "C": 4})
result = left + right

assert result["B"] == 23
assert pd.isna(result["A"])
assert pd.isna(result["C"])
```

两个 Series 相加时按标签而非行位置配对。缺一侧的标签产生缺失值。若业务上缺失应视为零，要明确写出 `left.add(right, fill_value=0)`，不要让默认缺失值悄悄流进指标。

## 问题二：重复标签可能放大数据

```python
orders = pd.DataFrame({"sku": ["A", "A"], "qty": [1, 2]})
prices = pd.DataFrame({"sku": ["A"], "price": [10]})
joined = orders.merge(prices, on="sku", validate="many_to_one")
assert len(joined) == 2
```

若左右两边的 `sku` 都重复，连接会形成多对多组合，行数可能倍增。`validate="many_to_one"` 把“价格表每个 SKU 唯一”的业务假设变成可执行检查。不要把 `merge` 概括成“按列对齐”：它是按指定键连接，未指定 `on` 时还有默认选择共同列等规则。

## 设置、重置与检查索引

```python
frame = pd.DataFrame({"sku": ["A", "B"], "qty": [1, 2]})
indexed = frame.set_index("sku")
assert indexed.index.is_unique
assert indexed.reset_index().columns.tolist() == ["sku", "qty"]

duplicated = frame.loc[frame["sku"].duplicated(keep=False)]
assert duplicated.empty
```

`set_index` 改变的是标签组织方式，不自动保证唯一。允许重复是否正确取决于**粒度**：一张订单明细表可以有重复 SKU，而产品主数据表通常需要稳定的唯一键。

## 多级索引与选择原则

多级索引适合同时按地区、日期、SKU 等层级选择或透视，但并非越多越好。如果业务表要频繁与 SQL、CSV 或其他系统交换，保留显式列往往更直观。可用 `set_index(["region", "sku"])` 建立多级索引，再用 `reset_index()` 回到普通列。

## 现阶段认知

遇到意外结果，依次检查 **行粒度 → 键是否唯一 → 按标签还是按位置 → 缺失值从何而来**。这比死记 `.loc`、`.iloc` 的语法更重要。

## 依据

- [pandas 官方文档：索引与选择](https://pandas.pydata.org/docs/user_guide/indexing.html)
- [pandas 官方文档：重复标签](https://pandas.pydata.org/docs/user_guide/duplicates.html)
- [pandas 官方文档：合并与连接](https://pandas.pydata.org/docs/user_guide/merging.html)
