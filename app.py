from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import pandas as pd
import secrets
import phase2_face_liveness as phase2

import phase1_identity
import phase2_face_liveness
import phase3_offline_otp
import phase4_voting
from phase5_results import get_results_data, verify_admin
from flask import Response
import json
import base64
import cv2
from PIL import Image
import time

# ======================================================
# APP CONFIGURATION
# ======================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config["SESSION_PERMANENT"] = False


# ======================================================
# HELPER
# ======================================================

def reset_session():
    session.clear()


# ======================================================
# HOME
# ======================================================

@app.route("/")
def index():
    reset_session()
    return render_template("index.html")


# ======================================================
# PHASE 1 - IDENTITY
# ======================================================

@app.route("/identity", methods=["GET", "POST"])
def identity():

    # ==============================
    # HANDLE FORM SUBMISSION
    # ==============================
    if request.method == "POST":

        voter_id = request.form.get("voter_id", "").strip()

        # 🔹 Check empty input
        if not voter_id:
            return render_template(
                "identity.html",
                error="Please enter Voter ID."
            )

        # 🔹 Verify identity using Phase 1
        result = phase1_identity.verify_identity(voter_id)

        # 🔹 If voter ID invalid
        if not result.get("status"):
            return render_template(
                "identity.html",
                error=result.get("reason", "Invalid Voter ID.")
            )

        voter_data = result.get("data", {})

        # 🔥 BLOCK ALREADY VOTED USERS
        if voter_data.get("has_voted", "").strip().lower() == "yes":
            return render_template(
                "identity.html",
                error="❌ You have already voted. Duplicate voting is not allowed."
            )

        # 🔹 Reset old session safely
        reset_session()

        # 🔹 Store voter details in session
        session["identity_verified"] = True
        session["voter_id"] = voter_data.get("voter_id")
        session["face_id"] = voter_data.get("face_id")
        session["voter_name"] = voter_data.get("name")
        session["village"] = voter_data.get("village")
        session["voting_center"] = voter_data.get("voting_center")

        return redirect(url_for("details"))

    # ==============================
    # LOAD PAGE (GET REQUEST)
    # ==============================
    return render_template("identity.html")

