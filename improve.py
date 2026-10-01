# -*- coding: utf-8 -*-

import math
import sys
import time

ROW, COL = 17, 82

MIDDLE_COL, LEFT_COL, RIGHT_COL = 40, 16, 65

SPAWN_LEFT, SPAWN_MIDDLE, SPAWN_RIGHT = 35, 40, 46

RUNNING, JUMP, DOWN, GLIDE = 0, 1, 2, 3

NONE = 0
INVINCIBLE = 4
FLYING = 5
SUPER_JUMP = 6
MAGNET = 7
DOUBLE_SCORE = 8
DOUBLE_COIN = 9

FRAME_DELAY = 0.01
HINDER_PERIOD = 4
PROP_PERIOD = 45


try:
    import msvcrt

    def kbhit() -> bool:
        return msvcrt.kbhit()

    def getch() -> str:
        ch = msvcrt.getch()
        if ch in (b'\x00', b'\xe0'):
            msvcrt.getch()
            return ''
        return ch.decode('utf-8', 'ignore')
except ImportError:
    import select
    import termios
    import tty

    def kbhit() -> bool:
        return bool(select.select([sys.stdin], [], [], 0)[0])

    def getch() -> str:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clear_screen() -> None:
    sys.stdout.write('\x1b[2J\x1b[H')
    sys.stdout.flush()


def hide_cursor() -> None:
    sys.stdout.write('\x1b[?25l')
    sys.stdout.flush()


def show_cursor() -> None:
    sys.stdout.write('\x1b[?25h')
    sys.stdout.flush()


class Node:
    __slots__ = ('row', 'col', 'eaten', 'hinder_type', 'prop_type')

    def __init__(self, row=0, col=0, eaten=0, hinder_type=' ', prop_type=NONE):
        self.row = row
        self.col = col
        self.eaten = eaten
        self.hinder_type = hinder_type
        self.prop_type = prop_type


map_grid = [[' '] * COL for _ in range(ROW)]

head_col = MIDDLE_COL
head_row = 13

score = 0
coin_nums = 0
score_add = 3

run_flag = 0

speed = 1
speed_limit = 5

speed_hinder_happen = 1
speed_prop_happen = 1

coins: list = []
hinders: list = []
props: list = []

move_state = RUNNING
move_state_time = 1
move_state_time_limit = 24

prop_state = NONE
prop_state_time = 1
prop_state_time_limit = 150

PLACE = (SPAWN_LEFT, SPAWN_MIDDLE, SPAWN_RIGHT)
HINDER_CHARS = ('^', '_', '#', 'x')
PROP_TYPES = (INVINCIBLE, FLYING, SUPER_JUMP, MAGNET, DOUBLE_SCORE, DOUBLE_COIN)

lose = False
replay = True


def put(r: int, c: int, ch: str) -> None:
    if 0 <= r < ROW and 0 <= c < COL:
        map_grid[r][c] = ch


def get(r: int, c: int) -> str:
    if 0 <= r < ROW and 0 <= c < COL:
        return map_grid[r][c]
    return ' '


def print_small_guy() -> None:
    put(head_row, head_col - 1, '(')
    put(head_row, head_col, '*')
    put(head_row, head_col + 1, ')')
    put(head_row + 1, head_col - 1, '/')
    put(head_row + 1, head_col, '|')
    put(head_row + 1, head_col + 1, '\\')
    put(head_row + 2, head_col - 1, '/')
    put(head_row + 2, head_col + 1, '\\')


def clear_small_guy() -> None:
    for dr in range(3):
        for dc in (-1, 0, 1):
            put(head_row + dr, head_col + dc, ' ')


def print_run() -> None:
    global run_flag
    if run_flag == 0:
        run_flag = 1
        put(head_row + 2, head_col - 1, ' ')
        put(head_row + 2, head_col + 1, '\\')
        put(head_row + 1, head_col + 1, ' ')
        put(head_row + 1, head_col - 1, '/')
    else:
        run_flag = 0
        put(head_row + 2, head_col + 1, ' ')
        put(head_row + 2, head_col - 1, '/')
        put(head_row + 1, head_col + 1, '\\')
        put(head_row + 1, head_col - 1, ' ')


