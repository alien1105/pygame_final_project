import pygame
import sys

# 1. 遊戲初始化
pygame.init()

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

# 載入字型 (使用電腦內建的中文字型)
font = pygame.font.SysFont("microsoftjhenghei", 28)
font_small = pygame.font.SysFont("microsoftjhenghei", 20)
font_title = pygame.font.SysFont("microsoftjhenghei", 64)

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

    gif = Image.open('main_character_walk2.gif')
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
        conductor_img_original = pygame.image.load('main_character.png').convert_alpha()
        conductor_img = pygame.transform.scale(conductor_img_original, (CONDUCTOR_SIZE, CONDUCTOR_SIZE))
    except pygame.error as e2:
        print(f"無法載入圖片 'main_character.png': {e2}")
        print("將使用藍色方塊作為替代。")
        conductor_img = None

# 載入開始畫面的背景圖片
try:
    cover_img_original = pygame.image.load('cover.png').convert()
    cover_img = pygame.transform.scale(cover_img_original, (WIDTH, HEIGHT))
except pygame.error as e:
    print(f"無法載入圖片 'cover.png': {e}")
    print("請確認 'cover.png' 檔案與 main.py 在同一個資料夾中。")
    print("將使用黑色背景作為替代。")
    cover_img = None # 如果圖片載入失敗，設定為 None

# 載入開始畫面的標題圖片
try:
    title_img_original = pygame.image.load('title.png').convert_alpha()
    TITLE_IMG_WIDTH = 280
    title_img_height = round(TITLE_IMG_WIDTH * title_img_original.get_height() / title_img_original.get_width())
    title_img = pygame.transform.smoothscale(title_img_original, (TITLE_IMG_WIDTH, title_img_height))
except pygame.error as e:
    print(f"無法載入圖片 'title.png': {e}")
    print("請確認 'title.png' 檔案與 main.py 在同一個資料夾中。")
    print("將改用文字標題作為替代。")
    title_img = None # 如果圖片載入失敗，設定為 None

# 載入白天車廂背景圖片（維持原始長寬比例縮放，不拉伸變形；
# 車廂用兩張完整的圖片並排組成，車廂寬度改成剛好是圖片寬度的兩倍）
TRAIN_DAY_TILE_COUNT = 2
try:
    train_day_img_original = pygame.image.load('train_day.png').convert_alpha()
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

# 載入白天座椅圖片，並裁掉圖片邊緣多餘的透明留白，避免椅腳貼地時浮空
try:
    from PIL import Image as PILImage

    import numpy as np

    chair_pil = PILImage.open('chair_day.png').convert('RGBA')
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

# 載入老太太專用圖片（已經包含椅子跟人物本身，取代車廂一的第一張椅子）
try:
    from PIL import Image as PILImage
    import numpy as np

    granny_pil = PILImage.open('granny.png').convert('RGBA')
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
close_button_rect = pygame.Rect(WIDTH - 50, 50, 30, 30) # 手冊的關閉按鈕

# --- 開始畫面 ---
start_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 60, 200, 55) # 開始遊戲按鈕
exit_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 130, 200, 55) # 退出遊戲按鈕

# --- 遊戲中按 ESC 跳出的選單（由上到下：繼續遊玩、返回主頁）---
resume_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 40, 200, 55) # 繼續遊玩按鈕
back_to_menu_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 30, 200, 55) # 返回主頁按鈕

