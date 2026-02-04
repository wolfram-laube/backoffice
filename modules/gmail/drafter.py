"""
Email Drafter
=============
Generates personalized application emails based on profiles and project data.
"""

from pathlib import Path
from typing import Dict, Optional, List, Any

from .profiles import load_profile, get_team_config, get_profile_or_team


class Drafter:
    """Email draft generator with profile support."""
    
    def __init__(self, profile_key: str = "wolfram", config_path: Optional[Path] = None):
        """
        Initialize drafter with a profile.
        
        Args:
            profile_key: Profile or team key (e.g., 'wolfram', 'wolfram_ian')
            config_path: Path to profiles.yaml
        """
        self.config_path = config_path
        self.profile = get_profile_or_team(profile_key, config_path)
        self.profile_key = profile_key
    
    def generate(
        self,
        project_title: str,
        contact_email: str = "",
        project_url: str = "",
        custom_body: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate email data for a project.
        
        Args:
            project_title: Title of the position/project
            contact_email: Recipient email (can be empty)
            project_url: URL to project listing
            custom_body: Override auto-generated body
            
        Returns:
            Dict with to, subject, body, attachments
        """
        subject = self._generate_subject(project_title)
        body = custom_body or self._generate_body(project_title, project_url)
        attachments = self._resolve_attachments()
        
        return {
            "to": contact_email,
            "subject": subject,
            "body": body,
            "attachments": attachments,
            "profile": self.profile_key,
        }
    
    def _generate_subject(self, project_title: str) -> str:
        """Generate email subject."""
        title = project_title[:50] + "..." if len(project_title) > 50 else project_title
        return f"Bewerbung: {title}"
    
    def _generate_body(self, project_title: str, project_url: str = "") -> str:
        """Generate email body based on profile and project."""
        name = self.profile.get("name", "")
        rate = self.profile.get("rate", "105")
        signature = self.profile.get("signature", "")
        
        # Detect project type for tailored intro
        title_lower = project_title.lower()
        body_content = self._get_body_for_project_type(title_lower)
        
        # Check if team or individual
        is_team = "members" in self.profile
        
        if is_team:
            intro = self._get_team_intro(project_title)
        else:
            intro = f"""Sehr geehrte Damen und Herren,

mit großem Interesse habe ich Ihre Ausschreibung "{project_title}" gesehen und bewerbe mich hiermit auf diese Position.

{body_content}"""
        
        footer = f"""
Verfügbarkeit: Ab sofort, 100% Remote
{"Team-Rate" if is_team else "Stundensatz"}: {rate} {"EUR" if rate.isdigit() else ""}

{signature}"""
        
        if project_url:
            footer += f"\n\nProjektlink: {project_url}"
        
        return intro + footer
    
    def _get_body_for_project_type(self, title_lower: str) -> str:
        """Get tailored body based on project keywords."""
        
        if any(kw in title_lower for kw in ["ai", "ki", "llm", "ml", "machine learning", "nlp", "rag", "genai"]):
            return """**AI/ML Qualifikationen:**
- **AI Bachelor JKU Linz** (Abschluss Q1/2026) - Deep Learning, NLP, Computer Vision
- IBM-zertifiziert: Applied AI, Advanced Machine Learning, Advanced Data Science
- Python: 10+ Jahre, TensorFlow, PyTorch, Keras, scikit-learn
- Praktisch: RAG-Pipelines, LLM-Integration, MLOps auf Kubernetes

**Einzigartige Kombination:**
AI-Expertise + 25 Jahre Enterprise-Architektur + CKA/CKAD = 
Ich kann AI-Lösungen nicht nur entwickeln, sondern auch produktionsreif deployen."""

        elif any(kw in title_lower for kw in ["kubernetes", "k8s", "devops", "platform"]):
            return """**Relevante Qualifikationen:**
- CKA + CKAD zertifiziert (2024)
- Kubernetes seit 2016: OpenShift, AKS, EKS, GKE, Vanilla
- Cloud-Architekturen: AWS, Azure, GCP
- CI/CD: GitLab, Jenkins, ArgoCD, Helm

**Aktuelle Referenz:**
50Hertz/Elia Group (2024-2025): IaaS Software Architect für KRITIS-konforme Hybrid-Cloud-Plattform."""

        elif any(kw in title_lower for kw in ["python", "fastapi", "django", "flask"]):
            return """**Python-Expertise (10+ Jahre):**
- Backend: FastAPI, Flask, Django
- Data Science: Pandas, NumPy, scikit-learn
- Async: asyncio, aiohttp, Celery
- DevOps: Poetry, Docker, CI/CD

**Python in Produktion:**
- 50Hertz: Automation für Hybrid-Cloud-Infrastruktur
- Frauscher: ML-Pipelines, Time Series Analysis
- RAG-Pipeline mit LangChain, Vector DBs"""

        elif any(kw in title_lower for kw in ["java", "spring", "jee"]):
            return """**Java-Expertise (25+ Jahre):**
- Spring Boot, Microservices
- Enterprise: Bank Austria, Siemens, DKV, AOK
- OpenShift/Kubernetes: CKA + CKAD zertifiziert

**Referenzen:**
- Deutsche Bahn VENDO: Cloud Architect
- Bank Austria: 7 Jahre Core Banking, Trading"""

        else:
            return """**Profil-Highlights:**
- 25+ Jahre IT-Erfahrung, davon 10+ als Solution Architect
- Python: 10+ Jahre (FastAPI, Django, Pandas, ML-Stack)
- AI Bachelor JKU Linz (Abschluss Q1/2026)
- CKA + CKAD zertifiziert (2024)
- Multi-Cloud: AWS, Azure, GCP

**Branchen:** Banking, Energie (KRITIS), Healthcare, Mobility"""

    def _get_team_intro(self, project_title: str) -> str:
        """Generate team introduction."""
        name = self.profile.get("name", "Team")
        pitch = self.profile.get("pitch", "")
        members = self.profile.get("members", [])
        
        intro = f"""Sehr geehrte Damen und Herren,

wir bewerben uns als Team auf Ihre Ausschreibung "{project_title}".

**Unser Angebot - {pitch}:**
"""
        # Add member highlights
        for member_profile in self.profile.get("member_profiles", []):
            member_name = member_profile.get("name", "")
            skills = member_profile.get("skills", {}).get("primary", [])[:3]
            intro += f"- **{member_name}**: {', '.join(skills)}\n"
        
        return intro
    
    def _resolve_attachments(self) -> List[str]:
        """Resolve attachment paths."""
        attachments = self.profile.get("attachments", [])
        attachments_dir = self.profile.get("attachments_dir", "attachments")
        
        resolved = []
        for att in attachments:
            # Try multiple locations
            candidates = [
                Path(att),  # Absolute or relative
                Path(attachments_dir) / att,  # In attachments dir
                Path("/mnt/project") / att,  # In project mount
            ]
            
            for path in candidates:
                if path.exists():
                    resolved.append(str(path))
                    break
            else:
                # Include anyway, let client warn
                resolved.append(str(Path(attachments_dir) / att))
        
        return resolved


def generate_email(
    project_title: str,
    profile_key: str = "wolfram",
    contact_email: str = "",
    project_url: str = "",
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to generate an email.
    
    Args:
        project_title: Position/project title
        profile_key: Profile or team key
        contact_email: Recipient email
        project_url: Project listing URL
        
    Returns:
        Dict with to, subject, body, attachments
    """
    drafter = Drafter(profile_key=profile_key)
    return drafter.generate(
        project_title=project_title,
        contact_email=contact_email,
        project_url=project_url,
        **kwargs
    )