def print_jump() -> None:
    print_small_guy()
    put(head_row + 2, head_col - 1, '-')
    put(head_row + 2, head_col + 1, '-')


def print_squat() -> None:
    print_small_guy()
    put(head_row + 1, head_col - 1, '-')
    put(head_row + 1, head_col + 1, '-')
    put(head_row + 2, head_col - 1, '-')
    put(head_row + 2, head_col + 1, '-')


def paint_gliding() -> None:
    print_small_guy()
    put(head_row + 1, head_col, '&')
    put(head_row + 1, head_col - 1, '/')
    put(head_row + 1, head_col + 1, '\\')
    put(head_row + 2, head_col - 1, ' ')
    put(head_row + 2, head_col + 1, ' ')


def clear_coin_hinder(node: Node, letter: str) -> None:
    if node.row <= 15 and get(node.row, node.col) == letter:
        put(node.row, node.col, ' ')


def paint_coin_hinder(node: Node, letter: str) -> None:
    if node.row <= 15:
        put(node.row, node.col, letter)


def clear_prop(node: Node) -> None:
    if node.row <= 15:
        put(node.row, node.col, ' ')
        put(node.row, node.col + 1, ' ')


def paint_prop(node: Node, p: int) -> None:
    if node.row > 15:
        return
    r, c = node.row, node.col
    if p == INVINCIBLE:
        put(r, c, '@'); put(r, c + 1, '@')
    elif p == FLYING:
        put(r, c, '>'); put(r, c + 1, '<')
    elif p == SUPER_JUMP:
        put(r, c, 'd'); put(r, c + 1, 'b')
    elif p == MAGNET:
        put(r, c, 'U'); put(r, c + 1, 'U')
    elif p == DOUBLE_SCORE:
        put(r, c, 'X'); put(r, c + 1, '2')
    elif p == DOUBLE_COIN:
        put(r, c, 'X'); put(r, c + 1, '$')


def clear_hinder_perspective(node: Node) -> None:
    r, c = node.row, node.col
    if r in (2, 3, 4):
        put(r, c - 1, ' ')
    elif r in (5, 6, 7):
        put(r, c - 2, ' '); put(r, c - 1, ' ')
    elif r in (8, 9, 10):
        put(r, c - 2, ' '); put(r, c - 1, ' ')
        put(r, c + 2, ' '); put(r, c + 3, ' ')
    elif 11 <= r <= 15:
        put(r, c - 3, ' '); put(r, c - 2, ' '); put(r, c - 1, ' ')
        put(r, c + 2, ' '); put(r, c + 3, ' ')

    if get(r, c + 1) not in ('@', '<', 'b', 'U', 'X'):
        put(r, c + 1, ' ')


def paint_hinder_perspective(node: Node, letter: str) -> None:
    r, c = node.row, node.col
    if r in (2, 3, 4):
        put(r, c - 1, letter); put(r, c + 1, letter)
    elif r in (5, 6, 7):
        put(r, c - 2, letter); put(r, c - 1, letter); put(r, c + 1, letter)
    elif r in (8, 9, 10):
        put(r, c - 2, letter); put(r, c - 1, letter); put(r, c + 1, letter)
        put(r, c + 2, letter); put(r, c + 3, letter)
    elif 11 <= r <= 15:
        put(r, c - 3, letter); put(r, c - 2, letter); put(r, c - 1, letter)
        put(r, c + 1, letter); put(r, c + 2, letter); put(r, c + 3, letter)


def bottom_clear(lst: list) -> None:
    global score, coin_nums
    idx = -1
    for i, node in enumerate(lst):
        if node.row > 15:
            idx = i
            break
    if idx < 0:
        return
    lst.pop(idx)
    if prop_state == MAGNET:
        score += 3
        coin_nums += 1


def speed_run() -> None:
    global speed_limit
    print_small_guy()
    print_run()
    if ((150 <= score < 300 and speed_limit == 5)
            or (300 <= score < 600 and speed_limit == 4)
            or (600 <= score < 1000 and speed_limit == 3)
            or (score >= 1000 and speed_limit == 2)):
        speed_limit -= 1


