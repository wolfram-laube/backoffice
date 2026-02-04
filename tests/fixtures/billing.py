# Billing Test Fixtures
# Used by test_billing_*.py

import json
from pathlib import Path

# Sample clients.yaml content
SAMPLE_CONFIG = {
    "consultants": {
        "wolfram": {
            "name": "Wolfram Laube",
            "gitlab_username": "wolfram.laube",
            "email": "wolfram@blauweiss-edv.com"
        },
        "ian": {
            "name": "Ian Matejka",
            "gitlab_username": "ian.matejka",
            "email": "ian.matejka@gmail.com"
        }
    },
    "clients": {
        "testclient": {
            "name": "Test Client GmbH",
            "short": "TST",
            "address": {
                "street": "Teststraße 1",
                "city": "12345 Teststadt"
            },
            "reg_id": "HRB 12345",
            "vat_id": "DE123456789",
            "contract_number": "TEST-001",
            "template": "rechnung-de",
            "currency": "EUR",
            "gitlab_label": "client:testclient",
            "billing_email": "billing@testclient.de",
            "rates": {
                "remote": 105,
                "onsite": 120
            },
            "approver": {
                "name": "Max Mustermann",
                "title": "Projektleiter"
            },
            "consultants": ["wolfram", "ian"]
        }
    }
}

# Sample GraphQL API response for time entries
SAMPLE_GRAPHQL_RESPONSE = {
    "data": {
        "project": {
            "issues": {
                "nodes": [
                    {
                        "title": "Implement feature X",
                        "iid": "42",
                        "webUrl": "https://gitlab.com/test/project/-/issues/42",
                        "timelogs": {
                            "nodes": [
                                {
                                    "spentAt": "2026-01-15T10:00:00Z",
                                    "timeSpent": 14400,  # 4 hours in seconds
                                    "note": "Backend implementation",
                                    "user": {
                                        "username": "wolfram.laube"
                                    }
                                },
                                {
                                    "spentAt": "2026-01-16T10:00:00Z",
                                    "timeSpent": 7200,  # 2 hours
                                    "note": "Code review",
                                    "user": {
                                        "username": "wolfram.laube"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "title": "Fix bug Y",
                        "iid": "43",
                        "webUrl": "https://gitlab.com/test/project/-/issues/43",
                        "timelogs": {
                            "nodes": [
                                {
                                    "spentAt": "2026-01-15T14:00:00Z",
                                    "timeSpent": 3600,  # 1 hour
                                    "note": "Debugging",
                                    "user": {
                                        "username": "wolfram.laube"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
}

# Expected consolidated entries from SAMPLE_GRAPHQL_RESPONSE
EXPECTED_CONSOLIDATED_ENTRIES = {
    15: [
        (4.0, "Implement feature X: Backend implementation"),
        (1.0, "Fix bug Y: Debugging")
    ],
    16: [
        (2.0, "Implement feature X: Code review")
    ]
}

# Sample timesheet sync.json
SAMPLE_SYNC_DATA = {
    "client_id": "testclient",
    "consultant_id": "wolfram",
    "year": 2026,
    "month": 1,
    "lang": "de",
    "total_hours": 7.0,
    "entries": {
        "15": [(4.0, "Implement feature X"), (1.0, "Fix bug Y")],
        "16": [(2.0, "Code review")]
    },
    "generated_at": "2026-01-20T10:00:00",
    "api_source": "graphql"
}

# Sample sequences.yaml
SAMPLE_SEQUENCES = {
    "invoices": {
        "prefix": "AR",
        "next_number": 42,
        "format": "{prefix}-{number:03d}"
    }
}

# Sample Typst output for timesheet
EXPECTED_TIMESHEET_TYP_CONTAINS = [
    "#set page(",
    "Test Client GmbH",
    "Wolfram Laube",
    "Januar 2026",
    "105",  # Rate
    "7.0",  # Total hours or similar
]

# Sample Typst output for invoice
EXPECTED_INVOICE_TYP_CONTAINS = [
    "#set page(",
    "Rechnung",
    "Test Client GmbH",
    "AR-042",  # Invoice number
    "EUR",
]


def create_temp_config(tmp_path: Path) -> Path:
    """Create temporary config directory with test fixtures."""
    import yaml
    
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Write clients.yaml
    with open(config_dir / "clients.yaml", "w") as f:
        yaml.dump(SAMPLE_CONFIG, f)
    
    # Write sequences.yaml
    with open(config_dir / "sequences.yaml", "w") as f:
        yaml.dump(SAMPLE_SEQUENCES, f)
    
    return config_dir


def create_temp_templates(tmp_path: Path) -> Path:
    """Create temporary templates directory."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Minimal timesheet template
    timesheet_typ = '''
#set page(paper: "a4", margin: 2cm)
#set text(font: "Arial", size: 11pt)

= Timesheet

*Client:* #client_name \\
*Consultant:* #consultant_name \\
*Period:* #period \\
*Rate:* #rate EUR/h \\

== Entries

#entries_table

*Total:* #total_hours hours \\
*Amount:* #total_amount EUR
'''
    
    with open(templates_dir / "timesheet.typ", "w") as f:
        f.write(timesheet_typ)
    
    # Minimal invoice template
    invoice_typ = '''
#set page(paper: "a4", margin: 2cm)
#set text(font: "Arial", size: 11pt)

= Rechnung #invoice_number

*An:* #client_name \\
#client_address

== Positionen

#line_items

*Summe:* #total_amount #currency
'''
    
    with open(templates_dir / "rechnung-de.typ", "w") as f:
        f.write(invoice_typ)
    
    return templates_dir
