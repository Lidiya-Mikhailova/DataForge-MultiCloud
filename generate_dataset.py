import json
import random
from datetime import datetime, timedelta
import uuid

random.seed(42)

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter"
]

COMPANIES = [
    "TechFlow Solutions", "CloudPeak Systems", "DataSphere Inc", "NexGen Analytics",
    "QuantumLeap AI", "SyncBridge Technologies", "Apex Dynamics", "NovaTech Labs",
    "Horizon Ventures", "Stellar Systems", "CoreLogic Group", "Velocity Software",
    "PivotPoint Media", "ScaleForge", "Metric Insights", "StreamLine CRM",
    "Amplify Growth", "PulsePoint Digital", "Vertex Solutions", "Catalyst Networks",
    "Summit Analytics", "Forge Digital", "Elevate Tech", "Nexus Platforms",
    "Prism Data", "Orbit Innovations", "Zenith AI Labs", "Flux Technologies",
    "Arc Systems", "Vortex Analytics", "Momentum Software", "Radius Cloud",
    "Synergy Platforms", "GridWorks Inc", "Pulse Analytics", "Echo Systems",
    "Helix Technologies", "Spark Innovation", "WaveFront Labs", "CoreVault Data"
]

INDUSTRIES = ["SaaS", "Marketing", "CRM", "AI"]
LIFECYCLE_STAGES = ["lead", "marketingqualifiedlead", "opportunity", "customer"]
SOURCES = ["google_ads", "linkedin", "referral", "organic"]
COMPANY_SUFFIXES = ["Inc", "LLC", "Corp", "Ltd", "Solutions", "Group", "Systems", "Technologies"]


def generate_email(first_name: str, last_name: str, company: str) -> str:
    patterns = [
        f"{first_name.lower()}.{last_name.lower()}@{company.lower().replace(' ', '')}.com",
        f"{first_name.lower()}{last_name.lower()}@{company.lower().replace(' ', '')}.com",
        f"{first_name.lower()[0]}{last_name.lower()}@{company.lower().replace(' ', '')}.com",
        f"{first_name.lower()}@{company.lower().replace(' ', '')}.com",
    ]
    return random.choice(patterns)


def generate_invalid_email(reason: str) -> str:
    if reason == "no_at":
        return f"invalidemail{''.join(random.choices('abcdefghij', k=8))}.com"
    elif reason == "no_domain":
        return f"user@"
    elif reason == "no_tld":
        return f"user@domain"
    elif reason == "spaces":
        return f"user name@company.com"
    elif reason == "special_chars":
        return f"user!#$%@company.com"
    elif reason == "empty":
        return ""
    else:
        return "notanemail"


def generate_date(offset_days: int = None, invalid: bool = False):
    if offset_days is None:
        offset_days = random.randint(1, 365)
    
    date = datetime.now() - timedelta(days=offset_days)
    
    if invalid:
        formats = [
            "%Y-%m-%d",  # wrong - missing time
            "%d/%m/%Y",  # wrong format
            "%m-%d-%Y",  # US format
            "%Y/%m/%d %H:%M",  # wrong separator
            "invalid",
            "",
            date.strftime("%Y-%m-%dT%H:%M:%SZ") + " +0000",  # extra timezone
        ]
        return random.choice(formats)
    
    return date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def generate_record(record_id: int, make_invalid: bool = False, invalid_type: str = None):
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    company = random.choice(COMPANIES)
    industry = random.choice(INDUSTRIES)
    lifecycle = random.choice(LIFECYCLE_STAGES)
    source = random.choice(SOURCES)
    
    record = {
        "id": str(record_id),
        "properties": {
            "email": generate_email(first_name, last_name, company),
            "firstname": first_name,
            "lastname": last_name,
            "company": f"{company} {random.choice(COMPANY_SUFFIXES)}",
            "createdate": generate_date(random.randint(1, 180)),
            "industry": industry,
            "lifecyclestage": lifecycle,
            "hs_lead_status": lifecycle_to_status(lifecycle),
            "hs_analytics_source": source,
            "annualrevenue": str(random.randint(50000, 5000000)),
            "numberofemployees": str(random.choice([5, 10, 25, 50, 100, 250, 500, 1000])),
        }
    }
    
    if make_invalid:
        record = apply_invalid(record, invalid_type)
    
    return record


