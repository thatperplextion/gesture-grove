import cv2
import time
import numpy as np
import pyautogui
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import handtrackingmodule as htm
# ================= SETTINGS =================
QUIT_KEY = 'q'          # Press 'q' to quit
SWIPE_THRESHOLD = 80    # Pixels hand must travel (L->R) to count as a swipe
COOLDOWN = 1            # Seconds between actions to avoid double fires
# =============================================

# Webcam setup with resolution cycling
resolutions = [(640, 480), (960, 540), (1280, 720)]
res_index = 0
wCam, hCam = resolutions[res_index]

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

pTime = 0

# Hand Detector
detector = htm.handDetector(detectionCon=0.7, maxHands=1)

# Audio Control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
minVol, maxVol, _ = volume.GetVolumeRange()

# Variables
volBar, volPer, area = 400, 0, 0
calibrated_min, calibrated_max = 50, 200
last_action_time = time.time()
status_text = ""
status_color = (255, 255, 255)
bar_color = (0, 255, 0)

# For smooth animation
smooth_volBar = volBar
smooth_volPer = volPer

# Swipe tracking
swipe_start_time = None
swipe_start_x = None

# Gesture state
start_state = "neutral"     # 'neutral' | 'fist'


while True:
    success, img = cap.read()
    if not success:
        break
    img = cv2.flip(img, 1)
    img = detector.findHands(img, draw=True)
    lmList, bbox = detector.findPosition(img, draw=True)

    if lmList:
        fingers = detector.fingersUp()
        hand_x, hand_y = lmList[0][1], lmList[0][2]  # wrist pos
        current_time = time.time()

        # ========== HIGH-PRIORITY GESTURES ==========
        # Fist = Play/Pause
        if sum(fingers) <= 1 and (current_time - last_action_time > COOLDOWN):
            pyautogui.press("playpause")
            status_text, status_color = "Play/Pause", (255, 255, 0)
            last_action_time = current_time
            start_state = "fist"

        # After a fist: Index+Middle up => +5% volume
        elif start_state == "fist" and fingers == [0, 1, 1, 0, 0] and (current_time - last_action_time > COOLDOWN):
            cur = volume.GetMasterVolumeLevelScalar()  # current volume (0.0 - 1.0)
            new_vol = min(1.0, cur + 0.05)  # add +5%
            volume.SetMasterVolumeLevelScalar(new_vol, None)

            status_text, status_color = f"Vol +5% ({int(new_vol * 100)}%)", (0, 200, 255)
            last_action_time = current_time
            start_state = "neutral"

        # ----------------- PALM TWIST (NEXT TRACK) -----------------
        if fingers == [1, 1, 1, 1, 1]:  # only when palm is open
            # Thumb tip (lm 4) and pinky tip (lm 20)
            thumb_x = lmList[4][1]
            pinky_x = lmList[20][1]

            # If thumb crosses over pinky horizontally => palm twist detected
            if thumb_x > pinky_x and (current_time - last_action_time > COOLDOWN):
                pyautogui.press("nexttrack")
                status_text, status_color = "Next Track", (255, 100, 0)
                last_action_time = current_time

        # ========== VOLUME PINCH ==========
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) // 100
        if 200 < area < 1200:
            if fingers == [1, 1, 0, 0, 0]:  # Thumb+Index up only
                length, img, lineInfo = detector.findDistance(4, 8, img)

                calibrated_min = min(calibrated_min, length)
                calibrated_max = max(calibrated_max, length)

                volBar = np.interp(length, [calibrated_min, calibrated_max], [400, 150])
                volPer = np.interp(length, [calibrated_min, calibrated_max], [0, 100])

                smooth_volBar = int(smooth_volBar + (volBar - smooth_volBar) * 0.2)
                smooth_volPer = int(smooth_volPer + (volPer - smooth_volPer) * 0.2)

                volume.SetMasterVolumeLevelScalar(volPer / 100, None)
                status_text, status_color = f"Volume: {int(volPer)}%", (0, 255, 0)

                # Bar color gradient
                bar_color = (
                    int(255 * (smooth_volPer / 100)),
                    int(255 * (1 - smooth_volPer / 100)),
                    0
                )

        # ================= FUTURISTIC HUD - OPTION B =================
        panel_x, panel_y = hand_x + 120, hand_y - 100

        # Glass panel background
        # ================= FUTURISTIC HUD - OPTION B =================
        panel_width, panel_height = 220, 140

        # Default: panel on the right side of the hand
        panel_x = hand_x + 120
        panel_y = hand_y - 100

        # If hand is too close to right edge → move panel to left
        if panel_x + panel_width > wCam:
            panel_x = hand_x - (panel_width + 120)

        # If hand is too close to top → shift down
        if panel_y < 0:
            panel_y = 20
        # If hand is too close to bottom → shift up
        elif panel_y + panel_height > hCam:
            panel_y = hCam - panel_height - 20

        # Borders
        cv2.rectangle(img, (panel_x, panel_y), (panel_x + 220, panel_y + 140), (0, 255, 255), 2)

        # Labels
        cv2.putText(img, "GESTURE PANEL", (panel_x + 10, panel_y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 255), 2)

        # Dynamic feedback
        if status_text == "Play/Pause":
            cv2.putText(img, "play / pause", (panel_x + 20, panel_y + 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
        elif status_text == "Next Track":
            cv2.putText(img, "next", (panel_x + 80, panel_y + 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 0), 3)
        elif "Vol +5%" in status_text:  # 👈 new condition
            cv2.putText(img, "+5% volume", (panel_x + 20, panel_y + 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 3)
        elif "Volume" in status_text:
            cv2.putText(img, f"Vol: {int(smooth_volPer)}%", (panel_x + 20, panel_y + 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # FPS
    cTime = time.time()
    fps = 1 / (cTime - pTime) if (time.time()-pTime) > 0 else 0
    pTime = cTime
    cv2.putText(img, f'FPS: {int(fps)}', (40, 50),
                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 3)

    # Display
    cv2.imshow("Gesture Music & Volume Control", img)

    # ---- Keys ----
    key = cv2.waitKey(1) & 0xFF
    if key == ord(QUIT_KEY):
        break
    elif key == ord('r'):  # cycle resolution
        res_index = (res_index + 1) % len(resolutions)
        wCam, hCam = resolutions[res_index]
        cap.set(3, wCam)
        cap.set(4, hCam)
        print(f"Requested: {wCam}x{hCam} | Actual: {int(cap.get(3))}x{int(cap.get(4))}")

# Cleanup
cap.release()
cv2.destroyAllWindows()
