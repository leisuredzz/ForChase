# -*- coding: utf-8 -*-
"""
my_uyils —— 自定义工具包
==========================

【命名说明】
目录名 `my_uyils` 是 `my_utils`（my utilities，我的工具）的笔误。
这里保持不变是为了不影响已有的导入路径；
如果你愿意，可以把它重命名为 `my_utils`，然后全局替换引用：
    my_uyils  ->  my_utils

【__init__.py 是干什么的】
一个目录里只要有 __init__.py，Python 就把它当成"包"（package），
里面的 .py 文件才能被 import 进来。

从 Python 3.3 起其实不再强制要求 __init__.py，
但它的两个作用依然很有用：
    1) 明确告诉别人"这是一个包"
    2) 可以在里面写"预导入"，让包的使用者少打几个字
"""

# 预导入：这样外部就可以直接 `from ...my_uyils import str_reverse`，
# 而不用写 `from ...my_uyils.str_util import str_reverse`
from .str_util import str_reverse, substr, is_palindrome, count_chars
from .file_util import print_file_info, append_to_file

# __all__ 定义了"from my_uyils import *" 时会导出哪些名字
__all__ = [
    'str_reverse',
    'substr',
    'is_palindrome',
    'count_chars',
    'print_file_info',
    'append_to_file',
]
