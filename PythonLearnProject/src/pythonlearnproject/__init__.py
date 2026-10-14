# -*- coding: utf-8 -*-
"""
pythonlearnproject —— Python 学习项目
=======================================

【这个文件的作用】
它是整个项目的"顶层包入口"。名字出现的位置在 pyproject.toml 里：

    [project]
    name = "pythonlearnproject"

    [project.scripts]
    pythonlearnproject = "pythonlearnproject:main"

最后那行意味着：`uv run pythonlearnproject` 会去调用本文件的 `main()` 函数。

【关于 __init__.py】
- 它让 Python 把 `src/pythonlearnproject/` 当成一个"包"
- 它在包被第一次导入时执行，所以里面**不要写耗时操作**
- 保持轻量是个好习惯，重的东西放到具体模块里按需导入
"""

__version__ = '0.1.0'


def main() -> None:
    """命令行入口：`uv run pythonlearnproject` 会执行这里"""
    print('Hello from pythonlearnproject!')
    print()
    print('这个项目里有哪些内容可以看（按学习顺序编号）：')
    print('  01.基础概念/    变量、输出、格式化输出、调试、Python 特性')
    print('  02.运算符/      算术运算符、转义字符、输入、类型转换')
    print('  03.数据结构/    列表、元组、字典、文件读写、综合练习册')
    print('  04.面向对象/    类、对象、继承、封装')
    print('  05.模块与包/    自己写的可复用工具包 my_uyils')
    print('  06.NumPy/       数组的创建、属性、运算、索引切片')
    print('  07.pandas/      Series / DataFrame、清洗、合并、时间序列')
    print('  08.Matplotlib/  折线图、散点图、条形图、饼图、箱型图')
    print('  09.数据可视化/  pyecharts 图表与地图')
    print('  10.MySQL/       数据库连接与增删改查')
    print()
    print('打开 00.学习路线.ipynb 可以看到完整的学习顺序和每份笔记的说明。')


if __name__ == '__main__':
    main()
