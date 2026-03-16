# phase5_results.py

import os
import hashlib
import pandas as pd

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


# ===================== FILE PATHS =====================

CANDIDATE_FILE = os.path.join("data", "candidates.csv")
RESULT_DIR = "results"
CSV_FILE = os.path.join(RESULT_DIR, "results.csv")
PDF_FILE = os.path.join(RESULT_DIR, "results.pdf")


# ===================== ADMIN CREDENTIALS =====================

ADMIN_USER = "admin"
ADMIN_PASS_HASH = hashlib.sha256("admin123".encode()).hexdigest()


# ===================== ADMIN AUTH =====================

def verify_admin(username, password):
    """
    Verifies admin credentials using SHA256 hash.
    """
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return username == ADMIN_USER and password_hash == ADMIN_PASS_HASH



# ===================== LOAD & PROCESS RESULTS =====================

def get_results_data():
    """
    Returns:
    - Sorted result list
    - Winner(s)
    - Tie status
    """

    if not os.path.exists(CANDIDATE_FILE):
        return None

    df = pd.read_csv(CANDIDATE_FILE)

    if df.empty:
        return None

    # Ensure votes column exists
    if "votes" not in df.columns:
        df["votes"] = 0

    # Sort descending by votes
    df = df.sort_values(by="votes", ascending=False)

    max_votes = df.iloc[0]["votes"]
    winners = df[df["votes"] == max_votes]

    return {
        "data": df.to_dict(orient="records"),
        "winners": winners.to_dict(orient="records"),
        "tie": len(winners) > 1
    }


# ===================== EXPORT CSV =====================

def save_csv(df):
    """
    Saves results as CSV file.
    """
    os.makedirs(RESULT_DIR, exist_ok=True)
    df.to_csv(CSV_FILE, index=False)


# ===================== EXPORT PDF (Professional Layout) =====================

def save_pdf(df):
    """
    Generates professional PDF using ReportLab Platypus.
    """
    os.makedirs(RESULT_DIR, exist_ok=True)

    doc = SimpleDocTemplate(PDF_FILE, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    normal_style = styles["Normal"]

    elements.append(Paragraph("Election Results Summary", title_style))
    elements.append(Spacer(1, 0.4 * inch))

    for _, row in df.iterrows():
        
        candidate = row.get("leader_name", "Unknown")

        party = row.get("party_name", "Independent")
        votes = int(row.get("votes", 0))

        text = f"{candidate} ({party}) - {votes} votes"
        elements.append(Paragraph(text, normal_style))
        elements.append(Spacer(1, 0.25 * inch))

    doc.build(elements)


# ===================== GENERATE ALL RESULT FILES =====================

def generate_result_files():
    """
    Creates both CSV and PDF result files.
    Returns True if successful.
    """

    if not os.path.exists(CANDIDATE_FILE):
        return False

    df = pd.read_csv(CANDIDATE_FILE)

    if df.empty:
        return False

    # Ensure votes column exists
    if "votes" not in df.columns:
        df["votes"] = 0

    df = df.sort_values(by="votes", ascending=False)

    save_csv(df)
    save_pdf(df)

    return True