def move_state_time_countdown() -> None:
    global move_state_time, move_state, move_state_time_limit
    if move_state_time < move_state_time_limit:
        move_state_time += 1
    else:
        move_state_time = 1
        move_state = RUNNING

    limits = {5: 22, 4: 18, 3: 14, 2: 10, 1: 6}
    if speed_limit in limits:
        move_state_time_limit = limits[speed_limit]


def prop_state_time_countdown() -> None:
    global prop_state_time, prop_state, prop_state_time_limit
    if prop_state_time < prop_state_time_limit:
        prop_state_time += 1
        if prop_state_time in (26 * speed_limit, 28 * speed_limit):
            clear_screen()
    else:
        prop_state_time = 1
        clear_screen()
        prop_state = NONE

    limits = {4: 120, 3: 90, 2: 60, 1: 30}
    if speed_limit in limits:
        prop_state_time_limit = limits[speed_limit]


def coin_happen() -> None:
    idx = int(abs(2.3 * math.sin(score)))
    node = Node(row=1, col=PLACE[idx])
    coins.append(node)
    paint_coin_hinder(node, '$')


def coin_move() -> None:
    for node in coins:
        if node.col <= SPAWN_LEFT:
            clear_coin_hinder(node, '$')
            node.col -= 2 if node.row % 2 == 1 else 1
            node.row += 1
            paint_coin_hinder(node, '$')
        if node.col == SPAWN_MIDDLE:
            clear_coin_hinder(node, '$')
            node.row += 1
            paint_coin_hinder(node, '$')
        if node.col >= SPAWN_RIGHT:
            clear_coin_hinder(node, '$')
            node.col += 2 if node.row % 2 == 1 else 1
            node.row += 1
            paint_coin_hinder(node, '$')


def coin_eat() -> bool:
    for node in coins:
        if (node.row == 15
                and head_col - 2 <= node.col <= head_col + 2
                and move_state not in (JUMP, GLIDE)):
            node.eaten = 1
            return True
    return False


def coin_clear() -> None:
    global score, coin_nums
    idx = -1
    for i, node in enumerate(coins):
        if node.eaten == 1:
            idx = i
            break
    if idx < 0:
        return
    node = coins.pop(idx)
    clear_coin_hinder(node, '$')

    if prop_state == DOUBLE_COIN:
        score += score_add
        coin_nums += 1
    score += score_add
    coin_nums += 1


def hinder_happen() -> None:
    global speed_hinder_happen
    possible = []
    if map_grid[1][SPAWN_LEFT] == ' ':
        possible.append(SPAWN_LEFT)
    if map_grid[1][SPAWN_MIDDLE] == ' ' and len(possible) <= 1:
        possible.append(SPAWN_MIDDLE)
    if map_grid[1][SPAWN_RIGHT] == ' ' and len(possible) <= 1:
        possible.append(SPAWN_RIGHT)

    if len(possible) == 0:
        speed_hinder_happen = HINDER_PERIOD * speed_limit
        return

    r2 = int(abs(3.15 * math.sin(score)))
    if len(possible) == 1:
        col = possible[0]
    else:
        r1 = int(abs(1.414 * math.sin(score)))
        col = possible[r1]

    node = Node(row=1, col=col, hinder_type=HINDER_CHARS[r2])
    hinders.append(node)
    paint_coin_hinder(node, node.hinder_type)


def hinder_move() -> None:
    for node in hinders:
        if node.col <= SPAWN_LEFT:
            clear_coin_hinder(node, node.hinder_type)
            clear_hinder_perspective(node)
            node.col -= 2 if node.row % 2 == 1 else 1
            node.row += 1
            paint_coin_hinder(node, node.hinder_type)
            paint_hinder_perspective(node, node.hinder_type)
        if node.col == SPAWN_MIDDLE:
            clear_coin_hinder(node, node.hinder_type)
            clear_hinder_perspective(node)
            node.row += 1
            paint_coin_hinder(node, node.hinder_type)
            paint_hinder_perspective(node, node.hinder_type)
        if node.col >= SPAWN_RIGHT:
            clear_coin_hinder(node, node.hinder_type)
            clear_hinder_perspective(node)
            node.col += 2 if node.row % 2 == 1 else 1
            node.row += 1
            paint_coin_hinder(node, node.hinder_type)
            paint_hinder_perspective(node, node.hinder_type)


