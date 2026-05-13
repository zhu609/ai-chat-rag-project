import turtle
import random
import time

# --- 配置部分 ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BG_COLOR = "black"
TREE_COLOR = "forest green"
STAR_COLOR = "gold"

# --- 初始化屏幕 ---
screen = turtle.Screen()
screen.setup(SCREEN_WIDTH, SCREEN_HEIGHT)
screen.title("Merry Christmas - Python Turtle Demo")
screen.bgcolor(BG_COLOR)
screen.tracer(0)  # 关闭自动刷新，用于实现动画效果

# 创建画笔
pen = turtle.Turtle()
pen.hideturtle()
pen.speed(0)

# 用于存储灯光位置的列表，以便让它们闪烁
light_positions = []
# 用于存储雪花的列表
snowflakes = []


def create_snowflake():
    """创建一个雪花对象"""
    t = turtle.Turtle()
    t.hideturtle()
    t.penup()
    t.color("white")
    t.shape("circle")
    t.shapesize(random.uniform(0.1, 0.3))  # 雪花大小随机
    x = random.randint(-SCREEN_WIDTH // 2, SCREEN_WIDTH // 2)
    y = random.randint(SCREEN_HEIGHT // 3, SCREEN_HEIGHT // 2)  # 从屏幕上方生成
    t.goto(x, y)
    t.speed = random.uniform(1, 3)  # 下落速度
    return t


def draw_star(size, x, y):
    """在树顶画一颗五角星"""
    pen.penup()
    pen.goto(x, y)
    pen.pendown()
    pen.color(STAR_COLOR)
    pen.begin_fill()
    for _ in range(5):
        pen.forward(size)
        pen.right(144)
    pen.end_fill()


def draw_tree(branch_len, t):
    """递归绘制分形圣诞树"""
    if branch_len > 15:
        # 树干变细
        t.pensize(branch_len / 10)
        t.forward(branch_len)

        # 右分支
        angle = random.randint(20, 30)
        sub_len = random.uniform(0.6, 0.8)
        t.right(angle)
        draw_tree(branch_len * sub_len, t)

        # 左分支
        t.left(angle * 2)
        draw_tree(branch_len * sub_len, t)

        # 回到主干
        t.right(angle)
        t.backward(branch_len)
    else:
        # 树梢末端：记录位置用于画彩灯，画一点绿色叶子
        t.color("light green")
        t.pensize(2)
        t.forward(branch_len)

        # 记录灯光位置 (x, y)
        if random.random() > 0.3:  # 70%的概率在树梢加灯
            light_positions.append(t.pos())

        t.backward(branch_len)
        t.color(TREE_COLOR)


def draw_lights(colors):
    """在记录的位置画出彩色灯光"""
    for pos in light_positions:
        pen.penup()
        pen.goto(pos)
        pen.pendown()
        pen.dot(random.randint(5, 10), random.choice(colors))


def write_text():
    """写入节日祝福"""
    # 英文
    pen.penup()
    pen.goto(0, -250)
    pen.color("red")
    pen.write("Merry Christmas", align="center", font=("Script MT Bold", 40, "bold"))

    # 中文 (注意：如果系统没有SimHei字体，可能需要换成Arial等)
    pen.goto(0, -300)
    pen.color("gold")
    pen.write("圣诞快乐", align="center", font=("SimHei", 30, "bold"))


def init_scene():
    """初始化场景绘制（只画一次的部分）"""
    # 1. 移动到底部准备画树
    t = turtle.Turtle()
    t.hideturtle()
    t.speed(0)
    t.left(90)
    t.penup()
    t.goto(0, -150)
    t.pendown()
    t.color(TREE_COLOR)

    # 2. 画树
    draw_tree(100, t)

    # 3. 画树顶星星
    # 获取树顶的大致位置，这里手动微调一下
    draw_star(30, -15, 110)

    # 4. 写字
    write_text()

    # 5. 初始化雪花
    for _ in range(50):
        snow = create_snowflake()
        snowflakes.append(snow)


# --- 主程序逻辑 ---

# 先画出静态的树和文字
init_scene()

# 灯光颜色池
light_colors = ["red", "yellow", "blue", "orange", "cyan", "magenta", "white"]

# 动画循环
try:
    while True:
        # 1. 刷新灯光 (闪烁效果)
        # 只需要重画灯光点，不需要重画整棵树
        # 清除之前的灯光点比较麻烦，这里利用覆盖的方式，或者简单的颜色切换
        # 为了性能，我们让灯光在每一帧随机变色
        draw_lights(light_colors)

        # 2. 雪花下落逻辑
        pen.clear()  # 清除上一帧的动态元素（如果用pen画的话）
        # 注意：这里我们只清除pen画的东西（灯光），树是另一个turtle画的，不会被清除

        for snow in snowflakes:
            snow.clear()  # 清除上一次雪花位置
            y = snow.ycor()
            y -= snow.speed
            x = snow.xcor()

            # 飘动效果
            x += random.uniform(-1, 1)

            # 如果落到底部，重置到顶部
            if y < -SCREEN_HEIGHT // 2:
                y = random.randint(SCREEN_HEIGHT // 3, SCREEN_HEIGHT // 2)
                x = random.randint(-SCREEN_WIDTH // 2, SCREEN_WIDTH // 2)

            snow.goto(x, y)
            snow.showturtle()  # 显示雪花（圆点）
            # 注意：大量turtle对象移动会慢，这里用stamp或dot会更快，但在tracer(0)下还可以接受

        screen.update()  # 刷新画面
        time.sleep(0.05)  # 控制动画速度

except turtle.Terminator:
    # 处理窗口关闭时的报错
    pass