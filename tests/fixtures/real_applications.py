"""
Test Fixture: Real Application Data

Canonical test data derived from actual applications.
Used across Unit, Integration, and E2E tests for coherent coverage.

Principle: One real use case, tested at every layer of the pyramid.
"""


# =============================================================================
# FIXTURE: Randstad Archivierung Hamburg (2026-02-05)
# =============================================================================
# This is a real project that exercises the full pipeline:
#   Crawl → Match → QA → Draft → CRM Sync

RANDSTAD_ARCHIVIERUNG_PROJECT = {
    "title": "Java Software Engineer (m/w/d) - Kubernetes / Kafka für Archivierungssystem",
    "company": "Randstad Professional",
    "url": "https://www.gulp.de/gulp2/g/projekte/C01236721",
    "project_id": "C01236721",
    "location": "Hamburg",
    "remote_percentage": None,  # Not specified — must be clarified
    "start_date": "2026-02-23",
    "duration": "bis Ende August 2026",
    "workload": "12 PT/Monat (3.5 Tage/Woche)",
    "description": (
        "Der Archivierungs-Service ist ein Java-basierter Backend-Service, "
        "der in der Kubernetes Umgebung betrieben wird. Er verarbeitet "
        "Archivierungsaufträge ereignisgetrieben und orchestriert die Ablage "
        "von Dokumenten in einem externen Archivsystem. "
        "Entgegennahme von Archivierungsereignissen über Kafka. "
        "Persistente Zwischenspeicherung (Inbox Pattern) zur Ausfallsicherheit. "
        "Aggregation mehrerer Events zu Archivierungsvorgängen. "
        "Orchestrierung mehrstufiger Archivierungsprozesse. "
        "Streaming-basierter Upload von Dokumenten. "
        "Fehlerbehandlung, Retry-Mechanismen und Audit-Fähigkeit."
    ),
    "skills": [
        "Java", "Spring Boot", "Kafka", "Kubernetes",
        "REST-API", "AWS", "S3", "Monitoring", "Logging",
        "verteilte Systeme", "Idempotenz", "DevOps",
        "Dokumentenmanagement", "Archivsystem",
    ],
    "must_have": [
        "Java / Spring Boot",
        "Eventgetriebene Architekturen (Kafka)",
        "Kubernetes Betrieb",
        "Verteilte Systeme, Fehlerbehandlung, Idempotenz",
        "REST-APIs und externe Systemintegrationen",
    ],
    "nice_to_have": [
        "Dokumentenmanagement- oder Archivsysteme",
        "Streaming großer Dateien",
        "AWS (insb. S3)",
        "DevOps (Monitoring, Logging, Health Checks)",
    ],
    "contact": {
        "name": "Matthias Steckiewicz",
        "company": "Randstad Professional",
        "phone": "+49 40 468987785",
        "email": None,
    },
}

RANDSTAD_ARCHIVIERUNG_EXPECTED_MATCH = {
    "min_score": 80,
    "max_score": 95,
    "must_have_keywords_hit": ["java", "spring", "kafka", "kubernetes", "rest"],
    "nice_to_have_keywords_hit": ["aws", "s3", "devops", "monitoring"],
    "profile": "wolfram",
}

RANDSTAD_ARCHIVIERUNG_CSV_ENTRY = {
    "date_recorded": "2026-02-05",
    "project_title": "Java Software Engineer - Kubernetes/Kafka Archivierungssystem",
    "provider": "Randstad Professional / GULP",
    "contact_name": "Matthias Steckiewicz",
    "contact_email": "",
    "phone": "+49 40 468987785",
    "location": "Hamburg (Remote-Anteil klären)",
    "start": "23.02.2026",
    "duration": "bis Ende August 2026",
    "workload": "Teilzeit 12 PT/Monat (3.5 Tage/Woche)",
    "rate_eur_h": "105",
    "status": "versendet",
}

RANDSTAD_ARCHIVIERUNG_DRAFT = {
    "to": "",  # GULP portal, no direct email
    "subject": "Bewerbung: Java Software Engineer K8s/Kafka Archivierungssystem (C01236721)",
    "expected_keywords_in_body": [
        "ICMPD",           # DMS experience (nice-to-have differentiator)
        "50Hertz",         # KRITIS / Kafka reference
        "CKA",             # K8s certification
        "Spring Boot",     # Core requirement
        "Kafka",           # Core requirement
        "105",             # Rate
    ],
    "attachment": "Profil_Laube_w_Summary_DE.pdf",
}

RANDSTAD_ARCHIVIERUNG_CRM_ISSUE = {
    "expected_title": "[Randstad Professional / GULP] Java Software Engineer - Kubernetes/Kafka Archivierungssystem",
    "expected_labels": [
        "status::versendet",
        "rate::105+",
        "tech::java",
        "tech::kubernetes",
        "branche::sonstige",
    ],
}


# =============================================================================
# FIXTURE: Generic Project Templates (for parameterized tests)
# =============================================================================

AI_PROJECT = {
    "title": "KI/ML Engineer - LLM Platform",
    "company": "TechCorp",
    "description": "Building RAG pipelines with LangChain and vector databases",
    "skills": ["Python", "LLM", "RAG", "LangChain", "Kubernetes", "AWS"],
    "location": "Remote",
}

DEVOPS_PROJECT = {
    "title": "DevOps Engineer - Cloud Native Platform",
    "company": "EnergyCo",
    "description": "Kubernetes platform engineering with GitOps and Terraform",
    "skills": ["Kubernetes", "Terraform", "GitLab CI", "AWS", "Helm", "ArgoCD"],
    "location": "Berlin",
}

LOW_MATCH_PROJECT = {
    "title": "SAP ABAP Developer - FI/CO Module",
    "company": "ConsultingAG",
    "description": "ABAP development for SAP FI/CO in automotive sector",
    "skills": ["SAP", "ABAP", "FI/CO", "S/4HANA"],
    "location": "Stuttgart",
}
