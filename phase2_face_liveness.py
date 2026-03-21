import cv2
import os
import base64
import numpy as np
import face_recognition
import random

# ================= CONFIG =================

DATASET_DIR = "static/images/voters/"
MATCH_TOLERANCE = 0.45
NOSE_MOVEMENT_THRESHOLD = 12
BLINK_THRESHOLD = 4
MAX_ATTEMPTS = 3   # 🔒 Maximum allowed failures

# ================= GLOBAL STATE =================

liveness_state = {}

# ================= RESET =================

def reset_liveness():
    global liveness_state

    challenges = [
        "BLINK",
        "TURN_LEFT",
        "TURN_RIGHT",
        "LOOK_UP",
        "LOOK_DOWN"
    ]

    liveness_state = {
        "face_matched": False,
        "challenge": random.choice(challenges),
        "challenge_done": False,
        "neutral_x": None,
        "neutral_y": None,
        "known_encoding": None,
        "attempt_count": 0   # 🔥 Track failures
    }

# ================= LOAD REGISTERED FACE =================

def load_registered_face(face_id):

    folder = os.path.join(DATASET_DIR, face_id)
    if not os.path.exists(folder):
        return None

    for file in os.listdir(folder):
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(folder, file)
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                return encodings[0]

    return None

# ================= DECODE =================

def decode_base64_image(frame_data):
    header, encoded = frame_data.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

# ================= MAIN =================

def process_frame(face_id, frame_data):

    global liveness_state

    if not liveness_state:
        reset_liveness()

    # 🔒 Check attempt limit
    if liveness_state["attempt_count"] >= MAX_ATTEMPTS:
        return {
            "status": False,
            "locked": True,
            "message": "Face verification failed after 3 attempts."
        }

    try:
        frame = decode_base64_image(frame_data)
    except:
        return {"status": False, "message": "Invalid image data"}

    frame = cv2.resize(frame, (320, 240))
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # ================= STEP 1: FACE MATCH =================

    if not liveness_state["face_matched"]:

        if liveness_state["known_encoding"] is None:
            known = load_registered_face(face_id)
            if known is None:
                return {"status": False, "message": "No registered face found"}
            liveness_state["known_encoding"] = known

        known_encoding = liveness_state["known_encoding"]

        locations = face_recognition.face_locations(rgb, model="hog")

        if len(locations) != 1:
            return {"status": False, "message": "Show exactly one face"}

        encodings = face_recognition.face_encodings(rgb, locations)

        if not encodings:
            return {"status": False, "message": "Face encoding failed"}

        match = face_recognition.compare_faces(
            [known_encoding],
            encodings[0],
            tolerance=MATCH_TOLERANCE
        )

        if not match[0]:
            liveness_state["attempt_count"] += 1   # 🔥 Increase failure count
            remaining = MAX_ATTEMPTS - liveness_state["attempt_count"]

            return {
                "status": False,
                "message": f"Face mismatch. Attempts left: {remaining}"
            }

        liveness_state["face_matched"] = True

        return {
            "status": False,
            "message": f"Face matched. Please {liveness_state['challenge']}"
        }

    # ================= STEP 2: LIVENESS =================

    landmarks_list = face_recognition.face_landmarks(rgb)

    if not landmarks_list:
        return {"status": False, "message": "Face not detected"}

    landmarks = landmarks_list[0]
    challenge = liveness_state["challenge"]

    nose = landmarks["nose_tip"]
    nose_x = np.mean([p[0] for p in nose])
    nose_y = np.mean([p[1] for p in nose])

    if liveness_state["neutral_x"] is None:
        liveness_state["neutral_x"] = nose_x
        liveness_state["neutral_y"] = nose_y
        return {"status": False, "message": f"Please {challenge}"}

    nx = liveness_state["neutral_x"]
    ny = liveness_state["neutral_y"]

    if challenge == "LOOK_UP" and nose_y < ny - NOSE_MOVEMENT_THRESHOLD:
        liveness_state["challenge_done"] = True

    elif challenge == "LOOK_DOWN" and nose_y > ny + NOSE_MOVEMENT_THRESHOLD:
        liveness_state["challenge_done"] = True

    elif challenge == "TURN_LEFT" and nose_x < nx - NOSE_MOVEMENT_THRESHOLD:
        liveness_state["challenge_done"] = True

    elif challenge == "TURN_RIGHT" and nose_x > nx + NOSE_MOVEMENT_THRESHOLD:
        liveness_state["challenge_done"] = True

    elif challenge == "BLINK":
        left_eye = landmarks["left_eye"]
        right_eye = landmarks["right_eye"]

        left_height = abs(left_eye[1][1] - left_eye[5][1])
        right_height = abs(right_eye[1][1] - right_eye[5][1])

        if left_height < BLINK_THRESHOLD and right_height < BLINK_THRESHOLD:
            liveness_state["challenge_done"] = True

    # ================= FINAL =================

    if liveness_state["challenge_done"]:
        reset_liveness()
        return {"status": True}

    return {
        "status": False,
        "message": f"Please {challenge}"
    }
