#!/usr/bin/env python3
"""
PROFILE-DEFINITIONEN
====================
Keywords und Gewichtungen für Wolfram, Ian und Michael.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Profile:
    """Ein Freelancer-Profil mit Keywords für Matching."""
    name: str
    email: str
    phone: str
    cv_de: str
    cv_en: str = None
    rate_min: int = 90
    rate_max: int = 120
    rate_preferred: int = 105
    
    # Keyword-Kategorien mit Gewichtung
    must_have: Set[str] = field(default_factory=set)      # Gewicht: 3
    strong_match: Set[str] = field(default_factory=set)   # Gewicht: 2
    nice_to_have: Set[str] = field(default_factory=set)   # Gewicht: 1
    exclude: Set[str] = field(default_factory=set)        # Ausschluss
    
    # Constraints
    remote_only: bool = True
    languages: List[str] = field(default_factory=lambda: ["Deutsch", "Englisch"])
    min_duration_months: int = 3
    
    def match_score(self, text: str) -> Dict:
        """Berechnet Match-Score für einen Text."""
        text_lower = text.lower()
        
        # Ausschluss prüfen
        for kw in self.exclude:
            if kw.lower() in text_lower:
                return {"score": 0, "percentage": 0, "excluded_by": kw, "matches": {}}
        
        matches = {"must_have": [], "strong_match": [], "nice_to_have": []}
        score = 0
        
        for kw in self.must_have:
            if kw.lower() in text_lower:
                matches["must_have"].append(kw)
                score += 3
        
        for kw in self.strong_match:
            if kw.lower() in text_lower:
                matches["strong_match"].append(kw)
                score += 2
        
        for kw in self.nice_to_have:
            if kw.lower() in text_lower:
                matches["nice_to_have"].append(kw)
                score += 1
        
        # Prozent basierend auf REALISTISCHEM Match
        # Ein gutes Projekt matcht ~5-10 Must-haves, ~3-5 Strong, ~2-3 Nice
        # Das wäre: 5*3 + 4*2 + 2*1 = 25 Punkte = 100%
        realistic_max = 25
        percentage = min(100, int((score / realistic_max) * 100))
        
        # Bonus wenn viele must_have matchen
        must_have_ratio = len(matches["must_have"]) / max(1, min(8, len(self.must_have) // 5))
        if must_have_ratio >= 0.5:
            percentage = min(100, percentage + 10)
        
        return {
            "score": score,
            "percentage": percentage,
            "matches": matches,
            "excluded_by": None
        }


# ══════════════════════════════════════════════════════════════════════════════
# WOLFRAM LAUBE
# ══════════════════════════════════════════════════════════════════════════════

WOLFRAM = Profile(
    name="Wolfram Laube",
    email="wolfram.laube@blauweiss-edv.at",
    phone="+43 664 4011521",
    cv_de="Profil_Laube_w_Summary_DE.pdf",
    cv_en="Profil_Laube_w_Summary_EN.pdf",
    rate_preferred=105,
    rate_min=90,
    rate_max=120,
    remote_only=True,
    
    must_have={
        # Core Skills
        "java", "kubernetes", "k8s", "docker", "devops",
        "cloud", "aws", "azure", "gcp", "terraform", "ansible",
        "ci/cd", "gitlab", "jenkins", "openshift",
        # PYTHON - prominent!
        "python", "python3", "python developer", "python entwickler",
        "fastapi", "flask", "django",
        # Architektur
        "architekt", "architect", "solution", "infrastructure",
        "microservices", "spring boot", "spring",
        # AI/ML - JETZT AUCH MUST-HAVE!
        "ai", "ki", "artificial intelligence", "künstliche intelligenz",
        "machine learning", "ml", "deep learning",
        "llm", "large language model", "rag", "nlp",
    },
    
    strong_match={
        # Python Ecosystem
        "pandas", "numpy", "scipy", "scikit-learn", "sklearn",
        "pytest", "poetry", "pip", "asyncio", "aiohttp",
        "pydantic", "sqlalchemy", "celery", "redis",
        # Zertifizierungen/Spezialisierungen  
        "cka", "ckad", "keycloak", "oauth", "oidc", "iam",
        "kafka", "rabbitmq", "event-driven",
        "prometheus", "grafana", "monitoring", "observability",
        "helm", "argocd", "gitops", "flux",
        # AI/ML Frameworks & Tools
        "tensorflow", "pytorch", "keras", "huggingface",
        "langchain", "llamaindex", "openai", "claude",
        "mlops", "kubeflow", "mlflow", "sagemaker",
        "vector", "embedding", "pinecone", "milvus", "chroma",
        "prompt engineering", "fine-tuning",
        # Branchen
        "bank", "finance", "energie", "energy", "kritis", "kritische infrastruktur",
        "bahn", "railway", "mobility", "healthcare", "gesundheit",
    },
    
    nice_to_have={
        "linux", "bash", "postgresql", "oracle", "mongodb",
        "rest", "api", "graphql", "grpc",
        "agile", "scrum", "kanban", "jira", "confluence",
        "security", "devsecops", "sast", "dast",
        "data lake", "data engineering", "etl",
        "remote", "100% remote", "vollständig remote",
        "jupyter", "notebook", "streamlit", "gradio",
        "computer vision", "speech", "opencv",
        "beautifulsoup", "scrapy", "selenium",
    },
    
    exclude={
        "vor ort pflicht", "keine remote", "onsite only",
        "junior", "werkstudent", "praktikum", "internship",
        "us citizen", "security clearance",  # Nicht erfüllbar
    }
)


# ══════════════════════════════════════════════════════════════════════════════
# IAN MATEJKA
# ══════════════════════════════════════════════════════════════════════════════

IAN = Profile(
    name="Ian Matejka",
    email="ian.matejka@blauweiss-llc.com",  # TODO: Richtige Email
    phone="+1 XXX XXX XXXX",  # TODO
    cv_de="CV_Ian_Matejka_DE.pdf",
    cv_en="IanMatejkaCV1013MCM.pdf",
    rate_preferred=105,
    rate_min=85,
    rate_max=130,
    remote_only=True,
    languages=["Englisch", "Deutsch"],
    
    must_have={
        # Core AI/ML
        "python", "ai", "ki", "machine learning", "ml",
        "llm", "large language model", "gpt", "claude", "openai",
        "rag", "retrieval", "embedding", "vector",
        "nlp", "natural language",
        # ML Frameworks
        "pytorch", "tensorflow", "keras", "huggingface",
        "langchain", "llamaindex", "dspy",
    },
    
    strong_match={
        # MLOps & Infrastructure
        "mlops", "kubeflow", "mlflow", "sagemaker",
        "kubernetes", "k8s", "docker", "aws", "eks",
        "milvus", "pinecone", "weaviate", "chroma",  # Vector DBs
        # Specializations
        "computer vision", "cv", "image", "video",
        "speech", "audio", "whisper",
        "fine-tuning", "training", "inference",
        "prompt engineering", "prompt",
        "agent", "agentic", "mcp", "tool use",
    },
    
    nice_to_have={
        "fastapi", "flask", "streamlit", "gradio",
        "jupyter", "notebook", "pandas", "numpy",
        "sql", "postgresql", "mongodb",
        "git", "ci/cd", "linux",
        "research", "paper", "academic",
        "startup", "product",
    },
    
    exclude={
        "vor ort pflicht", "onsite only", "no remote",
        "junior", "intern", "entry level",
        "java", "c++", "c#",  # Nicht sein Stack
        ".net", "dotnet",
    }
)


# ══════════════════════════════════════════════════════════════════════════════
# MICHAEL MATEJKA
# ══════════════════════════════════════════════════════════════════════════════

MICHAEL = Profile(
    name="Michael Matejka",
    email="michael.matejka@blauweiss-llc.com",  # TODO
    phone="+1 XXX XXX XXXX",  # TODO
    cv_de="CV_Michael_Matejka_DE.pdf",
    cv_en="Michael_Matejka_CV_102025.pdf",
    rate_preferred=120,
    rate_min=100,
    rate_max=150,
    remote_only=True,
    languages=["Englisch", "Deutsch"],
    
    must_have={
        # Business/Strategy
        "project manager", "projektmanager", "program manager",
        "product manager", "product owner",
        "business", "strategy", "strategie",
        "mba", "consulting", "berater",
        # Technical PM
        "technical", "engineering manager", "tech lead",
        "agile", "scrum", "kanban",
    },
    
    strong_match={
        # Domain Expertise
        "oil", "gas", "energy", "energie", "petroleum",
        "reservoir", "simulation", "drilling",
        "data analytics", "analytics", "bi", "business intelligence",
        "ai", "ki", "machine learning", "automation",
        # Leadership
        "team lead", "leadership", "management",
        "stakeholder", "executive", "c-level",
        "transformation", "change management",
        "m&a", "merger", "acquisition",
    },
    
    nice_to_have={
        "sql", "python", "excel", "powerbi", "tableau",
        "sap", "oracle", "salesforce",
        "pmp", "prince2", "safe",
        "budget", "p&l", "financial",
        "international", "global", "remote",
    },
    
    exclude={
        "developer", "entwickler", "programmer", "coder",
        "junior", "entry level", "intern",
        "hands-on coding", "full-time coding",
    }
)


# ══════════════════════════════════════════════════════════════════════════════
# KOMBINATIONEN
# ══════════════════════════════════════════════════════════════════════════════

PROFILES = {
    "wolfram": WOLFRAM,
    "ian": IAN,
    "michael": MICHAEL,
}

# Team-Kombinationen für komplexe Projekte
TEAM_COMBOS = {
    "wolfram_ian": {
        "name": "Wolfram + Ian (AI + MLOps + Infrastructure)",
        "profiles": [WOLFRAM, IAN],
        "keywords": {
            # AI/ML Core
            "ai", "ki", "ml", "llm", "rag", "nlp", "genai", "gpt", "chatgpt", "openai",
            "machine learning", "deep learning", "neural", "transformer",
            # MLOps & Infrastructure
            "mlops", "kubernetes", "k8s", "cloud", "aws", "azure", "gcp",
            "platform", "infrastructure", "devops", "docker",
            # Data & Engineering
            "python", "data engineer", "data scientist", "data analytics",
            "tensorflow", "pytorch", "langchain", "huggingface",
            # Roles
            "engineer", "entwickler", "architect", "senior",
        },
        "description": "Doppelte AI-Expertise + Cloud Infrastructure = End-to-End AI Delivery"
    },
    "wolfram_michael": {
        "name": "Wolfram + Michael (Tech + Business)",
        "profiles": [WOLFRAM, MICHAEL],
        "keywords": {
            # Architecture & Tech Leadership
            "architect", "architekt", "solution", "enterprise", "lead", "senior",
            "infrastructure", "platform", "system",
            # Cloud & DevOps
            "cloud", "devops", "kubernetes", "aws", "azure",
            # Management & Strategy
            "transformation", "strategy", "consulting", "berater",
            "project", "program", "management", "agile", "scrum",
            # Business
            "stakeholder", "budget", "delivery", "migration",
        },
        "description": "Technical Architecture + Business Strategy"
    },
    "ian_michael": {
        "name": "Ian + Michael (AI + Business)",
        "profiles": [IAN, MICHAEL],
        "keywords": {
            # AI/ML
            "ai", "ki", "ml", "llm", "genai", "machine learning", "data",
            # Product & Business
            "product", "owner", "strategy", "transformation", "analytics",
            "business", "intelligence", "bi", "dashboard",
            # Roles
            "manager", "lead", "scientist", "analyst",
        },
        "description": "AI/ML Implementation + Business/Product Strategy"
    },
    "all_three": {
        "name": "Wolfram + Ian + Michael (Full Stack Team)",
        "profiles": [WOLFRAM, IAN, MICHAEL],
        "keywords": {
            # Kombination aller Stärken
            "ai", "ki", "ml", "llm", "genai", "platform", "enterprise",
            "transformation", "cloud", "devops", "product", "end-to-end",
            "architect", "engineer", "manager", "senior", "lead",
            "infrastructure", "data", "analytics", "strategy",
        },
        "description": "Complete delivery team: Infra + AI + Business"
    }
}


def get_best_matches(text: str, min_percentage: int = 30) -> List[Dict]:
    """Findet die besten Profile-Matches für einen Text."""
    results = []
    
    for key, profile in PROFILES.items():
        match = profile.match_score(text)
        if match["percentage"] >= min_percentage and not match["excluded_by"]:
            results.append({
                "profile": key,
                "name": profile.name,
                **match
            })
    
    # Sortieren nach Score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


if __name__ == "__main__":
    # Test
    test_text = """
    Senior DevOps Engineer gesucht für Kubernetes-Migration.
    Erfahrung mit AWS, Terraform, CI/CD erforderlich.
    Python-Kenntnisse von Vorteil. 100% Remote möglich.
    """
    
    print("Test-Matching:")
    print("-" * 50)
    for result in get_best_matches(test_text):
        print(f"{result['name']}: {result['percentage']}%")
        print(f"  Must-have: {result['matches']['must_have']}")
        print(f"  Strong: {result['matches']['strong_match']}")