def if_hinder_clash() -> None:
    global lose, score
    cur = None
    for node in hinders:
        if node.row == 15:
            cur = node
            break
    if cur is None:
        return
    if not (head_col - 2 <= cur.col <= head_col + 2):
        return

    ht = cur.hinder_type
    if ht == '_':
        if move_state in (JUMP, GLIDE):
            return
        lose = True
    elif ht == '^':
        if move_state == DOWN or (move_state == JUMP and prop_state == SUPER_JUMP):
            return
        lose = True
    elif ht == 'x':
        if move_state == JUMP and prop_state == SUPER_JUMP:
            return
        lose = True
    elif ht == '#':
        if move_state == GLIDE or (move_state == JUMP and prop_state == SUPER_JUMP):
            return
        lose = True

    if prop_state == INVINCIBLE:
        lose = False
        score += 3
        clear_hinder_perspective(cur)
        return


def prop_happen() -> None:
    global speed_prop_happen
    possible = []
    if map_grid[1][SPAWN_LEFT] == ' ':
        possible.append(SPAWN_LEFT)
    if map_grid[1][SPAWN_MIDDLE] == ' ' and len(possible) <= 1:
        possible.append(SPAWN_MIDDLE)
    if map_grid[1][SPAWN_RIGHT] == ' ' and len(possible) <= 1:
        possible.append(SPAWN_RIGHT)

    if len(possible) == 0:
        speed_prop_happen = PROP_PERIOD * speed_limit
        return

    r2 = int(abs(5.23 * math.sin(score)))
    if len(possible) == 1:
        col = possible[0]
    else:
        r1 = int(abs(1.414 * math.sin(score)))
        col = possible[r1]

    node = Node(row=1, col=col, prop_type=PROP_TYPES[r2])
    props.append(node)
    paint_prop(node, node.prop_type)


def prop_move() -> None:
    for node in props:
        if node.col <= SPAWN_LEFT:
            clear_prop(node)
            node.col -= 2 if node.row % 2 == 1 else 1
            node.row += 1
            paint_prop(node, node.prop_type)
        if node.col == SPAWN_MIDDLE:
            clear_prop(node)
            node.row += 1
            paint_prop(node, node.prop_type)
        if node.col >= SPAWN_RIGHT:
            clear_prop(node)
            node.col += 2 if node.row % 2 == 1 else 1
            node.row += 1
            paint_prop(node, node.prop_type)


def prop_eat() -> bool:
    for node in props:
        if (node.row == 15
                and head_col - 2 <= node.col <= head_col + 2
                and move_state not in (JUMP, GLIDE)):
            clear_screen()
            node.eaten = 1
            return True
    return False


def prop_clear() -> None:
    global prop_state
    if not props:
        return
    node = props.pop(0)
    clear_prop(node)
    prop_state = node.prop_type


def start_up() -> None:
    print('-' * COL)
    for _ in range(5):
        print('|' + ' ' * (COL - 2) + '|')
    print('|' + ' ' * 28 + 'Welcome to Metro Running' + ' ' * 28 + '|')
    print('|' + ' ' * 29 + "Press 'Enter' to start" + ' ' * 29 + '|')
    for _ in range(8):
        print('|' + ' ' * (COL - 2) + '|')
    print('-' * COL)
    hide_cursor()

    while True:
        if getch() in ('\r', '\n'):
            break
    clear_screen()