# ======================================================
# NEW VOTER REGISTRATION
# ======================================================
# ======================================================
# NEW VOTER REGISTRATION
# ======================================================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # ===============================
        # GET FORM DATA
        # ===============================
        from datetime import datetime
        aadhaar_id = request.form.get("aadhaar_id", "").strip()
        dob = request.form.get("dob", "").strip()
        mobile = request.form.get("mobile", "").strip()
        name = request.form.get("name", "").strip()
        village = request.form.get("village", "").strip()
        voting_center = request.form.get("voting_center", "").strip()
        captured_images = request.form.get("captured_images")

        # ===============================
        # VALIDATION - FACE CAPTURE
        # ===============================
        if not captured_images:
            return render_template(
                "register.html",
                error="Face capture is mandatory. Please capture 3 images."
            )

        images = json.loads(captured_images)

        if len(images) != 3:
            return render_template(
                "register.html",
                error="Please capture exactly 3 face images."
            )


        # ===============================
        # AGE ELIGIBILITY CHECK (18+)
        # ===============================
        
        try:
            birth_date = datetime.strptime(dob, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
            if age < 18:
                return render_template(
            "register.html",
                    error="You must be at least 18 years old to register."
                )
        except:
            return render_template(
        "register.html",
        error="Invalid Date of Birth."
    )

        # ===============================
        # PREVENT DUPLICATE AADHAAR
        # ===============================
        voter_file = "data/voter_details.csv"
        os.makedirs("data", exist_ok=True)

        if os.path.exists(voter_file):
            df_existing = pd.read_csv(voter_file, dtype=str)
            # Normalize Aadhaar values
            existing_aadhaars = df_existing["aadhaar_id"].astype(str).str.strip()
            if aadhaar_id.strip() in existing_aadhaars.values:
                return render_template(
                    "register.html",
                    error="❌ A voter with this Aadhaar ID already exists."
                )
            next_number = len(df_existing) + 1

     
        else:
            next_number = 1

        # ===============================
        # GENERATE CLEAN SEQUENTIAL IDS
        # ===============================

        # 🔹 Face ID → voter_0XX
        face_id = f"voter_{str(next_number).zfill(3)}"

        # 🔹 Voter ID → 22JR1AXXX
        voter_id = f"22JR1A{str(next_number).zfill(4)}"

        # ===============================
        # CREATE VOTER FOLDER
        # ===============================
        voters_path = os.path.join("static", "images", "voters")
        os.makedirs(voters_path, exist_ok=True)

        save_folder = os.path.join(voters_path, face_id)
        os.makedirs(save_folder, exist_ok=True)

        # ===============================
        # SAVE CAPTURED FACE IMAGES
        # ===============================
        for i, image_data in enumerate(images):

            image_data = image_data.split(",")[1]
            image_bytes = base64.b64decode(image_data)

            with open(os.path.join(save_folder, f"img{i+1}.jpg"), "wb") as f:
                f.write(image_bytes)

        # ===============================
        # SAVE OPTIONAL PROFILE IMAGE
        # ===============================
        uploaded_file = request.files.get("profile_image")

        if uploaded_file and uploaded_file.filename != "":
            uploaded_file.save(
                os.path.join(save_folder, "img.jpg")
            )

        # ===============================
        # SAVE DATA TO CSV
        # ===============================
        new_voter = {
    "voter_id": voter_id,
    "face_id": face_id,
    "name": name,
    "aadhaar_id": aadhaar_id,
    "dob": dob,
    "mobile": mobile,
    "village": village,
    "voting_center": voting_center,
    "has_voted": "No"
}

        if os.path.exists(voter_file):
            df_existing = pd.read_csv(voter_file)
            df_updated = pd.concat(
                [df_existing, pd.DataFrame([new_voter])],
                ignore_index=True
            )
        else:
            df_updated = pd.DataFrame([new_voter])

        df_updated.to_csv(voter_file, index=False)

        # ===============================
        # SUCCESS RESPONSE
        # ===============================
        return render_template(
            "register.html",
            success=True,
            voter_id=voter_id
        )

    return render_template("register.html")
# ======================================================
# DETAILS CONFIRMATION
# ======================================================

@app.route("/details", methods=["GET", "POST"])
def details():

    if not session.get("identity_verified"):
        return redirect(url_for("identity"))

    face_id = session.get("face_id")
    folder_path = os.path.join("static", "images", "voters", face_id)

    image_file = "img1.jpg"

    if os.path.exists(folder_path):
        files = os.listdir(folder_path)
        if "img.jpeg" in files:
            image_file = "img.jpeg"
        elif "img1.jpg" in files:
            image_file = "img1.jpg"

    image_path = f"images/voters/{face_id}/{image_file}"

    if request.method == "POST":
        session["details_confirmed"] = True
        return redirect(url_for("face_camera"))

    return render_template("details.html", image_path=image_path)


# ======================================================
# PHASE 2 - FACE LIVENESS
# ======================================================
# ======================================================
# FACE INSTRUCTION
# ======================================================

@app.route("/face")
def face():

    if not session.get("details_confirmed"):
        return redirect(url_for("identity"))

    return render_template("face.html")


# ======================================================
# FACE CAMERA
# ======================================================

@app.route("/face_camera")
def face_camera():

    if not session.get("details_confirmed"):
        return redirect(url_for("identity"))

    return render_template("face_camera.html")


# ======================================================
# FACE VERIFICATION API
# ======================================================

@app.route("/api/verify_face", methods=["POST"])
def api_verify_face():

    if not session.get("details_confirmed"):
        return jsonify({"status": False, "message": "Session expired"})

    if "liveness_initialized" not in session:
        phase2_face_liveness.reset_liveness()
        session["liveness_initialized"] = True

    data = request.get_json()
    image_data = data.get("image")

    if not image_data:
        return jsonify({"status": False, "message": "No image received"})

    face_id = session.get("face_id")

    result = phase2_face_liveness.process_frame(face_id, image_data)

    # 🔴 FACE VERIFICATION LOCKED
    if result.get("locked"):
        session.clear()

        return jsonify({
            "status": "LOCKED",
            "message": result.get("message")
        })

    # ✅ FACE VERIFIED
    if result["status"]:
        session["face_verified"] = True
        session.pop("liveness_initialized", None)

        return jsonify({"status": True})

    return jsonify({
        "status": False,
        "message": result.get("message", "Face verification failed")
    })

# ======================================================
# PHASE 3 - OFFICER CONTROLLED OTP
# ======================================================

@app.route("/otp")
def otp():

    if not session.get("face_verified"):
        return redirect(url_for("identity"))

    voter_id = session.get("voter_id")

    if not voter_id:
        return redirect(url_for("identity"))

    if not session.get("otp_session_started"):
        phase3_offline_otp.start_otp_session(session, voter_id)

    return render_template("otp.html")

# ======================================================
# CHECK OTP STATUS (AJAX POLLING)
# ======================================================

@app.route("/check_otp_status")
def check_otp_status():

    voter_id = session.get("voter_id")

    if not voter_id:
        return jsonify({"status": "NO_SESSION"})

    result = phase3_offline_otp.check_otp_status(voter_id)

    if result["status"] == "APPROVED":
        session["otp_verified"] = True

    return jsonify(result)



# ======================================================
# REAL-TIME OTP STREAM (SSE)
# ======================================================


@app.route("/otp_stream")
def otp_stream():

    voter_id = session.get("voter_id")

    if not voter_id:
        return Response(
            "data: {\"status\":\"NO_SESSION\"}\n\n",
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    def event_stream():

        last_status = None

        while True:
            result = phase3_offline_otp.check_otp_status(voter_id)
            current_status = result["status"]

            if current_status != last_status:
                yield f"data: {json.dumps(result)}\n\n"
                last_status = current_status
            if current_status in ["APPROVED","REJECTED","LOCKED"]:
                break

            time.sleep(0.3)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

# ======================================================
# RESEND OTP
# ======================================================

@app.route("/resend_otp")
def resend_otp_route():

    voter_id = session.get("voter_id")

    if not voter_id:
        return jsonify({"status": "NO_SESSION"})

    result = phase3_offline_otp.resend_otp(voter_id)

    # If max attempts reached, clear session
    if result["status"] == "LOCKED":
        session.clear()

    return jsonify(result)
# ======================================================
# PHASE 4 - VOTING
# ======================================================
@app.route("/voting", methods=["GET", "POST"])
def voting():

    voter_id = session.get("voter_id")

    if not voter_id:
        return redirect(url_for("identity"))

    otp_status = phase3_offline_otp.check_otp_status(voter_id)["status"]

    if otp_status != "APPROVED":
        return redirect(url_for("identity"))

    candidates = phase4_voting.load_candidates()

    if request.method == "POST":

        candidate_id = request.form.get("selected_candidate")

        result = phase4_voting.cast_vote(voter_id, candidate_id)

        if result["status"]:
            name = session.get("voter_name")
            reset_session()
            session["voter_name"] = name
            return redirect(url_for("vote_success"))

        error_map = {
            "ALREADY_VOTED": "You have already voted.",
            "INVALID_CANDIDATE": "Invalid candidate selected.",
            "INVALID_VOTER": "Invalid voter."
        }

        return render_template("voting.html",
                               candidates=candidates,
                               error=error_map.get(result.get("reason"),
                                                   "System error occurred."))

    return render_template("voting.html",
                           candidates=candidates)
# ======================================================
# VOTE SUCCESS
# ======================================================

@app.route("/vote_success")
def vote_success():

    name = session.get("voter_name", "Voter")

    return render_template(
        "vote_success.html",
        name=name
    )


# ======================================================
# OFFICER LOGIN
# ======================================================

@app.route("/officer_login", methods=["GET", "POST"])
def officer_login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "officer" and password == "1234":
            
            session["officer"] = True
            return redirect(url_for("officer_dashboard"))

        return render_template("officer_login.html",
                               error="Invalid Officer Credentials")

    return render_template("officer_login.html")


# ======================================================
# OFFICER DASHBOARD
# ======================================================

@app.route("/officer_dashboard")
def officer_dashboard():

    if not session.get("officer"):
        return redirect(url_for("officer_login"))

    otp_file = "data/otp_sessions.csv"
    voters = []

    if os.path.exists(otp_file):
        df = pd.read_csv(otp_file)
        voters = df.to_dict(orient="records")

    waiting = sum(1 for v in voters if v["status"] == "WAITING")
    approved = sum(1 for v in voters if v["status"] == "APPROVED")
    rejected = sum(1 for v in voters if v["status"] == "REJECTED")

    return render_template(
        "officer_dashboard.html",
        voters=voters,
        waiting_count=waiting,
        approved_count=approved,
        rejected_count=rejected
    )


# ======================================================
# APPROVE / REJECT
# ======================================================

@app.route("/approve_otp/<voter_id>")
def approve_otp_route(voter_id):

    phase3_offline_otp.approve_otp(voter_id)

    if session.get("voter_id") == voter_id:
        session["otp_verified"] = True

    return jsonify({"status": "APPROVED"})

@app.route("/reject_otp/<voter_id>")
def reject_otp_route(voter_id):

  
    phase3_offline_otp.reject_otp(voter_id)

    return jsonify({"status": "REJECTED"})


# ======================================================
# ADMIN LOGIN
# ======================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if verify_admin(username, password):
            
            session["admin"] = True
            return redirect(url_for("results"))

        return render_template("admin_login.html",
                               error="Invalid credentials")

    return render_template("admin_login.html")


# ======================================================
# RESULTS
# ======================================================

@app.route("/results")
def results():

    if not session.get("admin"):
        return redirect(url_for("admin"))

    results_data = get_results_data()

    if not results_data:
        return render_template("results.html",
                               results=None,
                               winner="No Data",
                               total=0,
                               cast=0,
                               turnout=0)

    results_list = results_data["data"]
    votes_cast = sum(r["votes"] for r in results_list)

    winner = "Tie Between Multiple Candidates" \
        if results_data["tie"] \
        else results_data["winners"][0].get("leader_name", "Unknown")

    voter_file = "data/voter_details.csv"
    total_voters = len(pd.read_csv(voter_file)) if os.path.exists(voter_file) else 0

    turnout = round((votes_cast / total_voters) * 100, 2) if total_voters else 0

    return render_template("results.html",
                           results=results_list,
                           winner=winner,
                           total=total_voters,
                           cast=votes_cast,
                           turnout=turnout)


# ======================================================
# LOGOUT
# ======================================================

@app.route("/logout")
def logout():
    reset_session()
    return redirect(url_for("index"))


# ======================================================
# RUN (LAN / HOTSPOT ENABLED)
# ======================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
