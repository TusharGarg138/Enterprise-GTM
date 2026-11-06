"""
Synthetic CRM data generator.
Creates realistic fictional company accounts with consistent FK relationships.
Run: python scripts/generate_synthetic_crm.py
"""
import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # Reproducible data

# ---------------------------------------------------------------------------
# Fictional company data
# ---------------------------------------------------------------------------

COMPANIES = [
    {"company_name": "Nexus Dynamics", "industry": "Technology", "website": "https://nexusdynamics.example.com", "employee_band": "200-500", "company_description": "Enterprise cloud infrastructure platform for distributed teams."},
    {"company_name": "Prism Analytics", "industry": "Analytics", "website": "https://prismanalytics.example.com", "employee_band": "50-200", "company_description": "Real-time business intelligence and data visualization platform."},
    {"company_name": "Vortex Health", "industry": "Healthcare", "website": "https://vortexhealth.example.com", "employee_band": "500-1000", "company_description": "Digital health platform for patient engagement and care coordination."},
    {"company_name": "Apex Financial", "industry": "Finance", "website": "https://apexfinancial.example.com", "employee_band": "1000-5000", "company_description": "Fintech platform for investment management and wealth advisory."},
    {"company_name": "Synapse Robotics", "industry": "Manufacturing", "website": "https://synapserobots.example.com", "employee_band": "50-200", "company_description": "Industrial automation and robotics solutions for manufacturing."},
    {"company_name": "CloudPulse", "industry": "Technology", "website": "https://cloudpulse.example.com", "employee_band": "10-50", "company_description": "DevOps automation and CI/CD pipeline management for startups."},
    {"company_name": "Meridian Retail", "industry": "Retail", "website": "https://meridianretail.example.com", "employee_band": "1000-5000", "company_description": "Omnichannel retail platform connecting physical and digital commerce."},
    {"company_name": "Horizon Logistics", "industry": "Logistics", "website": "https://horizonlogistics.example.com", "employee_band": "500-1000", "company_description": "Supply chain visibility and freight management platform."},
    {"company_name": "Cipher Security", "industry": "Cybersecurity", "website": "https://ciphersecurity.example.com", "employee_band": "50-200", "company_description": "Zero-trust security platform for hybrid enterprise environments."},
    {"company_name": "Lumina Education", "industry": "Education", "website": "https://luminaedu.example.com", "employee_band": "200-500", "company_description": "Online learning management system for professional development."},
    {"company_name": "Spectra Media", "industry": "Media", "website": "https://spectramedia.example.com", "employee_band": "50-200", "company_description": "Content distribution platform for digital publishers."},
    {"company_name": "Forge Manufacturing", "industry": "Manufacturing", "website": "https://forgemfg.example.com", "employee_band": "1000-5000", "company_description": "Smart factory solutions with IoT integration for discrete manufacturing."},
    {"company_name": "Pivot Consulting", "industry": "Professional Services", "website": "https://pivotconsulting.example.com", "employee_band": "10-50", "company_description": "Digital transformation advisory for mid-market enterprises."},
    {"company_name": "Atlas Energy", "industry": "Energy", "website": "https://atlasenergy.example.com", "employee_band": "500-1000", "company_description": "Renewable energy management and grid optimization platform."},
    {"company_name": "Nova Pharma", "industry": "Pharmaceutical", "website": "https://novapharma.example.com", "employee_band": "1000-5000", "company_description": "Clinical trial management and regulatory compliance software."},
    {"company_name": "Drift Payments", "industry": "Fintech", "website": "https://driftpayments.example.com", "employee_band": "50-200", "company_description": "API-first payment orchestration platform for global e-commerce."},
    {"company_name": "Summit Real Estate", "industry": "Real Estate", "website": "https://summitre.example.com", "employee_band": "10-50", "company_description": "Property management and tenant experience platform for commercial real estate."},
    {"company_name": "Flare Marketing", "industry": "Marketing", "website": "https://flaremarketing.example.com", "employee_band": "10-50", "company_description": "AI-powered marketing automation and campaign attribution platform."},
    {"company_name": "Titan Aerospace", "industry": "Aerospace", "website": "https://titanaero.example.com", "employee_band": "1000-5000", "company_description": "Aerospace simulation and mission planning software."},
    {"company_name": "Echo Telecom", "industry": "Telecommunications", "website": "https://echotelecom.example.com", "employee_band": "5000+", "company_description": "Network management and 5G infrastructure orchestration platform."},
]

FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry", "Iris", "James", "Karen", "Leo", "Maria", "Nick", "Olivia", "Paul", "Quinn", "Rachel", "Sam", "Tara"]
LAST_NAMES = ["Anderson", "Brown", "Chen", "Davis", "Evans", "Foster", "Garcia", "Harris", "Ingram", "Johnson", "Kim", "Lee", "Martinez", "Nelson", "Ortega", "Patel", "Quinn", "Rivera", "Singh", "Torres"]
ROLES = ["CTO", "VP Sales", "Head of Engineering", "Director of IT", "CISO", "VP Operations", "COO", "CFO", "Head of Product", "Director of Finance", "VP Marketing", "Chief Digital Officer"]

ACTIVITY_TYPES = ["call", "email", "meeting", "demo", "note"]
OPPORTUNITY_STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]

def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def random_email(name: str, company: str) -> str:
    first, last = name.split(" ", 1)
    domain = company.lower().replace(" ", "").replace(".", "") + ".example.com"
    return f"{first.lower()}.{last.lower()}@{domain}"

def random_date(start_days_ago: int, end_days_ago: int) -> str:
    days = random.randint(end_days_ago, start_days_ago)
    dt = datetime.utcnow() - timedelta(days=days)
    return dt.strftime("%Y-%m-%d")

def generate_contacts(companies: list[dict]) -> list[dict]:
    contacts = []
    for company in companies:
        # 1-4 contacts per company
        num_contacts = random.randint(1, 4)
        for _ in range(num_contacts):
            name = random_name()
            contacts.append({
                "account_name": company["company_name"],
                "name": name,
                "role": random.choice(ROLES),
                "email": random_email(name, company["company_name"]),
            })
    return contacts

def generate_activities(companies: list[dict]) -> list[dict]:
    activities = []
    for company in companies:
        # Risk profiles: some companies have recent activity, some stale, some none
        risk_profile = random.choices(
            ["healthy", "aging", "stale", "inactive"],
            weights=[40, 25, 25, 10],
        )[0]

        if risk_profile == "healthy":
            num = random.randint(3, 8)
            date_range = (30, 0)  # Last 30 days
        elif risk_profile == "aging":
            num = random.randint(2, 5)
            date_range = (120, 31)  # 31-120 days ago
        elif risk_profile == "stale":
            num = random.randint(1, 3)
            date_range = (365, 121)  # 121-365 days ago
        else:
            num = 0
            date_range = (365, 0)

        for _ in range(num):
            notes_options = [
                "Discussed product roadmap and pricing.",
                "Demo completed. Prospect showed strong interest.",
                "Follow-up call scheduled for next week.",
                "Sent proposal document for review.",
                "No answer — left voicemail.",
                "Meeting postponed. Rescheduling in progress.",
                "Technical questions about API integration.",
                "Budget approval pending Q4.",
                "Positive feedback on POC results.",
                "Internal stakeholder alignment in progress.",
            ]
            activities.append({
                "account_name": company["company_name"],
                "activity_type": random.choice(ACTIVITY_TYPES),
                "activity_date": random_date(*date_range),
                "notes": random.choice(notes_options),
            })

    return activities

def generate_opportunities(companies: list[dict]) -> list[dict]:
    opportunities = []
    for company in companies:
        # Not all companies have opportunities
        if random.random() < 0.8:
            num = random.randint(1, 3)
            for _ in range(num):
                stage = random.choice(OPPORTUNITY_STAGES)
                deal_base = random.choice([10000, 25000, 50000, 100000, 250000])
                deal_value = deal_base + random.randint(-2000, 5000)

                # Close date: future for active, past for stalled/closed
                if stage in ("closed_won", "closed_lost"):
                    close_date = random_date(180, 30)
                elif stage in ("negotiation", "proposal"):
                    close_date = (datetime.utcnow() + timedelta(days=random.randint(14, 90))).strftime("%Y-%m-%d")
                else:
                    close_date = (datetime.utcnow() + timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d")

                opportunities.append({
                    "account_name": company["company_name"],
                    "stage": stage,
                    "deal_value": deal_value,
                    "close_date": close_date,
                })

    return opportunities


def write_csv(data: list[dict], path: str) -> None:
    if not data:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"Written: {path} ({len(data)} rows)")


if __name__ == "__main__":
    base = Path(__file__).parent.parent / "data" / "sample_crm"

    contacts = generate_contacts(COMPANIES)
    activities = generate_activities(COMPANIES)
    opportunities = generate_opportunities(COMPANIES)

    write_csv(COMPANIES, str(base / "accounts.csv"))
    write_csv(contacts, str(base / "contacts.csv"))
    write_csv(activities, str(base / "activities.csv"))
    write_csv(opportunities, str(base / "opportunities.csv"))

    print(f"\nGenerated synthetic CRM data:")
    print(f"  Accounts: {len(COMPANIES)}")
    print(f"  Contacts: {len(contacts)}")
    print(f"  Activities: {len(activities)}")
    print(f"  Opportunities: {len(opportunities)}")
    print(f"\nFiles saved to: {base}")
