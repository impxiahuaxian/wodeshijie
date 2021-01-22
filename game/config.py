import math

TICKS_PER_SEC = 60

MAX_DISTANCE = 8

SECTOR_SIZE = 16

FOV = 74

WALKING_SPEED = 5
FLYING_SPEED = 15

GRAVITY = 20.0
MAX_JUMP_HEIGHT = 1.0 # 一个方块的高度。

# 要导出用于计算跳跃速度的公式，请先求解
# v_t = v_0 - g * t
# t为达到最大高度的时间

# 由v_t = 0得最大高度所需时间：
# t = v_0 / g
# 使用t和所需的跳跃高度来求解v_0（跳跃速度）
# s = s_0 + v_0 * t -（g * t ^ 2）/ 2
JUMP_SPEED = math.sqrt(2 * GRAVITY * MAX_JUMP_HEIGHT)
TERMINAL_VELOCITY = 50

PLAYER_HEIGHT = 2




