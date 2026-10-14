"""
爱心动画 —— pygame 入门综合示例
================================

这是本项目里唯一一个"图形界面"脚本。前面学的变量、循环、函数、类、数据结构，
在这里全部用上了，可以当成一次**综合练习**来看。

它做了三件事：
    1. 用【参数方程】画出一个心形
    2. 让心形有【心跳】一样的缩放节奏
    3. 从中心向四周喷出【粒子】，营造"绽放"的效果

运行方式
--------
    python heart_animation.py                # 正常打开窗口
    python heart_animation.py --frames 120   # 只跑 120 帧就自动退出（用于自动化验证）

按 ESC 或点窗口右上角的 × 都能退出。

依赖
----
    pygame（本项目已通过 uv 装好：uv add pygame）

================================
修复说明（相对原始版本）
================================
原脚本在当前 pygame（2.6.1）下会**直接崩溃**：

    ValueError: Can't normalize Vector of length Zero

原因在粒子的初始化：

    x, y = width // 2, height // 2
    velocity = pygame.Vector2(
        (pygame.Vector2(x, y) - pygame.Vector2(width // 2, height // 2)).normalize().x * 5, ...
    )

`(x, y)` 和 `(width // 2, height // 2)` **完全相等**，相减得到零向量 `(0, 0)`，
而对零向量求 `normalize()`（单位化）在数学上是"除以 0"，pygame 新版会**直接报错**
（老版本会静默返回零向量，所以这个 bug 藏了很久）。

即使不报错，逻辑上也是错的：速度恒为 `(0, 0)` 意味着
**100 个粒子全都叠在正中心一动不动**，根本看不到"喷射"效果。

修法：给每个粒子一个**随机的方向角**，这样它们才会朝四面八方散开。

顺便还改了两个小问题：
    - 原来 `heart_points` 算了一遍却没用上（主循环里又重算了一遍）-> 抽成函数复用
    - 原来每一帧都新建一次字体对象 `pygame.font.SysFont(...)` -> 提到循环外，只建一次
"""

import math
import random
import sys

import pygame

# ============================================================
# 一、配置区：把所有"可调参数"集中放在开头
#    （好习惯：以后想改颜色、大小，只来这里改，不用翻遍全文件）
# ============================================================

WIDTH, HEIGHT = 800, 600          # 窗口尺寸
FPS = 60                          # 目标帧率
BG_COLOR = (12, 12, 20)           # 深色背景（比纯黑柔和一点，粒子更显眼）

RED = (220, 20, 60)               # 心形填充色
PINK = (255, 182, 193)            # 心形描边色
TEXT_COLOR = (235, 235, 245)

PARTICLE_COLORS = [               # 粒子的颜色池（随机抽）
    (255, 0, 0),
    (255, 20, 147),
    (255, 105, 180),
    (255, 192, 203),
]
PARTICLE_COUNT = 120              # 粒子数量
PARTICLE_SPEED = 5.0              # 粒子初速度（像素/帧）
PARTICLE_SIZE = 3.0               # 粒子初始边长
PARTICLE_DECAY = 0.05             # 每帧缩小多少（越小越"长寿"）

HEART_SCALE = 10                  # 心形放大倍数（参数方程的原始尺度很小）
HEART_STEPS = 360                 # 采样点数（越细心形越平滑）
PULSE_AMPLITUDE = 0.06            # 心跳幅度（0.06 = 最大缩放 ±6%）
PULSE_SPEED = 250                 # 心跳快慢（数值越小跳得越快）


# ============================================================
# 二、心形曲线：用数学公式画出"心"
# ============================================================
#
# 心形的参数方程（t 从 0 到 2π 走一圈）：
#
#     x = 16·sin³(t)
#     y = 13·cos(t) − 5·cos(2t) − 2·cos(3t) − cos(4t)
#
# 这是一个经典的"心形线"公式。
# 注意：**屏幕坐标系的 y 轴是向下的**（原点在左上角），
# 而数学坐标系 y 轴向上，所以最后要写 `-y` 把它翻过来。

def heart_points(scale: float = 1.0, center: tuple = (WIDTH // 2, HEIGHT // 2)):
    """返回构成心形的点列表，可以直接交给 pygame.draw.polygon / lines 使用。

    参数
    ----
    scale  : 缩放倍数，1.0 是原始大小
    center : 心形的中心坐标 (x, y)
    """
    cx, cy = center
    points = []
    for i in range(HEART_STEPS):
        t = math.radians(i)                       # 转成弧度，math 里的三角函数要弧度
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t)
             - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t)
             - math.cos(4 * t))
        points.append((
            x * HEART_SCALE * scale + cx,         # 缩放 + 平移到中心
            -y * HEART_SCALE * scale + cy,        # 【注意】y 取负，翻转到屏幕坐标系
        ))
    return points


