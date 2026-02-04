"""
Gmail Module
============
Gmail draft creation with profile support and attachments.

Usage:
    from modules.gmail import GmailClient, Drafter, load_profile
    
    # Create draft
    client = GmailClient()
    drafter = Drafter(profile="wolfram")
    email = drafter.generate(project_title="DevOps Engineer", contact_email="hr@example.com")
    client.create_draft(**email)
    
    # Or from CI with JSON
    from modules.gmail import create_drafts_from_b64
    create_drafts_from_b64(os.environ["DRAFTS_JSON_B64"])
"""

from .client import GmailClient
from .drafter import Drafter, generate_email
from .profiles import load_profile, load_profiles, get_team_config

__all__ = [
    "GmailClient",
    "Drafter", 
    "generate_email",
    "load_profile",
    "load_profiles",
    "get_team_config",
]


def create_drafts_from_b64(drafts_b64: str, dry_run: bool = False) -> int:
    """
    Create Gmail drafts from base64-encoded JSON.
    Used by CI pipeline.
    
    Args:
        drafts_b64: Base64-encoded JSON array of draft specs
        dry_run: If True, only print what would be created
        
    Returns:
        Number of drafts created
    """
    import base64
    import json
    
    drafts_json = base64.b64decode(drafts_b64).decode("utf-8")
    drafts = json.loads(drafts_json)
    
    if dry_run:
        for d in drafts:
            print(f"Would create: {d.get('subject', 'No subject')}")
        return len(drafts)
    
    client = GmailClient()
    created = 0
    
    for draft in drafts:
        try:
            draft_id = client.create_draft(
                to=draft.get("to", ""),
                subject=draft.get("subject", ""),
                body=draft.get("body", ""),
                attachments=draft.get("attachments", [])
            )
            if draft_id:
                created += 1
                print(f"✅ Created draft: {draft_id}")
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return created
