import pygame
import sys
import os

# 1. 遊戲初始化
pygame.init()


def asset_path(filename):
    """圖片、圖檔等素材都放在 pictures 資料夾裡，統一組出正確路徑"""
    return os.path.join('pictures', filename)

# 2. 設定視窗大小與標題
WIDTH, HEIGHT = 800, 400 # 遊戲畫面的邏輯解析度（所有繪圖座標都以這個尺寸為準）
CARRIAGE_WIDTH = 1600 # 車廂場景的寬度
COCKPIT_WIDTH = 500 # 駕駛艙場景的寬度
CONNECTION_WIDTH = 400 # 連接處場景的寬度

# 實際的全螢幕視窗（使用螢幕原生解析度），遊戲畫面另外畫在 screen 這張邏輯畫布上，
# 每一幀再用平滑縮放（而不是預設的最近鄰縮放）放大貼滿整個螢幕，畫質會清晰很多。
# 直接拉伸填滿螢幕（不維持長寬比例），螢幕比例跟遊戲畫面不同時，畫面會有一點點被拉寬/拉高，
# 但沒有黑邊、所有內容跟 UI 都看得到。
display_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("軌遇")
screen = pygame.Surface((WIDTH, HEIGHT))

RENDER_SIZE = display_surface.get_size()
RENDER_OFFSET = (0, 0)


def to_logical_pos(pos):
    """把滑鼠在實際全螢幕視窗上的座標，換算成遊戲邏輯畫面 (WIDTH x HEIGHT) 的座標，
    這樣按鈕的 collidepoint() 判斷才會準確"""
    x, y = pos
    logical_x = (x - RENDER_OFFSET[0]) * WIDTH / RENDER_SIZE[0]
    logical_y = (y - RENDER_OFFSET[1]) * HEIGHT / RENDER_SIZE[1]
    return (logical_x, logical_y)


def feather_alpha_edges(arr, radius=1.5):
    """把去背後的 RGBA numpy 陣列邊緣做羽化模糊（例如人物、椅子去背後太銳利的鋸齒邊緣）。
    採用 premultiplied alpha 的方式模糊 RGB，再除回去，避免邊緣出現原本背景顏色的鑲邊。"""
    import numpy as np
    from scipy.ndimage import gaussian_filter

    arr = arr.astype(np.float32)
    alpha = arr[:, :, 3]
    premult = arr[:, :, :3] * (alpha[:, :, None] / 255.0)
    blurred_alpha = gaussian_filter(alpha, sigma=radius)
    blurred_premult = np.dstack([gaussian_filter(premult[:, :, c], sigma=radius) for c in range(3)])
    safe_alpha = np.maximum(blurred_alpha, 1.0)
    new_rgb = np.clip(blurred_premult / (safe_alpha[:, :, None] / 255.0), 0, 255)
    out = np.dstack([new_rgb, np.clip(blurred_alpha, 0, 255)])
    return out.astype(np.uint8)

# 遊戲常數
FLOOR_HEIGHT = 50
FPS = 60
PLAYER_SPEED = 5
DOOR_HEIGHT = 200
DOOR_WIDTH = 10 # 門的視覺／版面配置寬度（用來預留椅子、主角出生位置等的安全距離）
DOOR_HITBOX_WIDTH = 1 # 門的實際互動碰撞箱寬度（按 F 互動判定用，跟版面配置寬度分開）
CONDUCTOR_SIZE = 240 # 主角的寬高（原本 160 的 1.5 倍）
CONDUCTOR_Y_OFFSET = 20 # 主角往下移動的距離

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
TAPE_COLOR = (222, 184, 135) # 封住暗格的膠帶顏色
NIGHT_OVERLAY_COLOR = (10, 10, 40, 140) # 夜晚時疊加的半透明深藍色

# 載入字型（全部統一改用 ThePeakFontBeta_V0_102.ttf 這套字型）
try:
    font = pygame.font.Font('ThePeakFontBeta_V0_102.ttf', 28)
    font_small = pygame.font.Font('ThePeakFontBeta_V0_102.ttf', 20)
    font_title = pygame.font.Font('ThePeakFontBeta_V0_102.ttf', 64)
except (pygame.error, FileNotFoundError) as e:
    print(f"無法載入字型 'ThePeakFontBeta_V0_102.ttf': {e}")
    print("將改用電腦內建的中文字型作為替代。")
    font = pygame.font.SysFont("microsoftjhenghei", 28)
    font_small = pygame.font.SysFont("microsoftjhenghei", 20)
    font_title = pygame.font.SysFont("microsoftjhenghei", 64)

# 手寫風格字型，專門給操作手冊／生存指南畫面使用，其他地方仍用上面的一般字型
try:
    font_handwriting = pygame.font.Font('ThePeakFontBeta_V0_102.ttf', 28)
    font_handwriting_small = pygame.font.Font('ThePeakFontBeta_V0_102.ttf', 17)
except (pygame.error, FileNotFoundError) as e:
    print(f"無法載入字型 'ThePeakFontBeta_V0_102.ttf': {e}")
    print("操作手冊／生存指南將改用一般字型作為替代。")
    font_handwriting = font
    font_handwriting_small = font_small

# 對話框也改用同一套手寫字型，字級比手冊小一點，跟縮小後的對話框搭配
try:
    font_dialogue = pygame.font.Font('ThePeakFontBeta_V0_102.ttf', 20)
    font_dialogue_small = pygame.font.Font('ThePeakFontBeta_V0_102.ttf', 15)
except (pygame.error, FileNotFoundError) as e:
    print(f"無法載入字型 'ThePeakFontBeta_V0_102.ttf': {e}")
    print("對話框將改用一般字型作為替代。")
    font_dialogue = font
    font_dialogue_small = font_small

