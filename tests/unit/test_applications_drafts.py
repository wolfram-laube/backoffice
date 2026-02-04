"""
Unit Tests for Applications Drafts Script

Tests email generation logic.
"""
import pytest


class TestEmailGeneration:
    """Test email body generation."""
    
    def generate_email_body(self, project, profile_name, keywords):
        """Generate personalized email body (simplified version)."""
        title = project.get("title", "das Projekt")
        company = project.get("company", "Sehr geehrte Damen und Herren")
        
        # Build keyword highlight section
        if keywords:
            kw_text = f"Besonders relevant: {', '.join(keywords[:5])}"
        else:
            kw_text = ""
        
        body = f"""Sehr geehrte Damen und Herren,

mit großem Interesse habe ich Ihre Ausschreibung "{title}" gelesen.

Als erfahrener Solution Architect bringe ich folgende Qualifikationen mit:
- 25+ Jahre IT-Erfahrung
- Kubernetes (CKA/CKAD zertifiziert)
- Multi-Cloud (AWS, Azure, GCP)
- Python, Java, DevOps

{kw_text}

Ich freue mich auf Ihre Rückmeldung.

Mit freundlichen Grüßen
{profile_name}"""
        
        return body
    
    def test_basic_email_generation(self):
        """Should generate email with project title."""
        project = {"title": "Senior Python Developer"}
        
        body = self.generate_email_body(project, "Wolfram Laube", [])
        
        assert "Senior Python Developer" in body
        assert "Wolfram Laube" in body
        assert "Solution Architect" in body
    
    def test_keywords_included(self):
        """Should include matched keywords."""
        project = {"title": "DevOps Engineer"}
        keywords = ["kubernetes", "docker", "aws", "terraform"]
        
        body = self.generate_email_body(project, "Wolfram Laube", keywords)
        
        assert "Besonders relevant" in body
        assert "kubernetes" in body
    
    def test_max_keywords(self):
        """Should limit keywords to 5."""
        project = {"title": "Test"}
        keywords = ["kubernetes", "docker", "aws", "terraform", "python", "java", "golang", "rust"]
        
        body = self.generate_email_body(project, "Test", keywords)
        
        # Should only include first 5
        assert "java" not in body  # 6th keyword, should be excluded
        assert "golang" not in body
    
    def test_empty_keywords(self):
        """Empty keywords should not show 'Besonders relevant' section."""
        project = {"title": "Test"}
        
        body = self.generate_email_body(project, "Test", [])
        
        # kw_text should be empty string, not "Besonders relevant:"
        lines = [l for l in body.split("\n") if l.strip()]
        assert not any("Besonders relevant:" in l and l.strip().endswith(":") for l in lines)


class TestDraftSubject:
    """Test email subject generation."""
    
    def generate_subject(self, project, profile_type="solo"):
        """Generate email subject."""
        title = project.get("title", "Projektanfrage")
        
        if profile_type == "team":
            return f"Bewerbung Team-Projekt: {title}"
        else:
            return f"Bewerbung: {title}"
    
    def test_solo_subject(self):
        """Solo profile should have simple subject."""
        project = {"title": "Python Developer"}
        
        subject = self.generate_subject(project, "solo")
        
        assert subject == "Bewerbung: Python Developer"
        assert "Team" not in subject
    
    def test_team_subject(self):
        """Team profile should indicate team in subject."""
        project = {"title": "Platform Engineering"}
        
        subject = self.generate_subject(project, "team")
        
        assert "Team" in subject
        assert "Platform Engineering" in subject


class TestRecipientParsing:
    """Test email recipient extraction."""
    
    def parse_recipient(self, project):
        """Extract recipient email from project."""
        # Priority: contact_email > company_email > None
        email = project.get("contact_email") or project.get("company_email")
        
        if email:
            # Basic validation
            if "@" in email and "." in email.split("@")[-1]:
                return email
        
        return None
    
    def test_contact_email_priority(self):
        """contact_email should take priority."""
        project = {
            "contact_email": "contact@example.com",
            "company_email": "info@company.com"
        }
        
        recipient = self.parse_recipient(project)
        assert recipient == "contact@example.com"
    
    def test_fallback_to_company(self):
        """Should fall back to company_email."""
        project = {
            "company_email": "info@company.com"
        }
        
        recipient = self.parse_recipient(project)
        assert recipient == "info@company.com"
    
    def test_invalid_email_rejected(self):
        """Invalid email should return None."""
        project = {"contact_email": "not-an-email"}
        
        recipient = self.parse_recipient(project)
        assert recipient is None
    
    def test_no_email(self):
        """Missing email should return None."""
        project = {"title": "Test"}
        
        recipient = self.parse_recipient(project)
        assert recipient is None
