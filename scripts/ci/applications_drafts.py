#!/usr/bin/env python3
"""
Applications Pipeline - Drafts Job
Creates Gmail drafts for top matched projects (AI prioritized!)
"""

import os
import json
import base64
from email.mime.text import MIMEText
import requests

def get_access_token():
    """Get OAuth access token from refresh token."""
    CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET")
    REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN")
    
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ Gmail credentials not configured!")
        print("   Need: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN")
        return None
    
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    })
    
    if resp.status_code != 200:
        print(f"❌ Token error: {resp.text}")
        return None
    
    return resp.json()["access_token"]

def create_draft(access_token, to, subject, body):
    """Create a Gmail draft."""
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to
    message["subject"] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    resp = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"message": {"raw": raw}}
    )
    
    if resp.status_code == 200:
        return resp.json()["id"]
    else:
        print(f"❌ Draft error: {resp.status_code} - {resp.text}")
        return None

def generate_email_body(project, profile_name, keywords):
    """Generate personalized email body."""
    title = project.get("title", "")
    company = project.get("company", "Sehr geehrte Damen und Herren")
    url = project.get("url", "")
    
    # Personalized intro based on AI or not
    if any(kw in title.lower() for kw in ["ki", "ai", "llm", "ml", "genai", "data scientist"]):
        intro = """als AI/ML-spezialisierter Solution Architect mit laufendem AI-Bachelor an der JKU Linz 
und 25+ Jahren IT-Erfahrung bin ich sehr an diesem Projekt interessiert."""
    else:
        intro = """als Senior Solution/Cloud/DevOps Architect mit 25+ Jahren IT-Erfahrung und 
aktuellen CKA/CKAD-Zertifizierungen bin ich sehr an diesem Projekt interessiert."""
    
    body = f"""Sehr geehrte Damen und Herren,

bezugnehmend auf Ihr Projekt "{title}" - {intro}

Mein Profil in Kürze:
• 25+ Jahre IT-Erfahrung (Bank Austria, 50Hertz, diverse Enterprise-Projekte)
• Cloud/DevOps: AWS, Azure, GCP, Kubernetes (CKA/CKAD 2024), Terraform
• AI/ML: Python, LLM/RAG-Architekturen, aktuell AI-Bachelor JKU Linz (Abschluss Q1/2026)
• Branchen: Energie (KRITIS), Banking, Healthcare, Mobility

Meine Verfügbarkeit: Ab sofort, Remote bevorzugt (≥75%)
Stundensatz: 105€/h (verhandelbar)

Gerne sende ich Ihnen mein detailliertes Profil zu oder stehe für ein kurzes 
Kennenlerngespräch zur Verfügung.

Mit freundlichen Grüßen,
Wolfram Laube

---
Blauweiss EDV e.U.
+43 664 4011521
wolfram.laube@blauweiss-edv.at

Projektlink: {url}
"""
    return body

def main():
    max_drafts = int(os.environ.get("MAX_DRAFTS", "5"))
    profile = os.environ.get("DRAFT_PROFILE", "wolfram")
    
    print(f"📧 Gmail Drafts erstellen (max {max_drafts}, Profil: {profile})")
    print("=" * 60)
    
    # Load matches
    with open("output/matches.json") as f:
        data = json.load(f)
    
    matches = data.get("profiles", {}).get(profile, {}).get("top", [])
    
    if not matches:
        print(f"❌ Keine Matches für Profil '{profile}' gefunden!")
        return
    
    # Filter: nur AI-Projekte oder Top-Score
    ai_matches = [m for m in matches if m.get("is_ai")]
    other_matches = [m for m in matches if not m.get("is_ai")]
    
    # Prioritize AI, then others
    selected = (ai_matches + other_matches)[:max_drafts]
    
    print(f"📋 {len(selected)} Projekte ausgewählt ({sum(1 for m in selected if m.get('is_ai'))} AI)")
    
    # Get token
    access_token = get_access_token()
    if not access_token:
        return
    
    print("✅ Gmail Token erhalten")
    
    # Create drafts
    created = 0
    for i, match in enumerate(selected, 1):
        project = match["project"]
        title = project.get("title", "Projekt")[:50]
        company = project.get("company", "")
        
        # Email details
        # Try to extract recruiter email from company, otherwise use generic
        to_email = ""  # Will be filled manually
        subject = f"Bewerbung: {title}"
        body = generate_email_body(project, profile, match.get("keywords", []))
        
        print(f"\n{i}. {title}...")
        
        draft_id = create_draft(access_token, to_email, subject, body)
        if draft_id:
            print(f"   ✅ Draft erstellt: {draft_id}")
            created += 1
        else:
            print(f"   ❌ Fehler beim Erstellen")
    
    print(f"\n{'=' * 60}")
    print(f"✅ {created}/{len(selected)} Drafts erstellt!")
    print(f"   → Öffne Gmail und füge die Empfänger-Adressen hinzu")

if __name__ == "__main__":
    main()