# --- 天數／白天晚上切換（依序循環：第一天白天 → 第一天晚上 → 第二天白天 → 第二天晚上）---
DAY_NIGHT_STAGES = ['DAY1_DAY', 'DAY1_NIGHT', 'DAY2_DAY', 'DAY2_NIGHT']
DAY_NIGHT_LABELS = {
    'DAY1_DAY': '第一天白天',
    'DAY1_NIGHT': '第一天晚上',
    'DAY2_DAY': '第二天白天',
    'DAY2_NIGHT': '第二天晚上',
}
day_night_index = 0 # 目前所在階段在 DAY_NIGHT_STAGES 中的索引
time_toggle_button_rect = pygame.Rect(WIDTH // 2 - 90, 15, 180, 34) # 切換到下一個天數／時段的按鈕

# --- 第一天晚上劇情 ---
day1_night_triggered = False # 是否已經播放過第一天晚上的事件，避免重複觸發
day1_night_resolved = False # 第一天晚上的劇情是否已經解完，解完之前無法前進到第二天
lights_out = False # 列車燈光是否熄滅中，此時任務指引是返回駕駛室，且開門需要手電筒

# --- 手電筒 ---
flashlight_on = False # 手電筒是否開啟中（需持有「老式手電筒」才能開關）
facing_direction = 'RIGHT' # 角色目前面向，決定手電筒照亮的方向

# --- 走路動畫 ---
conductor_anim_index = 0 # 目前播放到走路動畫的第幾格
conductor_anim_timer = 0 # 累積經過的毫秒數，用來判斷何時切換下一格

night1_intro_lines = [
    ("旁白", "主角第一次執行夜班，一開始一切正常。"),
    ("旁白", "列車離站，經過隧道、經過森林、經過幾個車站。"),
    ("旁白", "凌晨 00:17，列車燈光突然熄滅。"),
]

night1_knock_lines = [
    ("旁白", "叩。叩。叩。有人在敲駕駛室門。"),
]

night1_lines_no_flashlight = [ # 沒有手電筒，無法在黑暗中返回駕駛室
    ("旁白", "四周一片漆黑，你完全看不清任何東西。"),
    ("旁白", "你伸手在黑暗中摸索，想找到回駕駛室的路——"),
    ("旁白", "但沒有光，你什麼都找不到。"),
    ("旁白", "你聽見腳步聲，從四面八方逐漸逼近。"),
]

night1_lines_closed = [ # 選擇「不開門」後的劇情
    ("旁白", "你沒有開門。幾秒後，敲門聲停止了。"),
    ("旁白", "列車離開隧道，燈恢復正常。"),
    ("旁白", "主角看向監視器，發現最後一節車廂多了一個人。"),
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
    ("主角", "是。"),
    ("老太太", "那你晚上可別回頭。"),
    ("主角", "回頭？"),
    ("老太太", "……"), # 她卻像沒說過這句話一樣
]

# 已經聊過一次之後，再找她說話會改播這段
old_lady_dialogue_repeat = [
    ("老太太", "……"),
]

has_talked_to_old_lady = False # 是否已經完整聊過第一次對話

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

# 已經拿到畫之後，再找她說話會改播這段（不會重複給畫）
girl_dialogue_repeat = [
    ("小女孩", "……"),
]

# --- 老維修員 NPC（第二天白天起才會出現）---
OLD_WORKER_SCENE = 'CARRIAGE_2'
OLD_WORKER_MIN_DAY_INDEX = 2 # DAY_NIGHT_STAGES 中 'DAY2_DAY' 的索引
old_worker_rect = pygame.Rect(700, HEIGHT - FLOOR_HEIGHT - 90, 60, 90) # 坐在車廂二的另一個座位上
WORKER_COLOR = (90, 110, 90) # 老維修員用暗綠色方塊代表

# 老維修員第二天白天的對話：主線內容
old_worker_dialogue_intro = [
    ("主角", "欸，你知道昨晚到底發生了什麼事嗎？"),
    ("老維修員", "……那種事，還是別多問比較好。"),
    ("主角", "可是我真的看到了什麼。"),
    ("老維修員", "如果你晚上看見第七站，別停。"),
    ("主角", "第七站？這條路線不是只有六個車站嗎？"),
    ("老維修員", "……以前，是有第七站的。"),
]

# 若玩家持有第一天拿到的舊路線圖，會多出這段揭露「青木站」的內容
old_worker_dialogue_map_reveal = [
    ("主角", "（我想起背包裡的舊路線圖……）"),
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
    "主角": BLUE,
    "旁白": DARK_GRAY,
}

# --- 對話狀態管理 ---
dialogue_lines = []
dialogue_index = 0
active_npc = None # 記錄目前正在對話的 NPC，用於對話結束後觸發後續事件
has_girl_painting = False # 是否已從小女孩手中取得畫
has_guide = False # 是否已取得《夜間行駛生存指南》，取得後可在手冊畫面切換查看

# --- 手冊畫面（含左側頁籤，可切換操作手冊／生存指南）---
manual_view = 'MANUAL' # 目前手冊畫面顯示的頁籤：MANUAL 操作手冊 / GUIDE 生存指南
manual_panel_rect = pygame.Rect(WIDTH // 2 - 350, HEIGHT // 2 - 160, 700, 320)
manual_sidebar_width = 160
manual_tab_manual_rect = pygame.Rect(manual_panel_rect.x + 15, manual_panel_rect.y + 70, manual_sidebar_width - 30, 50)
manual_tab_guide_rect = pygame.Rect(manual_panel_rect.x + 15, manual_panel_rect.y + 130, manual_sidebar_width - 30, 50)

# 《夜間行駛生存指南》第一頁的前三條規則，格式為 (規則標題, 規則內容, 補充說明)
guide_rules = [
    ("規則一", "夜間駕駛時，看到月台有人，不要鳴笛。", "因為那個人不一定是在等車。"),
    ("規則二", "列車進入隧道後，如果車廂燈熄滅，不要離開駕駛室。", "不管你聽見什麼。"),
    ("規則三", "凌晨 00:17，不要查看後視鏡。", "如果已經看了，不要數車廂裡有幾個人。"),
]

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
        'scene': 'CONNECTION_1',
        'rect': pygame.Rect(30, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 70, DOOR_HEIGHT), # 連接處牆壁上
        'items': ['舊路線圖'],
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
        'min_day_index': 2, # 第二天白天起才會出現
        'reveal_lines': [
            ("旁白", "員工日誌最後一筆寫著："),
            ("旁白", "「00:17，青木站再次亮燈。」"),
        ],
    },
]


