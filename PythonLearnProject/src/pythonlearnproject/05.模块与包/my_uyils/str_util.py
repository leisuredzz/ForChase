# -*- coding: utf-8 -*-
"""
字符串工具模块
================

【这个模块是干什么的】
把常用的字符串操作封装成函数，方便在多个项目里复用。

【为什么要写成"模块"】
如果每次写代码都要重新写一遍"反转字符串"，那太浪费时间。
把它们放进一个 .py 文件，以后 `import` 一下就能用 —— 这就是"模块复用"。

【怎么用】
    # 先把"工具包所在的目录"加进搜索路径（因为上层目录名带 05. 前缀，
    # 不能直接写进 import 语句里）
    import sys
    sys.path.insert(0, <my_uyils 的上一层目录>)

    import my_uyils
    print(my_uyils.str_reverse('新年快乐'))

    也可以：from my_uyils import str_reverse

    （完整讲解见同级的 05.01-模块与包.ipynb）
"""


def str_reverse(s):
    """反转字符串

    参数：
        s：任意字符串
    返回：
        反转后的新字符串

    >>> str_reverse('abc')
    'cba'
    """
    # s[::-1] 是切片语法：步长 -1 表示从后往前取，所以整个字符串就反过来了
    return s[::-1]


def substr(s, x, y):
    """截取子串（左闭右开，和切片保持一致）

    参数：
        s：原字符串
        x：起始下标（包含）
        y：结束下标（不包含）
    返回：
        截取出来的子串

    >>> substr('abcdefg', 0, 3)
    'abc'
    """
    return s[x:y]


def is_palindrome(s):
    """判断是不是回文（正着读反着读都一样）

    >>> is_palindrome('上海自来水来自海上')
    True
    """
    return s == s[::-1]


def count_chars(s):
    """统计每个字符出现的次数

    返回：
        一个字典，键是字符，值是出现次数

    >>> count_chars('aab')
    {'a': 2, 'b': 1}
    """
    result = {}
    for ch in s:
        # dict.get(key, 默认值) 是"取不到就给默认值"，比 if 判断简洁
        result[ch] = result.get(ch, 0) + 1
    return result


# ----------------------------------------------------------------------
# 这段 if 的作用：只有当【直接运行本文件】时才执行，被 import 时不执行
# ----------------------------------------------------------------------
# 为什么要加它？
#   如果别的文件 import 本模块，下面这些 print 会莫名其妙地输出出来，
#   这叫"副作用"，会污染对方的输出。
#   __name__ 在"直接运行"时是 '__main__'，在"被导入"时是模块名。
if __name__ == '__main__':
    # 下面这几行是"自测代码"：直接运行本文件，用来验证函数写对了没
    print('反转 abcdefg      ->', str_reverse('abcdefg'))
    print('截取 [0:3]        ->', substr('abcdefg', 0, 3))
    print('判断回文          ->', is_palindrome('上海自来水来自海上'))
    print('统计字符 aabbcc   ->', count_chars('aabbcc'))
