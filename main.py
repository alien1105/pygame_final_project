import pygame
import sys

# 1. 遊戲初始化
pygame.init()

# 2. 設定視窗大小與標題
WIDTH, HEIGHT = 800, 400 # 螢幕大小
CARRIAGE_WIDTH = 1600 # 車廂場景的寬度
COCKPIT_WIDTH = 500 # 駕駛艙場景的寬度
CONNECTION_WIDTH = 400 # 連接處場景的寬度
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("列車長模擬器")

# 遊戲常數
FLOOR_HEIGHT = 50
FPS = 60
PLAYER_SPEED = 5
DOOR_HEIGHT = 200
DOOR_WIDTH = 80

# 定義顏色 (RGB 格式)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
DARK_GRAY = (100, 100, 100)
BLUE = (50, 50, 255)  # 列車長用藍色方塊代表
BLACK = (0, 0, 0)
BROWN = (139, 69, 19) # 座椅顏色
DARK_BROWN = (101, 67, 33) # 座椅暗面顏色
RED = (255, 0, 0) # 按鈕顏色
GREEN = (0, 255, 0) # 按鈕顏色
PURPLE = (150, 100, 150) # 老太太用紫色方塊代表
PINK = (230, 160, 190) # 小女孩用粉色方塊代表
GOLD = (218, 165, 32) # 可拾取道具標記顏色

# 載入字型 (使用電腦內建的中文字型)
font = pygame.font.SysFont("microsoftjhenghei", 28)
font_small = pygame.font.SysFont("microsoftjhenghei", 20)

# 3. 載入並設定列車長
try:
    # 載入圖片，convert_alpha() 會轉換圖片格式以優化繪製速度並處理透明度
    conductor_img_original = pygame.image.load('main_character.png').convert_alpha()
    # 調整圖片大小以符合我們的角色尺寸 (160x160)
    conductor_img = pygame.transform.scale(conductor_img_original, (160, 160))
except pygame.error as e:
    print(f"無法載入圖片 'main_character.png': {e}")
    print("請確認 'main_character.png' 檔案與 main.py 在同一個資料夾中。")
    print("將使用藍色方塊作為替代。")
    conductor_img = None # 如果圖片載入失敗，設定為 None

# 設定列車長的碰撞框 (Rect)
conductor_rect = pygame.Rect(
    COCKPIT_WIDTH - DOOR_WIDTH - 160 - 10, # 初始 x 位置：駕駛艙門的左邊再過去一點
    HEIGHT - FLOOR_HEIGHT - 160, 
    160, 
    160
)
# 控制遊戲更新頻率的時鐘
clock = pygame.time.Clock()

# 攝影機的 X 軸位置
camera_x = 0

# --- 場景管理 ---
current_scene = 'COCKPIT' # 遊戲從駕駛艙開始

# --- 遊戲狀態管理 ---
game_state = 'MANUAL' # 初始狀態為顯示手冊
close_button_rect = pygame.Rect(WIDTH - 50, 50, 30, 30) # 手冊的關閉按鈕

doors = { # 定義每個場景的互動門
    'CARRIAGE_1': {
        'cockpit_door': pygame.Rect(0, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_WIDTH, DOOR_HEIGHT),
        'exit_door': pygame.Rect(CARRIAGE_WIDTH - DOOR_WIDTH, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_WIDTH, DOOR_HEIGHT),
    },
    'CONNECTION': {
        'entry_door_1': pygame.Rect(0, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_WIDTH, DOOR_HEIGHT),
        'exit_door_2': pygame.Rect(CONNECTION_WIDTH - DOOR_WIDTH, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_WIDTH, DOOR_HEIGHT),
    },
    'CARRIAGE_2': {
        'entry_door': pygame.Rect(0, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_WIDTH, DOOR_HEIGHT),
    }
    ,
    'COCKPIT': {
        'exit_door': pygame.Rect(COCKPIT_WIDTH - DOOR_WIDTH, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_WIDTH, DOOR_HEIGHT),
    }
}

