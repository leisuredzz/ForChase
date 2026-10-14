# -*- coding: utf-8 -*-
"""
文件工具模块
==============

【这个模块是干什么的】
把"读文件打印出来""往文件追加内容"这两件常做的事封成函数。

【本文件修掉的两个真 bug】（详见 03_模块与包 笔记）
    1) 原来 finally 里写的是 `if f: True`，等于什么都没做，文件句柄根本没关
    2) 原来 __main__ 里用的是 "/03.数据结构/data.txt" 这种路径，在任何目录下都找不到文件
"""

import os


def print_file_info(file_info):
    """把文件内容打印到控制台

    参数：
        file_info：文件路径
    返回：
        读到的内容；文件不存在时返回 None

    【要点】用 try/except 兜住"文件不存在"的情况，避免调用方程序崩溃。
    """
    f = None
    try:
        f = open(file_info, 'r', encoding='utf-8')
        content = f.read()
        print('文件的内容如下：')
        print(content)
        return content
    except FileNotFoundError:
        print(f'文件不存在：{file_info}')
        return None
    except Exception as e:
        # 兜底：把异常类型也打出来，方便定位问题
        print(f'读文件出错了：{type(e).__name__} -> {e}')
        return None
    finally:
        # 【修正点】原代码这里是 `if f: True`，是个笔误。
        # 正确写法是 `if f: f.close()` —— 只有确实打开了文件才需要关闭。
        if f:
            f.close()


def append_to_file(file_info, content):
    """向文件末尾追加一行内容

    参数：
        file_info：文件路径
        content：要写入的内容
    返回：
        写入的字符数

    【要点 1】用 'a' 模式，不会覆盖原内容。
    【要点 2】用 with 语句，即使中途出错文件也会自动关闭。
    """
    # 如果目标文件在子目录里，先把目录建出来，否则会 FileNotFoundError
    folder = os.path.dirname(file_info)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

    with open(file_info, 'a', encoding='utf-8') as f:
        # '\n' 要自己写，'a' 模式不会自动给你加换行
        written = f.write(content + '\n')
    return written


if __name__ == '__main__':
    # 【修正点】原代码用的是 "/03.数据结构/data.txt"，这是一个从盘符根目录开始的路径，
    # 在绝大多数机器上都不存在。这里改成"以本文件所在目录为基准"来定位，
    # 这样无论你从哪个目录运行，都能找到正确的位置。
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    demo_file = os.path.join(BASE_DIR, 'demo.txt')

    append_to_file(demo_file, 'Hello World')
    append_to_file(demo_file, 'happy everyday')
    print_file_info(demo_file)

    # 演示：读一个不存在的文件，看看优雅的报错
    print('\n--- 故意读一个不存在的文件 ---')
    print_file_info(os.path.join(BASE_DIR, '不存在.txt'))
