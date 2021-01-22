from game.config import *

def normalize(position):
    """ 接受任意精度的“position”，并返回包含该位置的方块。

    参数
    ----------
    position : tuple of len 3

    返回
    -------
    block_position : tuple of ints of len 3

    """
    x, y, z = position
    x, y, z = (int(round(x)), int(round(y)), int(round(z)))
    return (x, y, z)


def sectorize(position):
    """ 返回给与的坐标所在的区块。

    参数
    ----------
    position : tuple of len 3

    返回
    -------
    sector : tuple of len 3

    """
    x, y, z = normalize(position)
    x, y, z = x // SECTOR_SIZE, y // SECTOR_SIZE, z // SECTOR_SIZE
    return (x, 0, z)