def lifecycle_to_status(lifecycle: str) -> str:
    mapping = {
        "lead": random.choice(["NEW", "OPEN", "CONNECTED"]),
        "marketingqualifiedlead": random.choice(["IN_PROGRESS", "ATTENDED"]),
        "opportunity": random.choice(["WORKING", "IN_PROGRESS"]),
        "customer": "CLOSED"
    }
    return mapping.get(lifecycle, "NEW")


def apply_invalid(record: dict, invalid_type: str = None):
    if invalid_type is None:
        invalid_type = random.choice(["invalid_email", "invalid_date", "missing_field", "duplicate", "null_email"])
    
    properties = record["properties"]
    
    if invalid_type == "invalid_email":
        properties["email"] = generate_invalid_email(random.choice(["no_at", "no_domain", "no_tld", "spaces", "special_chars"]))
    
    elif invalid_type == "invalid_date":
        properties["createdate"] = generate_date(invalid=True)
    
    elif invalid_type == "missing_field":
        missing_field = random.choice(["firstname", "lastname", "company", "industry"])
        properties[missing_field] = None
    
    elif invalid_type == "null_email":
        properties["email"] = None
    
    elif invalid_type == "empty_fields":
        empty_count = random.randint(1, 3)
        fields_to_empty = random.sample(["firstname", "lastname", "company", "jobtitle", "industry"], empty_count)
        for field in fields_to_empty:
            properties[field] = None
    
    elif invalid_type == "duplicate":
        record["id"] = str(random.randint(1, 50))  # Duplicate ID from existing range
    
    return record


def generate_dataset(total_records: int = 1000, invalid_percentage: float = 0.25):
    records = []
    invalid_count = int(total_records * invalid_percentage)
    valid_count = total_records - invalid_count
    
    duplicate_ids = set()
    for i in range(1, valid_count + 1):
        record = generate_record(i, make_invalid=False)
        records.append(record)
    
    for i in range(valid_count + 1, total_records + 1):
        invalid_type = random.choice(["invalid_email", "invalid_date", "missing_field", "null_email", "empty_fields"])
        record = generate_record(i, make_invalid=True, invalid_type=invalid_type)
        records.append(record)
    
    num_duplicates = int(total_records * 0.03)
    for _ in range(num_duplicates):
        source_idx = random.randint(0, len(records) - 1)
        duplicate = json.loads(json.dumps(records[source_idx]))
        duplicate["id"] = str(random.randint(1, valid_count))
        records.append(duplicate)
    
    random.shuffle(records)
    
    for idx, record in enumerate(records, 1):
        record["id"] = str(idx)
    
    return records


def main():
    print("Generating HubSpot contacts dataset...")
    
    records = generate_dataset(total_records=1000, invalid_percentage=0.25)
    
    output_file = "hubspot_contacts_dataset.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    
    print(f"Generated {len(records)} records")
    print(f"Saved to: {output_file}")
    
    email_list = [r["properties"].get("email") or "" for r in records]
    invalid_emails_count = sum(1 for e in email_list if "@" not in e)
    null_emails_count = sum(1 for e in email_list if not e)
    
    ids = [r["id"] for r in records]
    duplicates_count = len(ids) - len(set(ids))
    
    print(f"\nData quality summary:")
    print(f"  Total records: {len(records)}")
    print(f"  Invalid emails (no @): {invalid_emails_count}")
    print(f"  Null/empty emails: {null_emails_count}")
    print(f"  Duplicate IDs: {duplicates_count}")


if __name__ == "__main__":
    main()
