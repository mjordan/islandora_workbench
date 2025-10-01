"""
Script to generate tiles for an image viewed using the Mirador Viewer by rendering the node.
Also takes a screenshot of the page for quick QA of results. Input is a file containing a list
of node IDs for nodes with an Islandora Model of Page or Image.
"""

import sys
import os
from time import sleep
import re
import logging
from pathlib import Path

from ruamel.yaml import YAML
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import cv2
import numpy as np

workbench_config_file = sys.argv[1]
node_id_to_warm = sys.argv[2]

#################################
### Configuration variables. ####
#################################

yaml = YAML()
with open(workbench_config_file, "r") as stream:
    config = yaml.load(stream)

log_file_path = "tile_warmer.log"
# screenshots_dir_path must exist.
screenshots_dir_path = "/tmp/screenshots"
base_url = config["host"].rstrip("/")

# We pause to allow the tiles to be generated. It's also at
# this point that the screenshot is taken.
sleep_length = 35

# % of pixels in image within gray range.
large_gray_area_threshold = 75
# Define the gray range (pure black is 0, pure white is 255).
lower_gray = 235
upper_gray = 255

logging.basicConfig(
    filename=log_file_path,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--start-maximized")


#################
### Functions ###
#################


def get_screenshot_filename(url):
    return re.sub("[^0-9a-zA-Z]+", "_", url)


def mirador_is_empty(screenshot_file_path):
    """Attempt to determine if the screenshot contains an empty
    (i.e. all gray) Mirador Viewer by calculating the ratio
    of gray pixels to the total number of pixels in the cropped image.

    Returns True if the image did not appear to be fully tiled
    (i.e., the image is mostly gray pixels), False if it did
    appear to be successfully tiled (i.e., the image is not mostly
    gray pixels).
    """
    # Load the image.
    image = cv2.imread(screenshot_file_path)

    # Convert it to grayscale.
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Get the width of the image.
    dimensions = gray_image.shape
    width = dimensions[1]
    # Crop the image to remove stuff below the Mirador Viewer,
    # making for a more accurate proportion of gray pixels.
    gray_image_cropped = gray_image[0:width, 0:width]

    # Apply thresholding to get the gray areas.
    thresh, gray_mask = cv2.threshold(
        gray_image_cropped, lower_gray, upper_gray, cv2.THRESH_BINARY
    )

    # Get the total number of pixels in the image.
    total_pixels = gray_image_cropped.size

    # Get the number of gray (within the range) pixels in the image.s
    gray_pixel_count = np.sum(gray_mask == 255)

    # Get the percentage of gray area in the image.
    gray_area_percentage = (gray_pixel_count / total_pixels) * 100

    if gray_area_percentage > large_gray_area_threshold:
        return True
    else:
        return False


def render_node(url, screenshot_file_path):
    """Hits the node with Chrome (via Selenium) to trigger Cantaloupe to
    generate and cache the tiles.
    """
    try:
        driver = webdriver.Chrome(options=chrome_options)

        driver.get(url)
        sleep(sleep_length)
        required_width = driver.execute_script(
            "return document.documentElement.scrollWidth"
        )
        required_height = driver.execute_script(
            "return document.documentElement.scrollHeight"
        )
        driver.set_window_size(required_width, required_height)
        driver.save_screenshot(screenshot_file_path)
        driver.quit()
    except Exception as e:
        logging.error(
            f"Attempt to generate IIIF tiles for {url} encountered an error: {e}"
        )

    outcome = mirador_is_empty(screenshot_file_path)
    if outcome is True:
        logging.warning(f"Mirador viewer for node {url} does not appear to show image.")
    else:
        logging.info(f"Mirador viewer for node {url} appears to show image.")


def warm_url(node_id):
    """Processes a single node by hitting it with Selenium. If the resulting
    screenshot shows that the tiling was incomplete, retry it.
    """
    url = f"{base_url}/node/{node_id}"
    print(f"Tiling image for {url}.")
    # screenshot_filename = re.sub("[^0-9a-zA-Z]+", "_", url)
    screenshot_filename = get_screenshot_filename(url)
    screenshot_file_path = os.path.join(
        screenshots_dir_path, screenshot_filename + ".png"
    )
    render_node(url, screenshot_file_path)


##########################
### Main script logic. ###
##########################

if __name__ == "__main__":
    warm_url(node_id_to_warm)
