import time
import pyautogui
import handtrackingmodule as htm
from src.gesture_grove.gesture_music_control import detector


class MusicGestures:
    def __init__(self, swipe_threshold=80, cooldown=1, x_wrist=None):
        self.prev_x = None
        self.swipe_threshold = swipe_threshold
        self.last_swipe_time = 0
        self.last_pause_time = 0
        self.cooldown = cooldown

        def detect(self, lmList, detector):
            if not lmList or len(lmList) < 1:  # Make sure we have at least one landmark
                return

            # Wrist coordinates
            x_wrist = lmList[0][1]

        # ===== SWIPE DETECTION =====
        if self.prev_x is not None:
            dx = x_wrist - self.prev_x

            # Next track
            if dx > self.swipe_threshold and (time.time() - self.last_swipe_time) > self.cooldown:
                print("Next Track")
                pyautogui.press('nexttrack')
                self.last_swipe_time = time.time()

            # Previous track
            elif dx < -self.swipe_threshold and (time.time() - self.last_swipe_time) > self.cooldown:
                print("Previous Track")
                pyautogui.press('prevtrack')
                self.last_swipe_time = time.time()

        self.prev_x = x_wrist

        # ===== PAUSE/PLAY DETECTION =====
        fingers = detector.fingersUp(lmList)  # Pass lmList here
        if fingers.count(1) == 0 and (time.time() - self.last_pause_time) > self.cooldown:
            print("Pause/Play")
            pyautogui.press('playpause')
            self.last_pause_time = time.time()  # check if any changes