# 3. 載入並設定列車長（走路動畫）
CONDUCTOR_WALK_CROP = (713, 74, 1261, 1054) # main_character_walk2.gif 裡角色的裁切範圍 (left, top, right, bottom)，貼齊腳底，避免角色浮空
conductor_walk_frames = []    # 走路動畫的每一張畫格 (pygame Surface)
conductor_walk_durations = [] # 每一張畫格要停留的毫秒數
conductor_img = None          # 靜止不動時顯示的畫面（走路動畫的第一格，或備用的靜態圖片）
CONDUCTOR_VISIBLE_PAD = 0     # conductor_rect（畫布）左右兩側的透明留白寬度，移動邊界判定要扣掉這個，不然會有一大段「空氣牆」
try:
    from PIL import Image
    import numpy as np
    from scipy import ndimage

    gif = Image.open(asset_path('main_character_walk2.gif'))
    crop_w = CONDUCTOR_WALK_CROP[2] - CONDUCTOR_WALK_CROP[0]
    crop_h = CONDUCTOR_WALK_CROP[3] - CONDUCTOR_WALK_CROP[1]
    scaled_h = CONDUCTOR_SIZE
    scaled_w = max(1, round(scaled_h * crop_w / crop_h)) # 維持長寬比例，避免角色被拉扁
    CONDUCTOR_VISIBLE_PAD = (CONDUCTOR_SIZE - scaled_w) // 2
    for i in range(gif.n_frames):
        gif.seek(i)
        frame_rgba = gif.convert('RGBA').crop(CONDUCTOR_WALK_CROP)
        arr = np.array(frame_rgba)
        # GIF 背景是不透明的淺灰色攝影棚背景，沒有真正的透明資訊。
        # 先用「明亮且低飽和度」找出背景像素，再只保留夠大的連通區域（濾掉角色身上零星的亮點雜訊），
        # 最後把乾淨的背景範圍向外擴張兩圈，吃掉邊緣殘留的淺色鑲邊，讓輪廓更乾淨。
        maxc = arr[:, :, :3].max(axis=2).astype(np.int16)
        minc = arr[:, :, :3].min(axis=2).astype(np.int16)
        brightness = arr[:, :, :3].mean(axis=2)
        saturation = maxc - minc
        background = (brightness > 100) & (saturation < 50)
        labeled, num_components = ndimage.label(background)
        if num_components > 0:
            sizes = ndimage.sum(background, labeled, range(1, num_components + 1))
            large_components = [idx + 1 for idx, size in enumerate(sizes) if size > 20]
            background = np.isin(labeled, large_components)
            background = ndimage.binary_dilation(background, iterations=2)
        arr[background, 3] = 0
        arr = feather_alpha_edges(arr, radius=1.5) # 讓去背邊緣柔和一點，不要太銳利
        frame_surf = pygame.image.frombuffer(arr.tobytes(), (arr.shape[1], arr.shape[0]), 'RGBA').convert_alpha()
        frame_surf = pygame.transform.smoothscale(frame_surf, (scaled_w, scaled_h))
        # 貼到透明畫布中央，維持角色尺寸一致
        canvas = pygame.Surface((CONDUCTOR_SIZE, CONDUCTOR_SIZE), pygame.SRCALPHA)
        canvas.blit(frame_surf, ((CONDUCTOR_SIZE - scaled_w) // 2, 0))
        conductor_walk_frames.append(canvas)
        conductor_walk_durations.append(gif.info.get('duration', 80))
    conductor_img = conductor_walk_frames[0]
except Exception as e:
    print(f"無法載入圖片 'main_character_walk2.gif': {e}")
    print("請確認 'main_character_walk2.gif' 與 main.py 在同一個資料夾中，且已安裝 Pillow 與 numpy。")
    print("將改用 'main_character.png' 靜態圖片作為替代。")
    conductor_walk_frames = []
    conductor_walk_durations = []
    try:
        conductor_img_original = pygame.image.load(asset_path('main_character.png')).convert_alpha()
        conductor_img = pygame.transform.scale(conductor_img_original, (CONDUCTOR_SIZE, CONDUCTOR_SIZE))
    except pygame.error as e2:
        print(f"無法載入圖片 'main_character.png': {e2}")
        print("將使用藍色方塊作為替代。")
        conductor_img = None

# 載入主頁背景音樂（26秒一個循環，進到主頁就重複播放，離開主頁就停止）
music_volume = 0.5 # 音量（0.0~1.0），開始畫面跟遊戲裡的暫停選單都能調整
try:
    pygame.mixer.music.load(os.path.join('sound', '859529__notmeat2020__stems-4-santuario-f-minor.wav'))
    pygame.mixer.music.set_volume(music_volume)
    start_menu_music_loaded = True
except (pygame.error, FileNotFoundError) as e:
    print(f"無法載入主頁背景音樂: {e}")
    print("請確認 sound 資料夾裡有該音樂檔案。")
    start_menu_music_loaded = False

# 載入開始畫面的背景圖片
try:
    cover_img_original = pygame.image.load(asset_path('cover.png')).convert()
    cover_img = pygame.transform.scale(cover_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'cover.png': {e}")
    print("請確認 'cover.png' 檔案與 main.py 在同一個資料夾中。")
    print("將使用黑色背景作為替代。")
    cover_img = None # 如果圖片載入失敗，設定為 None

# 載入開始畫面的標題圖片
try:
    title_img_original = pygame.image.load(asset_path('title.png')).convert_alpha()
    TITLE_IMG_WIDTH = 220 # 縮小一點，讓下面三個按鈕（含設定）疊起來還有空間
    title_img_height = round(TITLE_IMG_WIDTH * title_img_original.get_height() / title_img_original.get_width())
    title_img = pygame.transform.smoothscale(title_img_original, (TITLE_IMG_WIDTH, title_img_height))
except pygame.error as e:
    print(f"無法載入圖片 'title.png': {e}")
    print("請確認 'title.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用文字標題作為替代。")
    title_img = None # 如果圖片載入失敗，設定為 None

# 載入開始畫面的「開始遊戲」「退出遊戲」「設定」按鈕圖片（鐵牌造型），維持原始長寬比例縮放
BUTTON_IMG_WIDTH = 165 # 三個按鈕統一用這個寬度，維持一樣大小
try:
    start_game_img_original = pygame.image.load(asset_path('start_game.png')).convert_alpha()
    start_game_img_height = round(BUTTON_IMG_WIDTH * start_game_img_original.get_height() / start_game_img_original.get_width())
    start_game_img = pygame.transform.smoothscale(start_game_img_original, (BUTTON_IMG_WIDTH, start_game_img_height))
except pygame.error as e:
    print(f"無法載入圖片 'start_game.png': {e}")
    print("請確認 'start_game.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用文字方塊按鈕作為替代。")
    start_game_img = None # 如果圖片載入失敗，設定為 None

try:
    exit_game_img_original = pygame.image.load(asset_path('exit_game.png')).convert_alpha()
    exit_game_img_height = round(BUTTON_IMG_WIDTH * exit_game_img_original.get_height() / exit_game_img_original.get_width())
    exit_game_img = pygame.transform.smoothscale(exit_game_img_original, (BUTTON_IMG_WIDTH, exit_game_img_height))
except pygame.error as e:
    print(f"無法載入圖片 'exit_game.png': {e}")
    print("請確認 'exit_game.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用文字方塊按鈕作為替代。")
    exit_game_img = None # 如果圖片載入失敗，設定為 None

# 載入「設定」按鈕圖片（同樣是鐵牌造型），跟開始／退出遊戲用同樣的寬度，維持原始長寬比例縮放
try:
    setting_img_original = pygame.image.load(asset_path('setting.png')).convert_alpha()
    setting_img_height = round(BUTTON_IMG_WIDTH * setting_img_original.get_height() / setting_img_original.get_width())
    setting_img = pygame.transform.smoothscale(setting_img_original, (BUTTON_IMG_WIDTH, setting_img_height))
except pygame.error as e:
    print(f"無法載入圖片 'setting.png': {e}")
    print("請確認 'setting.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用文字方塊按鈕作為替代。")
    setting_img = None # 如果圖片載入失敗，設定為 None

# 載入暫停選單的「繼續遊戲」「返回主頁」按鈕圖片（同樣是鐵牌造型），維持原始長寬比例縮放
try:
    continue_game_img_original = pygame.image.load(asset_path('continue_game.png')).convert_alpha()
    continue_game_img_height = round(BUTTON_IMG_WIDTH * continue_game_img_original.get_height() / continue_game_img_original.get_width())
    continue_game_img = pygame.transform.smoothscale(continue_game_img_original, (BUTTON_IMG_WIDTH, continue_game_img_height))
except pygame.error as e:
    print(f"無法載入圖片 'continue_game.png': {e}")
    print("請確認 'continue_game.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用文字方塊按鈕作為替代。")
    continue_game_img = None # 如果圖片載入失敗，設定為 None

try:
    back_home_img_original = pygame.image.load(asset_path('back_home.png')).convert_alpha()
    back_home_img_height = round(BUTTON_IMG_WIDTH * back_home_img_original.get_height() / back_home_img_original.get_width())
    back_home_img = pygame.transform.smoothscale(back_home_img_original, (BUTTON_IMG_WIDTH, back_home_img_height))
except pygame.error as e:
    print(f"無法載入圖片 'back_home.png': {e}")
    print("請確認 'back_home.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用文字方塊按鈕作為替代。")
    back_home_img = None # 如果圖片載入失敗，設定為 None

# 載入操作手冊／生存指南畫面的背景圖片（攤開的筆記本），先裁掉圖片邊緣多餘的透明留白，
# 再拉伸蓋滿畫面（左側留一小條空間放書籤標籤，不維持原始長寬比例）
MANUAL_TAB_COLUMN_WIDTH = 150 # 左側留給書籤標籤的寬度
try:
    from PIL import Image as PILImage

    manual_bg_pil = PILImage.open(asset_path('生存指南_內頁.png')).convert('RGBA')
    manual_bg_bbox = manual_bg_pil.split()[3].getbbox() # 只用透明度找出書本實際內容範圍
    if manual_bg_bbox:
        manual_bg_pil = manual_bg_pil.crop(manual_bg_bbox)
    manual_bg_img_original = pygame.image.frombuffer(manual_bg_pil.tobytes(), manual_bg_pil.size, 'RGBA').convert_alpha()
    MANUAL_BG_HEIGHT = HEIGHT - 4
    MANUAL_BG_WIDTH = WIDTH - MANUAL_TAB_COLUMN_WIDTH
    manual_bg_img = pygame.transform.smoothscale(manual_bg_img_original, (MANUAL_BG_WIDTH, MANUAL_BG_HEIGHT))
except Exception as e:
    print(f"無法載入圖片 '生存指南_內頁.png': {e}")
    print("請確認 '生存指南_內頁.png' 檔案與 main.py 在同一個資料夾中。")
    print("操作手冊／生存指南畫面將改用原本繪製的白色面板作為替代。")
    manual_bg_img = None # 如果圖片載入失敗，設定為 None

# 載入白天車廂背景圖片（維持原始長寬比例縮放，不拉伸變形；
# 車廂用兩張完整的圖片並排組成，車廂寬度改成剛好是圖片寬度的兩倍）
TRAIN_DAY_TILE_COUNT = 2
try:
    train_day_img_original = pygame.image.load(asset_path('train_day.png')).convert_alpha()
    train_day_scale = HEIGHT / train_day_img_original.get_height()
    train_day_tile_width = round(train_day_img_original.get_width() * train_day_scale)
    train_day_img = pygame.transform.smoothscale(train_day_img_original, (train_day_tile_width, HEIGHT))
    CARRIAGE_WIDTH = train_day_tile_width * TRAIN_DAY_TILE_COUNT # 車廂寬度改成圖片寬度的兩倍
except pygame.error as e:
    print(f"無法載入圖片 'train_day.png': {e}")
    print("請確認 'train_day.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的車廂背景作為替代。")
    train_day_img = None # 如果圖片載入失敗，設定為 None
    train_day_scale = HEIGHT / 1024
    train_day_tile_width = CARRIAGE_WIDTH // TRAIN_DAY_TILE_COUNT

# 縮放後的圖片邊緣會有一條很淡的模糊像素，兩張圖直接並排時會看起來像一條縫，
# 讓每一塊之間互相重疊幾個像素蓋掉它
TRAIN_DAY_TILE_OVERLAP = 3
train_day_tile_step = train_day_tile_width - TRAIN_DAY_TILE_OVERLAP

# train_day.png 原圖（寬 3323px）裡四扇窗戶的實際中心位置，用來決定座椅要擺在哪裡
TRAIN_DAY_WINDOW_CENTERS_ORIGINAL = [345, 915, 2405, 2975]

# 載入晚上車廂背景圖片，做法跟白天車廂完全一樣（兩張完整圖片並排組成車廂）
TRAIN_NIGHT_TILE_COUNT = 2
try:
    train_night_img_original = pygame.image.load(asset_path('train_night.png')).convert_alpha()
    train_night_scale = HEIGHT / train_night_img_original.get_height()
    train_night_tile_width = round(train_night_img_original.get_width() * train_night_scale)
    train_night_img = pygame.transform.smoothscale(train_night_img_original, (train_night_tile_width, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'train_night.png': {e}")
    print("請確認 'train_night.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的車廂背景作為替代。")
    train_night_img = None # 如果圖片載入失敗，設定為 None
    train_night_scale = HEIGHT / 1024
    train_night_tile_width = CARRIAGE_WIDTH // TRAIN_NIGHT_TILE_COUNT

TRAIN_NIGHT_TILE_OVERLAP = 3 # 原因同白天車廂：蓋掉縮放後兩張圖拼接處的模糊縫
train_night_tile_step = train_night_tile_width - TRAIN_NIGHT_TILE_OVERLAP

# train_night.png 原圖（寬 3320px）裡四扇窗戶的實際中心位置，用來決定座椅要擺在哪裡
TRAIN_NIGHT_WINDOW_CENTERS_ORIGINAL = [355, 890, 2435, 2960]

# 載入駕駛室白天背景圖片，直接拉伸蓋滿整個畫面（800x400），不維持原始長寬比例
try:
    drive_room_day_img_original = pygame.image.load(asset_path('drive_room_day_locked.png')).convert_alpha()
    drive_room_day_img = pygame.transform.smoothscale(drive_room_day_img_original, (WIDTH, HEIGHT))
    COCKPIT_WIDTH = WIDTH # 駕駛艙圖片現在直接蓋滿整個畫面寬度，不用再左右捲動
except pygame.error as e:
    print(f"無法載入圖片 'drive_room_day_locked.png': {e}")
    print("請確認 'drive_room_day_locked.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的駕駛艙背景作為替代。")
    drive_room_day_img = None # 如果圖片載入失敗，設定為 None

# 載入駕駛室白天「已取得生存指南」背景圖片，做法跟鎖著的版本一樣：直接拉伸蓋滿整個畫面
try:
    drive_room_day_unlocked_img_original = pygame.image.load(asset_path('drive_room_day_unlocked.png')).convert_alpha()
    drive_room_day_unlocked_img = pygame.transform.smoothscale(drive_room_day_unlocked_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'drive_room_day_unlocked.png': {e}")
    print("請確認 'drive_room_day_unlocked.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用鎖著的駕駛室背景作為替代。")
    drive_room_day_unlocked_img = drive_room_day_img # 解鎖圖片載入失敗時，退回鎖著的圖片

# 載入駕駛室晚上背景圖片，做法跟白天一樣：直接拉伸蓋滿整個畫面
try:
    drive_room_night_img_original = pygame.image.load(asset_path('drive_room_night.png')).convert_alpha()
    drive_room_night_img = pygame.transform.smoothscale(drive_room_night_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'drive_room_night.png': {e}")
    print("請確認 'drive_room_night.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的駕駛艙背景作為替代。")
    drive_room_night_img = None # 如果圖片載入失敗，設定為 None

# 載入連接處白天背景圖片：CONNECTION_1／CONNECTION_4（車廂間的一般通道）用 connect_day，
# CONNECTION_2（廁所）用 connect_toilet_day，CONNECTION_3（工具間）用 connect_toolroom_day。
# 左右拉伸1.25倍、上下蓋滿整個畫面高度；這個拉伸後的寬度直接當作連接處場景的世界寬度，
# 這樣往前一節／下一節車廂的門（在世界的最左、最右邊）才會剛好對齊圖片邊緣。
CONNECTION_WIDTH = round(CONNECTION_WIDTH * 1.25)
try:
    connect_day_img_original = pygame.image.load(asset_path('connect_day.png')).convert_alpha()
    connect_day_img = pygame.transform.smoothscale(connect_day_img_original, (CONNECTION_WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'connect_day.png': {e}")
    print("請確認 'connect_day.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的連接處背景作為替代。")
    connect_day_img = None # 如果圖片載入失敗，設定為 None

try:
    connect_toilet_day_img_original = pygame.image.load(asset_path('connect_toilet_day.png')).convert_alpha()
    connect_toilet_day_img = pygame.transform.smoothscale(connect_toilet_day_img_original, (CONNECTION_WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'connect_toilet_day.png': {e}")
    print("請確認 'connect_toilet_day.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的連接處背景作為替代。")
    connect_toilet_day_img = None # 如果圖片載入失敗，設定為 None

try:
    connect_toolroom_day_img_original = pygame.image.load(asset_path('connect_toolroom_day.png')).convert_alpha()
    connect_toolroom_day_img = pygame.transform.smoothscale(connect_toolroom_day_img_original, (CONNECTION_WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'connect_toolroom_day.png': {e}")
    print("請確認 'connect_toolroom_day.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的連接處背景作為替代。")
    connect_toolroom_day_img = None # 如果圖片載入失敗，設定為 None

# 載入廁所內部圖片（按 F 走進廁所門後顯示的畫面），直接拉伸蓋滿整個畫面
try:
    toilet_img_original = pygame.image.load(asset_path('toilet.png')).convert_alpha()
    toilet_img = pygame.transform.smoothscale(toilet_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'toilet.png': {e}")
    print("請確認 'toilet.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用黑色背景作為替代。")
    toilet_img = None # 如果圖片載入失敗，設定為 None

# 載入工具間內部、工作桌特寫圖片，做法跟廁所一樣：直接拉伸蓋滿整個畫面
try:
    toolroom_img_original = pygame.image.load(asset_path('toolroom.png')).convert_alpha()
    toolroom_img = pygame.transform.smoothscale(toolroom_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'toolroom.png': {e}")
    print("請確認 'toolroom.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用黑色背景作為替代。")
    toolroom_img = None # 如果圖片載入失敗，設定為 None

try:
    tooltable_img_original = pygame.image.load(asset_path('tooltable.png')).convert_alpha()
    tooltable_img = pygame.transform.smoothscale(tooltable_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'tooltable.png': {e}")
    print("請確認 'tooltable.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用黑色背景作為替代。")
    tooltable_img = None # 如果圖片載入失敗，設定為 None

# 載入「第X天白天／晚上」的標題卡圖片（毛筆手寫字、透明背景），切換天數／時段時會疊在畫面上短暫顯示
DAY_TITLE_CARD_WIDTH = 500
day_title_images = {}
for _day_stage_name, _day_stage_filename in [
    ('DAY1_DAY', 'day1_day.png'),
    ('DAY1_NIGHT', 'day1_night.png'),
    ('DAY2_DAY', 'day2_day.png'),
    ('DAY2_NIGHT', 'day2_night.png'),
]:
    try:
        _day_img_original = pygame.image.load(asset_path(_day_stage_filename)).convert_alpha()
        _day_img_height = round(DAY_TITLE_CARD_WIDTH * _day_img_original.get_height() / _day_img_original.get_width())
        day_title_images[_day_stage_name] = pygame.transform.smoothscale(_day_img_original, (DAY_TITLE_CARD_WIDTH, _day_img_height))
    except pygame.error as e:
        print(f"無法載入圖片 '{_day_stage_filename}': {e}")

# 載入駕駛室櫃子內部圖片。這張圖片比例接近正方形，跟畫面的長寬比差很多，
# 直接拉伸蓋滿整個畫面會變形得很明顯，所以改成維持原始比例縮放到蓋滿畫面高度、置中顯示，
# 左右兩側沒有圖片蓋到的地方保留黑邊（做法跟連接處背景一樣）。
try:
    case_img_original = pygame.image.load(asset_path('case.png')).convert_alpha()
    case_img_width = round(HEIGHT * case_img_original.get_width() / case_img_original.get_height())
    case_img = pygame.transform.smoothscale(case_img_original, (case_img_width, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'case.png': {e}")
    print("請確認 'case.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用黑色背景作為替代。")
    case_img = None # 如果圖片載入失敗，設定為 None

# 載入操作台細節畫面的背景圖片（按 F 聚焦操作台後顯示），做法跟廁所一樣：直接拉伸蓋滿整個畫面。
# 置物櫃鎖著／解鎖分別對應 operator_day_locked.png、operator_day_unlocked.png 兩張圖。
try:
    operator_day_locked_img_original = pygame.image.load(asset_path('operator_day_locked.png')).convert_alpha()
    operator_day_locked_img = pygame.transform.smoothscale(operator_day_locked_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'operator_day_locked.png': {e}")
    print("請確認 'operator_day_locked.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用黑色背景作為替代。")
    operator_day_locked_img = None # 如果圖片載入失敗，設定為 None

try:
    operator_day_unlocked_img_original = pygame.image.load(asset_path('operator_day_unlocked.png')).convert_alpha()
    operator_day_unlocked_img = pygame.transform.smoothscale(operator_day_unlocked_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'operator_day_unlocked.png': {e}")
    print("請確認 'operator_day_unlocked.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用鎖著的操作台圖片作為替代。")
    operator_day_unlocked_img = operator_day_locked_img # 解鎖圖片載入失敗時，退回鎖著的圖片

# 載入置物櫃門特寫圖片（點擊操作台右下角的櫃門後顯示），鎖著／解鎖分別對應 box_locked.png、box_unlocked.png
try:
    box_locked_img_original = pygame.image.load(asset_path('box_locked.png')).convert_alpha()
    box_locked_img = pygame.transform.smoothscale(box_locked_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'box_locked.png': {e}")
    print("請確認 'box_locked.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用黑色背景作為替代。")
    box_locked_img = None # 如果圖片載入失敗，設定為 None

try:
    box_unlocked_img_original = pygame.image.load(asset_path('box_unlocked.png')).convert_alpha()
    box_unlocked_img = pygame.transform.smoothscale(box_unlocked_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'box_unlocked.png': {e}")
    print("請確認 'box_unlocked.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用鎖著的櫃門圖片作為替代。")
    box_unlocked_img = box_locked_img # 解鎖圖片載入失敗時，退回鎖著的圖片

# 載入白天座椅圖片，並裁掉圖片邊緣多餘的透明留白，避免椅腳貼地時浮空
try:
    from PIL import Image as PILImage

    import numpy as np

    chair_pil = PILImage.open(asset_path('chair_day.png')).convert('RGBA')
    chair_alpha_bbox = chair_pil.split()[3].getbbox() # 只用透明度找出實際內容範圍
    if chair_alpha_bbox:
        chair_pil = chair_pil.crop(chair_alpha_bbox)
    chair_arr = feather_alpha_edges(np.array(chair_pil), radius=1.5) # 讓椅子邊緣柔和一點，不要太銳利
    chair_day_img_original = pygame.image.frombuffer(chair_arr.tobytes(), (chair_arr.shape[1], chair_arr.shape[0]), 'RGBA').convert_alpha()
    CHAIR_DAY_HEIGHT = 150
    chair_day_width = round(CHAIR_DAY_HEIGHT * chair_day_img_original.get_width() / chair_day_img_original.get_height())
    chair_day_img = pygame.transform.smoothscale(chair_day_img_original, (chair_day_width, CHAIR_DAY_HEIGHT))
except Exception as e:
    print(f"無法載入圖片 'chair_day.png': {e}")
    print("請確認 'chair_day.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的座椅作為替代。")
    chair_day_img = None # 如果圖片載入失敗，設定為 None

# 載入晚上座椅圖片，做法跟白天座椅一樣
try:
    chair_night_pil = PILImage.open(asset_path('chair_night.png')).convert('RGBA')
    chair_night_alpha_bbox = chair_night_pil.split()[3].getbbox()
    if chair_night_alpha_bbox:
        chair_night_pil = chair_night_pil.crop(chair_night_alpha_bbox)
    chair_night_arr = feather_alpha_edges(np.array(chair_night_pil), radius=1.5)
    chair_night_img_original = pygame.image.frombuffer(chair_night_arr.tobytes(), (chair_night_arr.shape[1], chair_night_arr.shape[0]), 'RGBA').convert_alpha()
    CHAIR_NIGHT_HEIGHT = 150
    chair_night_width = round(CHAIR_NIGHT_HEIGHT * chair_night_img_original.get_width() / chair_night_img_original.get_height())
    chair_night_img = pygame.transform.smoothscale(chair_night_img_original, (chair_night_width, CHAIR_NIGHT_HEIGHT))
except Exception as e:
    print(f"無法載入圖片 'chair_night.png': {e}")
    print("請確認 'chair_night.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用原本繪製的座椅作為替代。")
    chair_night_img = None # 如果圖片載入失敗，設定為 None

# 載入老太太專用圖片（已經包含椅子跟人物本身，取代車廂一的第一張椅子）
try:
    from PIL import Image as PILImage
    import numpy as np

    granny_pil = PILImage.open(asset_path('granny.png')).convert('RGBA')
    granny_alpha_bbox = granny_pil.split()[3].getbbox()
    if granny_alpha_bbox:
        granny_pil = granny_pil.crop(granny_alpha_bbox)
    granny_arr = feather_alpha_edges(np.array(granny_pil), radius=1.5) # 讓邊緣柔和一點，不要太銳利
    granny_img_original = pygame.image.frombuffer(granny_arr.tobytes(), (granny_arr.shape[1], granny_arr.shape[0]), 'RGBA').convert_alpha()
    GRANNY_HEIGHT = 150 # 跟其他椅子（CHAIR_DAY_HEIGHT）一樣高，避免看起來比較大
    granny_width = round(GRANNY_HEIGHT * granny_img_original.get_width() / granny_img_original.get_height())
    granny_img = pygame.transform.smoothscale(granny_img_original, (granny_width, GRANNY_HEIGHT))
except Exception as e:
    print(f"無法載入圖片 'granny.png': {e}")
    print("請確認 'granny.png' 檔案與 main.py 在同一個資料夾中。")
    print("老太太將改用方塊繪製作為替代。")
    granny_img = None # 如果圖片載入失敗，設定為 None

# 載入小女孩專用圖片（已經包含椅子跟人物本身，取代車廂二的第四張椅子）。
# 這張圖片背景是純黑色、沒有透明度，用亮度門檻去背（跟角色走路動畫用的手法一樣），
# 只留下夠大的連通區域再往外擴張兩圈，避免深色的頭髮、制服被誤判成背景挖空。
try:
    from scipy import ndimage

    girl_pil = PILImage.open(asset_path('little_girl.png')).convert('RGB')
    girl_arr = np.array(girl_pil)
    girl_rgba_arr = np.dstack([girl_arr, np.full(girl_arr.shape[:2], 255, dtype=np.uint8)])
    girl_background = girl_arr.max(axis=2) < 15 # 純黑背景，跟人物的深色衣服/頭髮還是有落差
    girl_labeled, girl_num_components = ndimage.label(girl_background)
    if girl_num_components > 0:
        girl_sizes = ndimage.sum(girl_background, girl_labeled, range(1, girl_num_components + 1))
        girl_large_components = [idx + 1 for idx, size in enumerate(girl_sizes) if size > 500]
        girl_background = np.isin(girl_labeled, girl_large_components)
        girl_background = ndimage.binary_dilation(girl_background, iterations=2)
    girl_rgba_arr[girl_background, 3] = 0
    girl_cut_pil = PILImage.fromarray(girl_rgba_arr, 'RGBA')
    girl_cut_bbox = girl_cut_pil.split()[3].getbbox()
    if girl_cut_bbox:
        girl_cut_pil = girl_cut_pil.crop(girl_cut_bbox)
    girl_feathered_arr = feather_alpha_edges(np.array(girl_cut_pil), radius=1.5) # 讓去背邊緣柔和一點，不要太銳利
    little_girl_img_original = pygame.image.frombuffer(girl_feathered_arr.tobytes(), (girl_feathered_arr.shape[1], girl_feathered_arr.shape[0]), 'RGBA').convert_alpha()
    LITTLE_GIRL_HEIGHT = 150 # 跟其他椅子（CHAIR_DAY_HEIGHT）一樣高，避免看起來比較大
    little_girl_width = round(LITTLE_GIRL_HEIGHT * little_girl_img_original.get_width() / little_girl_img_original.get_height())
    little_girl_img = pygame.transform.smoothscale(little_girl_img_original, (little_girl_width, LITTLE_GIRL_HEIGHT))
except Exception as e:
    print(f"無法載入圖片 'little_girl.png': {e}")
    print("請確認 'little_girl.png' 檔案與 main.py 在同一個資料夾中。")
    print("小女孩將改用方塊繪製作為替代。")
    little_girl_img = None # 如果圖片載入失敗，設定為 None

# 載入老維修員專用圖片（已經包含椅子跟人物本身，取代車廂三的第三張椅子），做法跟老太太一樣
try:
    old_engineer_pil = PILImage.open(asset_path('old_engineer.png')).convert('RGBA')
    old_engineer_alpha_bbox = old_engineer_pil.split()[3].getbbox()
    if old_engineer_alpha_bbox:
        old_engineer_pil = old_engineer_pil.crop(old_engineer_alpha_bbox)
    old_engineer_arr = feather_alpha_edges(np.array(old_engineer_pil), radius=1.5) # 讓邊緣柔和一點，不要太銳利
    old_engineer_img_original = pygame.image.frombuffer(old_engineer_arr.tobytes(), (old_engineer_arr.shape[1], old_engineer_arr.shape[0]), 'RGBA').convert_alpha()
    OLD_ENGINEER_HEIGHT = 150 # 跟其他椅子（CHAIR_DAY_HEIGHT）一樣高，避免看起來比較大
    old_engineer_width = round(OLD_ENGINEER_HEIGHT * old_engineer_img_original.get_width() / old_engineer_img_original.get_height())
    old_engineer_img = pygame.transform.smoothscale(old_engineer_img_original, (old_engineer_width, OLD_ENGINEER_HEIGHT))
except Exception as e:
    print(f"無法載入圖片 'old_engineer.png': {e}")
    print("請確認 'old_engineer.png' 檔案與 main.py 在同一個資料夾中。")
    print("老維修員將改用方塊繪製作為替代。")
    old_engineer_img = None # 如果圖片載入失敗，設定為 None


def load_item_icon(filename, max_size):
    """載入道具圖示，裁掉邊緣多餘的透明留白，再等比例縮放到剛好放進 max_size 的方框內"""
    icon_pil = PILImage.open(asset_path(filename)).convert('RGBA')
    icon_bbox = icon_pil.split()[3].getbbox()
    if icon_bbox:
        icon_pil = icon_pil.crop(icon_bbox)
    icon_img = pygame.image.frombuffer(icon_pil.tobytes(), icon_pil.size, 'RGBA').convert_alpha()
    scale = min(max_size / icon_img.get_width(), max_size / icon_img.get_height())
    icon_w = max(1, round(icon_img.get_width() * scale))
    icon_h = max(1, round(icon_img.get_height() * scale))
    return pygame.transform.smoothscale(icon_img, (icon_w, icon_h))


# 道具圖示：鍵是道具名稱，值是縮放好的圖片，載入失敗的道具會保持原本的色塊顯示
ITEM_ICONS = {}
for _icon_item_name, _icon_filename, _icon_max_size in [
    ('老式手電筒', 'flashlight.png', 110),
    ('車站鑰匙', 'station_key.png', 110),
    ('維修員留下的螺絲起子', 'screwdriver.png', 110),
    ('工具間鑰匙', 'toolroom_key.png', 110),
    ('舊車票', 'old_ticket.png', 24),
    ('舊路線圖', 'old_route_map.png', 24),
    ('舊報紙', 'old_news.png', 24),
    ('車站員工日誌', '員工日誌.png', 24),
    ('《夜間行駛生存指南》', '生存指南.png', 110),
]:
    try:
        ITEM_ICONS[_icon_item_name] = load_item_icon(_icon_filename, _icon_max_size)
    except Exception as e:
        print(f"無法載入道具圖示 '{_icon_filename}': {e}")

# 地上道具點的小標記圖示：跟 ITEM_ICONS 是同一批圖片，但再縮小到剛好放進 26x26 的標記框，
# 避免像車站鑰匙這種背包用的大圖示（110px）直接畫在地上標記時整個爆框
ITEM_MARKER_MAX_SIZE = 24
ITEM_MARKER_ICONS = {}
for _marker_item_name, _marker_icon in ITEM_ICONS.items():
    _marker_scale = min(1.0, ITEM_MARKER_MAX_SIZE / _marker_icon.get_width(), ITEM_MARKER_MAX_SIZE / _marker_icon.get_height())
    if _marker_scale < 1.0:
        _marker_w = max(1, round(_marker_icon.get_width() * _marker_scale))
        _marker_h = max(1, round(_marker_icon.get_height() * _marker_scale))
        ITEM_MARKER_ICONS[_marker_item_name] = pygame.transform.smoothscale(_marker_icon, (_marker_w, _marker_h))
    else:
        ITEM_MARKER_ICONS[_marker_item_name] = _marker_icon

# 置物櫃門的四個孔洞上蓋著的螺絲圖示，要用螺絲起子點擊轉開才會消失
try:
    box_screw_icon = load_item_icon('rose.png', 28)
except Exception as e:
    print(f"無法載入道具圖示 'rose.png': {e}")
    box_screw_icon = None

# 依照背景圖片裡窗戶的實際位置，計算白天座椅要擺放的世界座標（每張背景圖裡的每扇窗戶前都放一張椅子）
chair_day_positions = []
if train_day_img:
    window_centers_scaled = [round(x * train_day_scale) for x in TRAIN_DAY_WINDOW_CENTERS_ORIGINAL]
    chair_half_width = (chair_day_img.get_width() // 2) if chair_day_img else 60
    safe_min = DOOR_WIDTH + chair_half_width
    safe_max = CARRIAGE_WIDTH - DOOR_WIDTH - chair_half_width
    for tile_index in range(TRAIN_DAY_TILE_COUNT):
        for center in window_centers_scaled:
            pos = tile_index * train_day_tile_step + center
            if safe_min <= pos <= safe_max:
                chair_day_positions.append(pos)

# 依照背景圖片裡窗戶的實際位置，計算晚上座椅要擺放的世界座標，做法跟白天座椅一樣
chair_night_positions = []
if train_night_img:
    night_window_centers_scaled = [round(x * train_night_scale) for x in TRAIN_NIGHT_WINDOW_CENTERS_ORIGINAL]
    chair_night_half_width = (chair_night_img.get_width() // 2) if chair_night_img else 60
    night_safe_min = DOOR_WIDTH + chair_night_half_width
    night_safe_max = CARRIAGE_WIDTH - DOOR_WIDTH - chair_night_half_width
    for tile_index in range(TRAIN_NIGHT_TILE_COUNT):
        for center in night_window_centers_scaled:
            pos = tile_index * train_night_tile_step + center
            if night_safe_min <= pos <= night_safe_max:
                chair_night_positions.append(pos)

# 設定列車長的碰撞框 (Rect)
conductor_rect = pygame.Rect(
    COCKPIT_WIDTH - DOOR_WIDTH - CONDUCTOR_SIZE - 10, # 初始 x 位置：駕駛艙門的左邊再過去一點
    HEIGHT - FLOOR_HEIGHT - CONDUCTOR_SIZE + CONDUCTOR_Y_OFFSET,
    CONDUCTOR_SIZE,
    CONDUCTOR_SIZE
)
# 控制遊戲更新頻率的時鐘
clock = pygame.time.Clock()

# 攝影機的 X 軸位置
camera_x = 0

# --- 場景管理 ---
current_scene = 'COCKPIT' # 遊戲從駕駛艙開始

# --- 遊戲狀態管理 ---
game_state = 'START' # 初始狀態為遊戲開始畫面

# --- 開始畫面 ---
# 開始遊戲／設定／退出遊戲，由上到下疊放：用鐵牌圖片的實際大小當碰撞箱，圖片載入失敗時才用預設方塊大小
_start_ui_top = 160 # 按鈕堆疊區塊的最上緣（標題下方）
_start_ui_gap = 10

if start_game_img:
    start_button_rect = start_game_img.get_rect(midtop=(WIDTH // 2, _start_ui_top))
else:
    start_button_rect = pygame.Rect(WIDTH // 2 - 95, _start_ui_top, 190, 55)

# 開始遊戲／退出遊戲中間的設定按鈕（點進去才能調整音量）
if setting_img:
    settings_button_rect = setting_img.get_rect(midtop=(WIDTH // 2, start_button_rect.bottom + _start_ui_gap))
else:
    settings_button_rect = pygame.Rect(0, start_button_rect.bottom + _start_ui_gap, 110, 34)
    settings_button_rect.centerx = WIDTH // 2

if exit_game_img:
    exit_button_rect = exit_game_img.get_rect(midtop=(WIDTH // 2, settings_button_rect.bottom + _start_ui_gap))
else:
    exit_button_rect = pygame.Rect(WIDTH // 2 - 95, settings_button_rect.bottom + _start_ui_gap, 190, 55)

# --- 遊戲中按 ESC 跳出的選單（由上到下：繼續遊玩、設定、返回主頁）---
_pause_ui_top = 140 # 按鈕堆疊區塊的最上緣（「已暫停」標題下方）
if continue_game_img:
    resume_button_rect = continue_game_img.get_rect(midtop=(WIDTH // 2, _pause_ui_top))
else:
    resume_button_rect = pygame.Rect(WIDTH // 2 - 100, _pause_ui_top, 200, 55) # 繼續遊玩按鈕

if setting_img:
    pause_settings_button_rect = setting_img.get_rect(midtop=(WIDTH // 2, resume_button_rect.bottom + 15))
else:
    pause_settings_button_rect = pygame.Rect(0, resume_button_rect.bottom + 15, 110, 34)
    pause_settings_button_rect.centerx = WIDTH // 2

if back_home_img:
    back_to_menu_button_rect = back_home_img.get_rect(midtop=(WIDTH // 2, pause_settings_button_rect.bottom + 15))
else:
    back_to_menu_button_rect = pygame.Rect(WIDTH // 2 - 100, pause_settings_button_rect.bottom + 15, 200, 55) # 返回主頁按鈕

# --- 設定畫面（音量滑桿＋返回按鈕），可以從開始畫面或暫停選單點「設定」進來 ---
settings_return_state = 'START' # 記錄是從哪個畫面點進設定的，按返回才知道要回哪裡
settings_volume_track_rect = pygame.Rect(0, HEIGHT // 2 - 3, 260, 6)
settings_volume_track_rect.centerx = WIDTH // 2
settings_back_button_rect = pygame.Rect(WIDTH // 2 - 90, HEIGHT // 2 + 70, 180, 50)

# --- 天數／白天晚上切換（依序循環：第一天白天 → 第一天晚上 → 第二天白天 → 第二天晚上）---
DAY_NIGHT_STAGES = ['DAY1_DAY', 'DAY1_NIGHT', 'DAY2_DAY', 'DAY2_NIGHT']
DAY_NIGHT_LABELS = {
    'DAY1_DAY': '第一天白天',
    'DAY1_NIGHT': '第一天晚上',
    'DAY2_DAY': '第二天白天',
    'DAY2_NIGHT': '第二天晚上',
}
day_night_index = 0 # 目前所在階段在 DAY_NIGHT_STAGES 中的索引


def is_daytime():
    """目前是否是白天（不是 XX_NIGHT 階段）"""
    return not DAY_NIGHT_STAGES[day_night_index].endswith('NIGHT')

# --- 第一天晚上劇情 ---
day1_night_triggered = False # 是否已經播放過第一天晚上的事件，避免重複觸發
day1_night_resolved = False # 第一天晚上的劇情是否已經解完，解完之前無法前進到第二天
night1_pending_intro = False # 是否已經切到第一天晚上、但要等玩家關掉手冊（生存指南頁）後才播放開場劇情
night1_patrol_active = False # 是否正在「巡視車廂」任務中（intro 劇情結束後開始，走到第五節車廂後結束）
lights_out = False # 列車燈光是否熄滅中，此時任務指引是先打開手電筒、再返回駕駛室，且開門需要手電筒；
                    # 熄燈期間除了車廂門以外，無法跟任何東西互動（也不會顯示互動提示）

# --- 手電筒 ---
flashlight_on = False # 手電筒是否開啟中（需持有「老式手電筒」才能開關）
facing_direction = 'RIGHT' # 角色目前面向，決定手電筒照亮的方向

# --- 走路動畫 ---
conductor_anim_index = 0 # 目前播放到走路動畫的第幾格
conductor_anim_timer = 0 # 累積經過的毫秒數，用來判斷何時切換下一格

night1_intro_lines = [
    ("我", "上班第一天就快要結束了，巡視完列車就可以下班了。"),
    ("旁白", "我起身，準備開始夜班的第一次巡視。"),
]

night1_blackout_lines = [ # 走到第五節車廂、且持有手電筒時播放，播完後任務改成「打開手電筒」
    ("旁白", "凌晨 00:17，列車燈光突然熄滅。"),
]

night1_knock_lines = [
    ("旁白", "叩。叩。叩。有人在敲駕駛室門。"),
]

night1_lines_no_flashlight = [ # 走到第五節車廂時沒有手電筒，直接迎來黑暗中的結局
    ("旁白", "凌晨 00:17，列車燈光突然熄滅。"),
    ("旁白", "四周一片漆黑，你完全看不清任何東西。"),
    ("旁白", "你伸手在黑暗中摸索，想找到回駕駛室的路——"),
    ("旁白", "但沒有光，你什麼都找不到。"),
    ("旁白", "你聽見腳步聲，從四面八方逐漸逼近。"),
]

night1_lines_closed = [ # 選擇「不開門」後的劇情
    ("旁白", "你沒有開門。幾秒後，敲門聲停止了。"),
    ("旁白", "列車離開隧道，燈恢復正常。"),
    ("旁白", "我看向監視器，發現最後一節車廂多了一個人。"),
    ("旁白", "白天看到的乘客名單明明只有五人，現在卻變成六人。"),
    ("旁白", "畫裡的第六個人，就是現在出現的人。"),
    ("旁白", "第一天，結束。"),
]

night1_lines_open = [ # 選擇「開門」後的劇情——會被發現
    ("旁白", "你打開了駕駛室的門。"),
    ("旁白", "門外空無一人，只有一陣刺骨的冷風灌了進來。"),
    ("旁白", "就在這時，你感覺背後傳來一股視線。"),
    ("旁白", "你緩緩回過頭——那個「多出來的人」，正站在你身後，直直地看著你。"),
]

night1_choice_open_rect = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 20, 140, 50)
night1_choice_close_rect = pygame.Rect(WIDTH // 2 + 40, HEIGHT // 2 + 20, 140, 50)

game_over_reason = "" # Game Over 畫面顯示的死因說明，依觸發事件動態更換

# --- 第二天晚上劇情 ---
day2_night_triggered = False # 是否已經播放過第二天晚上的事件，避免重複觸發

night2_intro_lines = [
    ("旁白", "列車進入夜間，一切原本正常。"),
    ("旁白", "但玩家漸漸發現，路線標誌開始出現不合理的變化。"),
    ("旁白", "原本：第六站 → 終點"),
    ("旁白", "突然變成：第六站 → 青木站 → 終點"),
]

night2_stop_result_brake = [ # 選擇「停車」後的過渡劇情
    ("旁白", "你試圖煞車——但列車彷彿不受控制，仍舊緩緩滑進了一座不存在的月台。"),
]

night2_stop_result_no_brake = [ # 選擇「不停車」後的過渡劇情
    ("旁白", "你沒有煞車，任由列車照著詭異的路線行駛。"),
    ("旁白", "最終，列車還是緩緩滑進了一座不存在的月台。"),
]

night2_platform_lines = [ # 兩種停車選擇之後，共同接續的劇情
    ("旁白", "指南規則四：「如果列車停靠一個沒有名字的車站，請保持車門關閉，不要讓任何人上車。」"),
    ("旁白", "月台上站著很多人，全部面向列車，沒有人動。"),
]

night2_lines_closed_door = [ # 選擇「不開門」後的劇情——安全路線
    ("旁白", "你緊閉車門。"),
    ("旁白", "突然，月台上所有人一起轉頭看向駕駛室。"),
    ("旁白", "你屏住呼吸，直到他們一動也不動——列車終於再次啟動。"),
    ("旁白", "凌晨 00:17，青木站消失了，彷彿從未存在過。"),
    ("旁白", "你翻出白天蒐集到的舊路線圖、員工日誌與事故報紙，重新拼湊出真相："),
    ("旁白", "青木站不是普通的廢站。三年前事故當晚，列車根本沒有按照正常路線行駛，"),
    ("旁白", "而是被人為切換到了青木站。"),
    ("旁白", "第二天，結束。"),
]

night2_lines_open_door = [ # 選擇「開門」後的劇情——違反規則四
    ("旁白", "你打開了車門。"),
    ("旁白", "月台上所有人同時轉過頭，直直地看向你。"),
    ("旁白", "沒有人說話，但他們開始，一步一步地朝列車走來。"),
]

# --- 通用選擇畫面（可重複用來詢問「A / B」二選一）---
choice_prompt = ""
choice_label_a = ""
choice_label_b = ""
choice_result_a = None # (dialogue_lines, active_npc)
choice_result_b = None
choice_rect_a = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 20, 140, 50)
choice_rect_b = pygame.Rect(WIDTH // 2 + 40, HEIGHT // 2 + 20, 140, 50)


def start_choice(prompt, label_a, result_a, label_b, result_b):
    """開始一個通用的二選一選擇畫面"""
    global choice_prompt, choice_label_a, choice_label_b, choice_result_a, choice_result_b, game_state
    choice_prompt = prompt
    choice_label_a = label_a
    choice_label_b = label_b
    choice_result_a = result_a
    choice_result_b = result_b
    game_state = 'STORY_CHOICE'

# 場景順序：決定按 F 開門時要往哪個方向移動（每節車廂之間都有一個連接處）
SCENE_ORDER = [
    'COCKPIT',
    'CARRIAGE_1', 'CONNECTION_1',
    'CARRIAGE_2', 'CONNECTION_2',
    'CARRIAGE_3', 'CONNECTION_3',
    'CARRIAGE_4', 'CONNECTION_4',
    'CARRIAGE_5',
]


def get_scene_width(scene_name):
    """回傳指定場景的世界寬度"""
    if 'CARRIAGE' in scene_name:
        return CARRIAGE_WIDTH
    elif 'CONNECTION' in scene_name:
        return CONNECTION_WIDTH
    else: # COCKPIT
        return COCKPIT_WIDTH


def build_doors():
    """依照 SCENE_ORDER 自動產生每個場景的互動門：
    'prev' 通往上一個場景（駕駛室方向），'next' 通往下一個場景（車尾方向）"""
    result = {}
    for index, scene_name in enumerate(SCENE_ORDER):
        scene_doors = {}
        if index > 0:
            scene_doors['prev'] = pygame.Rect(0, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_HITBOX_WIDTH, DOOR_HEIGHT)
        if index < len(SCENE_ORDER) - 1:
            scene_width = get_scene_width(scene_name)
            scene_doors['next'] = pygame.Rect(scene_width - DOOR_HITBOX_WIDTH, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, DOOR_HITBOX_WIDTH, DOOR_HEIGHT)
        result[scene_name] = scene_doors
    return result


doors = build_doors() # 定義每個場景的互動門

# --- 開場自白：玩家第一次關閉操作手冊後，主角的自言自語 ---
intro_monologue_lines = [
    ("我", "今天是我上任的第一天，心情有點緊張啊……"),
    ("我", "自從三年前父親失蹤之後，我便努力的考上鐵路車長這個職位"),
    ("我", "只因為對於父親無故失蹤，鐵路公司給出的回答是"),
    ("我", "「陳啟明於三年前因精神狀況不佳離職。」"),
    ("我", "陳啟明是我的父親"),
    ("我", "我不相信……父親不可能就這樣無故消失……"),
    ("我", "所以三年後"),
    ("我", "我在這裡，決定把真相找出來……"),
]
intro_monologue_shown = False # 是否已經播放過開場自白，避免之後重新打開手冊、關閉時又重播一次

# --- 老太太 NPC（用 granny.png 取代車廂一的第一張椅子，圖片本身已經包含椅子） ---
OLD_LADY_SCENE = 'CARRIAGE_1'
GRANNY_CHAIR_X = chair_day_positions[1] if len(chair_day_positions) > 1 else 410 # 車廂一第二張椅子的位置
if granny_img:
    old_lady_rect = granny_img.get_rect()
    old_lady_rect.midbottom = (GRANNY_CHAIR_X, HEIGHT - FLOOR_HEIGHT + 20)
else:
    old_lady_rect = pygame.Rect(GRANNY_CHAIR_X - 30, HEIGHT - FLOOR_HEIGHT - 90, 60, 90) # 圖片載入失敗時的備用碰撞箱

# 互動判定範圍縮小成人物大小，不要用整張椅子圖片的範圍（椅子含扶手、椅背，比實際人物大很多）
old_lady_interact_rect = pygame.Rect(0, 0, 10, 90)
old_lady_interact_rect.midbottom = old_lady_rect.midbottom

# 老太太第一天的對話劇情，格式為 (說話者, 台詞)
old_lady_dialogue = [
    ("老太太", "新人？"),
    ("我", "是。"),
    ("老太太", "那你晚上可別回頭。"),
    ("我", "回頭？"),
    ("老太太", "……"), # 她卻像沒說過這句話一樣
]

# 已經聊過一次之後，再找她說話會改播這段
old_lady_dialogue_repeat = [
    ("老太太", "……"),
]

has_talked_to_old_lady = False # 是否已經完整聊過第一次對話

# --- 小女孩 NPC（用 little_girl.png 取代車廂二的第四張椅子，圖片本身已經包含椅子） ---
GIRL_SCENE = 'CARRIAGE_2' # 她一個人坐在第二節車廂
GIRL_CHAIR_X = chair_day_positions[3] if len(chair_day_positions) > 3 else 410 # 車廂二第四張椅子的位置
if little_girl_img:
    girl_rect = little_girl_img.get_rect()
    girl_rect.midbottom = (GIRL_CHAIR_X, HEIGHT - FLOOR_HEIGHT + 20)
else:
    girl_rect = pygame.Rect(GIRL_CHAIR_X - 25, HEIGHT - FLOOR_HEIGHT - 80, 50, 80) # 圖片載入失敗時的備用碰撞箱

# 互動判定範圍縮小成人物大小，不要用整張椅子圖片的範圍（椅子含扶手、椅背，比實際人物大很多）
girl_interact_rect = pygame.Rect(0, 0, 40, 80)
girl_interact_rect.midbottom = girl_rect.midbottom

# 小女孩第一天的對話劇情
girl_dialogue = [
    ("小女孩", "……"),
    ("我", "你在畫什麼？"),
    ("小女孩", "火車。"),
    ("我", "（她把畫轉向你，畫裡的火車旁畫了六個人。）"),
    ("我", "這班車明明只有五個人……可以給我看看這張畫嗎？"),
    ("小女孩", "……嗯。"),
    (" ", "從小女孩手中拿到了「小女孩的畫」。"),
]

# 已經拿到畫之後，再找她說話會改播這段（不會重複給畫）
girl_dialogue_repeat = [
    ("小女孩", "……"),
]

# --- 老維修員 NPC（第二天白天起才會出現，用 old_engineer.png 取代車廂三的第三張椅子，圖片本身已經包含椅子）---
OLD_WORKER_SCENE = 'CARRIAGE_3'
OLD_WORKER_MIN_DAY_INDEX = 2 # DAY_NIGHT_STAGES 中 'DAY2_DAY' 的索引
OLD_WORKER_CHAIR_X = chair_day_positions[2] if len(chair_day_positions) > 2 else 410 # 車廂三第三張椅子的位置
if old_engineer_img:
    old_worker_rect = old_engineer_img.get_rect()
    old_worker_rect.midbottom = (OLD_WORKER_CHAIR_X, HEIGHT - FLOOR_HEIGHT + 20)
else:
    old_worker_rect = pygame.Rect(OLD_WORKER_CHAIR_X - 30, HEIGHT - FLOOR_HEIGHT - 90, 60, 90) # 圖片載入失敗時的備用碰撞箱

# 互動判定範圍縮小成人物大小，不要用整張椅子圖片的範圍（椅子含扶手、椅背，比實際人物大很多）
old_worker_interact_rect = pygame.Rect(0, 0, 40, 90)
old_worker_interact_rect.midbottom = old_worker_rect.midbottom

WORKER_COLOR = (90, 110, 90) # 圖片載入失敗時，老維修員改用暗綠色方塊代表；對話框文字顏色也用這個

# 老維修員第二天白天的對話：主線內容
old_worker_dialogue_intro = [
    ("我", "欸，你知道昨晚到底發生了什麼事嗎？"),
    ("老維修員", "……那種事，還是別多問比較好。"),
    ("我", "可是我真的看到了什麼。"),
    ("老維修員", "如果你晚上看見第七站，別停。"),
    ("我", "第七站？這條路線不是只有六個車站嗎？"),
    ("老維修員", "……以前，是有第七站的。"),
]

# 若玩家持有第一天拿到的舊路線圖，會多出這段揭露「青木站」的內容
old_worker_dialogue_map_reveal = [
    ("我", "（我想起背包裡的舊路線圖……）"),
    ("旁白", "你翻出舊路線圖，發現上面有一個被塗黑的車站——「青木站」。"),
    ("旁白", "但現在的官方路線圖上，根本沒有這個地方。"),
]

old_worker_dialogue_outro = [
    ("老維修員", "……你最好，什麼都別想起來。"),
]


def build_old_worker_dialogue():
    """組合老維修員的對話內容，若玩家持有舊路線圖會多顯示青木站的揭露"""
    lines = list(old_worker_dialogue_intro)
    if '舊路線圖' in inventory:
        lines += old_worker_dialogue_map_reveal
    lines += old_worker_dialogue_outro
    return lines


# 對話中不同說話者對應的文字顏色
SPEAKER_COLORS = {
    "老太太": RED,
    "小女孩": PINK,
    "老維修員": WORKER_COLOR,
    "我": BLUE,
    "旁白": DARK_GRAY,
}

# --- 對話狀態管理 ---
dialogue_lines = []
dialogue_index = 0
active_npc = None # 記錄目前正在對話的 NPC，用於對話結束後觸發後續事件
has_girl_painting = False # 是否已從小女孩手中取得畫
has_guide = False # 是否已取得《夜間行駛生存指南》，取得後可在手冊畫面切換查看

# --- 手冊畫面（背景是攤開的筆記本圖片，靠右塞滿畫面；左側留一排書籤標籤可切換操作手冊／生存指南）---
manual_view = 'MANUAL' # 目前手冊畫面顯示的頁籤：MANUAL 操作手冊 / GUIDE 生存指南
if manual_bg_img:
    manual_panel_rect = manual_bg_img.get_rect()
    manual_panel_rect.topleft = (MANUAL_TAB_COLUMN_WIDTH, (HEIGHT - manual_bg_img.get_height()) // 2)
else:
    manual_panel_rect = pygame.Rect(MANUAL_TAB_COLUMN_WIDTH, HEIGHT // 2 - 195, 700 - MANUAL_TAB_COLUMN_WIDTH, 390)

# 貼在書本左側、垂直置中的書籤標籤（縱向排列）。刻意疊進書本邊緣幾個像素，
# 蓋掉書本圖片縮放後邊緣那條很淡的模糊像素，不然兩者中間會看起來有一條縫。
MANUAL_TAB_WIDTH = 140
MANUAL_TAB_HEIGHT = 48
MANUAL_TAB_GAP = 10
MANUAL_TAB_OVERLAP = 8
_manual_tabs_total_height = MANUAL_TAB_HEIGHT * 2 + MANUAL_TAB_GAP
_manual_tabs_top = manual_panel_rect.centery - _manual_tabs_total_height // 2
manual_tab_manual_rect = pygame.Rect(manual_panel_rect.x - MANUAL_TAB_WIDTH + MANUAL_TAB_OVERLAP, _manual_tabs_top, MANUAL_TAB_WIDTH, MANUAL_TAB_HEIGHT)
manual_tab_guide_rect = pygame.Rect(manual_panel_rect.x - MANUAL_TAB_WIDTH + MANUAL_TAB_OVERLAP, manual_tab_manual_rect.bottom + MANUAL_TAB_GAP, MANUAL_TAB_WIDTH, MANUAL_TAB_HEIGHT)

# 《夜間行駛生存指南》第一頁的前三條規則，格式為 (規則標題, 規則內容, 補充說明)
guide_rules = [
    ("規則一", "夜間駕駛時，看到月台有人，不要鳴笛。", "因為那個人不一定是在等車。"),
    ("規則二", "列車進入隧道後，如果車廂燈熄滅，不要離開駕駛室。", "不管你聽見什麼。"),
    ("規則三", "凌晨 00:17，不要查看後視鏡。", "如果已經看了，不要數車廂裡有幾個人。"),
]

# --- 第一天白天可收集道具 ---
inventory = [] # 玩家背包，存放已取得的道具名稱

# --- 獲得道具時跳出的提示（圖案＋文字，過一段時間自動消失）---
ITEM_POPUP_DURATION = 2400 # 顯示的總毫秒數（含淡出）
ITEM_POPUP_FADE = 500 # 最後淡出的毫秒數
item_popup = None # None 表示目前沒有要顯示的提示；有的話是 {'name': 道具名稱, 'start_time': 開始顯示的時間}


def show_item_popup(item_name):
    """觸發「獲得道具」的提示，顯示道具圖案（有的話）跟名稱"""
    global item_popup
    item_popup = {'name': item_name, 'start_time': pygame.time.get_ticks()}


# --- 切換天數／白天晚上時，疊在畫面上短暫顯示的標題卡（毛筆字「第X天白天／晚上」）---
DAY_TITLE_CARD_DURATION = 2600 # 顯示的總毫秒數（含淡入淡出）
DAY_TITLE_CARD_FADE = 500 # 開頭淡入、結尾淡出各佔的毫秒數
day_title_card = None # None 表示目前沒有要顯示的標題卡；有的話是 {'stage': 階段名稱, 'start_time': 開始顯示的時間}


def show_day_title_card(stage_name):
    """觸發「第X天白天／晚上」的標題卡"""
    global day_title_card
    day_title_card = {'stage': stage_name, 'start_time': pygame.time.get_ticks()}

# 每個道具點的位置定義：所在場景、可互動範圍、內含道具、是否已被拾取
item_spots = [
    {
        'scene': 'CARRIAGE_1',
        'rect': pygame.Rect(840, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 60, DOOR_HEIGHT), # 車廂座位上
        'items': ['舊車票'],
        'collected': False,
    },
    {
        'scene': 'CARRIAGE_1',
        'rect': pygame.Rect(1030, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 60, DOOR_HEIGHT), # 舊車票右邊的座位上
        'items': ['車站鑰匙'],
        'collected': False,
    },
    {
        'scene': 'CARRIAGE_1',
        'rect': pygame.Rect(650, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 60, DOOR_HEIGHT), # 車廂座位上
        'items': ['舊報紙'],
        'collected': False,
        'min_day_index': 2, # 第二天白天起才會出現
        'reveal_lines': [
            ("旁白", "報紙記錄：「三年前列車事故造成多人死亡。」"),
            ("旁白", "事故地點：青木站附近。"),
        ],
    },
    {
        'scene': 'COCKPIT',
        'rect': pygame.Rect(340, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 60, DOOR_HEIGHT), # 駕駛室角落
        'items': ['車站員工日誌'],
        'collected': False,
        'requires_item': '舊路線圖', # 要先跟老維修員拿到舊路線圖，日誌才會出現在駕駛室
        'reveal_lines': [
            ("旁白", "員工日誌最後一筆寫著："),
            ("旁白", "「00:17，青木站再次亮燈。」"),
        ],
    },
]


def item_spot_available(spot):
    """判斷道具點目前是否符合出現條件（天數限制、需要先取得的道具等）"""
    if day_night_index < spot.get('min_day_index', 0):
        return False
    requires_item = spot.get('requires_item')
    if requires_item and requires_item not in inventory:
        return False
    return True


def get_item_spot_at(scene, rect):
    """回傳玩家目前所在位置可拾取、且尚未拾取的道具點（沒有則回傳 None）"""
    for spot in item_spots:
        if spot['collected'] or spot['scene'] != scene:
            continue
        if not item_spot_available(spot):
            continue
        if rect.colliderect(spot['rect']):
            return spot
    return None


def get_current_scene_door_at(rect):
    """回傳玩家目前所在位置碰到的門（沒有則回傳 None）"""
    for door_rect in doors.get(current_scene, {}).values():
        if rect.colliderect(door_rect):
            return door_rect
    return None


# --- 駕駛艙操作台細節（按 F 進入細節畫面，改成顯示 operator_day_locked.png／operator_day_unlocked.png）---
CONSOLE_FOCUS_SCENE = 'COCKPIT'
console_cabinet_rect = pygame.Rect(30, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 100, DOOR_HEIGHT) # 操作台下置物櫃

# 操作台細節畫面裡，右下角置物櫃門的範圍，點擊後會聚焦看櫃門特寫（box_locked.png／box_unlocked.png）
console_cabinet_door_rect = pygame.Rect(547, 287, 177, 100)

# 櫃門特寫畫面裡，門上四個孔洞的位置，每個都蓋著一顆螺絲（box_screw_icon），要有螺絲起子才能點擊轉開
console_box_screw_positions = [(447, 142), (439, 173), (439, 236), (446, 273)]
console_box_screw_rects = []
for _screw_pos in console_box_screw_positions:
    _screw_rect = pygame.Rect(0, 0, 32, 32)
    _screw_rect.center = _screw_pos
    console_box_screw_rects.append(_screw_rect)
console_box_screws = [True, True, True, True] # True 表示該孔洞的螺絲還在，尚未被轉開
console_box_unlocked = False # 四顆螺絲都被轉開後才會變 True，畫面換成 box_unlocked.png

# 櫃門解鎖後，裡面的《夜間行駛生存指南》擺放的位置
console_box_guide_pos = (484, 275)
console_box_guide_rect = pygame.Rect(0, 0, 70, 70)
console_box_guide_rect.center = console_box_guide_pos


# --- 駕駛室的櫃子（按 F 進去看櫃子內部，裡面有老式手電筒、工具間鑰匙可以拿，再按 F 離開）---
DRIVE_CABINET_SCENE = 'COCKPIT'
drive_cabinet_interact_rect = pygame.Rect(0, HEIGHT - FLOOR_HEIGHT - 180, 100, 180) # 對應背景圖片裡玻璃櫃的位置
drive_cabinet_interact_rect.centerx = 517

FLASHLIGHT_CASE_ITEM_NAME = '老式手電筒'
flashlight_case_pos = (400, 254) # 櫃子內部特寫畫面裡道具擺放的位置
flashlight_case_rect = pygame.Rect(0, 0, 60, 60)
flashlight_case_rect.center = flashlight_case_pos

TOOLROOM_KEY_ITEM_NAME = '工具間鑰匙'
toolroom_key_case_pos = (536, 350) # 櫃子內部特寫畫面裡道具擺放的位置
toolroom_key_case_rect = pygame.Rect(0, 0, 60, 60)
toolroom_key_case_rect.center = toolroom_key_case_pos

# --- 連接處的廁所（按 F 進去看廁所內部，再按 F 離開）---
TOILET_SCENE = 'CONNECTION_2'
toilet_interact_rect = pygame.Rect(0, HEIGHT - FLOOR_HEIGHT - 180, 100, 180) # 對應圖片中間的廁所門
toilet_interact_rect.centerx = CONNECTION_WIDTH // 2

# --- 連接處的工具間（按 F 進去，點工作桌可以看特寫、拿走螺絲起子，按 F 逐層退出）---
TOOLROOM_SCENE = 'CONNECTION_3'
toolroom_interact_rect = pygame.Rect(0, HEIGHT - FLOOR_HEIGHT - 180, 100, 180) # 對應圖片中間的工具間門
toolroom_interact_rect.centerx = CONNECTION_WIDTH // 2

work_table_rect = pygame.Rect(309, 129, 214, 197) # 工具間畫面裡工作桌的範圍，滑鼠點擊用
SCREWDRIVER_TABLE_ITEM_NAME = '維修員留下的螺絲起子'
screwdriver_table_pos = (367, 225) # 螺絲起子特寫畫面裡道具擺放的位置
screwdriver_table_rect = pygame.Rect(0, 0, 90, 90) # 圖示放大1.5倍（60->90），互動範圍跟著放大
screwdriver_table_rect.center = screwdriver_table_pos


def draw_hover_glow(rect, mouse_pos, color=(255, 240, 150)):
    """如果滑鼠停在 rect 上，在它周圍畫一圈柔和的亮光，提示這裡可以點擊互動"""
    if not rect.collidepoint(mouse_pos):
        return
    glow = pygame.Surface((rect.width + 44, rect.height + 44), pygame.SRCALPHA)
    center = glow.get_rect().center
    for scale, alpha in ((1.4, 35), (1.22, 65), (1.08, 100)):
        glow_rect = pygame.Rect(0, 0, round(rect.width * scale), round(rect.height * scale))
        glow_rect.center = center
        pygame.draw.rect(glow, (*color, alpha), glow_rect, border_radius=14)
    screen.blit(glow, glow.get_rect(center=rect.center))


def draw_simple_button(rect, text, bg_color):
    """畫一個簡單的文字方塊按鈕（背景色＋白色邊框＋置中文字）"""
    pygame.draw.rect(screen, bg_color, rect)
    pygame.draw.rect(screen, WHITE, rect, 2)
    text_surf = font_small.render(text, True, WHITE)
    screen.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))


def draw_volume_slider(track_rect):
    """畫音量滑桿：左邊「音量」文字、中間滑軌（紅色部分代表目前音量）、右邊百分比數字"""
    label_surf = font_small.render("音量", True, WHITE)
    screen.blit(label_surf, (track_rect.x - label_surf.get_width() - 10, track_rect.centery - label_surf.get_height() // 2))

    pygame.draw.rect(screen, DARK_GRAY, track_rect, border_radius=track_rect.height // 2)
    fill_width = round(track_rect.width * music_volume)
    if fill_width > 0:
        fill_rect = pygame.Rect(track_rect.x, track_rect.y, fill_width, track_rect.height)
        pygame.draw.rect(screen, RED, fill_rect, border_radius=track_rect.height // 2)

    knob_center = (track_rect.x + fill_width, track_rect.centery)
    pygame.draw.circle(screen, WHITE, knob_center, 9)
    pygame.draw.circle(screen, BLACK, knob_center, 9, 2)

    percent_surf = font_small.render(f"{round(music_volume * 100)}%", True, WHITE)
    screen.blit(percent_surf, (track_rect.right + 10, track_rect.centery - percent_surf.get_height() // 2))


dragging_volume_slider = False # 滑鼠是否正按著音量滑桿拖曳中


def set_volume_from_x(track_rect, x):
    """依照滑鼠目前的 x 座標換算音量（超出滑軌範圍就夾在 0~1 之間）"""
    global music_volume
    ratio = (x - track_rect.x) / track_rect.width
    music_volume = max(0.0, min(1.0, ratio))
    pygame.mixer.music.set_volume(music_volume)


def handle_volume_slider_mousedown(track_rect, mouse_pos):
    """如果點下的位置落在滑桿（含一點誤差範圍）上，立刻設定音量、並開始拖曳，回傳是否有點中"""
    global dragging_volume_slider
    hit_rect = track_rect.inflate(20, 20) # 稍微加大可點擊範圍，滑桿本身很細，太難點中
    if not hit_rect.collidepoint(mouse_pos):
        return False
    set_volume_from_x(track_rect, mouse_pos[0])
    dragging_volume_slider = True
    return True


def draw_start_screen():
    """繪製遊戲開始畫面"""
    if cover_img:
        screen.blit(cover_img, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
    else:
        screen.fill(BLACK)

    if title_img:
        screen.blit(title_img, (WIDTH // 2 - title_img.get_width() // 2, 15))
    else:
        title_surf = font_title.render("軌遇", True, WHITE)
        screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 2 - 130))

    #subtitle_surf = font_small.render("列車長模擬器", True, GRAY)
    #screen.blit(subtitle_surf, (WIDTH // 2 - subtitle_surf.get_width() // 2, HEIGHT // 2 - 55))

    if start_game_img:
        screen.blit(start_game_img, start_button_rect)
    else:
        pygame.draw.rect(screen, RED, start_button_rect)
        pygame.draw.rect(screen, WHITE, start_button_rect, 3)
        start_text_surf = font.render("開始遊戲", True, WHITE)
        screen.blit(start_text_surf, (start_button_rect.centerx - start_text_surf.get_width() // 2,
                                      start_button_rect.centery - start_text_surf.get_height() // 2))

    if setting_img:
        screen.blit(setting_img, settings_button_rect)
    else:
        draw_simple_button(settings_button_rect, "設定", DARK_GRAY)

    if exit_game_img:
        screen.blit(exit_game_img, exit_button_rect)
    else:
        pygame.draw.rect(screen, DARK_GRAY, exit_button_rect)
        pygame.draw.rect(screen, WHITE, exit_button_rect, 3)
        exit_text_surf = font.render("退出遊戲", True, WHITE)
        screen.blit(exit_text_surf, (exit_button_rect.centerx - exit_text_surf.get_width() // 2,
                                     exit_button_rect.centery - exit_text_surf.get_height() // 2))


def draw_pause_menu():
    """繪製按 ESC 跳出的選單（繼續遊玩／返回主頁）"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    title_surf = font.render("已暫停", True, WHITE)
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 2 - 110))

    if continue_game_img:
        screen.blit(continue_game_img, resume_button_rect)
    else:
        pygame.draw.rect(screen, RED, resume_button_rect)
        pygame.draw.rect(screen, WHITE, resume_button_rect, 3)
        resume_text_surf = font.render("繼續遊玩", True, WHITE)
        screen.blit(resume_text_surf, (resume_button_rect.centerx - resume_text_surf.get_width() // 2,
                                       resume_button_rect.centery - resume_text_surf.get_height() // 2))

    if setting_img:
        screen.blit(setting_img, pause_settings_button_rect)
    else:
        draw_simple_button(pause_settings_button_rect, "設定", DARK_GRAY)

    if back_home_img:
        screen.blit(back_home_img, back_to_menu_button_rect)
    else:
        pygame.draw.rect(screen, DARK_GRAY, back_to_menu_button_rect)
        pygame.draw.rect(screen, WHITE, back_to_menu_button_rect, 3)
        back_text_surf = font.render("返回主頁", True, WHITE)
        screen.blit(back_text_surf, (back_to_menu_button_rect.centerx - back_text_surf.get_width() // 2,
                                     back_to_menu_button_rect.centery - back_text_surf.get_height() // 2))


def draw_settings_screen():
    """繪製設定畫面（目前只有音量），從開始畫面或暫停選單的「設定」按鈕進來"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    title_surf = font.render("設定", True, WHITE)
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 2 - 90))

    draw_volume_slider(settings_volume_track_rect)

    draw_simple_button(settings_back_button_rect, "返回", DARK_GRAY)


# 書籤標籤左側（外露那一側）的鋸齒狀撕紙邊緣，固定的一組偏移量，每次畫面都一樣、不會閃爍
TORN_EDGE_JITTER = [0, -3, 4, -2, 3, -4, 2, 0]


def draw_bookmark_tab(rect, active, text):
    """畫一個貼在書本左側的書籤標籤：外側（左邊）是粗糙的撕紙邊緣，內側（右邊）疊進書本裡"""
    steps = len(TORN_EDGE_JITTER) - 1
    left_points = []
    for i, jitter in enumerate(TORN_EDGE_JITTER):
        y = rect.top + rect.height * i / steps
        left_points.append((rect.left + jitter, y))
    points = left_points + [(rect.right, rect.bottom), (rect.right, rect.top)]

    fill_color = (235, 225, 195) if active else (150, 130, 100) # 選中時是米白色書頁色，沒選中時是暗卡其色標籤
    text_color = BLACK if active else (245, 240, 225)
    pygame.draw.polygon(screen, fill_color, points)
    pygame.draw.polygon(screen, BLACK, points, 2)
    text_surf = font_handwriting_small.render(text, True, text_color)
    text_x = rect.centerx - text_surf.get_width() // 2
    text_y = rect.centery - text_surf.get_height() // 2
    screen.blit(text_surf, (text_x, text_y))


def draw_manual_screen():
    """繪製手冊畫面，背景是攤開的筆記本圖片，上方兩個頁籤可切換操作手冊／生存指南"""
    # 半透明背景
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    panel_rect = manual_panel_rect
    if manual_bg_img:
        screen.blit(manual_bg_img, panel_rect)
    else:
        pygame.draw.rect(screen, WHITE, panel_rect)
        pygame.draw.rect(screen, BLACK, panel_rect, 3)

    # 「操作手冊」頁籤（書籤造型）
    draw_bookmark_tab(manual_tab_manual_rect, manual_view == 'MANUAL', "操作手冊")

    # 「生存指南」頁籤（取得指南後才會出現，書籤造型）
    if has_guide:
        draw_bookmark_tab(manual_tab_guide_rect, manual_view == 'GUIDE', "生存指南")

    # 內容區：只用左半頁的寬度，文字太長就換行，不要跨過中間裝訂線延伸到右頁
    content_x = panel_rect.x + round(panel_rect.width * 0.10)
    content_width = round(panel_rect.width * 0.36)
    line_height = 20

    if manual_view == 'GUIDE' and has_guide:
        title_surf = font_handwriting.render("《夜間行駛生存指南》", True, BLACK)
        screen.blit(title_surf, (content_x, panel_rect.y + 24))

        rule_y = panel_rect.y + 68
        for label, rule_text, desc_text in guide_rules:
            label_surf = font_handwriting_small.render(label, True, RED)
            screen.blit(label_surf, (content_x, rule_y))
            rule_y += line_height

            for line in wrap_text(rule_text, font_handwriting_small, content_width):
                line_surf = font_handwriting_small.render(line, True, BLACK)
                screen.blit(line_surf, (content_x, rule_y))
                rule_y += line_height

            for line in wrap_text(desc_text, font_handwriting_small, content_width):
                line_surf = font_handwriting_small.render(line, True, RED)
                screen.blit(line_surf, (content_x, rule_y))
                rule_y += line_height

            rule_y += 8 # 規則之間的間距
    else:
        title_surf = font_handwriting.render("操作手冊", True, BLACK)
        screen.blit(title_surf, (content_x, panel_rect.y + 24))

        instructions = [
            "左右方向鍵 / A D : 左右移動",
            "F : 與場景互動",
            "B : 開啟背包",
            "L : 開關手電筒（需持有手電筒）",
            "TAB : 關閉此手冊",
            "ESC : 開啟選單"
        ]
        for i, text in enumerate(instructions):
            text_surf = font_handwriting_small.render(text, True, BLACK)
            screen.blit(text_surf, (content_x, panel_rect.y + 90 + i * 40))


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
    scene_width = get_scene_width(current_scene)
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, HEIGHT - FLOOR_HEIGHT, scene_width, FLOOR_HEIGHT))

    # 畫上方的行李架
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, 60, scene_width, 15))

    # 根據當前場景繪製特定物件
    if 'CARRIAGE' in current_scene:
        draw_carriage_scene(camera_offset_x, current_scene)
    elif 'CONNECTION' in current_scene:
        draw_connection_scene(camera_offset_x, current_scene)
    elif current_scene == 'COCKPIT':
        draw_cockpit_scene(camera_offset_x)

def draw_carriage_scene(camera_offset_x, scene_name):
    """繪製指定車廂內的物件 (座椅、窗戶、門)"""
    is_day = not DAY_NIGHT_STAGES[day_night_index].endswith('NIGHT')

    # 白天／晚上都使用車廂背景圖片，蓋掉 draw_background 畫的素色牆壁與地板
    # 用兩張完整的圖片並排組成車廂背景（互相重疊幾個像素，蓋掉拼接縫）
    if is_day and train_day_img:
        for tile_index in range(TRAIN_DAY_TILE_COUNT):
            screen.blit(train_day_img, (tile_index * train_day_tile_step - camera_offset_x, 0))
    elif not is_day and train_night_img:
        for tile_index in range(TRAIN_NIGHT_TILE_COUNT):
            screen.blit(train_night_img, (tile_index * train_night_tile_step - camera_offset_x, 0))

    # 畫座椅：依照背景圖片裡窗戶的位置擺放；圖片載入失敗時才用原本繪製的樣式（依車廂實際寬度平均分佈）
    # 車廂一的第一張椅子改由 granny.png 取代、車廂二的第四張椅子改由 little_girl.png 取代、
    # 車廂三的第三張椅子在第二天白天起改由 old_engineer.png 取代
    # （這幾張圖片本身都已經包含椅子），這裡跳過不重複畫
    if is_day and chair_day_img and chair_day_positions:
        for pos in chair_day_positions:
            if scene_name == OLD_LADY_SCENE and pos == GRANNY_CHAIR_X:
                continue
            if scene_name == GIRL_SCENE and pos == GIRL_CHAIR_X:
                continue
            if scene_name == OLD_WORKER_SCENE and day_night_index >= OLD_WORKER_MIN_DAY_INDEX and pos == OLD_WORKER_CHAIR_X:
                continue
            chair_rect = chair_day_img.get_rect()
            chair_rect.midbottom = (pos - camera_offset_x, HEIGHT - FLOOR_HEIGHT + 20)
            screen.blit(chair_day_img, chair_rect)
    elif not is_day and chair_night_img and chair_night_positions:
        # 晚上老太太不出現、不用跳過位置；小女孩、老維修員晚上還在，要跳過對應位置（用容許誤差比對，
        # 因為晚上跟白天的座椅位置是分別計算的，不會完全一樣）
        for pos in chair_night_positions:
            if scene_name == GIRL_SCENE and abs(pos - GIRL_CHAIR_X) < 30:
                continue
            if scene_name == OLD_WORKER_SCENE and day_night_index >= OLD_WORKER_MIN_DAY_INDEX and abs(pos - OLD_WORKER_CHAIR_X) < 30:
                continue
            chair_rect = chair_night_img.get_rect()
            chair_rect.midbottom = (pos - camera_offset_x, HEIGHT - FLOOR_HEIGHT + 20)
            screen.blit(chair_night_img, chair_rect)
    else:
        chair_positions = range(140, CARRIAGE_WIDTH - DOOR_WIDTH - 75, 140)
        for pos in chair_positions:
            draw_side_chair(pos, camera_offset_x)

    # 畫窗戶（車廂背景圖片裡已經畫好窗戶了，不用再另外畫；圖片載入失敗時才依車廂實際寬度平均分佈畫窗戶）
    if not ((is_day and train_day_img) or (not is_day and train_night_img)):
        for x in range(100, CARRIAGE_WIDTH - DOOR_WIDTH - 150, 450):
            win_rect = pygame.Rect(x - camera_offset_x, 100, 150, 100)
            pygame.draw.rect(screen, WHITE, win_rect)
            pygame.draw.rect(screen, BLACK, win_rect, 3)
    # 這節車廂往上一節／下一節場景的門（不畫方塊，但互動邏輯保留在 doors 字典裡）

def draw_cockpit_scene(camera_offset_x):
    """繪製駕駛艙內的物件"""
    if is_daytime():
        # 白天使用駕駛室背景圖片，蓋掉 draw_background 畫的素色牆壁與地板
        # 取得生存指南後，置物櫃已經打開過了，改用 unlocked 版本的背景
        day_img = drive_room_day_unlocked_img if has_guide else drive_room_day_img
        if day_img:
            screen.blit(day_img, (-camera_offset_x, 0))
            return
    if not is_daytime() and drive_room_night_img:
        # 晚上使用駕駛室背景圖片，蓋掉 draw_background 畫的素色牆壁與地板
        screen.blit(drive_room_night_img, (-camera_offset_x, 0))
        return

    # 圖片載入失敗時，改用原本手繪的樣式
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

    # 駕駛艙的出口門（不畫方塊，但互動邏輯保留在 doors 字典裡）

def draw_connection_scene(camera_offset_x, scene_name):
    """繪製連接處的背景圖片：CONNECTION_2 是廁所、CONNECTION_3 是工具間，其他是一般通道。
    圖片寬度跟連接處的世界寬度是同一個值，所以用跟其他場景一樣的攝影機轉換來貼圖，
    圖片邊緣就會剛好對齊往前一節／下一節車廂的門；畫面比世界寬時，左右多出來的地方畫成黑邊。"""
    if scene_name == 'CONNECTION_2':
        connect_img = connect_toilet_day_img
    elif scene_name == 'CONNECTION_3':
        connect_img = connect_toolroom_day_img
    else:
        connect_img = connect_day_img

    if connect_img:
        screen.fill(BLACK)
        screen.blit(connect_img, (-camera_offset_x, 0))
    else:
        # 圖片載入失敗時，改用原本手繪的樣式
        toilet_rect = pygame.Rect(150 - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 180, 100, 180)
        pygame.draw.rect(screen, DARK_GRAY, toilet_rect)
        pygame.draw.rect(screen, BLACK, toilet_rect, 4)
        exit_door_rect = pygame.Rect(CONNECTION_WIDTH / 2 - 60 - camera_offset_x, 80, 120, 250)
        pygame.draw.rect(screen, (50, 50, 80), exit_door_rect)
        pygame.draw.rect(screen, BLACK, exit_door_rect, 4)
    # 往上一節／下一節車廂的門（不畫方塊，但互動邏輯保留在 doors 字典裡）

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
    """繪製老太太 NPC（僅在車廂一場景、且白天時顯示，用 granny.png 取代車廂一的第一張椅子）"""
    if current_scene != OLD_LADY_SCENE or not is_daytime():
        return
    screen_rect = old_lady_rect.move(-camera_offset_x, 0)
    if granny_img:
        screen.blit(granny_img, screen_rect)
    else:
        pygame.draw.rect(screen, PURPLE, screen_rect)
        pygame.draw.circle(screen, PURPLE, (screen_rect.centerx, screen_rect.top - 15), 15) # 頭部


def draw_girl(camera_offset_x):
    """繪製小女孩 NPC（僅在車廂二場景顯示，用 little_girl.png 取代車廂二的第四張椅子）"""
    if current_scene != GIRL_SCENE:
        return
    screen_rect = girl_rect.move(-camera_offset_x, 0)
    if little_girl_img:
        screen.blit(little_girl_img, screen_rect)
    else:
        pygame.draw.rect(screen, PINK, screen_rect)
        pygame.draw.circle(screen, PINK, (screen_rect.centerx, screen_rect.top - 12), 12) # 頭部


def draw_old_worker(camera_offset_x):
    """繪製老維修員 NPC（第二天白天起，僅在車廂三場景顯示，用 old_engineer.png 取代車廂三的第三張椅子）"""
    if current_scene != OLD_WORKER_SCENE or day_night_index < OLD_WORKER_MIN_DAY_INDEX:
        return
    screen_rect = old_worker_rect.move(-camera_offset_x, 0)
    if old_engineer_img:
        screen.blit(old_engineer_img, screen_rect)
    else:
        pygame.draw.rect(screen, WORKER_COLOR, screen_rect)
        pygame.draw.circle(screen, WORKER_COLOR, (screen_rect.centerx, screen_rect.top - 15), 15) # 頭部


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
        if not item_spot_available(spot):
            continue
        marker_rect = pygame.Rect(0, 0, 26, 26)
        marker_rect.center = (spot['rect'].centerx - camera_offset_x, HEIGHT - FLOOR_HEIGHT - 30)
        icon = ITEM_MARKER_ICONS.get(spot['items'][0]) if spot['items'] else None
        if icon:
            pygame.draw.rect(screen, BLACK, marker_rect, 2)
            screen.blit(icon, icon.get_rect(center=marker_rect.center))
        else:
            pygame.draw.rect(screen, GOLD, marker_rect)
            pygame.draw.rect(screen, BLACK, marker_rect, 2)


def draw_console_focus():
    """繪製操作台細節畫面（operator_day_locked.png／operator_day_unlocked.png），
    可以點擊右下角櫃門聚焦看櫃門特寫"""
    screen.fill(BLACK)
    bg_img = operator_day_unlocked_img if console_box_unlocked else operator_day_locked_img
    if bg_img:
        screen.blit(bg_img, (0, 0))

    mouse_pos = to_logical_pos(pygame.mouse.get_pos())
    draw_hover_glow(console_cabinet_door_rect, mouse_pos)

    draw_bottom_f_hint("點擊右下角櫃門查看・F : 離開細節畫面")


def draw_box_view():
    """繪製置物櫃門的特寫畫面：鎖著時要用螺絲起子點掉四顆螺絲才能打開，
    打開後（box_unlocked.png）可以點擊裡面的《夜間行駛生存指南》拾取"""
    screen.fill(BLACK)
    mouse_pos = to_logical_pos(pygame.mouse.get_pos())

    if not console_box_unlocked:
        if box_locked_img:
            screen.blit(box_locked_img, (0, 0))
        has_screwdriver = SCREWDRIVER_TABLE_ITEM_NAME in inventory
        for screw_pos, screw_present, screw_rect in zip(console_box_screw_positions, console_box_screws, console_box_screw_rects):
            if screw_present and has_screwdriver:
                draw_hover_glow(screw_rect, mouse_pos)
            if screw_present and box_screw_icon:
                screen.blit(box_screw_icon, box_screw_icon.get_rect(center=screw_pos))
        if has_screwdriver:
            hint_text = "點擊螺絲用起子轉開・F : 離開"
        else:
            hint_text = "螺絲鎖得很緊，需要螺絲起子才能轉開・F : 離開"
    else:
        if box_unlocked_img:
            screen.blit(box_unlocked_img, (0, 0))
        if not has_guide:
            draw_hover_glow(console_box_guide_rect, mouse_pos)
            guide_icon = ITEM_ICONS.get('《夜間行駛生存指南》')
            if guide_icon:
                screen.blit(guide_icon, guide_icon.get_rect(center=console_box_guide_pos))
            hint_text = "點擊《夜間行駛生存指南》拾取・F : 離開"
        else:
            hint_text = "F : 離開"

    draw_bottom_f_hint(hint_text)


def draw_bottom_f_hint(text):
    """在畫面底部畫一個半透明黑底的提示文字（例如「F : 離開」）"""
    hint_surf = font_small.render(text, True, WHITE)
    hint_bg_rect = pygame.Rect(0, 0, hint_surf.get_width() + 24, hint_surf.get_height() + 16)
    hint_bg_rect.centerx = WIDTH // 2
    hint_bg_rect.bottom = HEIGHT - 15
    hint_bg = pygame.Surface(hint_bg_rect.size, pygame.SRCALPHA)
    hint_bg.fill((0, 0, 0, 170))
    screen.blit(hint_bg, hint_bg_rect)
    screen.blit(hint_surf, (hint_bg_rect.centerx - hint_surf.get_width() // 2, hint_bg_rect.centery - hint_surf.get_height() // 2))


def draw_toilet_view():
    """繪製走進廁所後看到的畫面，底部顯示按 F 離開的提示"""
    if toilet_img:
        screen.blit(toilet_img, (0, 0))
    else:
        screen.fill(BLACK)
    draw_bottom_f_hint("F : 離開廁所")


def draw_toolroom_view():
    """繪製走進工具間後看到的畫面，可以用滑鼠點工作桌看特寫，底部顯示按 F 離開的提示"""
    if toolroom_img:
        screen.blit(toolroom_img, (0, 0))
    else:
        screen.fill(BLACK)
    draw_hover_glow(work_table_rect, to_logical_pos(pygame.mouse.get_pos()))
    draw_bottom_f_hint("F : 離開工具間")


def draw_tooltable_view():
    """繪製工作桌特寫畫面，桌上如果還沒被拿走就顯示螺絲起子，底部顯示按 F 離開的提示"""
    if tooltable_img:
        screen.blit(tooltable_img, (0, 0))
    else:
        screen.fill(BLACK)

    if SCREWDRIVER_TABLE_ITEM_NAME not in inventory:
        draw_hover_glow(screwdriver_table_rect, to_logical_pos(pygame.mouse.get_pos()))
        icon = ITEM_ICONS.get(SCREWDRIVER_TABLE_ITEM_NAME)
        if icon:
            big_icon = pygame.transform.smoothscale(icon, (round(icon.get_width() * 1.5), round(icon.get_height() * 1.5)))
            screen.blit(big_icon, big_icon.get_rect(center=screwdriver_table_pos))
        else:
            pygame.draw.rect(screen, GOLD, screwdriver_table_rect)
            pygame.draw.rect(screen, BLACK, screwdriver_table_rect, 2)

    draw_bottom_f_hint("F : 離開工作桌")


def draw_case_view():
    """繪製駕駛室櫃子內部的特寫畫面（置中顯示、左右保留黑邊），
    櫃子裡如果還沒被拿走就顯示老式手電筒、工具間鑰匙，底部顯示按 F 離開的提示"""
    screen.fill(BLACK)
    if case_img:
        screen.blit(case_img, ((WIDTH - case_img.get_width()) // 2, 0))

    mouse_pos = to_logical_pos(pygame.mouse.get_pos())
    for item_name, pos, fallback_rect in (
        (FLASHLIGHT_CASE_ITEM_NAME, flashlight_case_pos, flashlight_case_rect),
        (TOOLROOM_KEY_ITEM_NAME, toolroom_key_case_pos, toolroom_key_case_rect),
    ):
        if item_name in inventory:
            continue
        draw_hover_glow(fallback_rect, mouse_pos)
        icon = ITEM_ICONS.get(item_name)
        if icon:
            screen.blit(icon, icon.get_rect(center=pos))
        else:
            pygame.draw.rect(screen, GOLD, fallback_rect)
            pygame.draw.rect(screen, BLACK, fallback_rect, 2)

    draw_bottom_f_hint("F : 離開櫃子")


def draw_item_popup():
    """如果剛獲得道具，畫出圖案＋文字的提示卡片，過一段時間會自動淡出消失"""
    global item_popup
    if item_popup is None:
        return
    elapsed = pygame.time.get_ticks() - item_popup['start_time']
    if elapsed >= ITEM_POPUP_DURATION:
        item_popup = None
        return

    fade_start = ITEM_POPUP_DURATION - ITEM_POPUP_FADE
    alpha = 255 if elapsed <= fade_start else max(0, round(255 * (ITEM_POPUP_DURATION - elapsed) / ITEM_POPUP_FADE))

    name = item_popup['name']
    icon = ITEM_ICONS.get(name)
    icon_surf = None
    if icon:
        icon_size = 64
        scale = min(icon_size / icon.get_width(), icon_size / icon.get_height())
        icon_surf = pygame.transform.smoothscale(icon, (max(1, round(icon.get_width() * scale)), max(1, round(icon.get_height() * scale))))

    label_surf = font_small.render("獲得道具", True, (230, 200, 120))
    name_surf = font.render(name, True, WHITE)
    text_width = max(label_surf.get_width(), name_surf.get_width())
    text_height = label_surf.get_height() + name_surf.get_height() + 4

    padding = 14
    icon_area_width = (icon_surf.get_width() + padding) if icon_surf else 0
    card_width = padding * 2 + icon_area_width + text_width
    card_height = padding * 2 + max(icon_surf.get_height() if icon_surf else 0, text_height)

    card = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
    pygame.draw.rect(card, (20, 20, 20, 220), card.get_rect(), border_radius=10)
    pygame.draw.rect(card, (230, 200, 120, 255), card.get_rect(), 2, border_radius=10)

    if icon_surf:
        card.blit(icon_surf, (padding, (card_height - icon_surf.get_height()) // 2))
    text_x = padding + icon_area_width
    text_y = (card_height - text_height) // 2
    card.blit(label_surf, (text_x, text_y))
    card.blit(name_surf, (text_x, text_y + label_surf.get_height() + 4))

    card.set_alpha(alpha)
    card_rect = card.get_rect(midtop=(WIDTH // 2, 60))
    screen.blit(card, card_rect)


def draw_day_title_card():
    """如果剛切換天數／白天晚上，畫出「第X天白天／晚上」的毛筆字標題卡，淡入顯示一段時間後淡出消失"""
    global day_title_card
    if day_title_card is None:
        return
    elapsed = pygame.time.get_ticks() - day_title_card['start_time']
    if elapsed >= DAY_TITLE_CARD_DURATION:
        day_title_card = None
        return

    if elapsed < DAY_TITLE_CARD_FADE:
        alpha = round(255 * elapsed / DAY_TITLE_CARD_FADE)
    elif elapsed > DAY_TITLE_CARD_DURATION - DAY_TITLE_CARD_FADE:
        alpha = round(255 * (DAY_TITLE_CARD_DURATION - elapsed) / DAY_TITLE_CARD_FADE)
    else:
        alpha = 255

    # 白天版的圖片是黑色毛筆字，要用亮色背景才看得清楚；晚上版是白色毛筆字，要用暗色背景
    is_night_stage = day_title_card['stage'].endswith('NIGHT')
    overlay_color = (0, 0, 0) if is_night_stage else (245, 240, 225)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((*overlay_color, round(140 * alpha / 255)))
    screen.blit(overlay, (0, 0))

    img = day_title_images.get(day_title_card['stage'])
    if img:
        img_copy = img.copy()
        img_copy.set_alpha(alpha)
        screen.blit(img_copy, img_copy.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    else:
        text_color = WHITE if is_night_stage else BLACK
        label_surf = font.render(DAY_NIGHT_LABELS.get(day_title_card['stage'], ''), True, text_color)
        label_surf.set_alpha(alpha)
        screen.blit(label_surf, label_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))


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


def draw_flashlight_hint():
    """如果玩家持有手電筒，在左上角顯示目前開關狀態"""
    if '老式手電筒' not in inventory:
        return
    status_text = "手電筒：開啟" if flashlight_on else "手電筒：關閉"
    hint_text_surf = font_small.render(status_text, True, WHITE)
    hint_rect = hint_text_surf.get_rect()
    hint_bg_rect = pygame.Rect(0, 0, hint_rect.width + 20, hint_rect.height + 12)
    hint_bg_rect.topleft = (15, 55)
    hint_bg = pygame.Surface(hint_bg_rect.size, pygame.SRCALPHA)
    hint_bg.fill((200, 160, 60, 170) if flashlight_on else (0, 0, 0, 150))
    screen.blit(hint_bg, hint_bg_rect)
    screen.blit(hint_text_surf, (hint_bg_rect.centerx - hint_rect.width // 2, hint_bg_rect.centery - hint_rect.height // 2))


def draw_night_overlay():
    """如果目前階段是晚上，在畫面上疊加一層半透明深藍色營造夜晚氛圍"""
    if not DAY_NIGHT_STAGES[day_night_index].endswith('NIGHT'):
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(NIGHT_OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))


def draw_lights_out_overlay(camera_offset_x):
    """列車燈光熄滅期間，疊加更深的黑暗效果；若手電筒開啟則照亮角色前方"""
    if not lights_out:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))

    if flashlight_on and '老式手電筒' in inventory:
        origin_x = conductor_rect.centerx - camera_offset_x
        origin_y = conductor_rect.centery
        direction = 1 if facing_direction == 'RIGHT' else -1
        cone_length = 220
        cone_half_width = 90

        light_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cone_points = [
            (origin_x, origin_y - 20),
            (origin_x + direction * cone_length, origin_y - cone_half_width),
            (origin_x + direction * cone_length, origin_y + cone_half_width),
            (origin_x, origin_y + 20),
        ]
        pygame.draw.polygon(light_surf, (255, 255, 255, 190), cone_points)
        pygame.draw.circle(light_surf, (255, 255, 255, 210), (origin_x, origin_y), 45)
        overlay.blit(light_surf, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    screen.blit(overlay, (0, 0))


def draw_lights_out_hint():
    """第一天晚上事件期間，依目前階段顯示對應的任務指引：
    巡視車廂 → （走到第五節車廂熄燈後）打開手電筒 → 返回駕駛室"""
    if night1_patrol_active:
        task_text = "任務：巡視車廂"
    elif lights_out and not flashlight_on:
        task_text = "任務：打開手電筒"
    elif lights_out:
        task_text = "任務：返回駕駛室"
    else:
        return
    hint_text_surf = font_small.render(task_text, True, WHITE)
    hint_rect = hint_text_surf.get_rect()
    hint_bg_rect = pygame.Rect(0, 0, hint_rect.width + 24, hint_rect.height + 14)
    hint_bg_rect.midtop = (WIDTH // 2, 58)
    hint_bg = pygame.Surface(hint_bg_rect.size, pygame.SRCALPHA)
    hint_bg.fill((120, 0, 0, 190))
    screen.blit(hint_bg, hint_bg_rect)
    screen.blit(hint_text_surf, (hint_bg_rect.centerx - hint_rect.width // 2, hint_bg_rect.centery - hint_rect.height // 2))


def draw_time_label():
    """在畫面上方顯示目前是第幾天的白天／晚上（純顯示用，不能點擊切換）"""
    current_stage = DAY_NIGHT_STAGES[day_night_index]
    is_night = current_stage.endswith('NIGHT')
    label_bg_color = (200, 160, 60) if is_night else (70, 90, 160)

    label_surf = font_small.render(DAY_NIGHT_LABELS[current_stage], True, WHITE)
    label_bg_rect = pygame.Rect(0, 0, label_surf.get_width() + 24, label_surf.get_height() + 14)
    label_bg_rect.midtop = (WIDTH // 2, 15)
    label_bg = pygame.Surface(label_bg_rect.size, pygame.SRCALPHA)
    label_bg.fill((*label_bg_color, 190))
    screen.blit(label_bg, label_bg_rect)
    screen.blit(label_surf, (label_bg_rect.centerx - label_surf.get_width() // 2,
                             label_bg_rect.centery - label_surf.get_height() // 2))


def wrap_text(text, render_font, max_width):
    """依照可用寬度，把文字切成一行一行的列表（超出寬度就換行）"""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if render_font.size(test_line)[0] <= max_width or not current_line:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines


def draw_dialogue_box():
    """繪製對話框（縮小成一半大小、圓角、手寫字體），顯示目前這句台詞（超過文字框寬度會自動換行）"""
    speaker, text = dialogue_lines[dialogue_index]

    box_width = WIDTH - 120
    line_height = 22
    lines = wrap_text(text, font_dialogue, box_width - 28)
    box_height = max(60, 34 + len(lines) * line_height + 10)
    box_rect = pygame.Rect(60, HEIGHT - 40 - box_height, box_width, box_height)

    pygame.draw.rect(screen, WHITE, box_rect, border_radius=16)
    pygame.draw.rect(screen, BLACK, box_rect, 2, border_radius=16)

    name_surf = font_dialogue_small.render(speaker, True, SPEAKER_COLORS.get(speaker, BLACK))
    screen.blit(name_surf, (box_rect.x + 14, box_rect.y + 8))

    for i, line in enumerate(lines):
        line_surf = font_dialogue.render(line, True, BLACK)
        screen.blit(line_surf, (box_rect.x + 14, box_rect.y + 30 + i * line_height))

    hint_surf = font_dialogue_small.render("F : 繼續", True, DARK_GRAY)
    screen.blit(hint_surf, (box_rect.right - hint_surf.get_width() - 10, box_rect.bottom - hint_surf.get_height() - 6))


def draw_night1_choice():
    """繪製第一天晚上「開門／不開門」的選擇畫面"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    prompt_surf = font.render("要打開駕駛室的門嗎？", True, WHITE)
    screen.blit(prompt_surf, (WIDTH // 2 - prompt_surf.get_width() // 2, HEIGHT // 2 - 60))

    pygame.draw.rect(screen, RED, night1_choice_open_rect)
    pygame.draw.rect(screen, BLACK, night1_choice_open_rect, 3)
    open_surf = font_small.render("開門", True, WHITE)
    screen.blit(open_surf, (night1_choice_open_rect.centerx - open_surf.get_width() // 2,
                            night1_choice_open_rect.centery - open_surf.get_height() // 2))

    pygame.draw.rect(screen, (70, 90, 160), night1_choice_close_rect)
    pygame.draw.rect(screen, BLACK, night1_choice_close_rect, 3)
    close_surf = font_small.render("不開門", True, WHITE)
    screen.blit(close_surf, (night1_choice_close_rect.centerx - close_surf.get_width() // 2,
                             night1_choice_close_rect.centery - close_surf.get_height() // 2))


def draw_game_over_screen():
    """繪製 Game Over 畫面"""
    screen.fill(BLACK)

    title_surf = font.render("GAME OVER", True, RED)
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 2 - 60))

    reason_surf = font_small.render(game_over_reason, True, WHITE)
    screen.blit(reason_surf, (WIDTH // 2 - reason_surf.get_width() // 2, HEIGHT // 2))

    hint_surf = font_small.render("按 R 重新開始", True, GRAY)
    screen.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, HEIGHT // 2 + 40))


def draw_story_choice():
    """繪製通用的「A / B」二選一選擇畫面"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    prompt_surf = font.render(choice_prompt, True, WHITE)
    screen.blit(prompt_surf, (WIDTH // 2 - prompt_surf.get_width() // 2, HEIGHT // 2 - 60))

    pygame.draw.rect(screen, RED, choice_rect_a)
    pygame.draw.rect(screen, BLACK, choice_rect_a, 3)
    label_a_surf = font_small.render(choice_label_a, True, WHITE)
    screen.blit(label_a_surf, (choice_rect_a.centerx - label_a_surf.get_width() // 2,
                               choice_rect_a.centery - label_a_surf.get_height() // 2))

    pygame.draw.rect(screen, (70, 90, 160), choice_rect_b)
    pygame.draw.rect(screen, BLACK, choice_rect_b, 3)
    label_b_surf = font_small.render(choice_label_b, True, WHITE)
    screen.blit(label_b_surf, (choice_rect_b.centerx - label_b_surf.get_width() // 2,
                               choice_rect_b.centery - label_b_surf.get_height() // 2))


def reset_game():
    """重置遊戲進度，回到最初始狀態"""
    global current_scene, game_state, camera_x
    global day_night_index, day1_night_triggered, day1_night_resolved, day2_night_triggered, lights_out
    global night1_pending_intro, night1_patrol_active
    global flashlight_on, facing_direction
    global has_guide, has_girl_painting, has_talked_to_old_lady, active_npc, manual_view
    global dialogue_lines, dialogue_index, game_over_reason, intro_monologue_shown
    global console_box_screws, console_box_unlocked

    conductor_rect.x = COCKPIT_WIDTH - DOOR_WIDTH - CONDUCTOR_SIZE - 10
    conductor_rect.y = HEIGHT - FLOOR_HEIGHT - CONDUCTOR_SIZE + CONDUCTOR_Y_OFFSET
    current_scene = 'COCKPIT'
    game_state = 'START'
    camera_x = 0

    day_night_index = 0
    day1_night_triggered = False
    day1_night_resolved = False
    day2_night_triggered = False
    night1_pending_intro = False
    night1_patrol_active = False
    lights_out = False
    flashlight_on = False
    facing_direction = 'RIGHT'
    game_over_reason = ""

    has_guide = False
    has_girl_painting = False
    has_talked_to_old_lady = False
    intro_monologue_shown = False
    active_npc = None
    manual_view = 'MANUAL'
    dialogue_lines = []
    dialogue_index = 0

    inventory.clear()

    for spot in item_spots:
        spot['collected'] = False

    console_box_screws = [True, True, True, True]
    console_box_unlocked = False


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
    """如果玩家靠近可互動的門或 NPC，在角色上方顯示按 F 互動的提示。
    燈光熄滅期間完全不顯示互動提示；就算手電筒打開了，也只顯示車廂門的提示（其他都不能互動）"""
    scene_doors = doors.get(current_scene, {})
    interactables = list(scene_doors.values())
    if lights_out and not flashlight_on:
        interactables = []
    elif not lights_out:
        if current_scene == OLD_LADY_SCENE and is_daytime():
            interactables.append(old_lady_interact_rect)
        if current_scene == GIRL_SCENE:
            interactables.append(girl_interact_rect)
        if current_scene == OLD_WORKER_SCENE and day_night_index >= OLD_WORKER_MIN_DAY_INDEX:
            interactables.append(old_worker_interact_rect)
        for spot in item_spots:
            if spot['scene'] == current_scene and not spot['collected'] and item_spot_available(spot):
                interactables.append(spot['rect'])
        if current_scene == CONSOLE_FOCUS_SCENE:
            interactables.append(console_cabinet_rect)
        if current_scene == DRIVE_CABINET_SCENE:
            interactables.append(drive_cabinet_interact_rect)
        if current_scene == TOILET_SCENE:
            interactables.append(toilet_interact_rect)
        if current_scene == TOOLROOM_SCENE:
            interactables.append(toolroom_interact_rect)

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
dt = 0 # 每一幀經過的毫秒數，供走路動畫計時使用
running = True
previous_game_state = None # 用來偵測是否剛進入／離開主頁，藉此開關背景音樂
while running:
    if start_menu_music_loaded:
        if game_state == 'START' and previous_game_state != 'START':
            pygame.mixer.music.play(-1) # 迴圈播放，音樂檔本身就是26秒的循環
        elif game_state != 'START' and previous_game_state == 'START':
            pygame.mixer.music.stop()
    previous_game_state = game_state

    if game_state == 'START':
        # --- 開始畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if start_button_rect.collidepoint(mouse_pos):
                    game_state = 'MANUAL'
                elif settings_button_rect.collidepoint(mouse_pos):
                    settings_return_state = 'START'
                    game_state = 'SETTINGS'
                elif exit_button_rect.collidepoint(mouse_pos):
                    running = False

        draw_start_screen()

    elif game_state == 'SETTINGS':
        # --- 設定畫面的事件與繪圖（音量滑桿＋返回鍵，畫在原本畫面上方） ---
        if settings_return_state == 'START':
            draw_start_screen()
        else:
            draw_background(camera_x)
            draw_old_lady(camera_x)
            draw_girl(camera_x)
            draw_old_worker(camera_x)
            draw_item_spots(camera_x)
            draw_conductor(screen, conductor_rect, conductor_img, camera_x)
            draw_night_overlay()
            draw_pause_menu()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = settings_return_state
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if handle_volume_slider_mousedown(settings_volume_track_rect, mouse_pos):
                    pass
                elif settings_back_button_rect.collidepoint(mouse_pos):
                    game_state = settings_return_state
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_volume_slider = False
            if event.type == pygame.MOUSEMOTION and dragging_volume_slider:
                set_volume_from_x(settings_volume_track_rect, to_logical_pos(event.pos)[0])

        draw_settings_screen()

    elif game_state == 'MANUAL':
        # --- 手冊狀態的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    if not intro_monologue_shown:
                        # 第一次關閉手冊，先播放主角的開場自白，播完才進入遊戲
                        intro_monologue_shown = True
                        dialogue_lines = intro_monologue_lines
                        dialogue_index = 0
                        active_npc = 'INTRO'
                        game_state = 'DIALOGUE'
                    elif night1_pending_intro:
                        # 剛拿到生存指南、已經切到第一天晚上，關掉手冊後接著播放晚上的開場劇情
                        night1_pending_intro = False
                        dialogue_lines = night1_intro_lines
                        dialogue_index = 0
                        active_npc = 'NIGHT1_INTRO'
                        game_state = 'DIALOGUE'
                    else:
                        game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if manual_tab_manual_rect.collidepoint(mouse_pos):
                    manual_view = 'MANUAL'
                elif has_guide and manual_tab_guide_rect.collidepoint(mouse_pos):
                    manual_view = 'GUIDE'

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
                if event.key == pygame.K_ESCAPE:
                    game_state = 'PAUSE_MENU'
                if event.key == pygame.K_TAB:
                    game_state = 'MANUAL'
                if event.key == pygame.K_b:
                    game_state = 'INVENTORY'
                if event.key == pygame.K_l and '老式手電筒' in inventory:
                    flashlight_on = not flashlight_on
                if event.key == pygame.K_f and not lights_out and current_scene == OLD_LADY_SCENE and is_daytime() and conductor_rect.colliderect(old_lady_interact_rect):
                    # 與老太太互動，開始對話（聊過一次之後改播重複對話）
                    dialogue_lines = old_lady_dialogue_repeat if has_talked_to_old_lady else old_lady_dialogue
                    dialogue_index = 0
                    active_npc = 'OLD_LADY'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and not lights_out and current_scene == GIRL_SCENE and conductor_rect.colliderect(girl_interact_rect):
                    # 與小女孩互動，開始對話（已經拿過畫的話改播重複對話）
                    dialogue_lines = girl_dialogue_repeat if has_girl_painting else girl_dialogue
                    dialogue_index = 0
                    active_npc = 'GIRL'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and not lights_out and current_scene == OLD_WORKER_SCENE and day_night_index >= OLD_WORKER_MIN_DAY_INDEX and conductor_rect.colliderect(old_worker_interact_rect):
                    # 與老維修員互動，開始對話
                    dialogue_lines = build_old_worker_dialogue()
                    dialogue_index = 0
                    active_npc = 'OLD_WORKER'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and not lights_out and get_item_spot_at(current_scene, conductor_rect) is not None:
                    # 撿拾道具
                    item_spot = get_item_spot_at(current_scene, conductor_rect)
                    inventory.extend(item_spot['items'])
                    show_item_popup(item_spot['items'][-1])
                    item_spot['collected'] = True
                    pickup_line = (" ", f"獲得了「{ '、'.join(item_spot['items']) }」。")
                    dialogue_lines = item_spot.get('reveal_lines', []) + [pickup_line]
                    dialogue_index = 0
                    # 拿到車站員工日誌後要接著切到第二天晚上，其餘道具照舊撿完直接回到遊戲
                    active_npc = 'STAFF_LOG_PICKUP' if '車站員工日誌' in item_spot['items'] else None
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and not lights_out and current_scene == CONSOLE_FOCUS_SCENE and conductor_rect.colliderect(console_cabinet_rect):
                    # 聚焦查看操作台置物櫃細節
                    game_state = 'CONSOLE_FOCUS'
                elif event.key == pygame.K_f and not lights_out and current_scene == DRIVE_CABINET_SCENE and conductor_rect.colliderect(drive_cabinet_interact_rect):
                    # 查看駕駛室櫃子內部
                    game_state = 'CASE_VIEW'
                elif event.key == pygame.K_f and not lights_out and current_scene == TOILET_SCENE and conductor_rect.colliderect(toilet_interact_rect):
                    # 走進廁所
                    game_state = 'TOILET_VIEW'
                elif event.key == pygame.K_f and not lights_out and current_scene == TOOLROOM_SCENE and conductor_rect.colliderect(toolroom_interact_rect):
                    if TOOLROOM_KEY_ITEM_NAME in inventory:
                        # 走進工具間
                        game_state = 'TOOLROOM_VIEW'
                    else:
                        dialogue_lines = [(" ", "門鎖住了，需要工具間鑰匙才能進去。")]
                        dialogue_index = 0
                        active_npc = None
                        game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and lights_out and not flashlight_on:
                    # 燈光熄滅、手電筒還沒打開時，完全無法互動（包含開門），也不顯示任何提示
                    pass
                elif event.key == pygame.K_f:
                    # 場景切換邏輯：依 SCENE_ORDER 自動判斷要往前一節還是下一節場景移動
                    scene_doors = doors.get(current_scene, {})
                    scene_index = SCENE_ORDER.index(current_scene)
                    if 'prev' in scene_doors and conductor_rect.colliderect(scene_doors['prev']):
                        prev_scene = SCENE_ORDER[scene_index - 1]
                        current_scene = prev_scene
                        conductor_rect.x = doors[prev_scene]['next'].left - conductor_rect.width - 10
                    elif 'next' in scene_doors and conductor_rect.colliderect(scene_doors['next']):
                        next_scene = SCENE_ORDER[scene_index + 1]
                        current_scene = next_scene
                        conductor_rect.x = doors[next_scene]['prev'].right + 10
        # B. 遊戲邏輯
        current_world_width = get_scene_width(current_scene)

        keys = pygame.key.get_pressed()
        is_moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            conductor_rect.x -= PLAYER_SPEED
            facing_direction = 'LEFT'
            is_moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            conductor_rect.x += PLAYER_SPEED
            facing_direction = 'RIGHT'
            is_moving = True

        # 用角色實際可見的範圍（扣掉畫布左右透明留白）判斷邊界，避免走到車廂盡頭時還有一大段空氣牆
        if conductor_rect.left + CONDUCTOR_VISIBLE_PAD < 0:
            conductor_rect.left = -CONDUCTOR_VISIBLE_PAD
        if conductor_rect.right - CONDUCTOR_VISIBLE_PAD > current_world_width:
            conductor_rect.right = current_world_width + CONDUCTOR_VISIBLE_PAD

        # 更新走路動畫（GIF 裡的角色本來就面向左邊，面向右邊時要水平翻轉）
        if conductor_walk_frames:
            if is_moving:
                conductor_anim_timer += dt
                current_duration = conductor_walk_durations[conductor_anim_index]
                if conductor_anim_timer >= current_duration:
                    conductor_anim_timer -= current_duration
                    conductor_anim_index = (conductor_anim_index + 1) % len(conductor_walk_frames)
            else:
                conductor_anim_index = 0
                conductor_anim_timer = 0

            current_frame = conductor_walk_frames[conductor_anim_index]
            conductor_img = pygame.transform.flip(current_frame, True, False) if facing_direction == 'RIGHT' else current_frame

        camera_x = conductor_rect.centerx - (WIDTH // 2)
        if current_world_width <= WIDTH:
            # 場景比畫面窄（例如連接處），直接置中顯示，不用捲動
            camera_x = (current_world_width - WIDTH) // 2
        else:
            if camera_x < 0:
                camera_x = 0
            if camera_x > current_world_width - WIDTH:
                camera_x = current_world_width - WIDTH

        if night1_patrol_active and current_scene == 'CARRIAGE_5':
            # 巡視車廂任務走到第五節車廂：燈光突然熄滅，任務改成先打開手電筒、再返回駕駛室
            night1_patrol_active = False
            lights_out = True
            if '老式手電筒' not in inventory:
                # 沒有手電筒，直接迎來黑暗中的結局
                dialogue_lines = night1_lines_no_flashlight
                dialogue_index = 0
                active_npc = 'NIGHT1_NO_FLASHLIGHT'
            else:
                dialogue_lines = night1_blackout_lines
                dialogue_index = 0
                active_npc = 'NIGHT1_BLACKOUT'
            game_state = 'DIALOGUE'

        if lights_out and current_scene == 'COCKPIT':
            # 玩家已返回駕駛室，接續播放敲門劇情
            lights_out = False
            dialogue_lines = night1_knock_lines
            dialogue_index = 0
            active_npc = 'NIGHT1_KNOCK'
            game_state = 'DIALOGUE'

        # C. 畫面繪製
        draw_background(camera_x)
        draw_old_lady(camera_x)
        draw_girl(camera_x)
        draw_old_worker(camera_x)
        draw_item_spots(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_night_overlay()
        draw_lights_out_overlay(camera_x)
        draw_interact_hint(camera_x)
        draw_manual_hint()
        draw_inventory_hint()
        draw_flashlight_hint()
        draw_time_label()
        draw_lights_out_hint()

    elif game_state == 'PAUSE_MENU':
        # --- 暫停選單的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if resume_button_rect.collidepoint(mouse_pos):
                    game_state = 'PLAYING'
                elif pause_settings_button_rect.collidepoint(mouse_pos):
                    settings_return_state = 'PAUSE_MENU'
                    game_state = 'SETTINGS'
                elif back_to_menu_button_rect.collidepoint(mouse_pos):
                    game_state = 'START'

        draw_background(camera_x)
        draw_old_lady(camera_x)
        draw_girl(camera_x)
        draw_old_worker(camera_x)
        draw_item_spots(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_night_overlay()
        draw_pause_menu()

    elif game_state == 'DIALOGUE':
        # --- 對話狀態的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_SPACE:
                    dialogue_index += 1
                    if dialogue_index >= len(dialogue_lines):
                        if active_npc == 'OLD_LADY':
                            has_talked_to_old_lady = True
                            active_npc = None
                            game_state = 'PLAYING'
                        elif active_npc == 'GIRL':
                            if not has_girl_painting:
                                has_girl_painting = True
                                inventory.append('小女孩的畫')
                                show_item_popup('小女孩的畫')
                            active_npc = None
                            game_state = 'PLAYING'
                        elif active_npc == 'OLD_WORKER':
                            if '舊路線圖' not in inventory:
                                # 聽完他說「以前，是有第七站的。」之後拿到舊路線圖
                                inventory.append('舊路線圖')
                                show_item_popup('舊路線圖')
                            active_npc = None
                            game_state = 'PLAYING'
                        elif active_npc == 'STAFF_LOG_PICKUP':
                            # 拿到車站員工日誌後，直接切到第二天晚上並播放晚上的開場劇情
                            day_night_index = DAY_NIGHT_STAGES.index('DAY2_NIGHT')
                            day2_night_triggered = True
                            show_day_title_card('DAY2_NIGHT')
                            dialogue_lines = night2_intro_lines
                            dialogue_index = 0
                            active_npc = 'NIGHT2_INTRO'
                            game_state = 'DIALOGUE'
                        elif active_npc == 'NIGHT1_INTRO':
                            active_npc = None
                            show_day_title_card('DAY1_NIGHT')
                            # 任務指引改成巡視車廂，走到第五節車廂前燈光都還是正常的
                            night1_patrol_active = True
                            game_state = 'PLAYING'
                        elif active_npc == 'NIGHT1_BLACKOUT':
                            active_npc = None
                            game_state = 'PLAYING' # 任務指引改成打開手電筒（由 lights_out 狀態自動顯示）
                        elif active_npc == 'NIGHT1_KNOCK':
                            active_npc = None
                            game_state = 'NIGHT1_CHOICE'
                        elif active_npc == 'NIGHT1_NO_FLASHLIGHT':
                            active_npc = None
                            game_over_reason = "沒有手電筒，你在黑暗中迷失了方向……"
                            game_state = 'GAME_OVER'
                        elif active_npc == 'NIGHT1_OUTRO':
                            active_npc = None
                            day1_night_resolved = True
                            day_night_index = DAY_NIGHT_STAGES.index('DAY2_DAY') # 劇情結束後直接跳到第二天白天
                            show_day_title_card('DAY2_DAY')
                            game_state = 'PLAYING'
                        elif active_npc == 'NIGHT1_CAUGHT':
                            active_npc = None
                            game_over_reason = "你打開了門，被那個「多出來的人」發現了。"
                            game_state = 'GAME_OVER'
                        elif active_npc == 'NIGHT2_INTRO':
                            active_npc = None
                            start_choice(
                                "要緊急煞車嗎？",
                                "煞車", (night2_stop_result_brake + night2_platform_lines, 'NIGHT2_PLATFORM'),
                                "不煞車", (night2_stop_result_no_brake + night2_platform_lines, 'NIGHT2_PLATFORM'),
                            )
                        elif active_npc == 'NIGHT2_PLATFORM':
                            active_npc = None
                            start_choice(
                                "要打開車門嗎？",
                                "開門", (night2_lines_open_door, 'NIGHT2_CAUGHT'),
                                "不開門", (night2_lines_closed_door, 'NIGHT2_SAFE'),
                            )
                        elif active_npc == 'NIGHT2_SAFE':
                            active_npc = None
                            game_state = 'PLAYING'
                        elif active_npc == 'NIGHT2_CAUGHT':
                            active_npc = None
                            game_over_reason = "你打開了車門，月台上的人朝你走了過來。"
                            game_state = 'GAME_OVER'
                        elif active_npc == 'INTRO':
                            active_npc = None
                            game_state = 'PLAYING'
                            show_day_title_card('DAY1_DAY') # 開場自白結束、正式進入遊戲時顯示「第一天白天」標題卡
                        else:
                            active_npc = None
                            game_state = 'PLAYING'

        draw_background(camera_x)
        draw_old_lady(camera_x)
        draw_girl(camera_x)
        draw_old_worker(camera_x)
        draw_item_spots(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_night_overlay()
        draw_lights_out_overlay(camera_x)
        if game_state == 'DIALOGUE':
            draw_dialogue_box()
        draw_inventory_hint()

    elif game_state == 'NIGHT1_CHOICE':
        # --- 第一天晚上「開門／不開門」選擇畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if night1_choice_open_rect.collidepoint(mouse_pos):
                    dialogue_lines = night1_lines_open
                    dialogue_index = 0
                    active_npc = 'NIGHT1_CAUGHT'
                    game_state = 'DIALOGUE'
                elif night1_choice_close_rect.collidepoint(mouse_pos):
                    dialogue_lines = night1_lines_closed
                    dialogue_index = 0
                    active_npc = 'NIGHT1_OUTRO'
                    game_state = 'DIALOGUE'

        draw_background(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_night_overlay()
        if game_state == 'NIGHT1_CHOICE':
            draw_night1_choice()

    elif game_state == 'STORY_CHOICE':
        # --- 通用二選一選擇畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if choice_rect_a.collidepoint(mouse_pos):
                    dialogue_lines, active_npc = choice_result_a
                    dialogue_index = 0
                    game_state = 'DIALOGUE'
                elif choice_rect_b.collidepoint(mouse_pos):
                    dialogue_lines, active_npc = choice_result_b
                    dialogue_index = 0
                    game_state = 'DIALOGUE'

        draw_background(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_night_overlay()
        if game_state == 'STORY_CHOICE':
            draw_story_choice()

    elif game_state == 'GAME_OVER':
        # --- Game Over 畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_game()

        draw_game_over_screen()

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
        draw_old_worker(camera_x)
        draw_item_spots(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_night_overlay()
        draw_inventory_screen()

    elif game_state == 'CONSOLE_FOCUS':
        # --- 操作台細節畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if console_cabinet_door_rect.collidepoint(mouse_pos):
                    game_state = 'BOX_VIEW'

        draw_console_focus()

    elif game_state == 'BOX_VIEW':
        # --- 置物櫃門特寫畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'CONSOLE_FOCUS' # 退回操作台細節畫面，不是直接退出到遊戲
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if not console_box_unlocked:
                    if SCREWDRIVER_TABLE_ITEM_NAME in inventory:
                        for i, screw_rect in enumerate(console_box_screw_rects):
                            if console_box_screws[i] and screw_rect.collidepoint(mouse_pos):
                                console_box_screws[i] = False
                                if not any(console_box_screws):
                                    console_box_unlocked = True
                                break
                elif not has_guide and console_box_guide_rect.collidepoint(mouse_pos):
                    has_guide = True # 生存指南不放進背包，改成按 TAB 查看
                    show_item_popup('《夜間行駛生存指南》')
                    manual_view = 'GUIDE' # 拿到後直接翻開手冊的生存指南頁籤
                    game_state = 'MANUAL'
                    # 拿到生存指南後切到第一天晚上；等玩家關掉手冊才播放晚上的開場劇情
                    day_night_index = DAY_NIGHT_STAGES.index('DAY1_NIGHT')
                    day1_night_triggered = True
                    night1_pending_intro = True

        draw_box_view()

    elif game_state == 'TOILET_VIEW':
        # --- 廁所內部畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'PLAYING'

        draw_toilet_view()

    elif game_state == 'CASE_VIEW':
        # --- 駕駛室櫃子內部畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if FLASHLIGHT_CASE_ITEM_NAME not in inventory and flashlight_case_rect.collidepoint(mouse_pos):
                    inventory.append(FLASHLIGHT_CASE_ITEM_NAME)
                    show_item_popup(FLASHLIGHT_CASE_ITEM_NAME)
                elif TOOLROOM_KEY_ITEM_NAME not in inventory and toolroom_key_case_rect.collidepoint(mouse_pos):
                    inventory.append(TOOLROOM_KEY_ITEM_NAME)
                    show_item_popup(TOOLROOM_KEY_ITEM_NAME)

        draw_case_view()

    elif game_state == 'TOOLROOM_VIEW':
        # --- 工具間內部畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if work_table_rect.collidepoint(mouse_pos):
                    game_state = 'TOOLTABLE_VIEW'

        draw_toolroom_view()

    elif game_state == 'TOOLTABLE_VIEW':
        # --- 工作桌特寫畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'TOOLROOM_VIEW' # 退回工具間，不是直接退出到遊戲
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if SCREWDRIVER_TABLE_ITEM_NAME not in inventory and screwdriver_table_rect.collidepoint(mouse_pos):
                    inventory.append(SCREWDRIVER_TABLE_ITEM_NAME)
                    show_item_popup(SCREWDRIVER_TABLE_ITEM_NAME)

        draw_tooltable_view()

    # 獲得道具的提示卡片、天數切換標題卡：不管目前在哪個畫面狀態，都疊在最上層顯示，過一段時間自動淡出
    draw_item_popup()
    draw_day_title_card()

    # --- D. 更新畫面 ---
    # 把邏輯畫布平滑縮放後貼到全螢幕視窗中央（維持長寬比例，多餘的部分留黑邊）
    scaled_screen = pygame.transform.smoothscale(screen, RENDER_SIZE)
    display_surface.blit(scaled_screen, RENDER_OFFSET)
    pygame.display.flip()

    # 設定遊戲幀率 (Frame Rate) 為 60 FPS，並記錄這一幀經過的毫秒數供動畫使用
    dt = clock.tick(FPS)

# 離開遊戲
pygame.quit()
sys.exit() # 確保程式完全退出