# ============================================================
# 三、粒子：用"类"来管理，每个粒子自己管好自己的状态
# ============================================================
#
# 为什么要用类？
# 因为每个粒子都有自己的"位置、速度、大小、颜色"，
# 用类把它们打包在一起，代码比"一行一个列表 + 一堆下标"清楚得多。

class Particle:
    """一个从中心向外飞散的小方块。"""

    def __init__(self, center):
        self.center = pygame.Vector2(center)      # 记住出生点，方便"重生"
        self.reset()

    def reset(self):
        """回到中心，并随机挑一个方向重新出发。

        【关键修复】原脚本在这里用了 `(pos - center).normalize()`，
        因为 pos 和 center 一开始完全相同，得到的是零向量，会直接抛：
            ValueError: Can't normalize Vector of length Zero

        正确做法是**随机取一个方向角**，再用三角函数算出方向向量：
            (cos θ, sin θ) 本来就是长度为 1 的单位向量，不需要 normalize。
        """
        angle = random.uniform(0, math.tau)       # math.tau = 2π，一整圈
        direction = pygame.Vector2(math.cos(angle), math.sin(angle))

        self.pos = pygame.Vector2(self.center)
        self.vel = direction * PARTICLE_SPEED
        self.size = PARTICLE_SIZE
        self.color = random.choice(PARTICLE_COLORS)

    def update(self):
        """每帧调用一次：移动、变小，飞出屏幕或太小了就重生。"""
        self.pos += self.vel                      # Vector2 支持直接相加
        self.size -= PARTICLE_DECAY               # 逐渐缩小，营造"消散"感

        out_of_screen = not (0 <= self.pos.x <= WIDTH and 0 <= self.pos.y <= HEIGHT)
        if self.size <= 0.5 or out_of_screen:
            self.reset()

    def draw(self, surface):
        """把自己画到画布上。"""
        s = max(1.0, self.size)                   # 防止尺寸变成 0 或负数导致画不出来
        pygame.draw.rect(surface, self.color, (self.pos.x, self.pos.y, s, s))


# ============================================================
# 四、主程序
# ============================================================

def main():
    # 命令行参数：--frames N 表示只跑 N 帧就退出（方便自动化测试/截图）
    max_frames = None
    if '--frames' in sys.argv:
        idx = sys.argv.index('--frames')
        if idx + 1 < len(sys.argv):
            max_frames = int(sys.argv[idx + 1])

    # --- 初始化 ---
    pygame.init()                                  # 初始化所有 pygame 子系统
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('爱心动画 - 按 ESC 退出')
    clock = pygame.time.Clock()

    # 【优化】字体只需要建一次，不必每帧都建（原脚本每帧都在建，白白浪费性能）
    # 优先用系统中文字体；找不到会回退到 pygame 默认字体
    font = None
    for name in ('simhei', 'microsoftyahei', 'simsun'):
        try:
            font = pygame.font.SysFont(name, 32)
            break
        except Exception:
            continue
    if font is None:
        font = pygame.font.Font(None, 32)

    # --- 创建粒子 ---
    center = (WIDTH // 2, HEIGHT // 2)
    particles = [Particle(center) for _ in range(PARTICLE_COUNT)]

    # --- 主循环 ---
    running = True
    frames = 0

    while running:
        # 1) 处理事件：所有"用户输入"都要在这里读，否则窗口会卡死（无响应）
        for event in pygame.event.get():
            if event.type == pygame.QUIT:          # 点了右上角的关闭
                running = False
            elif event.type == pygame.KEYDOWN:     # 按了键盘
                if event.key == pygame.K_ESCAPE:   # ESC 退出
                    running = False

        # 2) 清屏（用深色铺满，相当于"擦掉上一帧"）
        screen.fill(BG_COLOR)

        # 3) 计算这一帧的心形缩放：用 sin 做平滑的往复变化，模拟心跳
        ticks = pygame.time.get_ticks()            # 从启动到现在的毫秒数
        scale = 1.0 + PULSE_AMPLITUDE * math.sin(ticks / PULSE_SPEED)

        # 4) 画心形：先填充，再描边
        pts = heart_points(scale, center)
        pygame.draw.polygon(screen, RED, pts)              # 填充（实心）
        pygame.draw.lines(screen, PINK, True, pts, 3)      # 描边（True = 闭合）

        # 5) 更新并绘制所有粒子（先更新状态，再画出来）
        for p in particles:
            p.update()
            p.draw(screen)

        # 6) 叠加一行文字
        text = font.render('爱心动画 - 按 ESC 退出', True, TEXT_COLOR)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 18))

        # 7) 把刚画好的这一帧"翻"到屏幕上显示
        pygame.display.flip()

        # 8) 控制帧率：不加这句会跑满 CPU，风扇狂转
        clock.tick(FPS)

        frames += 1
        if max_frames is not None and frames >= max_frames:
            print(f'已跑满 {frames} 帧，正常退出（--frames 指定）')
            running = False

    # --- 收尾 ---
    pygame.quit()          # 释放 pygame 占用的资源（窗口、音频等）


if __name__ == '__main__':
    main()
