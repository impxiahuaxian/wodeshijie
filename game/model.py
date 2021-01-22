from pyglet import image
from pyglet.gl import *
from pyglet.graphics import TextureGroup
from collections import deque
import random
import time

from game.config import *
from game.getTexture import *
from game.functions import *

FACES = [
    ( 0, 1, 0),
    ( 0,-1, 0),
    (-1, 0, 0),
    ( 1, 0, 0),
    ( 0, 0, 1),
    ( 0, 0,-1),
]

class Model(object):

    def __init__(self):

        # Batch是用于批处理渲染的顶点列表的集合。
        self.batch = pyglet.graphics.Batch()

        # 一个TextureGroup实例时启用，并绑定OpenGL纹理的一个组。
        self.group = TextureGroup(image.load(TEXTURE_PATH).get_texture())

        # 从方块坐标到方块纹理的映射。
        # 储存了所有方块。
        self.world = {}

        # 与"worlf"相同，但只包含要显示的方块。
        self.shown = {}

        # 从方块坐标到pyglet`VertextList`的映射。
        self._shown = {}

        # 区块与其所含的方块坐标列表的映射。
        self.sectors = {}

        # 简单的函数队列实现，队列中填充了_show_block（）和_hide_block（）的调用
        self.queue = deque()

        self._initialize()

    def _initialize(self):
        """ 初始化世界。

        """
        n = 80  # 游戏范围宽度和高度的一半
        s = 1  # step size
        y = 0  # 初始Y高度
        
        for x in range(-n, n + 1, s):
            for z in range(-n, n + 1, s):
                # 地面上铺一层石头与草方块。
                self.add_block((x, y - 2, z), GRASS, immediate=False)
                self.add_block((x, y - 3, z), STONE, immediate=False)
                if x in (-n, n) or z in (-n, n):
                    # 创建世界边界。
                    for dy in range(-2, 3):
                        self.add_block((x, y + dy, z), STONE, immediate=False)

        # 随机生成小山丘。
        o = n - 10
        for _ in range(120):
            a = random.randint(-o, o)  # 山的x坐标。
            b = random.randint(-o, o)  # 山的z坐标。
            c = -1  # 底。
            h = random.randint(1, 6)  # 高度。
            s = random.randint(4, 8)  # 2 * s 为山的边长。
            d = 1  # 坡度。
            t = random.choice([GRASS, SAND, BRICK])
            for y in range(c, c + h):
                for x in range(a - s, a + s + 1):
                    for z in range(b - s, b + s + 1):
                        if (x - a) ** 2 + (z - b) ** 2 > (s + 1) ** 2:
                            continue
                        if (x - 0) ** 2 + (z - 0) ** 2 < 5 ** 2:
                            continue
                        self.add_block((x, y, z), t, immediate=False)
                s -= d  # 减少角上的边长，使山变得圆润。

    def hit_test(self, position, vector, max_distance=MAX_DISTANCE):
        """ 从当前位置进行视线搜索。如果某个方块在视线内，则返回该方块以及
            先前位于视线中的块。如果没有则返回None，None。

        参数
        ----------
        position : tuple of len 3
            The (x, y, z) position to check visibility from.
        vector : tuple of len 3
            The line of sight vector.
        max_distance : int
            How many blocks away to search for a hit.

        """
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in range(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self.world:#如果key存在，而且world中存在
                return key, previous
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        return None, None

    def exposed(self, position):
        """ 如果position的6面全部被方块包围返回False，否则返回True。

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            if (x + dx, y + dy, z + dz) not in self.world:
                return True
        return False

    def add_block(self, position, texture, immediate=True):
        """ 在给定的位置添加给定纹理的方块。

        参数
        ----------
        position : tuple of len 3
            添加方块的(x, y, z) 坐标
        texture : list of len 3
            方块纹理的坐标. 用`tex_coords()`生成
        immediate : bool
            是否立刻绘制方块

        """
        if position in self.world:
            self.remove_block(position, immediate)
        self.world[position] = texture
        self.sectors.setdefault(sectorize(position), []).append(position)
        if immediate:
            if self.exposed(position):
                self.show_block(position)
            self.check_neighbors(position)

    def remove_block(self, position, immediate=True):
        """ 删除给定位置的块。

        参数
        ----------
        position : tuple of len 3
            要移除方块的(x, y, z)位置。
        immediate : bool
            是否立即在canvas中移除方块。

        """
        del self.world[position]
        self.sectors[sectorize(position)].remove(position)
        if immediate:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(position)

    def check_neighbors(self, position):
        """ 检查方块自身周围的方块，并确保其可视状态为最新状态。
            隐藏被完全包围的方块，并显示所有暴露出来的方块。
            通常在添加或删除方块后使用。

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            key = (x + dx, y + dy, z + dz)
            if key not in self.world:
                continue
            if self.exposed(key):
                if key not in self.shown:
                    self.show_block(key)
            else:
                if key in self.shown:
                    self.hide_block(key)

    def show_block(self, position, immediate=True):
        """ 显示给定位置处的方块. 此方法假定已使用add_block（）添加该方块。

        参数
        ----------
        position : tuple of len 3
            要显示方块的(x, y, z)位置。
        immediate : bool
            是否立即显示该方块。

        """
        texture = self.world[position]
        self.shown[position] = texture
        if immediate:
            self._show_block(position, texture)
        else:
            self._enqueue(self._show_block, position, texture)

    def _show_block(self, position, texture):###################################
        """ show_block（）方法的私有实现。

        参数
        ----------
        position : tuple of len 3
            
        texture : list of len 3
            

        """
        x, y, z = position
        vertex_data = cube_vertices(x, y, z, 0.5)
        texture_data = list(texture)
        # create vertex list
        # FIXME Maybe `add_indexed()` should be used instead
        self._shown[position] = self.batch.add(24, GL_QUADS, self.group,
            ('v3f/static', vertex_data),
            ('t2f/static', texture_data))

    def hide_block(self, position, immediate=True):
        """ 隐藏给定位置的方块，并不将其从world中删除。

        参数
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to hide.
        immediate : bool
            Whether or not to immediately remove the block from the canvas.

        """
        self.shown.pop(position)
        if immediate:
            self._hide_block(position)
        else:
            self._enqueue(self._hide_block, position)

    def _hide_block(self, position):
        """ “ hide_block（）”方法的私有实现。

        """
        self._shown.pop(position).delete()

    def show_sector(self, sector):
        """ 确保给定区块中应显示的所有方块都被绘制。

        """
        for position in self.sectors.get(sector, []):
            if position not in self.shown and self.exposed(position):
                self.show_block(position, False)

    def hide_sector(self, sector):
        """ 确保给定区块中所有应隐藏的方块不被绘制。

        """
        for position in self.sectors.get(sector, []):
            if position in self.shown:
                self.hide_block(position, False)

    def change_sectors(self, before, after):
        """ 移动区块后调用。
            区块是世界的连续x，y子区域。
            划分区块用于加速世界渲染。

        """
        before_set = set()
        after_set = set()
        pad = 4
        for dx in range(-pad, pad + 1):
            for dy in [0]:  # range(-pad, pad + 1):
                for dz in range(-pad, pad + 1):
                    if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                        continue
                    if before:
                        x, y, z = before
                        before_set.add((x + dx, y + dy, z + dz))
                    if after:
                        x, y, z = after
                        after_set.add((x + dx, y + dy, z + dz))
        show = after_set - before_set
        hide = before_set - after_set
        for sector in show:
            self.show_sector(sector)
        for sector in hide:
            self.hide_sector(sector)

    def _enqueue(self, func, *args):
        """ 将`func`添加到内部队列中。

        """
        self.queue.append((func, args))

    def _dequeue(self):
        """ 从内部队列中删除最上层的函数并调用它。

        """
        func, args = self.queue.popleft()
        func(*args)

    def process_queue(self):
        """ 定期处理整个队列。这样可以使游戏循环平稳运行。
            队列包含对_show_block（）和_hide_block（）的调用，
            因此，如果在使用Instant = False的情况下
            调用add_block（）或remove_block（），则应调用此方法。

        """
        start = time.perf_counter()
        while self.queue and time.perf_counter() - start < 1.0 / TICKS_PER_SEC:
            self._dequeue()

    def process_entire_queue(self):
        """ 不间断地处理整个队列。

        """
        while self.queue:
            self._dequeue()
