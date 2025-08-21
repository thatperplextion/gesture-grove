import cv2
import time
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import handtrackingmodule as htm

# Webcam
wCam, hCam = 640, 480
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0

# Hand detector
detector = htm.handDetector(detectionCon=0.7, maxHands=1)

# Audio control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volRange = volume.GetVolumeRange()
minVol, maxVol = volRange[0], volRange[1]

# Variables
volBar, volPer, area = 400, 0, 0
colorVol = (255, 0, 0)
calibrated_min, calibrated_max = 50, 200  # dynamic calibration values

while True:
    success, img = cap.read()
    if not success:
        break

    # Hand detection
    img = detector.findHands(img, draw=True)
    lmList, bbox = detector.findPosition(img, draw=True)

    if lmList:
        # Filter area for noise
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) // 100
        if 200 < area < 1200:

            # Distance between thumb & index
            length, img, lineInfo = detector.findDistance(4, 8, img)

            # Dynamic calibration
            calibrated_min = min(calibrated_min, length)
            calibrated_max = max(calibrated_max, length)

            # Convert to volume
            volBar = np.interp(length, [calibrated_min, calibrated_max], [400, 150])
            volPer = np.interp(length, [calibrated_min, calibrated_max], [0, 100])
            volPer = 10 * round(volPer / 10)  # smoothing

            # Gestures
            fingers = detector.fingersUp()
            if not fingers[4]:  # Pinky down = adjust volume
                volume.SetMasterVolumeLevelScalar(volPer / 100, None)
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 255, 0), cv2.FILLED)
                colorVol = (0, 255, 0)
            elif fingers == [0, 0, 0, 0, 0]:  # All fingers down = mute
                volume.SetMasterVolumeLevelScalar(0.0, None)
                colorVol = (0, 0, 255)
            else:
                colorVol = (255, 0, 0)

    # Draw UI
    cv2.rectangle(img, (50, 150), (85, 400), colorVol, 3)
    cv2.rectangle(img, (50, int(volBar)), (85, 400), colorVol, cv2.FILLED)
    cv2.putText(img, f'{int(volPer)} %', (40, 450), cv2.FONT_HERSHEY_COMPLEX, 1, colorVol, 3)
    cVol = int(volume.GetMasterVolumeLevelScalar() * 100)
    cv2.putText(img, f'Vol: {cVol}', (400, 50), cv2.FONT_HERSHEY_COMPLEX, 1, colorVol, 3)

    # FPS
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, f'FPS: {int(fps)}', (40, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 3)

    cv2.imshow("Volume Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