# --- 老太太 NPC ---
OLD_LADY_SCENE = 'CARRIAGE_1'
old_lady_rect = pygame.Rect(410, HEIGHT - FLOOR_HEIGHT - 90, 60, 90) # 坐在車廂一的座位上

# 老太太第一天的對話劇情，格式為 (說話者, 台詞)
old_lady_dialogue = [
    ("老太太", "新人？"),
    ("主角", "是。"),
    ("老太太", "那你晚上可別回頭。"),
    ("主角", "回頭？"),
    ("老太太", "……"), # 她卻像沒說過這句話一樣
]

# --- 小女孩 NPC ---
GIRL_SCENE = 'CARRIAGE_2' # 她一個人坐在最後一節車廂
girl_rect = pygame.Rect(410, HEIGHT - FLOOR_HEIGHT - 80, 50, 80) # 坐在車廂二的座位上

# 小女孩第一天的對話劇情
girl_dialogue = [
    ("小女孩", "……"),
    ("主角", "你在畫什麼？"),
    ("小女孩", "火車。"),
    ("主角", "（她把畫轉向你，畫裡的火車旁畫了六個人。）"),
    ("主角", "這班車明明只有五個人……可以給我看看這張畫嗎？"),
    ("小女孩", "……嗯。"),
    (" ", "從小女孩手中拿到了「小女孩的畫」。"),
]

# 對話中不同說話者對應的文字顏色
SPEAKER_COLORS = {
    "老太太": RED,
    "小女孩": PINK,
    "主角": BLUE,
    "旁白": DARK_GRAY,
}

# --- 對話狀態管理 ---
dialogue_lines = []
dialogue_index = 0
active_npc = None # 記錄目前正在對話的 NPC，用於對話結束後觸發後續事件
has_girl_painting = False # 是否已從小女孩手中取得畫

# --- 第一天白天可收集道具 ---
inventory = [] # 玩家背包，存放已取得的道具名稱

# 每個道具點的位置定義：所在場景、可互動範圍、內含道具、是否已被拾取
item_spots = [
    {
        'scene': 'CARRIAGE_1',
        'rect': pygame.Rect(840, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 60, DOOR_HEIGHT), # 車廂座位上
        'items': ['舊車票'],
        'collected': False,
    },
    {
        'scene': 'CONNECTION',
        'rect': pygame.Rect(30, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 70, DOOR_HEIGHT), # 連接處牆壁上
        'items': ['舊路線圖'],
        'collected': False,
    },
]


def get_item_spot_at(scene, rect):
    """回傳玩家目前所在位置可拾取、且尚未拾取的道具點（沒有則回傳 None）"""
    for spot in item_spots:
        if not spot['collected'] and spot['scene'] == scene and rect.colliderect(spot['rect']):
            return spot
    return None


# --- 駕駛艙操作台細節（按 F 進入細節畫面，用滑鼠點擊個別拾取）---
CONSOLE_FOCUS_SCENE = 'COCKPIT'
console_cabinet_rect = pygame.Rect(30, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 100, DOOR_HEIGHT) # 操作台下置物櫃

