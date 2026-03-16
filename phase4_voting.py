# phase4_voting.py

import pandas as pd
import os

# ===================== PATHS =====================

CANDIDATE_CSV = os.path.join("data", "candidates.csv")
VOTER_CSV = os.path.join("data", "voter_details.csv")


# ===================== LOAD CANDIDATES =====================
def load_candidates():
    """
    Returns list of candidates for rendering in voting.html
    """
    if not os.path.exists(CANDIDATE_CSV):
        return []

    df = pd.read_csv(CANDIDATE_CSV)

    # Ensure votes column exists
    if "votes" not in df.columns:
        df["votes"] = 0

    return df.to_dict(orient="records")


# ===================== CHECK IF VOTER EXISTS =====================
def voter_exists(voter_id):
    if not os.path.exists(VOTER_CSV):
        return False

    df = pd.read_csv(VOTER_CSV)

    return not df[df["voter_id"].astype(str) == str(voter_id)].empty


# ===================== CHECK DOUBLE VOTING =====================
def has_already_voted(voter_id):
    """
    Returns True if voter has already voted.
    Blocks unknown voters for safety.
    """
    if not os.path.exists(VOTER_CSV):
        return True  # Safety block

    df = pd.read_csv(VOTER_CSV)

    row = df[df["voter_id"].astype(str) == str(voter_id)]


    if row.empty:
        return True  # Unknown voter blocked

    status = str(row.iloc[0]["has_voted"]).strip().lower()

    return status == "yes"


# ===================== INCREMENT CANDIDATE VOTE =====================
def increment_candidate_vote(candidate_id):

    if not os.path.exists(CANDIDATE_CSV):
        return False

    df = pd.read_csv(CANDIDATE_CSV)
    df["candidate_id"] = df["candidate_id"].astype(str)
    if str(candidate_id) not in df["candidate_id"].values:

        return False

    df.loc[df["candidate_id"] == candidate_id, "votes"] += 1

    df.to_csv(CANDIDATE_CSV, index=False)

    return True


# ===================== MARK VOTER AS VOTED =====================
def mark_voter_voted(voter_id):

    df = pd.read_csv(VOTER_CSV)

    
    df.loc[df["voter_id"].astype(str) == str(voter_id), "has_voted"] = "Yes"


    df.to_csv(VOTER_CSV, index=False)


# ===================== CAST VOTE =====================
def cast_vote(voter_id, candidate_id):
    """
    Main function called from Flask after form submission.
    Handles:
    - Double vote prevention
    - Candidate validation
    - Safe vote update
    """

    # 🚫 1. Check voter exists
    if not voter_exists(voter_id):
        return {"status": False, "reason": "INVALID_VOTER"}

    # 🚫 2. Double voting protection
    if has_already_voted(voter_id):
        return {"status": False, "reason": "ALREADY_VOTED"}

    # 🚫 3. Validate candidate
    if not os.path.exists(CANDIDATE_CSV):
        return {"status": False, "reason": "SYSTEM_ERROR"}

    candidates = pd.read_csv(CANDIDATE_CSV)
    candidates["candidate_id"] = candidates["candidate_id"].astype(str)
    selected = candidates[candidates["candidate_id"] == str(candidate_id)]


    

    if selected.empty:
        return {"status": False, "reason": "INVALID_CANDIDATE"}

    # ✅ 4. Secure vote update
    success = increment_candidate_vote(candidate_id)

    if not success:
        return {"status": False, "reason": "SYSTEM_ERROR"}

    # ✅ 5. Mark voter
    mark_voter_voted(voter_id)

    return {"status": True}
