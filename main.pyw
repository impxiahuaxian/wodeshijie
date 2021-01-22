from __future__ import division

import math
import random
import time


from pyglet import image
from pyglet.gl import *
from pyglet.window import key, mouse

from game.config import *
from game.model import *
from game.functions import *


class Window(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        # 窗口是否锁定鼠标。
        self.exclusive = False

        # 飞行时重力没有影响，速度会提高。
        self.flying = False

        # Strafe表示移动方向，静止时为0,0，第一个元素前进时为-1后退时1
        # 第二个元素左移是为-1，右移时为1。
        self.strafe = [0, 0]

        # 当前所在坐标，数据为浮点数，Y为竖轴。
        self.position = (0, 0, 0)

        # 第一个元素为玩家视线在水平面中旋转角度，第二个元素为垂直平面的旋转角度
        self.rotation = (0, 0)

        # 玩家所在的区块
        self.sector = None

        # 十字准星
        self.reticle = None

        # 垂直速度
        self.dy = 0

        # 玩家可以放置的方块列表。
        self.inventory = [BRICK, GRASS, SAND]

        # 玩家当前可以放置的方块。
        self.block = self.inventory[0]

        # 方块选择
        self.num_keys = [
            key._1, key._2, key._3, key._4, key._5,
            key._6, key._7, key._8, key._9, key._0]

        # 处理方块的model实例。
        self.model = Model()

        # 显示在画面左上方的标签。
        self.label = pyglet.text.Label('', font_name='Arial', font_size=25,
            x=10, y=self.height - 10, anchor_x='left', anchor_y='top',
            color=(0, 0, 0, 255))

        
        pyglet.clock.schedule_interval(self.update, 1.0 / TICKS_PER_SEC)################

    def set_exclusive_mouse(self, exclusive):
        """ 如果“ exclusive”为True，则游戏将捕获鼠标，
            如果为False，则游戏将忽略鼠标。

        """
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def get_sight_vector(self):
        """ 返回当前视线矢量，指示玩家正在看的方向。

        """
        x, y = self.rotation
        #y的范围是-90到90，或者-pi/2到pi/2，所以m的范围是0到1，
        #当向前看与地面平行时，m是1，当向上或向下看时，m是0。
        m = math.cos(math.radians(y))#转化为弧度
        # dy的范围从-1到1，直下看是-1，直上看是1。
        dy = math.sin(math.radians(y))
        dx = math.cos(math.radians(x - 90)) * m
        dz = math.sin(math.radians(x - 90)) * m
        return (dx, dy, dz)

    def get_motion_vector(self):
        """ 返回指示玩家速度的当前运动向量。

        返回
        -------
        vector : tuple of len 3
            元组分别包含x，y和z的速度。

        """
        if any(self.strafe):
            x, y = self.rotation
            strafe = math.degrees(math.atan2(*self.strafe))
            y_angle = math.radians(y)
            x_angle = math.radians(x + strafe)
            if self.flying:
                m = math.cos(y_angle)
                dy = math.sin(y_angle)
                if self.strafe[1]:
                    # 向左或向右移动。
                    dy = 0.0
                    m = 1
                if self.strafe[0] > 0:
                    # 向后移动。
                    dy *= -1
                # 当玩家向上或向下飞行时的左右运动速度。
                dx = math.cos(x_angle) * m
                dz = math.sin(x_angle) * m
            else:
                dy = 0.0
                dx = math.cos(x_angle)
                dz = math.sin(x_angle)
        else:
            dy = 0.0
            dx = 0.0
            dz = 0.0
        return (dx, dy, dz)

    def update(self, dt):
        """ 此方法由pyglet时钟重复调用。

        参数
        ----------
        dt : float
            The change in time since the last call.

        """
        self.model.process_queue()
        sector = sectorize(self.position)
        if sector != self.sector:
            self.model.change_sectors(self.sector, sector)
            if self.sector is None:
                self.model.process_entire_queue()
            self.sector = sector
        m = 8
        dt = min(dt, 0.2)
        for _ in range(m):
            self._update(dt / m)

    def _update(self, dt):
        """  运动逻辑以及重力和碰撞检测。

        参数
        ----------
        dt : float
            The change in time since the last call.

        """
        # 行走
        speed = FLYING_SPEED if self.flying else WALKING_SPEED
        d = dt * speed
        dx, dy, dz = self.get_motion_vector()
        # 考虑重力之前的速度
        dx, dy, dz = dx * d, dy * d, dz * d
        # 重力
        if not self.flying:
            # 垂直速度更新
            self.dy -= dt * GRAVITY
            self.dy = max(self.dy, -TERMINAL_VELOCITY)
            dy += self.dy * dt
        # 碰撞检测
        x, y, z = self.position
        x, y, z = self.collide((x + dx, y + dy, z + dz), PLAYER_HEIGHT)
        self.position = (x, y, z)

    def collide(self, position, height):
        """ 检查玩家在给定的位置是否与世界上的任何障碍物发生碰撞。

        参数
        ----------
        position : tuple of len 3
            在位置(x, y, z)检查碰撞。
        height : int or float
            玩家高度。

        返回
        -------
        position : tuple of len 3
            玩家的新位置。

        """
        pad = 0.25
        p = list(position)
        np = normalize(position)
        for face in FACES:
            for i in range(3):
                if not face[i]:
                    continue
                d = (p[i] - np[i]) * face[i]
                if d < pad:
                    continue
                for dy in range(height):  
                    op = list(np)
                    op[1] -= dy
                    op[i] += face[i]
                    if tuple(op) not in self.model.world:
                        continue
                    p[i] -= (d - pad) * face[i]
                    if face == (0, -1, 0) or face == (0, 1, 0):
                        self.dy = 0
                    break
        return tuple(p)

    def on_mouse_press(self, x, y, button, modifiers):
        """ 鼠标按键被按下的时候调用.  按钮amd修饰符映射详见pyglet doc。

        参数
        ----------
        x, y : int
            鼠标点击时的坐标。如果鼠标被捕获，则始终位于屏幕中心。
        button : int
            表示已单击的鼠标按钮的数字。1代表左按钮，4代表右按钮。
        modifiers : int
            表示单击鼠标按钮时按下的任何修改键的数字。

        """
        if self.exclusive:
            vector = self.get_sight_vector()
            block, previous = self.model.hit_test(self.position, vector)
            if (button == mouse.RIGHT):
                if previous:
                    self.model.add_block(previous, self.block)
            elif button == pyglet.window.mouse.LEFT and block:
                texture = self.model.world[block]
                if texture != STONE:
                    self.model.remove_block(block)
        else:
            self.set_exclusive_mouse(True)

    def on_mouse_motion(self, x, y, dx, dy):
        """ 移动鼠标时被调用

        参数
        ----------
        x, y : int
            鼠标点击时的坐标。如果鼠标被捕获，则始终位于屏幕中心。
        dx, dy : float
            鼠标移动的量。

        """
        if self.exclusive:
            m = 0.15
            x, y = self.rotation
            x, y = x + dx * m, y + dy * m
            y = max(-90, min(90, y))
            self.rotation = (x, y)

    def on_key_press(self, symbol, modifiers):
        """ 按下键盘的时候启用，键位映射详见pyglet doc。

        参数
        ----------
        symbol : int
            表示按下的键的数字。
        modifiers : int
            表示按下的任何修改键的数字。

        """
        if symbol == key.W:
            self.strafe[0] -= 1
        elif symbol == key.S:
            self.strafe[0] += 1
        elif symbol == key.A:
            self.strafe[1] -= 1
        elif symbol == key.D:
            self.strafe[1] += 1
        elif symbol == key.SPACE:
            if self.dy == 0:
                self.dy = JUMP_SPEED
        elif symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)
        elif symbol == key.TAB:
            self.flying = not self.flying
        elif symbol in self.num_keys:
            index = (symbol - self.num_keys[0]) % len(self.inventory)
            self.block = self.inventory[index]

    def on_key_release(self, symbol, modifiers):
        """ 释放键盘按键的时候被调用，键位映射详见pyglet doc。
        参数
        ----------
        symbol : int
            表示按下的键的数字。
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        if symbol == key.W:
            self.strafe[0] += 1
        elif symbol == key.S:
            self.strafe[0] -= 1
        elif symbol == key.A:
            self.strafe[1] += 1
        elif symbol == key.D:
            self.strafe[1] -= 1

    def on_resize(self, width, height):
        """ 调整窗口大小的时候被调用。

        """
        # label
        self.label.y = height - 10
        # reticle
        if self.reticle:
            self.reticle.delete()
        x, y = self.width // 2, self.height // 2
        n = 10
        self.reticle = pyglet.graphics.vertex_list(4,
            ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n))
        )

    def set_2d(self):
        """ 配置OpenGL绘制2d图形。

        """
        width, height = self.get_size()
        glDisable(GL_DEPTH_TEST)
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, max(1, width), 0, max(1, height), -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set_3d(self):#######################################################
        """ 配置OpenGL绘制3d图形。

        """
        width, height = self.get_size()
        glEnable(GL_DEPTH_TEST)##########################
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(FOV, width / float(height), 0.1, 60.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        x, y = self.rotation
        glRotatef(x, 0, 1, 0)
        glRotatef(-y, math.cos(math.radians(x)), 0, math.sin(math.radians(x)))
        x, y, z = self.position
        glTranslatef(-x, -y, -z)

    def on_draw(self):
        """ 总图像绘制

        """
        self.clear()
        self.set_3d()
        glColor3d(1, 1, 1)
        self.model.batch.draw()
        self.draw_focused_block()
        self.set_2d()
        self.draw_label()
        self.draw_reticle()

    def draw_focused_block(self):
        """ 给被玩家指定的方块画上黑边。

        """
        vector = self.get_sight_vector()
        block = self.model.hit_test(self.position, vector)[0]
        if block:
            x, y, z = block
            vertex_data = cube_vertices(x, y, z, 0.51)
            glColor3d(0, 0, 0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            pyglet.graphics.draw(24, GL_QUADS, ('v3f/static', vertex_data))
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def draw_label(self):
        """ 绘制左上角显示数据的标签。

        """
        x, y, z = self.position
        self.label.text = '(%.2f, %.2f, %.2f) %d / %d %02d '% (x, y, z,len(self.model._shown),len(self.model.world), pyglet.clock.get_fps())
        self.label.draw()

    def draw_reticle(self):
        """ 在屏幕中心绘制一个十字准星

        """
        glColor3d(0, 0, 0)
        self.reticle.draw(GL_LINES)


def setup_fog():
    """ 渲染距离控制多少世界的区块立即可见。
        渲染的区块越少，每帧就渲染得越快，FPS因而更高。
        最远的地形会淡化成天空的颜色，就像起雾一样，
        这样来避免视野中出现尖锐的边缘；所以该选项也称为“雾”。

    """
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.5, 0.69, 1.0, 1))
    glHint(GL_FOG_HINT, GL_DONT_CARE)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 20.0)
    glFogf(GL_FOG_END, 60.0)


def setup():
    """ 基础OpenGL配置。

    """
    glClearColor(0.5, 0.69, 1.0, 1)
    glEnable(GL_CULL_FACE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    setup_fog()

    


if __name__ == '__main__':
    window = Window(width=900, height=675, caption='Pyglet', resizable=True)
    # 隐藏鼠标光标并防止鼠标离开窗口。
    window.set_exclusive_mouse(True)
    setup()
    pyglet.app.run()