console_panel_rect = pygame.Rect(WIDTH // 2 - 300, HEIGHT // 2 - 150, 600, 300)
_console_slot_size = 160
_console_slot_gap = 20
_console_slots_total_width = _console_slot_size * 3 + _console_slot_gap * 2
_console_slot_start_x = console_panel_rect.centerx - _console_slots_total_width // 2
_console_slot_y = console_panel_rect.y + 90

console_items = [
    {'name': '老式手電筒', 'color': (200, 200, 80), 'rect': pygame.Rect(_console_slot_start_x, _console_slot_y, _console_slot_size, _console_slot_size), 'collected': False},
    {'name': '車站鑰匙', 'color': (190, 190, 190), 'rect': pygame.Rect(_console_slot_start_x + (_console_slot_size + _console_slot_gap), _console_slot_y, _console_slot_size, _console_slot_size), 'collected': False},
    {'name': '維修員留下的螺絲起子', 'color': (150, 110, 70), 'rect': pygame.Rect(_console_slot_start_x + (_console_slot_size + _console_slot_gap) * 2, _console_slot_y, _console_slot_size, _console_slot_size), 'collected': False},
]


def console_has_items_left():
    """置物櫃裡是否還有尚未拾取的道具"""
    return any(not item['collected'] for item in console_items)

def draw_manual_screen():
    """繪製操作手冊畫面"""
    # 半透明背景
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # 手冊面板
    panel_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 150, 500, 300)
    pygame.draw.rect(screen, WHITE, panel_rect)
    pygame.draw.rect(screen, BLACK, panel_rect, 3)

    # 標題
    title_surf = font.render("操作手冊", True, BLACK)
    screen.blit(title_surf, (panel_rect.centerx - title_surf.get_width() // 2, panel_rect.y + 20))

    # 說明文字
    instructions = [
        "← → : 左右移動",
        "F : 與場景互動",
        "B : 開啟背包",
        "TAB : 關閉此手冊"
    ]
    for i, text in enumerate(instructions):
        text_surf = font_small.render(text, True, BLACK)
        screen.blit(text_surf, (panel_rect.x + 40, panel_rect.y + 80 + i * 40))

    # 關閉按鈕
    pygame.draw.rect(screen, RED, close_button_rect)
    close_text_surf = font.render("X", True, WHITE)
    screen.blit(close_text_surf, (close_button_rect.centerx - close_text_surf.get_width() // 2,
                                  close_button_rect.centery - close_text_surf.get_height() // 2))


def draw_manual_hint():
    """在右上角繪製提示：按 TAB 開關操作手冊"""
    hint_text_surf = font_small.render("TAB : 操作手冊", True, WHITE)
    hint_rect = hint_text_surf.get_rect()
    hint_bg_rect = pygame.Rect(0, 0, hint_rect.width + 20, hint_rect.height + 12)
    hint_bg_rect.topright = (WIDTH - 15, 15)
    hint_bg = pygame.Surface(hint_bg_rect.size, pygame.SRCALPHA)
    hint_bg.fill((0, 0, 0, 150))
    screen.blit(hint_bg, hint_bg_rect)
    screen.blit(hint_text_surf, (hint_bg_rect.centerx - hint_rect.width // 2, hint_bg_rect.centery - hint_rect.height // 2))


def draw_background(camera_offset_x):
    """繪製背景、地板和窗戶，根據攝影機位置調整"""
    # 畫背景 (車廂內部牆壁)
    screen.fill(GRAY)
    
    # 畫車廂地板
    # 根據當前場景決定地板寬度
    if 'CARRIAGE' in current_scene:
        scene_width = CARRIAGE_WIDTH
    elif current_scene == 'CONNECTION':
        scene_width = CONNECTION_WIDTH
    else: # COCKPIT
        scene_width = COCKPIT_WIDTH
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, HEIGHT - FLOOR_HEIGHT, scene_width, FLOOR_HEIGHT))
    
    # 畫上方的行李架
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, 60, scene_width, 15))

    # 根據當前場景繪製特定物件
    if 'CARRIAGE' in current_scene:
        draw_carriage_scene(camera_offset_x, current_scene)
    elif current_scene == 'CONNECTION':
        draw_connection_scene(camera_offset_x)
    elif current_scene == 'COCKPIT':
        draw_cockpit_scene(camera_offset_x)

def draw_carriage_scene(camera_offset_x, scene_name):
    """繪製指定車廂內的物件 (座椅、窗戶、門)"""
    # 畫座椅
    chair_positions = [140 + i * 140 for i in range(8)]
    for pos in chair_positions:
        draw_side_chair(pos, camera_offset_x)
    # 畫窗戶
    for i in range(3):
        win_rect = pygame.Rect(100 + i * 450 - camera_offset_x, 100, 150, 100)
        pygame.draw.rect(screen, WHITE, win_rect)
        pygame.draw.rect(screen, BLACK, win_rect, 3)
    # 根據是哪個車廂，畫對應的門
    if scene_name == 'CARRIAGE_1': # 車廂1有兩個門
        # 畫右邊通往連接處的門
        exit_door_rect = doors['CARRIAGE_1']['exit_door']
        exit_door_screen_rect = exit_door_rect.move(-camera_offset_x, 0)
        pygame.draw.rect(screen, DARK_BROWN, exit_door_screen_rect)
        pygame.draw.rect(screen, BLACK, exit_door_screen_rect, 4)
        # 畫左邊通往駕駛艙的門
        cockpit_door_rect = doors['CARRIAGE_1']['cockpit_door']
        cockpit_door_screen_rect = cockpit_door_rect.move(-camera_offset_x, 0)
        pygame.draw.rect(screen, DARK_BROWN, cockpit_door_screen_rect)
        pygame.draw.rect(screen, BLACK, cockpit_door_screen_rect, 4)
    else: # CARRIAGE_2 只有一個門
        entry_door_rect = doors['CARRIAGE_2']['entry_door']
        entry_door_screen_rect = entry_door_rect.move(-camera_offset_x, 0)
        pygame.draw.rect(screen, DARK_BROWN, entry_door_screen_rect)
        pygame.draw.rect(screen, BLACK, entry_door_screen_rect, 4)

def draw_cockpit_scene(camera_offset_x):
    """繪製駕駛艙內的物件"""
    # 畫一個大的駕駛窗
    cockpit_window_rect = pygame.Rect(20 - camera_offset_x, 80, 300, 150)
    pygame.draw.rect(screen, WHITE, cockpit_window_rect) # 窗戶玻璃
    pygame.draw.rect(screen, BLACK, cockpit_window_rect, 4) # 窗框

    # --- 畫側視的操作台 ---
    x_pos = 20
    # 操作台側面 (多邊形)
    console_side_points = [
        (x_pos - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 120), # 左上
        (x_pos + 300 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 80), # 右上 (斜面)
        (x_pos + 300 - camera_offset_x, HEIGHT - FLOOR_HEIGHT), # 右下
        (x_pos - camera_offset_x, HEIGHT - FLOOR_HEIGHT), # 左下
    ]
    pygame.draw.polygon(screen, GRAY, console_side_points)
    pygame.draw.polygon(screen, BLACK, console_side_points, 3)

    # 操作台正面 (深色矩形，製造立體感)
    pygame.draw.rect(screen, DARK_GRAY, (x_pos - 10 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 120, 10, 120))

    # 在斜面上畫按鈕
    pygame.draw.circle(screen, RED, (x_pos + 50 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 105), 10)
    pygame.draw.circle(screen, GREEN, (x_pos + 90 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 100), 10)

    # 畫駕駛艙的出口門
    exit_door_rect = doors['COCKPIT']['exit_door']
    exit_door_screen_rect = exit_door_rect.move(-camera_offset_x, 0)
    pygame.draw.rect(screen, DARK_BROWN, exit_door_screen_rect)
    pygame.draw.rect(screen, BLACK, exit_door_screen_rect, 4)

def draw_connection_scene(camera_offset_x):
    """繪製連接處的物件 (廁所、下車門、通道門)"""
    # 畫廁所門
    toilet_rect = pygame.Rect(150 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 180, 100, 180)
    pygame.draw.rect(screen, DARK_GRAY, toilet_rect)
    pygame.draw.rect(screen, BLACK, toilet_rect, 4)
    # 畫下車門
    exit_door_rect = pygame.Rect(CONNECTION_WIDTH / 2 - 60 - camera_offset_x, 80, 120, 250)
    pygame.draw.rect(screen, (50, 50, 80), exit_door_rect)
    pygame.draw.rect(screen, BLACK, exit_door_rect, 4)
    # 畫回到車廂1的門
    door1_rect = doors['CONNECTION']['entry_door_1']
    door1_screen_rect = door1_rect.move(-camera_offset_x, 0)
    pygame.draw.rect(screen, DARK_BROWN, door1_screen_rect)
    pygame.draw.rect(screen, BLACK, door1_screen_rect, 4)
    # 畫通往車廂2的門
    door2_rect = doors['CONNECTION']['exit_door_2']
    door2_screen_rect = door2_rect.move(-camera_offset_x, 0)
    pygame.draw.rect(screen, DARK_BROWN, door2_screen_rect)
    pygame.draw.rect(screen, BLACK, door2_screen_rect, 4)

def draw_side_chair(x_pos, camera_offset_x):
    """在指定 x 位置繪製一個側著的椅子"""
    seat_height = 40
    back_height = 80
    seat_depth = 60
    thickness = 15
    
    # 椅子側面 (較亮的 L 型)，所有 x 座標都要減去攝影機的偏移量
    side_points = [
        (x_pos - camera_offset_x, HEIGHT - FLOOR_HEIGHT - back_height), # 椅背頂部
        (x_pos - camera_offset_x, HEIGHT - FLOOR_HEIGHT), # 椅腳後方
        (x_pos + seat_depth - camera_offset_x, HEIGHT - FLOOR_HEIGHT), # 椅腳前方
        (x_pos + seat_depth - camera_offset_x, HEIGHT - FLOOR_HEIGHT - seat_height + thickness), # 座椅前端下方
        (x_pos + thickness - camera_offset_x, HEIGHT - FLOOR_HEIGHT - seat_height + thickness), # 座椅內側
        (x_pos + thickness - camera_offset_x, HEIGHT - FLOOR_HEIGHT - back_height), # 椅背內側
    ]
    pygame.draw.polygon(screen, BROWN, side_points)
    # 椅子正面 (較暗的矩形，製造立體感)
    pygame.draw.rect(screen, DARK_BROWN, (x_pos - 10 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - back_height, 10, back_height)) # 椅背正面
    pygame.draw.rect(screen, DARK_BROWN, (x_pos - 10 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - seat_height, seat_depth, seat_height)) # 座椅正面

def draw_old_lady(camera_offset_x):
    """繪製老太太 NPC（僅在車廂一場景顯示）"""
    if current_scene != OLD_LADY_SCENE:
        return
    screen_rect = old_lady_rect.move(-camera_offset_x, 0)
    pygame.draw.rect(screen, PURPLE, screen_rect)
    pygame.draw.circle(screen, PURPLE, (screen_rect.centerx, screen_rect.top - 15), 15) # 頭部


def draw_girl(camera_offset_x):
    """繪製小女孩 NPC（僅在車廂二場景顯示）"""
    if current_scene != GIRL_SCENE:
        return
    screen_rect = girl_rect.move(-camera_offset_x, 0)
    pygame.draw.rect(screen, PINK, screen_rect)
    pygame.draw.circle(screen, PINK, (screen_rect.centerx, screen_rect.top - 12), 12) # 頭部


def draw_inventory_screen():
    """繪製背包畫面，列出已拾取的道具"""
    # 半透明背景
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # 背包面板
    panel_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 150, 500, 300)
    pygame.draw.rect(screen, WHITE, panel_rect)
    pygame.draw.rect(screen, BLACK, panel_rect, 3)

    # 標題
    title_surf = font.render("背包", True, BLACK)
    screen.blit(title_surf, (panel_rect.centerx - title_surf.get_width() // 2, panel_rect.y + 20))

    if inventory:
        for i, item_name in enumerate(inventory):
            item_surf = font_small.render(f"・{item_name}", True, BLACK)
            screen.blit(item_surf, (panel_rect.x + 40, panel_rect.y + 70 + i * 32))
    else:
        empty_surf = font_small.render("目前沒有任何道具。", True, DARK_GRAY)
        screen.blit(empty_surf, (panel_rect.x + 40, panel_rect.y + 70))

    hint_surf = font_small.render("B : 關閉背包", True, DARK_GRAY)
    screen.blit(hint_surf, (panel_rect.right - hint_surf.get_width() - 20, panel_rect.bottom - hint_surf.get_height() - 15))


def draw_item_spots(camera_offset_x):
    """繪製目前場景中尚未拾取的道具標記"""
    for spot in item_spots:
        if spot['scene'] != current_scene or spot['collected']:
            continue
        marker_rect = pygame.Rect(0, 0, 26, 26)
        marker_rect.center = (spot['rect'].centerx - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 30)
        pygame.draw.rect(screen, GOLD, marker_rect)
        pygame.draw.rect(screen, BLACK, marker_rect, 2)

    if current_scene == CONSOLE_FOCUS_SCENE and console_has_items_left():
        marker_rect = pygame.Rect(0, 0, 26, 26)
        marker_rect.center = (console_cabinet_rect.centerx - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 30)
        pygame.draw.rect(screen, GOLD, marker_rect)
        pygame.draw.rect(screen, BLACK, marker_rect, 2)


def draw_console_focus():
    """繪製操作台置物櫃的細節畫面，可用滑鼠點擊個別拾取道具"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    pygame.draw.rect(screen, DARK_GRAY, console_panel_rect)
    pygame.draw.rect(screen, BLACK, console_panel_rect, 3)

    title_surf = font.render("置物櫃", True, WHITE)
    screen.blit(title_surf, (console_panel_rect.centerx - title_surf.get_width() // 2, console_panel_rect.y + 15))

    for item in console_items:
        slot_rect = item['rect']
        if item['collected']:
            pygame.draw.rect(screen, GRAY, slot_rect)
            pygame.draw.rect(screen, DARK_GRAY, slot_rect, 3)
            label = "(已拾取)"
        else:
            pygame.draw.rect(screen, item['color'], slot_rect)
            pygame.draw.rect(screen, BLACK, slot_rect, 3)
            label = item['name']

        label_surf = font_small.render(label, True, WHITE)
        screen.blit(label_surf, (slot_rect.centerx - label_surf.get_width() // 2, slot_rect.bottom + 10))

    hint_surf = font_small.render("點擊道具拾取・F : 離開細節畫面", True, WHITE)
    screen.blit(hint_surf, (console_panel_rect.centerx - hint_surf.get_width() // 2, console_panel_rect.bottom - 30))


def draw_inventory_hint():
    """在左上角顯示目前背包內的道具數量"""
    hint_text_surf = font_small.render(f"背包 : {len(inventory)}", True, WHITE)
    hint_rect = hint_text_surf.get_rect()
    hint_bg_rect = pygame.Rect(0, 0, hint_rect.width + 20, hint_rect.height + 12)
    hint_bg_rect.topleft = (15, 15)
    hint_bg = pygame.Surface(hint_bg_rect.size, pygame.SRCALPHA)
    hint_bg.fill((0, 0, 0, 150))
    screen.blit(hint_bg, hint_bg_rect)
    screen.blit(hint_text_surf, (hint_bg_rect.centerx - hint_rect.width // 2, hint_bg_rect.centery - hint_rect.height // 2))


def draw_dialogue_box():
    """繪製對話框，顯示目前這句台詞"""
    speaker, text = dialogue_lines[dialogue_index]

    box_rect = pygame.Rect(60, HEIGHT - 140, WIDTH - 120, 100)
    pygame.draw.rect(screen, WHITE, box_rect)
    pygame.draw.rect(screen, BLACK, box_rect, 3)

    name_surf = font_small.render(speaker, True, SPEAKER_COLORS.get(speaker, BLACK))
    screen.blit(name_surf, (box_rect.x + 20, box_rect.y + 12))

    text_surf = font.render(text, True, BLACK)
    screen.blit(text_surf, (box_rect.x + 20, box_rect.y + 45))

    hint_surf = font_small.render("F : 繼續", True, DARK_GRAY)
    screen.blit(hint_surf, (box_rect.right - hint_surf.get_width() - 15, box_rect.bottom - hint_surf.get_height() - 10))


def draw_conductor(surface, rect, image, camera_offset_x):
    """繪製列車長"""
    # 根據攝影機位置計算角色在螢幕上的位置
    screen_rect = rect.copy()
    screen_rect.x -= camera_offset_x
    if image: # 如果圖片成功載入
        surface.blit(image, screen_rect)
    else: # 否則，畫一個藍色方塊作為替代
        pygame.draw.rect(surface, BLUE, screen_rect)

def draw_interact_hint(camera_offset_x):
    """如果玩家靠近可互動的門或 NPC，在角色上方顯示按 F 互動的提示"""
    scene_doors = doors.get(current_scene, {})
    interactables = list(scene_doors.values())
    if current_scene == OLD_LADY_SCENE:
        interactables.append(old_lady_rect)
    if current_scene == GIRL_SCENE:
        interactables.append(girl_rect)
    for spot in item_spots:
        if spot['scene'] == current_scene and not spot['collected']:
            interactables.append(spot['rect'])
    if current_scene == CONSOLE_FOCUS_SCENE:
        interactables.append(console_cabinet_rect)

    for target_rect in interactables:
        if conductor_rect.colliderect(target_rect):
            hint_surf = font_small.render("F : 互動", True, WHITE)
            hint_bg = pygame.Surface((hint_surf.get_width() + 16, hint_surf.get_height() + 10), pygame.SRCALPHA)
            hint_bg.fill((0, 0, 0, 180))
            hint_bg.blit(hint_surf, (8, 5))
            screen_x = conductor_rect.centerx - camera_offset_x - hint_bg.get_width() // 2
            screen_y = conductor_rect.top - hint_bg.get_height() - 10
            screen.blit(hint_bg, (screen_x, screen_y))
            break

# 4. 遊戲主迴圈
running = True
while running:
    if game_state == 'MANUAL':
        # --- 手冊狀態的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN:
                if close_button_rect.collidepoint(event.pos):
                    game_state = 'PLAYING'
        
        # 繪製背景遊戲畫面
        draw_background(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        # 在上方繪製手冊
        draw_manual_screen()

    elif game_state == 'PLAYING':
        # --- 正常遊戲狀態的事件與邏輯 ---
        # A. 事件偵測
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    game_state = 'MANUAL'
                if event.key == pygame.K_b:
                    game_state = 'INVENTORY'
                if event.key == pygame.K_f and current_scene == OLD_LADY_SCENE and conductor_rect.colliderect(old_lady_rect):
                    # 與老太太互動，開始對話
                    dialogue_lines = old_lady_dialogue
                    dialogue_index = 0
                    active_npc = 'OLD_LADY'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and current_scene == GIRL_SCENE and conductor_rect.colliderect(girl_rect):
                    # 與小女孩互動，開始對話
                    dialogue_lines = girl_dialogue
                    dialogue_index = 0
                    active_npc = 'GIRL'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and get_item_spot_at(current_scene, conductor_rect) is not None:
                    # 撿拾道具
                    item_spot = get_item_spot_at(current_scene, conductor_rect)
                    inventory.extend(item_spot['items'])
                    item_spot['collected'] = True
                    dialogue_lines = [(" ", f"獲得了「{ '、'.join(item_spot['items']) }」。")]
                    dialogue_index = 0
                    active_npc = None
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and current_scene == CONSOLE_FOCUS_SCENE and conductor_rect.colliderect(console_cabinet_rect):
                    # 聚焦查看操作台置物櫃細節
                    game_state = 'CONSOLE_FOCUS'
                elif event.key == pygame.K_f:
                    # (場景切換邏輯...)
                    if current_scene == 'CARRIAGE_1':
                        if conductor_rect.colliderect(doors['CARRIAGE_1']['exit_door']):
                            current_scene = 'CONNECTION'
                            conductor_rect.x = doors['CONNECTION']['entry_door_1'].right + 10
                            camera_x = 0
                        elif conductor_rect.colliderect(doors['CARRIAGE_1']['cockpit_door']):
                            current_scene = 'COCKPIT'
                            conductor_rect.x = doors['COCKPIT']['exit_door'].left - conductor_rect.width - 10
                            camera_x = 0
                    elif current_scene == 'CONNECTION':
                        if conductor_rect.colliderect(doors['CONNECTION']['entry_door_1']):
                            current_scene = 'CARRIAGE_1'
                            conductor_rect.x = doors['CARRIAGE_1']['exit_door'].left - conductor_rect.width - 10
                            camera_x = conductor_rect.centerx - (WIDTH // 2)
                        elif conductor_rect.colliderect(doors['CONNECTION']['exit_door_2']):
                            current_scene = 'CARRIAGE_2'
                            conductor_rect.x = doors['CARRIAGE_2']['entry_door'].right + 10
                            camera_x = 0
                    elif current_scene == 'CARRIAGE_2':
                        if conductor_rect.colliderect(doors['CARRIAGE_2']['entry_door']):
                            current_scene = 'CONNECTION'
                            conductor_rect.x = doors['CONNECTION']['exit_door_2'].left - conductor_rect.width - 10
                    elif current_scene == 'COCKPIT':
                        if conductor_rect.colliderect(doors['COCKPIT']['exit_door']):
                            current_scene = 'CARRIAGE_1'
                            conductor_rect.x = doors['CARRIAGE_1']['cockpit_door'].right + 10

        # B. 遊戲邏輯
        if 'CARRIAGE' in current_scene:
            current_world_width = CARRIAGE_WIDTH
        elif current_scene == 'CONNECTION':
            current_world_width = CONNECTION_WIDTH
        else: # COCKPIT
            current_world_width = COCKPIT_WIDTH

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            conductor_rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            conductor_rect.x += PLAYER_SPEED

        if conductor_rect.left < 0:
            conductor_rect.left = 0
        if conductor_rect.right > current_world_width:
            conductor_rect.right = current_world_width

        camera_x = conductor_rect.centerx - (WIDTH // 2)
        if camera_x < 0:
            camera_x = 0
        if camera_x > current_world_width - WIDTH:
            camera_x = current_world_width - WIDTH

        # C. 畫面繪製
        draw_background(camera_x)
        draw_old_lady(camera_x)
        draw_girl(camera_x)
        draw_item_spots(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_interact_hint(camera_x)
        draw_manual_hint()
        draw_inventory_hint()

    elif game_state == 'DIALOGUE':
        # --- 對話狀態的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_SPACE:
                    dialogue_index += 1
                    if dialogue_index >= len(dialogue_lines):
                        if active_npc == 'GIRL':
                            has_girl_painting = True
                            inventory.append('小女孩的畫')
                        active_npc = None
                        game_state = 'PLAYING'

        draw_background(camera_x)
        draw_old_lady(camera_x)
        draw_girl(camera_x)
        draw_item_spots(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        if game_state == 'DIALOGUE':
            draw_dialogue_box()
        draw_inventory_hint()

    elif game_state == 'INVENTORY':
        # --- 背包狀態的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_b or event.key == pygame.K_TAB:
                    game_state = 'PLAYING'

        draw_background(camera_x)
        draw_old_lady(camera_x)
        draw_girl(camera_x)
        draw_item_spots(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_inventory_screen()

    elif game_state == 'CONSOLE_FOCUS':
        # --- 操作台置物櫃細節畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for item in console_items:
                    if not item['collected'] and item['rect'].collidepoint(event.pos):
                        inventory.append(item['name'])
                        item['collected'] = True
                        break

        draw_background(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_console_focus()
        draw_inventory_hint()

    # --- D. 更新畫面 ---
    pygame.display.flip()
    
    # 設定遊戲幀率 (Frame Rate) 為 60 FPS
    clock.tick(FPS)

# 離開遊戲
pygame.quit()
sys.exit() # 確保程式完全退出