def get_item_spot_at(scene, rect):
    """回傳玩家目前所在位置可拾取、且尚未拾取的道具點（沒有則回傳 None）"""
    for spot in item_spots:
        if spot['collected'] or spot['scene'] != scene:
            continue
        if day_night_index < spot.get('min_day_index', 0):
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


# --- 駕駛艙操作台細節（按 F 進入細節畫面，用滑鼠點擊個別拾取）---
CONSOLE_FOCUS_SCENE = 'COCKPIT'
console_cabinet_rect = pygame.Rect(30, HEIGHT - FLOOR_HEIGHT - DOOR_HEIGHT, 100, DOOR_HEIGHT) # 操作台下置物櫃

console_panel_rect = pygame.Rect(WIDTH // 2 - 330, HEIGHT // 2 - 160, 660, 320)
_console_slot_size = 130
_console_slot_gap = 15
_console_slots_total_width = _console_slot_size * 4 + _console_slot_gap * 3
_console_slot_start_x = console_panel_rect.centerx - _console_slots_total_width // 2
_console_slot_y = console_panel_rect.y + 90

console_items = [
    {'name': '老式手電筒', 'color': (200, 200, 80), 'rect': pygame.Rect(_console_slot_start_x, _console_slot_y, _console_slot_size, _console_slot_size), 'collected': False, 'sealed': False},
    {'name': '車站鑰匙', 'color': (190, 190, 190), 'rect': pygame.Rect(_console_slot_start_x + (_console_slot_size + _console_slot_gap), _console_slot_y, _console_slot_size, _console_slot_size), 'collected': False, 'sealed': False},
    {'name': '維修員留下的螺絲起子', 'color': (150, 110, 70), 'rect': pygame.Rect(_console_slot_start_x + (_console_slot_size + _console_slot_gap) * 2, _console_slot_y, _console_slot_size, _console_slot_size), 'collected': False, 'sealed': False},
    {'name': '《夜間行駛生存指南》', 'color': (90, 60, 40), 'rect': pygame.Rect(_console_slot_start_x + (_console_slot_size + _console_slot_gap) * 3, _console_slot_y, _console_slot_size, _console_slot_size), 'collected': False, 'sealed': True},
]


def console_has_items_left():
    """置物櫃裡是否還有尚未拾取的道具"""
    return any(not item['collected'] for item in console_items)


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
        screen.blit(title_img, (WIDTH // 2 - title_img.get_width() // 2, 35))
    else:
        title_surf = font_title.render("軌遇", True, WHITE)
        screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 2 - 130))

    #subtitle_surf = font_small.render("列車長模擬器", True, GRAY)
    #screen.blit(subtitle_surf, (WIDTH // 2 - subtitle_surf.get_width() // 2, HEIGHT // 2 - 55))

    pygame.draw.rect(screen, RED, start_button_rect)
    pygame.draw.rect(screen, WHITE, start_button_rect, 3)
    start_text_surf = font.render("開始遊戲", True, WHITE)
    screen.blit(start_text_surf, (start_button_rect.centerx - start_text_surf.get_width() // 2,
                                  start_button_rect.centery - start_text_surf.get_height() // 2))

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

    pygame.draw.rect(screen, RED, resume_button_rect)
    pygame.draw.rect(screen, WHITE, resume_button_rect, 3)
    resume_text_surf = font.render("繼續遊玩", True, WHITE)
    screen.blit(resume_text_surf, (resume_button_rect.centerx - resume_text_surf.get_width() // 2,
                                   resume_button_rect.centery - resume_text_surf.get_height() // 2))

    pygame.draw.rect(screen, DARK_GRAY, back_to_menu_button_rect)
    pygame.draw.rect(screen, WHITE, back_to_menu_button_rect, 3)
    back_text_surf = font.render("返回主頁", True, WHITE)
    screen.blit(back_text_surf, (back_to_menu_button_rect.centerx - back_text_surf.get_width() // 2,
                                 back_to_menu_button_rect.centery - back_text_surf.get_height() // 2))


def draw_manual_screen():
    """繪製手冊畫面，左側頁籤可切換操作手冊／生存指南"""
    # 半透明背景
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    panel_rect = manual_panel_rect
    pygame.draw.rect(screen, WHITE, panel_rect)
    pygame.draw.rect(screen, BLACK, panel_rect, 3)

    # 左側頁籤側欄
    sidebar_rect = pygame.Rect(panel_rect.x, panel_rect.y, manual_sidebar_width, panel_rect.height)
    pygame.draw.rect(screen, GRAY, sidebar_rect)
    pygame.draw.line(screen, BLACK, (sidebar_rect.right, panel_rect.y), (sidebar_rect.right, panel_rect.bottom), 3)

    # 「操作手冊」頁籤
    pygame.draw.rect(screen, WHITE if manual_view == 'MANUAL' else GRAY, manual_tab_manual_rect)
    pygame.draw.rect(screen, BLACK, manual_tab_manual_rect, 2)
    tab_manual_surf = font_small.render("操作手冊", True, BLACK)
    screen.blit(tab_manual_surf, (manual_tab_manual_rect.centerx - tab_manual_surf.get_width() // 2,
                                  manual_tab_manual_rect.centery - tab_manual_surf.get_height() // 2))

    # 「生存指南」頁籤（取得指南後才會出現）
    if has_guide:
        tab_guide_bg = WHITE if manual_view == 'GUIDE' else GRAY
        pygame.draw.rect(screen, tab_guide_bg, manual_tab_guide_rect)
        pygame.draw.rect(screen, BLACK, manual_tab_guide_rect, 2)
        tab_guide_surf = font_small.render("生存指南", True, BLACK)
        screen.blit(tab_guide_surf, (manual_tab_guide_rect.centerx - tab_guide_surf.get_width() // 2,
                                     manual_tab_guide_rect.centery - tab_guide_surf.get_height() // 2))

    # 右側內容區
    content_x = panel_rect.x + manual_sidebar_width + 25

    if manual_view == 'GUIDE' and has_guide:
        title_surf = font.render("《夜間行駛生存指南》", True, BLACK)
        screen.blit(title_surf, (content_x, panel_rect.y + 20))

        rule_y = panel_rect.y + 65
        for label, rule_text, desc_text in guide_rules:
            label_surf = font_small.render(label, True, RED)
            screen.blit(label_surf, (content_x, rule_y))

            rule_surf = font_small.render(rule_text, True, BLACK)
            screen.blit(rule_surf, (content_x, rule_y + 22))

            desc_surf = font_small.render(desc_text, True, DARK_GRAY)
            screen.blit(desc_surf, (content_x, rule_y + 44))

            rule_y += 22 * 3 + 8
    else:
        title_surf = font.render("操作手冊", True, BLACK)
        screen.blit(title_surf, (content_x, panel_rect.y + 20))

        instructions = [
            "← → / A D : 左右移動",
            "F : 與場景互動",
            "B : 開啟背包",
            "L : 開關手電筒（需持有手電筒）",
            "TAB : 關閉此手冊",
            "ESC : 回到主頁"
        ]
        for i, text in enumerate(instructions):
            text_surf = font_small.render(text, True, BLACK)
            screen.blit(text_surf, (content_x, panel_rect.y + 90 + i * 40))

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
    scene_width = get_scene_width(current_scene)
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, HEIGHT - FLOOR_HEIGHT, scene_width, FLOOR_HEIGHT))

    # 畫上方的行李架
    pygame.draw.rect(screen, DARK_GRAY, (0 - camera_offset_x, 60, scene_width, 15))

    # 根據當前場景繪製特定物件
    if 'CARRIAGE' in current_scene:
        draw_carriage_scene(camera_offset_x, current_scene)
    elif 'CONNECTION' in current_scene:
        draw_connection_scene(camera_offset_x)
    elif current_scene == 'COCKPIT':
        draw_cockpit_scene(camera_offset_x)

def draw_carriage_scene(camera_offset_x, scene_name):
    """繪製指定車廂內的物件 (座椅、窗戶、門)"""
    is_day = not DAY_NIGHT_STAGES[day_night_index].endswith('NIGHT')

    # 白天使用車廂背景圖片，蓋掉 draw_background 畫的素色牆壁與地板
    # 用兩張完整的圖片並排組成車廂背景（互相重疊幾個像素，蓋掉拼接縫）
    if is_day and train_day_img:
        for tile_index in range(TRAIN_DAY_TILE_COUNT):
            screen.blit(train_day_img, (tile_index * train_day_tile_step - camera_offset_x, 0))

    # 畫座椅：白天依照背景圖片裡窗戶的位置擺放，晚上維持原本繪製的樣式（依車廂實際寬度平均分佈）
    # 車廂一的第一張椅子改由 granny.png 取代（該圖片本身已經包含椅子），這裡跳過不重複畫
    if is_day and chair_day_img and chair_day_positions:
        for pos in chair_day_positions:
            if scene_name == OLD_LADY_SCENE and pos == GRANNY_CHAIR_X:
                continue
            chair_rect = chair_day_img.get_rect()
            chair_rect.midbottom = (pos - camera_offset_x, HEIGHT - FLOOR_HEIGHT + 20)
            screen.blit(chair_day_img, chair_rect)
    else:
        chair_positions = range(140, CARRIAGE_WIDTH - DOOR_WIDTH - 75, 140)
        for pos in chair_positions:
            draw_side_chair(pos, camera_offset_x)

    # 畫窗戶（白天車廂背景圖片裡已經畫好窗戶了，不用再另外畫；晚上依車廂實際寬度平均分佈）
    if not (is_day and train_day_img):
        for x in range(100, CARRIAGE_WIDTH - DOOR_WIDTH - 150, 450):
            win_rect = pygame.Rect(x - camera_offset_x, 100, 150, 100)
            pygame.draw.rect(screen, WHITE, win_rect)
            pygame.draw.rect(screen, BLACK, win_rect, 3)
    # 這節車廂往上一節／下一節場景的門（不畫方塊，但互動邏輯保留在 doors 字典裡）

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

    # 駕駛艙的出口門（不畫方塊，但互動邏輯保留在 doors 字典裡）

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
    """繪製老太太 NPC（僅在車廂一場景顯示，用 granny.png 取代車廂一的第一張椅子）"""
    if current_scene != OLD_LADY_SCENE:
        return
    screen_rect = old_lady_rect.move(-camera_offset_x, 0)
    if granny_img:
        screen.blit(granny_img, screen_rect)
    else:
        pygame.draw.rect(screen, PURPLE, screen_rect)
        pygame.draw.circle(screen, PURPLE, (screen_rect.centerx, screen_rect.top - 15), 15) # 頭部


def draw_girl(camera_offset_x):
    """繪製小女孩 NPC（僅在車廂二場景顯示）"""
    if current_scene != GIRL_SCENE:
        return
    screen_rect = girl_rect.move(-camera_offset_x, 0)
    pygame.draw.rect(screen, PINK, screen_rect)
    pygame.draw.circle(screen, PINK, (screen_rect.centerx, screen_rect.top - 12), 12) # 頭部


def draw_old_worker(camera_offset_x):
    """繪製老維修員 NPC（第二天白天起，僅在車廂二場景顯示）"""
    if current_scene != OLD_WORKER_SCENE or day_night_index < OLD_WORKER_MIN_DAY_INDEX:
        return
    screen_rect = old_worker_rect.move(-camera_offset_x, 0)
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
        if day_night_index < spot.get('min_day_index', 0):
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
        elif item.get('sealed'):
            pygame.draw.rect(screen, item['color'], slot_rect)
            pygame.draw.rect(screen, BLACK, slot_rect, 3)
            # 封住暗格的膠帶（交叉貼成 X 型）
            pygame.draw.line(screen, TAPE_COLOR, slot_rect.topleft, slot_rect.bottomright, 12)
            pygame.draw.line(screen, TAPE_COLOR, slot_rect.topright, slot_rect.bottomleft, 12)
            label = "被膠帶封住"
        else:
            pygame.draw.rect(screen, item['color'], slot_rect)
            pygame.draw.rect(screen, BLACK, slot_rect, 3)
            label = item['name']

        label_surf = font_small.render(label, True, WHITE)
        screen.blit(label_surf, (slot_rect.centerx - label_surf.get_width() // 2, slot_rect.bottom + 10))

    hint_surf = font_small.render("點擊膠帶撕開・點擊道具拾取・F : 離開細節畫面", True, WHITE)
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
    """列車燈光熄滅期間，顯示「返回駕駛室」的任務指引"""
    if not lights_out:
        return
    hint_text_surf = font_small.render("任務：返回駕駛室", True, WHITE)
    hint_rect = hint_text_surf.get_rect()
    hint_bg_rect = pygame.Rect(0, 0, hint_rect.width + 24, hint_rect.height + 14)
    hint_bg_rect.midtop = (WIDTH // 2, 58)
    hint_bg = pygame.Surface(hint_bg_rect.size, pygame.SRCALPHA)
    hint_bg.fill((120, 0, 0, 190))
    screen.blit(hint_bg, hint_bg_rect)
    screen.blit(hint_text_surf, (hint_bg_rect.centerx - hint_rect.width // 2, hint_bg_rect.centery - hint_rect.height // 2))


def draw_time_toggle_button():
    """繪製目前天數／時段按鈕，點擊後依序切換到下一個階段"""
    current_stage = DAY_NIGHT_STAGES[day_night_index]
    is_night = current_stage.endswith('NIGHT')
    button_color = (200, 160, 60) if is_night else (70, 90, 160)

    pygame.draw.rect(screen, button_color, time_toggle_button_rect)
    pygame.draw.rect(screen, BLACK, time_toggle_button_rect, 2)

    label_surf = font_small.render(DAY_NIGHT_LABELS[current_stage], True, WHITE)
    screen.blit(label_surf, (time_toggle_button_rect.centerx - label_surf.get_width() // 2,
                             time_toggle_button_rect.centery - label_surf.get_height() // 2))


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
    """繪製對話框，顯示目前這句台詞（超過文字框寬度會自動換行）"""
    speaker, text = dialogue_lines[dialogue_index]

    box_width = WIDTH - 120
    line_height = 32
    lines = wrap_text(text, font, box_width - 40)
    box_height = max(100, 55 + len(lines) * line_height + 15)
    box_rect = pygame.Rect(60, HEIGHT - 40 - box_height, box_width, box_height)

    pygame.draw.rect(screen, WHITE, box_rect)
    pygame.draw.rect(screen, BLACK, box_rect, 3)

    name_surf = font_small.render(speaker, True, SPEAKER_COLORS.get(speaker, BLACK))
    screen.blit(name_surf, (box_rect.x + 20, box_rect.y + 12))

    for i, line in enumerate(lines):
        line_surf = font.render(line, True, BLACK)
        screen.blit(line_surf, (box_rect.x + 20, box_rect.y + 45 + i * line_height))

    hint_surf = font_small.render("F : 繼續", True, DARK_GRAY)
    screen.blit(hint_surf, (box_rect.right - hint_surf.get_width() - 15, box_rect.bottom - hint_surf.get_height() - 10))


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
    global flashlight_on, facing_direction
    global has_guide, has_girl_painting, has_talked_to_old_lady, active_npc, manual_view
    global dialogue_lines, dialogue_index, game_over_reason

    conductor_rect.x = COCKPIT_WIDTH - DOOR_WIDTH - CONDUCTOR_SIZE - 10
    conductor_rect.y = HEIGHT - FLOOR_HEIGHT - CONDUCTOR_SIZE + CONDUCTOR_Y_OFFSET
    current_scene = 'COCKPIT'
    game_state = 'START'
    camera_x = 0

    day_night_index = 0
    day1_night_triggered = False
    day1_night_resolved = False
    day2_night_triggered = False
    lights_out = False
    flashlight_on = False
    facing_direction = 'RIGHT'
    game_over_reason = ""

    has_guide = False
    has_girl_painting = False
    has_talked_to_old_lady = False
    active_npc = None
    manual_view = 'MANUAL'
    dialogue_lines = []
    dialogue_index = 0

    inventory.clear()

    for spot in item_spots:
        spot['collected'] = False

    for item in console_items:
        item['collected'] = False
        item['sealed'] = (item['name'] == '《夜間行駛生存指南》')


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
        interactables.append(old_lady_interact_rect)
    if current_scene == GIRL_SCENE:
        interactables.append(girl_rect)
    if current_scene == OLD_WORKER_SCENE and day_night_index >= OLD_WORKER_MIN_DAY_INDEX:
        interactables.append(old_worker_rect)
    for spot in item_spots:
        if spot['scene'] == current_scene and not spot['collected'] and day_night_index >= spot.get('min_day_index', 0):
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
dt = 0 # 每一幀經過的毫秒數，供走路動畫計時使用
running = True
while running:
    if game_state == 'START':
        # --- 開始畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if start_button_rect.collidepoint(mouse_pos):
                    game_state = 'MANUAL'
                elif exit_button_rect.collidepoint(mouse_pos):
                    running = False

        draw_start_screen()

    elif game_state == 'MANUAL':
        # --- 手冊狀態的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if close_button_rect.collidepoint(mouse_pos):
                    game_state = 'PLAYING'
                elif manual_tab_manual_rect.collidepoint(mouse_pos):
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
                if event.key == pygame.K_f and current_scene == OLD_LADY_SCENE and conductor_rect.colliderect(old_lady_interact_rect):
                    # 與老太太互動，開始對話（聊過一次之後改播重複對話）
                    dialogue_lines = old_lady_dialogue_repeat if has_talked_to_old_lady else old_lady_dialogue
                    dialogue_index = 0
                    active_npc = 'OLD_LADY'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and current_scene == GIRL_SCENE and conductor_rect.colliderect(girl_rect):
                    # 與小女孩互動，開始對話（已經拿過畫的話改播重複對話）
                    dialogue_lines = girl_dialogue_repeat if has_girl_painting else girl_dialogue
                    dialogue_index = 0
                    active_npc = 'GIRL'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and current_scene == OLD_WORKER_SCENE and day_night_index >= OLD_WORKER_MIN_DAY_INDEX and conductor_rect.colliderect(old_worker_rect):
                    # 與老維修員互動，開始對話
                    dialogue_lines = build_old_worker_dialogue()
                    dialogue_index = 0
                    active_npc = 'OLD_WORKER'
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and get_item_spot_at(current_scene, conductor_rect) is not None:
                    # 撿拾道具
                    item_spot = get_item_spot_at(current_scene, conductor_rect)
                    inventory.extend(item_spot['items'])
                    item_spot['collected'] = True
                    pickup_line = (" ", f"獲得了「{ '、'.join(item_spot['items']) }」。")
                    dialogue_lines = item_spot.get('reveal_lines', []) + [pickup_line]
                    dialogue_index = 0
                    active_npc = None
                    game_state = 'DIALOGUE'
                elif event.key == pygame.K_f and current_scene == CONSOLE_FOCUS_SCENE and conductor_rect.colliderect(console_cabinet_rect):
                    # 聚焦查看操作台置物櫃細節
                    game_state = 'CONSOLE_FOCUS'
                elif event.key == pygame.K_f and lights_out and not flashlight_on and get_current_scene_door_at(conductor_rect) is not None:
                    # 燈光熄滅時，手電筒沒開就無法開門
                    dialogue_lines = [(" ", "太暗了，需要打開手電筒才能看清楚並打開這扇門。")]
                    dialogue_index = 0
                    active_npc = None
                    game_state = 'DIALOGUE'
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
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                if time_toggle_button_rect.collidepoint(mouse_pos) and DAY_NIGHT_STAGES[day_night_index] == 'DAY1_NIGHT' and day1_night_triggered and not day1_night_resolved:
                    # 第一天晚上的劇情還沒解完，無法前進到第二天
                    dialogue_lines = [(" ", "第一天晚上的劇情還沒結束，無法前進到下一天。")]
                    dialogue_index = 0
                    active_npc = None
                    game_state = 'DIALOGUE'
                elif time_toggle_button_rect.collidepoint(mouse_pos):
                    day_night_index = min(day_night_index + 1, len(DAY_NIGHT_STAGES) - 1)
                    if DAY_NIGHT_STAGES[day_night_index] == 'DAY1_NIGHT' and not day1_night_triggered:
                        # 觸發第一天晚上的劇情
                        day1_night_triggered = True
                        dialogue_lines = night1_intro_lines
                        dialogue_index = 0
                        active_npc = 'NIGHT1_INTRO'
                        game_state = 'DIALOGUE'
                    elif DAY_NIGHT_STAGES[day_night_index] == 'DAY2_NIGHT' and not day2_night_triggered:
                        # 觸發第二天晚上的劇情
                        day2_night_triggered = True
                        dialogue_lines = night2_intro_lines
                        dialogue_index = 0
                        active_npc = 'NIGHT2_INTRO'
                        game_state = 'DIALOGUE'

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
        if camera_x < 0:
            camera_x = 0
        if camera_x > current_world_width - WIDTH:
            camera_x = current_world_width - WIDTH

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
        draw_time_toggle_button()
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
                            active_npc = None
                            game_state = 'PLAYING'
                        elif active_npc == 'NIGHT1_INTRO':
                            active_npc = None
                            if current_scene == 'COCKPIT':
                                # 已經在駕駛室，直接接續播放敲門劇情
                                dialogue_lines = night1_knock_lines
                                dialogue_index = 0
                                active_npc = 'NIGHT1_KNOCK'
                                game_state = 'DIALOGUE'
                            elif '老式手電筒' not in inventory:
                                # 沒有手電筒，無法在黑暗中找到回駕駛室的路
                                dialogue_lines = night1_lines_no_flashlight
                                dialogue_index = 0
                                active_npc = 'NIGHT1_NO_FLASHLIGHT'
                                game_state = 'DIALOGUE'
                            else:
                                # 不在駕駛室，任務指引為返回駕駛室
                                lights_out = True
                                game_state = 'PLAYING'
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
        # --- 操作台置物櫃細節畫面的事件與繪圖 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f or event.key == pygame.K_ESCAPE:
                    game_state = 'PLAYING'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = to_logical_pos(event.pos)
                for item in console_items:
                    if item['collected'] or not item['rect'].collidepoint(mouse_pos):
                        continue
                    if item.get('sealed'):
                        item['sealed'] = False # 撕開膠帶
                    elif item['name'] == '《夜間行駛生存指南》':
                        has_guide = True # 生存指南不放進背包，改成按 TAB 查看
                        item['collected'] = True
                    else:
                        inventory.append(item['name'])
                        item['collected'] = True
                    break

        draw_background(camera_x)
        draw_conductor(screen, conductor_rect, conductor_img, camera_x)
        draw_night_overlay()
        draw_console_focus()
        draw_inventory_hint()

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