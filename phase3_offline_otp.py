import random
import time
import pandas as pd
import os

OTP_FILE = "data/otp_sessions.csv"
OTP_VALIDITY = 120  # seconds
MAX_RESEND = 3
AUTO_FILE = "data/auto_mode.txt"

os.makedirs("data", exist_ok=True)


# =====================================================
# GENERATE OTP
# =====================================================

def generate_otp():
    return str(random.randint(100000, 999999))


# =====================================================
# START OTP SESSION
# =====================================================

def start_otp_session(session, voter_id):

    otp = generate_otp()
    auto_mode = get_auto_mode()

    status = "APPROVED" if auto_mode == "ON" else "WAITING"

    data = {
        "voter_id": voter_id,
        "otp": otp,
        "status": status,
        "timestamp": time.time(),
        "resend_count": 0
    }

    df = pd.DataFrame([data])

    if os.path.exists(OTP_FILE):
        old = pd.read_csv(OTP_FILE)
        old = old[old["voter_id"] != voter_id]
        df = pd.concat([old, df])

    df.to_csv(OTP_FILE, index=False)

    session["otp_session_started"] = True
    return True


# =====================================================
# APPROVE OTP
# =====================================================

def approve_otp(voter_id):

    if not os.path.exists(OTP_FILE):
        return False

    df = pd.read_csv(OTP_FILE)
    df.loc[df["voter_id"] == voter_id, "status"] = "APPROVED"
    df.to_csv(OTP_FILE, index=False)
    return True


# =====================================================
# REJECT OTP
# =====================================================

def reject_otp(voter_id):

    if not os.path.exists(OTP_FILE):
        return False

    df = pd.read_csv(OTP_FILE)
    df.loc[df["voter_id"] == voter_id, "status"] = "REJECTED"
    df.to_csv(OTP_FILE, index=False)
    return True


# =====================================================
# RESEND OTP (MAX 3)
# =====================================================

def resend_otp(voter_id):

    if not os.path.exists(OTP_FILE):
        return {"status": "NO_SESSION"}

    df = pd.read_csv(OTP_FILE)
    row_index = df.index[df["voter_id"] == voter_id]

    if len(row_index) == 0:
        return {"status": "NO_SESSION"}

    idx = row_index[0]
    resend_count = int(df.at[idx, "resend_count"])

    if resend_count >= MAX_RESEND:
        df.at[idx, "status"] = "LOCKED"
        df.to_csv(OTP_FILE, index=False)
        return {"status": "LOCKED", "attempts_left": 0}

    new_otp = generate_otp()

    df.at[idx, "otp"] = new_otp
    df.at[idx, "timestamp"] = time.time()
    df.at[idx, "status"] = "WAITING"
    df.at[idx, "resend_count"] = resend_count + 1

    df.to_csv(OTP_FILE, index=False)

    return {
        "status": "RESENT",
        "attempts_left": MAX_RESEND - (resend_count + 1)
    }


# =====================================================
# AUTO MODE CONTROL
# =====================================================

def set_auto_mode(status):
    with open(AUTO_FILE, "w") as f:
        f.write(status)


def get_auto_mode():
    if not os.path.exists(AUTO_FILE):
        return "OFF"
    with open(AUTO_FILE, "r") as f:
        return f.read().strip()


# =====================================================
# CHECK OTP STATUS
# =====================================================

def check_otp_status(voter_id):

    if not os.path.exists(OTP_FILE):
        return {"status": "NO_SESSION"}

    df = pd.read_csv(OTP_FILE)
    row = df[df["voter_id"] == voter_id]

    if row.empty:
        return {"status": "NO_SESSION"}

    record = row.iloc[0]
    resend_count = int(record.get("resend_count", 0))

    if record["status"] == "WAITING":
        if time.time() - float(record["timestamp"]) > OTP_VALIDITY:
            df.loc[df["voter_id"] == voter_id, "status"] = "EXPIRED"
            df.to_csv(OTP_FILE, index=False)

            return {
                "status": "EXPIRED",
                "attempts_left": MAX_RESEND - resend_count
            }

    return {
        "status": record["status"],
        "attempts_left": MAX_RESEND - resend_count
    }