def initial() -> None:
    global score, coin_nums, score_add, head_col, head_row, run_flag
    global speed, speed_limit
    global move_state, move_state_time, move_state_time_limit
    global prop_state, prop_state_time, prop_state_time_limit
    global speed_hinder_happen, speed_prop_happen, lose, replay

    for i in range(ROW):
        for j in range(COL):
            map_grid[i][j] = ' '
    for i in range(ROW):
        map_grid[i][0] = '|'
        map_grid[i][COL - 1] = '|'
    for j in range(COL):
        map_grid[0][j] = '-'
        map_grid[ROW - 1][j] = '-'

    col1, col2 = 4, 77
    for row in range(15, 0, -1):
        map_grid[row][col1] = '/'
        map_grid[row][col2] = '\\'
        col1 += 2
        col2 -= 2

    col1, col2 = 24, 57
    for row in range(15, 0, -1):
        map_grid[row][col1] = '/'
        map_grid[row][col1 + 1] = '/'
        map_grid[row][col2] = '\\'
        map_grid[row][col2 - 1] = '\\'
        col1 += 1
        col2 -= 1

    score = 0
    coin_nums = 0
    score_add = 3
    head_col = MIDDLE_COL
    head_row = 13
    print_small_guy()
    run_flag = 0
    speed_limit = 5
    speed = 1
    move_state = RUNNING
    move_state_time = 1
    move_state_time_limit = 24
    prop_state = NONE
    prop_state_time = 1
    prop_state_time_limit = 150
    speed_hinder_happen = 1
    speed_prop_happen = 1
    lose = False
    replay = False

    coins.clear()
    hinders.clear()
    props.clear()


def show() -> None:
    out = [f"Score:{score:4d}         Coin:{coin_nums:4d}\n"]
    out.append('\n'.join(''.join(r) for r in map_grid))
    out.append('\n')
    sys.stdout.write('\x1b[H' + ''.join(out))
    sys.stdout.flush()


def update_with_input() -> None:
    global head_col, move_state, move_state_time

    if not kbhit():
        return
    ch = getch()

    if ch == 'a':
        if head_col == MIDDLE_COL:
            clear_small_guy()
            head_col = LEFT_COL
        elif head_col == RIGHT_COL:
            clear_small_guy()
            head_col = MIDDLE_COL
    elif ch == 'd':
        if head_col == MIDDLE_COL:
            clear_small_guy()
            head_col = RIGHT_COL
        elif head_col == LEFT_COL:
            clear_small_guy()
            head_col = MIDDLE_COL
    elif ch == 'w' and ((move_state not in (JUMP, GLIDE)) or prop_state == FLYING):
        move_state = JUMP
        move_state_time = 1
    elif ch == 's':
        if move_state == JUMP:
            move_state = GLIDE
        else:
            move_state = DOWN
        move_state_time = 1

    if ch == ' ':
        sys.stdout.write('\x1b[2;1HPress space to continue')
        sys.stdout.flush()
        while getch() != ' ':
            pass
        clear_screen()


def update_without_input() -> None:
    global speed, score, speed_hinder_happen, speed_prop_happen

    if speed >= speed_limit:
        coin_move()
        coin_happen()
        prop_move()
        hinder_move()
        bottom_clear(hinders)

    if speed_hinder_happen < HINDER_PERIOD * speed_limit:
        speed_hinder_happen += 1
    else:
        speed_hinder_happen = 1
        hinder_happen()

    if speed_prop_happen < PROP_PERIOD * speed_limit:
        speed_prop_happen += 1
    else:
        speed_prop_happen = 1
        prop_happen()

    move_state_time_countdown()
    if prop_state != NONE:
        prop_state_time_countdown()

    if_hinder_clash()
    if coin_eat():
        coin_clear()
    else:
        bottom_clear(coins)
    if prop_eat():
        prop_clear()
    else:
        bottom_clear(props)

    if speed < speed_limit:
        speed += 1
    else:
        speed = 1
        score += 1
        if prop_state == DOUBLE_SCORE:
            score += 1

        if move_state == RUNNING:
            speed_run()
        elif move_state == JUMP:
            print_jump()
        elif move_state == DOWN:
            print_squat()
        elif move_state == GLIDE:
            paint_gliding()


def end() -> None:
    global replay
    coins.clear()
    hinders.clear()
    props.clear()

    sys.stdout.write('\x1b[H')
    print('LOSE')
    print("If you want to try again, press 'y'")
    print("Else, press 'n' to exit")

    while True:
        c = getch()
        if c == 'y':
            replay = True
            clear_screen()
            return
        elif c == 'n':
            replay = False
            return


def main() -> None:
    hide_cursor()
    try:
        while replay:
            start_up()
            initial()
            while True:
                show()
                update_with_input()
                update_without_input()
                if lose:
                    break
                time.sleep(FRAME_DELAY)
            end()
    finally:
        show_cursor()
        clear_screen()


if __name__ == '__main__':
    main()
    