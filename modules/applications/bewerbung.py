#!/usr/bin/env python3
"""
BEWERBUNGS-TOOL
===============
Automatisiertes Tool für Freelance-Bewerbungen.

Zwei Modi:
  a) Gmail im Browser öffnen (schnell, ohne Attachments)
  b) Gmail Draft erstellen (mit Attachments)

Usage:
  python bewerbung.py
  python bewerbung.py --list
  python bewerbung.py --send ibsc --mode browser
  python bewerbung.py --send ibsc --mode draft
"""

import os
import sys
import webbrowser
import base64
import pickle
import argparse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from urllib.parse import quote

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
# PFADE
# ══════════════════════════════════════════════════════════════════════════════

ROOT_DIR = Path(__file__).parent.parent.parent  # modules/applications/ → root
CONFIG_DIR = ROOT_DIR / "config"
ATTACHMENTS_DIR = ROOT_DIR / "attachments"
TEMPLATES_DIR = ROOT_DIR / "templates"

CREDENTIALS_FILE = CONFIG_DIR / "google" / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "google" / "token.pickle"
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"

# ══════════════════════════════════════════════════════════════════════════════
# KONFIGURATION LADEN
# ══════════════════════════════════════════════════════════════════════════════

def load_settings():
    """Lädt settings.yaml oder gibt Defaults zurück."""
    if YAML_AVAILABLE and SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    # Fallback Defaults
    return {
        "bewerber": {
            "name": "Wolfram Laube",
            "telefon": "+43 664 4011521",
            "email": "wolfram.laube@blauweiss-edv.at",
            "stundensatz": 105,
        },
        "attachments": {
            "standard": [
                "Profil_Laube_w_Summary_DE.pdf",
                "Studienerfolg_08900915_1.pdf",
            ],
            "optional": [
                "Profil_Laube_w_Summary_EN.pdf",
                "CV_Ian_Matejka_DE.pdf",
                "CV_Michael_Matejka_DE.pdf",
                "IanMatejkaCV1013MCM.pdf",
                "Michael_Matejka_CV_102025.pdf",
            ]
        },
        "signatur": """Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    }

SETTINGS = load_settings()

# ══════════════════════════════════════════════════════════════════════════════
# BEWERBUNGEN
# ══════════════════════════════════════════════════════════════════════════════

BEWERBUNGEN = {
    "ibsc": {
        "name": "iBSC - Mainframe→AWS Migration (COBOL→Java)",
        "to": None,
        "subject": "Bewerbung: Mainframe to AWS Cloud Migration Expert (COBOL TO Java)",
        "freelancermap": "https://www.freelancermap.de/projekt/mainframe-to-aws-cloud-migration-expert-cobol-to-java-remote-german-speaking",
        "body": """Sehr geehrte Damen und Herren,

mit großem Interesse bewerbe ich mich auf das Projekt "Mainframe to AWS Cloud Migration Expert (COBOL TO Java)".

Warum ich:
- Mainframe-Integration hands-on: JCA-Interface (Java Connector Architecture) von OC4J/Orion zu VISA Mainframe designed und implementiert
- 7 Jahre Bank Austria: Legacy-Systeme, COBOL-Umfeld, Oracle, Mainframe-nahe Architekturen
- AWS/Cloud Migration: Kontinuierlich seit 2016 - von VMs zu Containern, von Monolithen zu Microservices
- Java: 25+ Jahre, Spring Boot bei DB VENDO, Siemens, A.T.U., DKV, AOK
- CKA + CKAD zertifiziert (2024)

Relevante Migrationsprojekte:
- Siemens: bare-metal → Kubernetes → OpenShift AWS
- Deutsche Bahn VENDO: J2EE Monolith → Microservices auf K8s/OpenShift
- DKV: OpenShift on-prem → AWS → Azure

Verfügbarkeit: Ab sofort, 100% Remote
Stundensatz: 105 EUR

Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    },
    
    "formation": {
        "name": "Formation Search - Senior DevOps Architect",
        "to": None,
        "subject": "Bewerbung: Senior DevOps Architect – Cloud Transformation & Platform Engineering",
        "freelancermap": "https://www.freelancermap.de/projekt/senior-devops-architect-m-w-d-cloud-transformation-und-platform-engineering",
        "body": """Sehr geehrte Damen und Herren,

mit großem Interesse bewerbe ich mich auf das Projekt "Senior DevOps Architect (m/w/d) – Cloud Transformation & Platform Engineering".

Profil:
- CKA + CKAD zertifiziert (2024)
- Cloud Transformation: 50Hertz (Hybrid Cloud), AOK (AWS/OpenShift), Miele (Azure AKS), Frauscher (Azure), DKV (OpenShift AWS→Azure)
- Platform Engineering: Self-Service Infrastruktur, CI/CD Pipelines, GitOps mit ArgoCD/Helm

Aktuellste Referenz:
50Hertz/Elia Group (2024-2025): IaaS Software Architect für cloud-native Hybrid-Plattform im Energiesektor (KRITIS). Kubernetes auf GCP, Azure und Vanilla. Terraform, Ansible, GitLab CI/CD.

Verfügbarkeit: Ab sofort, 100% Remote
Stundensatz: 105 EUR

Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    },
    
    "tergos": {
        "name": "Tergos - Senior Cloud & K8s DevOps Consultant",
        "to": None,
        "subject": "Bewerbung: Senior Cloud & Kubernetes DevOps Consultant",
        "freelancermap": "https://www.freelancermap.de/projekt/senior-cloud-und-kubernetes-devops-consultant-m-w-d",
        "body": """Sehr geehrte Damen und Herren,

mit großem Interesse bewerbe ich mich auf das Projekt "Senior Cloud & Kubernetes DevOps Consultant (m/w/d)".

Kubernetes-Expertise:
- CKA + CKAD zertifiziert (August 2024)
- Kubernetes seit 2016: Vanilla, OpenShift, AKS, EKS, GKE
- Hands-on bei: 50Hertz, AOK, Miele, Frauscher, Noventi, DKV, Siemens, Deutsche Bahn, BAMF, BA

Cloud-Erfahrung:
- AWS: DKV, Deutsche Bahn, Siemens, A.T.U.
- Azure: 50Hertz, Miele, Frauscher, DKV
- GCP: 50Hertz

DevOps Toolchain: GitLab CI/CD, ArgoCD, Helm, Terraform, Ansible, Prometheus/Grafana

Verfügbarkeit: Ab sofort, 100% Remote
Stundensatz: 105 EUR

Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    },
    
    "workgenius": {
        "name": "WorkGenius - Mainframe→AWS Migration Architect",
        "to": None,
        "subject": "Bewerbung: Mainframe to AWS-Cloud Migration Architect",
        "freelancermap": "https://www.freelancermap.de/projekt/mainframe-to-aws-cloud-migration-architect-consultant",
        "body": """Sehr geehrte Damen und Herren,

mit großem Interesse bewerbe ich mich auf das Projekt "Mainframe to AWS-Cloud Migration Architect | Consultant".

Legacy + Cloud Kombination:
- Mainframe-Integration hands-on: JCA-Interface (Java Connector Architecture) von OC4J/Orion zu VISA Mainframe designed und implementiert
- Bank Austria (7 Jahre): Core Banking, Trading, DWH - Mainframe-nahe Umgebungen, Oracle, COBOL-Integration
- Cloud Migration seit 2016: Durchgehend VM→Container, Monolith→Microservices
- AWS: DKV, Deutsche Bahn VENDO, Siemens, A.T.U.

Migrations-Track-Record:
- Siemens Spectrum Power 7: bare-metal → K8s → OpenShift AWS
- Deutsche Bahn VENDO: J2EE → Microservices auf OpenShift/AWS
- Bundesagentur für Arbeit: Legacy → Container (Federal Cloud)

CKA + CKAD zertifiziert (2024)

Verfügbarkeit: Ab sofort, 100% Remote
Stundensatz: 105 EUR

Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    },
    
    "globalhr": {
        "name": "Global HR - Java/Spring/OpenShift Architekt (A8954)",
        "to": None,
        "subject": "Bewerbung: Senior Software Architekt Java/Spring Boot/OpenShift/Kubernetes (A8954)",
        "freelancermap": "https://www.freelancermap.de/projekt/auftrag-a8954-senior-software-architekt-java-intellij-spring-boot-openshift-kubernetes-contract",
        "body": """Sehr geehrte Damen und Herren,

mit großem Interesse bewerbe ich mich auf das Projekt "Senior Software Architekt Java IntelliJ Spring Boot OpenShift Kubernetes" (Auftrag A8954).

Technischer Match:
- Java: 25+ Jahre, Spring Boot bei DB VENDO, Siemens, DKV, AOK
- OpenShift: AOK, DKV, Siemens, Deutsche Bahn - hands-on seit 2017
- Kubernetes: CKA + CKAD zertifiziert (August 2024)
- IntelliJ: Primäre IDE seit Jahren

Architektur-Erfahrung:
- 50Hertz/Elia Group: IaaS Software Architect
- Frauscher: Alleinige Architekturverantwortung für Cloud-Transformation
- Deutsche Bahn VENDO: Cloud Architect für digitale Vertriebsplattform

Zur Remote-Regelung: Die Ausschreibung nennt 60% Remote. Aufgrund persönlicher Umstände wäre für mich eine vollständige Remote-Tätigkeit notwendig. Ist hier Spielraum vorhanden? Meine Erfahrung zeigt, dass ich remote genauso effektiv arbeite, mit voller Erreichbarkeit und proaktiver Kommunikation.

Stundensatz: 105 EUR

Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    },
    
    # Beispiele mit E-Mail-Adressen
    "westhouse": {
        "name": "Westhouse - Mainframe Solution Architect",
        "to": "p.hoening@westhouse-consulting.com",
        "subject": "Bewerbung: Mainframe Solution Architect – Cloud Advisory (m/w/d)",
        "freelancermap": "https://www.freelancermap.de/projekt/mainframe-solution-architect-cloud-advisory-m-w-d",
        "body": """Sehr geehrter Herr Hoening,

mit großem Interesse bewerbe ich mich auf das Projekt "Mainframe Solution Architect – Cloud Advisory (m/w/d)".

Mein USP: Legacy + Cloud aus einer Hand

Legacy-Fundament (Bank Austria, 7 Jahre):
- JCA-Interface (Java Connector Architecture) von OC4J/Orion zu VISA Mainframe designed und implementiert
- Core Banking Systeme, Trading, Data Warehouse
- Mainframe-Integration, COBOL-Schnittstellen, Oracle
- ITIL-Prozesse in Großbank-Umgebung

Cloud Advisory (seit 2016):
- Strategische Architekturberatung für Cloud-Transformation
- Technologie-Evaluation und PoCs für Migrationsentscheidungen
- Hands-on Implementation: AWS, Azure, GCP

Behörden-/Konzern-Erfahrung: Deutsche Bahn, BAMF, Bundesagentur für Arbeit, AOK, 50Hertz (KRITIS)

CKA + CKAD zertifiziert (2024)

Zur Remote-Regelung: Aus persönlichen Gründen wäre für mich eine 100% Remote-Tätigkeit ideal. Wäre hier Flexibilität möglich?

Stundensatz: 105 EUR
Verfügbarkeit: Ab sofort

Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    },
    
    "spohr": {
        "name": "Dietrich Spohr - KI-Experte / AI Solution Architect",
        "to": "schmidt-horster@dietrich-spohr.de",
        "subject": "Bewerbung: KI-Experte / AI Solution Architect (m/w/d) - 6+ Monate",
        "freelancermap": "https://www.freelancermap.de/projekt/ki-experte-ai-solution-architect-mwd-6-monate",
        "body": """Sehr geehrter Herr Schmidt-Horster,

mit großem Interesse bewerbe ich mich auf das Projekt "KI-Experte / AI Solution Architect (m/w/d)".

KI-Expertise:
- AI Bachelor JKU Linz (Abschluss Q1/2026)
- IBM-zertifiziert: Applied AI with Deep Learning, Advanced Machine Learning, Advanced Data Science

Praktische KI-Projekte:
- Disy (2023): On-premise LLM mit GPT4All für Knowledge Base, RAG-Pipeline
- Frauscher (15 Mo): ML/MLOps für Predictive Maintenance, Time Series Analysis
- JKU: TensorFlow, Keras, Kubeflow, JupyterHub

Solution Architect Erfahrung:
- 50Hertz/Elia Group: IaaS Software Architect (KRITIS)
- Frauscher: End-to-End Architekturverantwortung ohne Gremienabstimmung
- 25+ Jahre Enterprise-Architekturen

Zur Remote-Regelung: Ich sehe, dass 80% Remote ausgeschrieben ist. Aus persönlichen Gründen wäre für mich eine 100% Remote-Lösung ideal. Wäre hier Flexibilität möglich?

Stundensatz: 105 EUR
Verfügbarkeit: Ab sofort

Mit freundlichen Grüßen,
Wolfram Laube
+43 664 4011521"""
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# GMAIL API
# ══════════════════════════════════════════════════════════════════════════════

SCOPES = ['https://www.googleapis.com/auth/gmail.compose']


def get_gmail_service():
    """Authentifiziert und gibt Gmail Service zurück."""
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("\n❌ Benötigte Pakete nicht installiert!")
        print("   pip install -r requirements.txt")
        return None
    
    creds = None
    
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"\n❌ {CREDENTIALS_FILE} nicht gefunden!")
                print("   Siehe: docs/SETUP_OAUTH.md")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)


def create_message_with_attachments(to, subject, body, attachment_paths):
    """Erstellt MIME-Nachricht mit Attachments."""
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    
    msg_body = MIMEText(body)
    message.attach(msg_body)
    
    for filepath in attachment_paths:
        path = Path(filepath)
        if not path.exists():
            print(f"   ⚠️  Nicht gefunden: {filepath}")
            continue
        
        with open(path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{path.name}"')
        message.attach(part)
        print(f"   📎 {path.name}")
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}


def create_draft(service, message):
    """Erstellt Gmail Draft."""
    draft = service.users().drafts().create(userId='me', body={'message': message}).execute()
    return draft['id']


# ══════════════════════════════════════════════════════════════════════════════
# MODI
# ══════════════════════════════════════════════════════════════════════════════

def open_in_browser(bewerbung):
    """Öffnet Gmail Compose oder freelancermap im Browser."""
    if bewerbung['to']:
        url = (
            f"https://mail.google.com/mail/?view=cm&fs=1"
            f"&to={quote(bewerbung['to'])}"
            f"&su={quote(bewerbung['subject'])}"
            f"&body={quote(bewerbung['body'])}"
        )
        print(f"\n🌐 Öffne Gmail für: {bewerbung['to']}")
        webbrowser.open(url)
    else:
        print(f"\n🌐 Öffne freelancermap...")
        webbrowser.open(bewerbung['freelancermap'])
    
    # Text in Zwischenablage
    try:
        import pyperclip
        pyperclip.copy(bewerbung['body'])
        print("📋 Text in Zwischenablage kopiert!")
    except ImportError:
        pass


def create_gmail_draft(bewerbung, attachments):
    """Erstellt Gmail Draft mit Attachments."""
    if not bewerbung['to']:
        print("\n❌ Keine E-Mail-Adresse bekannt!")
        print("   → Nutze freelancermap (Modus a)")
        return False
    
    service = get_gmail_service()
    if not service:
        return False
    
    print(f"\n📧 Erstelle Draft für: {bewerbung['to']}")
    print(f"   Betreff: {bewerbung['subject'][:50]}...")
    print(f"\n   Attachments:")
    
    message = create_message_with_attachments(
        bewerbung['to'],
        bewerbung['subject'],
        bewerbung['body'],
        attachments
    )
    
    draft_id = create_draft(service, message)
    
    print(f"\n✅ Draft erstellt!")
    draft_url = "https://mail.google.com/mail/#drafts"
    print(f"\n🔗 Öffne: {draft_url}")
    
    webbrowser.open(draft_url)
    return True


# ══════════════════════════════════════════════════════════════════════════════
# ATTACHMENT AUSWAHL
# ══════════════════════════════════════════════════════════════════════════════

def select_attachments():
    """Interaktive Attachment-Auswahl."""
    print("\n📎 Attachments:")
    
    standard = SETTINGS['attachments']['standard']
    optional = SETTINGS['attachments']['optional']
    all_attachments = standard + optional
    
    selected = []
    for i, att in enumerate(all_attachments, 1):
        is_standard = att in standard
        marker = "[x]" if is_standard else "[ ]"
        print(f"   {i}. {marker} {att}")
        if is_standard:
            selected.append(att)
    
    print("\n   Enter = Standard")
    print("   Nummern = z.B. '1,2,4' oder 'alle'")
    
    choice = input("\n   Auswahl: ").strip().lower()
    
    if choice == '':
        pass
    elif choice == 'alle':
        selected = all_attachments.copy()
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected = [all_attachments[i] for i in indices if 0 <= i < len(all_attachments)]
        except:
            print("   ⚠️  Ungültig, nutze Standard")
    
    # Pfade auflösen
    paths = []
    for att in selected:
        path = ATTACHMENTS_DIR / att
        if path.exists():
            paths.append(path)
        else:
            print(f"   ⚠️  Nicht gefunden: {path}")
    
    return paths


# ══════════════════════════════════════════════════════════════════════════════
# HAUPTMENÜ
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Bewerbungs-Tool')
    parser.add_argument('--list', action='store_true', help='Bewerbungen auflisten')
    parser.add_argument('--send', metavar='KEY', help='Bewerbung direkt senden')
    parser.add_argument('--mode', choices=['browser', 'draft'], default='browser')
    args = parser.parse_args()
    
    if args.list:
        for key, bew in BEWERBUNGEN.items():
            status = "📧" if bew['to'] else "🌐"
            print(f"  {key:15} {status} {bew['name']}")
        return
    
    if args.send:
        if args.send not in BEWERBUNGEN:
            print(f"❌ Unbekannt: {args.send}")
            return
        bewerbung = BEWERBUNGEN[args.send]
        if args.mode == 'draft':
            attachments = [ATTACHMENTS_DIR / a for a in SETTINGS['attachments']['standard']]
            create_gmail_draft(bewerbung, attachments)
        else:
            open_in_browser(bewerbung)
        return
    
    # Interaktives Menü
    print("""
╔══════════════════════════════════════════════════════════════╗
║           BEWERBUNGS-TOOL - Wolfram Laube                    ║
╠══════════════════════════════════════════════════════════════╣""")
    
    keys = list(BEWERBUNGEN.keys())
    for i, key in enumerate(keys, 1):
        bew = BEWERBUNGEN[key]
        email_status = "📧" if bew['to'] else "🌐"
        print(f"║  {i:2}. {email_status} {bew['name'][:52]:<52} ║")
    
    print("""╠══════════════════════════════════════════════════════════════╣
║  📧 = E-Mail bekannt (Draft möglich)                         ║
║  🌐 = Nur freelancermap                                      ║
╚══════════════════════════════════════════════════════════════╝""")
    
    try:
        choice = input(f"\nProjekt [1-{len(keys)}] (q=Ende): ")
        if choice.lower() == 'q':
            return
        
        idx = int(choice) - 1
        if idx < 0 or idx >= len(keys):
            print("❌ Ungültig")
            return
        
        bewerbung = BEWERBUNGEN[keys[idx]]
        print(f"\n✓ {bewerbung['name']}")
        
        if bewerbung['to']:
            print("\nModus?")
            print("  a) Browser öffnen (Attachments manuell)")
            print("  b) Gmail Draft (mit Attachments)")
            mode = input("\n[a/b]: ").strip().lower()
        else:
            mode = 'a'
        
        if mode == 'b':
            attachments = select_attachments()
            create_gmail_draft(bewerbung, attachments)
        else:
            open_in_browser(bewerbung)
            
    except KeyboardInterrupt:
        print("\n\nAbgebrochen.")
    except ValueError:
        print("❌ Zahl eingeben")


if __name__ == '__main__':
    main()
