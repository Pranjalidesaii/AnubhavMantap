import cv2
import time
import os
import sys
from picamera2 import Picamera2
from gpiozero import RotaryEncoder


# ============================================================
# CONFIGURATION
# ============================================================

# Circular display resolution
DISPLAY_SIZE = (720, 720)

# Camera capture resolution
CAMERA_CAPTURE_SIZE = (1280, 960)

# Zoom settings
ZOOM_MIN = 1.0
ZOOM_MAX = 3.0
ZOOM_STEP = 0.05

# Rotary encoder GPIO pins (BCM numbering)
ENCODER_CLK_PIN = 10
ENCODER_DT_PIN = 24

# Test video
VIDEO_PATH = "test_video.mp4"

# OpenCV window
WINDOW_NAME = "Microscope"


# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def make_fullscreen_window():
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    cv2.setWindowProperty(
        WINDOW_NAME,
        cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN
    )


def square_crop_resize(frame, size):
    """
    Center-crop the frame to a square and resize it
    to the display resolution.
    """

    h, w = frame.shape[:2]

    side = min(h, w)

    y0 = (h - side) // 2
    x0 = (w - side) // 2

    cropped = frame[
        y0:y0 + side,
        x0:x0 + side
    ]

    resized = cv2.resize(
        cropped,
        size,
        interpolation=cv2.INTER_LINEAR
    )

    return resized


# ============================================================
# DIGITAL ZOOM
# ============================================================

def digital_zoom(frame, zoom_factor):
    """
    Simulates digital zoom by cropping the center
    of the image and resizing it back to the
    original resolution.
    """

    if zoom_factor <= 1.0:
        return frame

    h, w = frame.shape[:2]

    new_w = int(w / zoom_factor)
    new_h = int(h / zoom_factor)

    x0 = (w - new_w) // 2
    y0 = (h - new_h) // 2

    cropped = frame[
        y0:y0 + new_h,
        x0:x0 + new_w
    ]

    zoomed = cv2.resize(
        cropped,
        (w, h),
        interpolation=cv2.INTER_LINEAR
    )

    return zoomed


# ============================================================
# CAMERA + ROTARY ENCODER
# ============================================================

def run_zoom_preview():
    """
    Start the Pi Camera Module 3.

    Rotary encoder controls zoom from 1x to 3x.

    When 3x is reached:
        - Camera stops
        - Camera closes
        - Function returns
    """

    print("[*] Starting Raspberry Pi Camera Module 3...")

    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={
            "size": CAMERA_CAPTURE_SIZE,
            "format": "RGB888"
        }
    )

    picam2.configure(config)

    picam2.start()

    # Give camera exposure and white balance time to settle
    time.sleep(2)

    # Number of encoder steps required to reach 3x
    max_steps = int(
        (ZOOM_MAX - ZOOM_MIN) / ZOOM_STEP
    )

    encoder = RotaryEncoder(
        ENCODER_CLK_PIN,
        ENCODER_DT_PIN,
        max_steps=max_steps,
        wrap=False
    )

    # Start at 1x
    encoder.steps = 0

    make_fullscreen_window()

    print("[*] Camera started.")
    print("[*] Rotate encoder to zoom from 1x to 3x.")
    print("[*] Video will automatically start at 3x.")

    try:

        while True:

            # Capture frame from Pi Camera
            frame = picam2.capture_array()

            # Convert RGB to BGR for OpenCV
            frame_bgr = frame

            # Calculate zoom
            zoom_factor = (
                ZOOM_MIN +
                (encoder.steps * ZOOM_STEP)
            )

            # Keep zoom inside limits
            zoom_factor = max(
                ZOOM_MIN,
                min(ZOOM_MAX, zoom_factor)
            )

            # Apply digital zoom
            zoomed = digital_zoom(
                frame_bgr,
                zoom_factor
            )

            # Make it square for the display
            display_frame = square_crop_resize(
                zoomed,
                DISPLAY_SIZE
            )

            # Display zoom level
            cv2.putText(
                display_frame,
                f"Zoom: {zoom_factor:.2f}x",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2
            )

            cv2.imshow(
                WINDOW_NAME,
                display_frame
            )

            # Check keyboard
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):

                print("[*] Q pressed.")
                print("[*] Exiting program.")

                return False

            # Check whether 3x has been reached
            if zoom_factor >= ZOOM_MAX:

                print("[*] 3x zoom reached.")
                print("[*] Stopping camera.")
                print("[*] Starting video.")

                return True

    finally:

        # Always shut down camera properly
        picam2.stop()
        picam2.close()

        encoder.close()

        cv2.destroyAllWindows()

        time.sleep(1)


# ============================================================
# VIDEO PLAYBACK
# ============================================================

def play_video():
    """
    Play the test video fullscreen.

    The video is cropped to a square and resized
    to fill the 720x720 circular display.
    """

    if not os.path.exists(VIDEO_PATH):

        print(
            f"[!] Video not found: {VIDEO_PATH}"
        )

        return

    print(f"[*] Opening video: {VIDEO_PATH}")

    cap = cv2.VideoCapture(VIDEO_PATH)

    if not cap.isOpened():

        print("[!] Could not open video.")

        return

    make_fullscreen_window()

    # Get video's FPS
    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 25

    delay = max(
        1,
        int(1000 / fps)
    )

    print("[*] Video is playing.")
    print("[*] Video will stop when it reaches the end.")

    try:

        while True:

            ret, frame = cap.read()

            # End of video
            if not ret:
                break

            # Crop and resize
            display_frame = square_crop_resize(
                frame,
                DISPLAY_SIZE
            )

            cv2.imshow(
                WINDOW_NAME,
                display_frame
            )

            key = cv2.waitKey(delay) & 0xFF

            # Optional emergency exit
            if key == ord("q"):

                print("[*] Q pressed.")
                print("[*] Exiting.")

                sys.exit(0)

    finally:

        cap.release()

        cv2.destroyAllWindows()


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print()
    print("========================================")
    print("        TELESCOPE TEST PROGRAM")
    print("========================================")
    print()

    # Start camera and zoom
    should_play_video = run_zoom_preview()

    # If 3x was reached, play the video
    if should_play_video:

        play_video()

    print()
    print("[*] Telescope program finished.")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
