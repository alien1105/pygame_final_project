import pygame
import sys

# 1. 遊戲初始化
pygame.init()

# 2. 設定視窗大小與標題
WIDTH, HEIGHT = 800, 400
WORLD_WIDTH = 2000 # 設定一個比螢幕寬的遊戲世界
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

def draw_background(camera_offset_x):
    """繪製背景、地板和窗戶，根據攝影機位置調整"""
    # 畫背景 (車廂內部牆壁)
    screen.fill(GRAY)
    
    # 畫車廂地板
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, HEIGHT - FLOOR_HEIGHT, WORLD_WIDTH, FLOOR_HEIGHT))
    
    # 畫上方的行李架
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, 60, WORLD_WIDTH, 15))

    # 使用迴圈畫出所有座椅
    # 產生 10 個座椅，間隔 140
    chair_positions = [140 + i * 140 for i in range(10)]
    for pos in chair_positions:
        draw_side_chair(pos, camera_offset_x)

    # 畫幾個車窗作為背景裝飾 (現在也需要考慮攝影機位置)
    window_1_rect = pygame.Rect(100 - camera_offset_x, 100, 150, 100)
    pygame.draw.rect(screen, WHITE, window_1_rect)
    pygame.draw.rect(screen, BLACK, window_1_rect, 3) # 窗框
    
    window_2_rect = pygame.Rect(550 - camera_offset_x, 100, 150, 100)
    pygame.draw.rect(screen, WHITE, window_2_rect)
    pygame.draw.rect(screen, BLACK, window_2_rect, 3) # 窗框

    # 增加更多窗戶來填滿更寬的世界
    window_3_rect = pygame.Rect(1200 - camera_offset_x, 100, 150, 100)
    pygame.draw.rect(screen, WHITE, window_3_rect)
    pygame.draw.rect(screen, BLACK, window_3_rect, 3) # 窗框

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
    # --- A. 偵測事件 (關閉視窗、按鍵等) ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False # 結束迴圈

    # --- B. 遊戲邏輯與角色移動 ---
    keys = pygame.key.get_pressed()
    
    # 偵測左右方向鍵
    if keys[pygame.K_LEFT]:
        conductor_rect.x -= PLAYER_SPEED
    if keys[pygame.K_RIGHT]:
        conductor_rect.x += PLAYER_SPEED

    # 世界邊界限制 (不讓列車長走出我們設定的世界)
    if conductor_rect.left < 0:
        conductor_rect.left = 0
    if conductor_rect.right > WORLD_WIDTH:
        conductor_rect.right = WORLD_WIDTH

    # 更新攝影機位置，使其跟隨玩家，讓玩家保持在畫面中央
    camera_x = conductor_rect.centerx - (WIDTH // 2)

    # 限制攝影機的移動範圍，避免在世界邊緣看到空白區域
    if camera_x < 0:
        camera_x = 0
    if camera_x > WORLD_WIDTH - WIDTH:
        camera_x = WORLD_WIDTH - WIDTH

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