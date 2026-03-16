
import os
import pandas as pd
import warnings
import re

warnings.filterwarnings("ignore")

VOTER_CSV = "data/voter_details.csv"

REQUIRED_COLUMNS = [
    "aadhaar_id",
    "voter_id",
    "name",
    "village",
    "voting_center",
    "face_id",
    "has_voted"
]


# ======================================================
# UTILITY: CLEAN AADHAAR
# ======================================================

def clean_aadhaar(value):
    """
    Ensures Aadhaar is stored as clean 12-digit string.
    Removes .0 issue and extra spaces.
    """
    return (
        str(value)
        .replace(".0", "")
        .strip()
    )


# ======================================================
# LOAD DATA SAFELY
# ======================================================

def load_voters():

    if not os.path.exists(VOTER_CSV):
        os.makedirs("data", exist_ok=True)
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_csv(VOTER_CSV, index=False)

    df = pd.read_csv(VOTER_CSV, dtype=str)
    df.fillna("", inplace=True)

    # Ensure correct columns
    if not set(REQUIRED_COLUMNS).issubset(df.columns):
        raise ValueError("CSV columns do not match required format")

    # Clean Aadhaar column permanently in memory
    df["aadhaar_id"] = df["aadhaar_id"].apply(clean_aadhaar)

    return df


# ======================================================
# VERIFY EXISTING VOTER
# ======================================================

def get_voter(voter_input):

    voter_input = clean_aadhaar(voter_input)
    df = load_voters()

    match = df[
        (df["voter_id"].astype(str).str.strip() == voter_input) |
        (df["aadhaar_id"] == voter_input)
    ]


    if match.empty:
        return None

    voter = match.iloc[0]

    if str(voter["has_voted"]).strip().lower() == "yes":
        return "ALREADY_VOTED"

    return {
        "voter_id": voter["voter_id"],
        "face_id": voter["face_id"],
        "name": voter["name"],
        "village": voter["village"],
        "voting_center": voter["voting_center"]
    }


def verify_identity(voter_input):

    try:
        result = get_voter(voter_input)

        if result is None:
            return {
                "status": False,
                "reason": "Invalid Voter ID / Aadhaar ID"
            }

        if result == "ALREADY_VOTED":
            return {
                "status": False,
                "reason": "You have already voted."
            }

        return {
            "status": True,
            "data": result
        }

    except Exception as e:
        return {
            "status": False,
            "reason": str(e)
        }


# ======================================================
# REGISTER NEW VOTER
# ======================================================

def register_new_voter(aadhaar, name, village, center):

    df = load_voters()

    aadhaar = clean_aadhaar(aadhaar)

    # ✅ Validate Aadhaar format
    if not re.fullmatch(r"\d{12}", aadhaar):
        return {
            "status": False,
            "reason": "Aadhaar must be exactly 12 digits."
        }

    # ✅ Strict duplicate check
    if df["aadhaar_id"].eq(aadhaar).any():
        return {
            "status": False,
            "reason": "This Aadhaar ID is already registered."
        }




    if df.empty:
        next_number = 1
    else:
        # Extract only last 4 digits after 22JR1A
        existing_numbers = (
        df["voter_id"]
        .str.extract(r"22JR1A(\d{4})")[0]
        .dropna()
        .astype(int)
        )
        next_number = existing_numbers.max() + 1 if not existing_numbers.empty else 1



    # Generate voter ID → 22JR1A0001 format
    voter_id = f"22JR1A{next_number:04d}"
    # Generate face ID → voter_0XX format
    face_id = f"voter_{next_number:03d}"

    new_row = {
        "aadhaar_id": aadhaar,
        "voter_id": voter_id,
        "name": name.strip(),
        "village": village.strip(),
        "voting_center": center.strip(),
        "face_id": face_id,
        "has_voted": "No"
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(VOTER_CSV, index=False)

    return {
        "status": True,
        "voter_id": voter_id,
        "face_id": face_id
    }
