import mss
from PIL import Image
import cv2
import numpy as np
from pathlib import Path


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

    smiley_center_x = x + round(template_width * best_scale) / 2
    smiley_center_y = y + round(template_height * best_scale) / 2

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
    
    
    return board_image, board_region


def captureboard(board_region):

    screenshot = capturescreen(0)

    left = board_region["left"]
    top = board_region["top"]

    right = left + board_region["width"]
    bottom = top + board_region["height"]

    return screenshot.crop((left, top, right, bottom))
    """ with mss.MSS() as sct:
        monitor = sct.monitors[0]

        region = {
            "left": monitor["left"] + board_region["left"],
            "top": monitor["top"] + board_region["top"],
            "width": board_region["width"],
            "height": board_region["height"]
        }

    print("Combined monitor:", monitor)
    print("Capture region:", region)

    screen = sct.grab({
        "left": 100,
        "top": 100,
        "width": 216,
        "height": 216
    })

    board_image = Image.frombytes("RGB", screen.size, screen.rgb)

    return board_image """


def recognisecell(cell_image):
    gray_cell = cell_image.convert("L")

    x = gray_cell.width // 2
    y = gray_cell.height // 2

    pixel = gray_cell.getpixel((x, y))
    print("Grayscale value:", pixel)

    values = {
        83: -1,
        63: 0,
        189: 1,
        162: 2,
        158: 3,
        179: 4
    }

    return values.get(pixel)


board_image, board_region = findboard(9, 9)

board_image = captureboard(board_region)

cell_image = getcellimage(board_image, 3, 3, 9, 9)

print(recognisecell(cell_image))