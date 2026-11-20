import ctypes

ctypes.windll.shcore.SetProcessDpiAwareness(2)

import mss
from PIL import Image
import cv2
import numpy as np
from pathlib import Path
from collections import Counter
import pyautogui
import time


def getcellcolours(cell_image):
    pixels = list(cell_image.convert("RGB").get_flattened_data())
    colour_counts = Counter(pixels)

    return colour_counts.most_common(10)


def isemptycell(cell_image):
    width, height = cell_image.size
    background = (57, 64, 72)

    for y in range(height // 3, 2 * height // 3):
        for x in range(width // 3, 2 * width // 3):
            pixel = cell_image.getpixel((x, y))

            if any(
                abs(pixel[i] - background[i]) > 3
                for i in range(3)
            ):
                return False

    return True


def capturescreen(monitor_index):
    with mss.MSS() as sct:
        monitor = sct.monitors[monitor_index]
        screen = sct.grab(monitor)

        screenshot = Image.frombytes("RGB", screen.size, screen.rgb)

    return screenshot


def getcellimage(board_image, row, col, rows, cols):
    cell_width = board_image.width / cols
    cell_height = board_image.height / rows

    left = round(col * cell_width)
    top = round(row * cell_height)
    right = round((col + 1) * cell_width)
    bottom = round((row + 1) * cell_height)

    cell_image = board_image.crop((left, top, right, bottom))

    return cell_image


def findboard(rows, cols):
    template_path = Path(__file__).parent / "smiley_template.png"
    template = cv2.imread(str(template_path))

    if template is None:
        raise FileNotFoundError("Could not load smiley.")

    
    screenshot = capturescreen(0)
    screenshot_array = np.array(screenshot)
    screenshot_gray = cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    best_score = -1
    best_location = None
    best_scale = None
    best_size = None


    for scale in [1.0, 1.25, 1.5, 1.75, 2.0]:
        resized_template = cv2.resize(template_gray, None, fx=scale, fy=scale)

        result = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = max_val
            best_location = max_loc
            best_scale = scale
            best_size = resized_template.shape[:2]


    if best_score < 0.9:
        raise ValueError("Minesweeper game could not be located.")

    x, y = best_location
    template_height, template_width = best_size

    smiley_region = {
        "left": x,
        "top": y,
        "width": template_width,
        "height": template_height
    }

    smiley_center_x = x + template_width / 2
    smiley_center_y = y + template_height / 2

    cell_size = 24 * best_scale

    board_width = round(cols * cell_size)
    board_height = round(rows * cell_size)

    board_left = round(smiley_center_x - board_width / 2 - best_scale)
    board_top = round(smiley_center_y + 41 * best_scale)


    board_right = board_left + board_width
    board_bottom = board_top  + board_height

    board_image = screenshot.crop((board_left, board_top, board_right, board_bottom))

    board_region = {
        "left": board_left,
        "top": board_top,
        "width": board_width,
        "height": board_height
    }
    
    
    return board_image, board_region, smiley_region


def captureboard(board_region, screenshot=None):
    if screenshot is None:
        screenshot = capturescreen(0)


    left = board_region["left"]
    top = board_region["top"]

    right = left + board_region["width"]
    bottom = top + board_region["height"]

    return screenshot.crop((left, top, right, bottom))


def countsimilarpixels(pixels, colour, tolerance=15):
    return sum(
        1
        for pixel in pixels
        if all(
            abs(pixel[i] - colour[i]) <= tolerance
            for i in range(3)
        )
    )


def flagcell(row, col, board_region, rows, cols, monitor_origin):
    x, y = celltoscreen(
        row, col, board_region, rows, cols, monitor_origin
    )

    ctypes.windll.user32.SetCursorPos(x, y)
    pyautogui.click(button="right")


def restartgame(smiley_region, monitor_origin):
    x = smiley_region["left"] + smiley_region["width"] / 2
    y = smiley_region["top"] + smiley_region["height"] / 2

    x += monitor_origin["left"]
    y += monitor_origin["top"]

    ctypes.windll.user32.SetCursorPos(round(x), round(y))
    pyautogui.click()


def recognisecell(cell_image):
    pixels = list(cell_image.convert("RGB").get_flattened_data())

    colours = {
        1: (137, 198, 253),
        2: (112, 192, 104),
        3: (246, 125, 138),
        4: (233, 140, 254),
        5: (215, 171, 47),
        6: (102, 204, 204)
    }

    for number, colour in colours.items():
        if countsimilarpixels(pixels, colour) >= 20:
            return number

    if countsimilarpixels(pixels, (217, 224, 232), tolerance=3) >= 20:
        return -3


    hidden_pixels = sum(
        1
        for r, g, b in pixels
        if abs(r - 77) <= 3
        and abs(g - 84) <= 3
        and abs(b - 92) <= 3
    )

    if hidden_pixels >= 300:
        return -1

    if isemptycell(cell_image):
        return 0

    return None


def recogniseboard(board_image, rows, cols):
    board = []

    for row in range(rows):
        board_row = []

        for col in range(cols):
            cell_image = getcellimage(board_image, row, col, rows, cols)
            cell_value = recognisecell(cell_image)

            if cell_value is None:
                raise ValueError(f"unrecognised cell at row {row}, column {col}")

            board_row.append(cell_value)

        board.append(board_row)




    return board


def celltoscreen(row, col, board_region, rows, cols, monitor_origin):
    cell_width = board_region["width"] / cols
    cell_height = board_region["height"] / rows

    x = board_region["left"] + (col + 0.5) * cell_width
    y = board_region["top"] + (row + 0.5) * cell_height

    x += monitor_origin["left"]
    y += monitor_origin["top"]

    return round(x), round(y)


def matchsmiley(screen_image, template, smiley_region):
    x = smiley_region["left"]
    y = smiley_region["top"]
    w = smiley_region["width"]
    h = smiley_region["height"]

    smiley_image = screen_image.crop((x, y, x + w, y + h))

    smiley_gray = cv2.cvtColor(np.array(smiley_image), cv2.COLOR_RGB2GRAY)

    resized_template = cv2.resize(template, (w, h))

    result = cv2.matchTemplate(smiley_gray, resized_template, cv2.TM_CCOEFF_NORMED)

    return cv2.minMaxLoc(result)[1]


def savesmileytemplate(screen_image, smiley_region, filename):
    x = smiley_region["left"]
    y = smiley_region["top"]
    w = smiley_region["width"]
    h = smiley_region["height"]

    smiley_image = screen_image.crop((x, y, x + w, y + h))

    smiley_image.save(filename)



from minesweeper_bot import solveboard


rows = 25
cols = 70
total_mines = 516


board_image, board_region, smiley_region = findboard(rows, cols)

with mss.MSS() as sct:
    monitor_origin = sct.monitors[0]


normal_template = cv2.imread(
    str(Path(__file__).parent / "smiley_template.png"),
    cv2.IMREAD_GRAYSCALE
)

win_template = cv2.imread(
    str(Path(__file__).parent / "templates" / "win.png"),
    cv2.IMREAD_GRAYSCALE
)

lose_template = cv2.imread(
    str(Path(__file__).parent / "templates" / "lose.png"),
    cv2.IMREAD_GRAYSCALE
)

if any(t is None for t in (normal_template, win_template, lose_template)):
    raise FileNotFoundError("Could not load one or more templates")


total_games = 1

total_wins = 0
total_losses = 0
total_moves = 0
total_time = 0

for game in range(total_games):
    print(f"\n--- Starting Game {game + 1} ---")

    start_time = time.perf_counter()
    moves_made = 0
    game_result = "Unknown"
    original_board = None



    while True:
        if time.perf_counter() - start_time > 500:
            print("Game exceeded 5 minutes. Stopping.")
            game_result = "Timeout"
            break

        screen_image = capturescreen(0)

        normal_score = matchsmiley(screen_image, normal_template, smiley_region)
        win_score = matchsmiley(screen_image, win_template, smiley_region)
        lose_score = matchsmiley(screen_image, lose_template, smiley_region)



        if win_score >= 0.9 and win_score > max(normal_score, lose_score):
            print("Game won!")
            game_result = "Win"
            break
        if lose_score >= 0.9 and lose_score > max(normal_score, win_score):
            print("Game lost!")
            game_result = "Loss"
            break

        board_image = captureboard(board_region, screen_image)
        board = recogniseboard(board_image, rows, cols)


        if original_board is not None and board == original_board:
            print("Board hasn't changed. Stopping.")
            break

        original_board = [row.copy() for row in board]

        try:
            move = solveboard(board, total_mines)
        except ValueError as e:
            print(f"Stopping bot: {e}")
            game_result = "Solver error"
            break

        mines_to_flag = []

        for row in range(rows):
            for col in range(cols):
                if original_board[row][col] == -1 and board[row][col] == -3:
                    mines_to_flag.append((row, col))

        for row, col in mines_to_flag:

            flagcell(row, col, board_region, rows, cols, monitor_origin)

            #time.sleep(0.3)


        if move is None:
            print("No more available")
            break

        row, col = move

        if original_board[row][col] != -1:
            raise ValueError("Recommended cell is not unrevealed")


        x, y = celltoscreen(row, col, board_region, rows, cols, monitor_origin)

        ctypes.windll.user32.SetCursorPos(x, y)

        pyautogui.click()
        moves_made += 1

        #time.sleep(0.5)


    elapsed_time = time.perf_counter() - start_time

    print("\n--- Game Statistics ---")
    print(f"Result: {game_result}")
    print(f"Moves made: {moves_made}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")

    if game_result == "Win":
        total_wins += 1
        total_moves += moves_made
        total_time += elapsed_time
    elif game_result == "Loss":
        total_losses += 1
        total_moves += moves_made
        total_time += elapsed_time



    if game < total_games - 1:
        if game_result not in ("Win", "Loss"):
            print("Stopping: game did not finish normally.")
            break

        restartgame(smiley_region, monitor_origin)
        time.sleep(0.5)



completed_games = total_wins + total_losses

print("\n--- Overall Statistics ---")
print(f"Games completed: {completed_games}")
print(f"Wins: {total_wins}")
print(f"Losses: {total_losses}")

if completed_games > 0:
    win_rate = total_wins / completed_games * 100

    print(f"Win rate: {win_rate:.2f}%")
    print(f"Average moves: {total_moves / completed_games:.2f}")
    print(f"Average time: {total_time / completed_games:.2f} seconds")
