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
    WIDTH // 2 - 80, 
    HEIGHT - FLOOR_HEIGHT - 160, 
    160, 
    160
)
# 控制遊戲更新頻率的時鐘
clock = pygame.time.Clock()

# 攝影機的 X 軸位置
camera_x = 0

# --- 場景管理 ---
current_scene = 'CARRIAGE_1' # 初始場景

# 定義每個場景的互動門
DOOR_HEIGHT = 200
DOOR_WIDTH = 80
doors = {
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

def draw_conductor(surface, rect, image, camera_offset_x):
    """繪製列車長"""
    # 根據攝影機位置計算角色在螢幕上的位置
    screen_rect = rect.copy()
    screen_rect.x -= camera_offset_x
    if image: # 如果圖片成功載入
        surface.blit(image, screen_rect)
    else: # 否則，畫一個藍色方塊作為替代
        pygame.draw.rect(surface, BLUE, screen_rect)

# 4. 遊戲主迴圈
running = True
while running:
    # --- A. 事件偵測 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False # 結束迴圈
        
        # 偵測 'F' 鍵按下事件
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                # 在第一個車廂，準備進入連接處
                if current_scene == 'CARRIAGE_1':
                    # 檢查是否在右邊的門 (去連接處)
                    if conductor_rect.colliderect(doors['CARRIAGE_1']['exit_door']):
                        current_scene = 'CONNECTION'
                        # 將玩家位置重設到連接處的入口
                        conductor_rect.x = doors['CONNECTION']['entry_door_1'].right + 10
                        camera_x = 0 # 重設攝影機
                    # 檢查是否在左邊的門 (去駕駛艙)
                    elif conductor_rect.colliderect(doors['CARRIAGE_1']['cockpit_door']):
                        current_scene = 'COCKPIT'
                        conductor_rect.x = doors['COCKPIT']['exit_door'].left - conductor_rect.width - 10
                        camera_x = 0 # 重設攝影機
                
                # 在連接處，準備回到第一個車廂
                elif current_scene == 'CONNECTION':
                    # 檢查是否在左邊的門 (回車廂1)
                    if conductor_rect.colliderect(doors['CONNECTION']['entry_door_1']):
                        current_scene = 'CARRIAGE_1'
                        # 將玩家位置重設到車廂的門口
                        conductor_rect.x = doors['CARRIAGE_1']['exit_door'].left - conductor_rect.width - 10
                        # 攝影機跟隨
                        camera_x = conductor_rect.centerx - (WIDTH // 2)
                    # 檢查是否在右邊的門 (去車廂2)
                    elif conductor_rect.colliderect(doors['CONNECTION']['exit_door_2']):
                        current_scene = 'CARRIAGE_2'
                        # 將玩家位置重設到車廂2的入口
                        conductor_rect.x = doors['CARRIAGE_2']['entry_door'].right + 10
                        camera_x = 0 # 重設攝影機
                
                # 在第二個車廂，準備回到連接處
                elif current_scene == 'CARRIAGE_2':
                    if conductor_rect.colliderect(doors['CARRIAGE_2']['entry_door']):
                        current_scene = 'CONNECTION'
                        conductor_rect.x = doors['CONNECTION']['exit_door_2'].left - conductor_rect.width - 10
                
                # 在駕駛艙，準備回到第一個車廂
                elif current_scene == 'COCKPIT':
                    if conductor_rect.colliderect(doors['COCKPIT']['exit_door']):
                        current_scene = 'CARRIAGE_1'
                        conductor_rect.x = doors['CARRIAGE_1']['cockpit_door'].right + 10

    # --- B. 遊戲邏輯 ---
    # 根據當前場景設定世界邊界
    if 'CARRIAGE' in current_scene:
        current_world_width = CARRIAGE_WIDTH
    elif current_scene == 'CONNECTION':
        current_world_width = CONNECTION_WIDTH
    else: # COCKPIT
        current_world_width = COCKPIT_WIDTH

    keys = pygame.key.get_pressed()
    
    # 記錄移動前的位置，用於碰撞後的位置修正
    prev_x = conductor_rect.x

    # 偵測左右方向鍵
    if keys[pygame.K_LEFT]:
        conductor_rect.x -= PLAYER_SPEED
    if keys[pygame.K_RIGHT]:
        conductor_rect.x += PLAYER_SPEED

    # 當前場景的世界邊界限制
    if conductor_rect.left < 0:
        conductor_rect.left = 0
    if conductor_rect.right > current_world_width:
        conductor_rect.right = current_world_width

    # 更新攝影機位置，使其跟隨玩家，讓玩家保持在畫面中央
    camera_x = conductor_rect.centerx - (WIDTH // 2)

    # 限制攝影機的移動範圍，避免在世界邊緣看到空白區域
    if camera_x < 0:
        camera_x = 0
    if camera_x > current_world_width - WIDTH:
        camera_x = current_world_width - WIDTH

    # --- C. 畫面繪製 ---
    draw_background(camera_x)
   
    # 繪製列車長
    draw_conductor(screen, conductor_rect, conductor_img, camera_x)

    # --- D. 更新畫面 ---
    pygame.display.flip()
    
    # 設定遊戲幀率 (Frame Rate) 為 60 FPS
    clock.tick(FPS)

# 離開遊戲
pygame.quit()
sys.exit() # 確保程式完全退出