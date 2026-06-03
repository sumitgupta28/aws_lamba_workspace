import csv
import random
import uuid
from datetime import date, timedelta

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna",
    "Kenneth", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts"
]

DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "example.com"]

CITIES = [
    ("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"), ("Chicago", "IL", "60601"),
    ("Houston", "TX", "77001"), ("Phoenix", "AZ", "85001"), ("Philadelphia", "PA", "19101"),
    ("San Antonio", "TX", "78201"), ("San Diego", "CA", "92101"), ("Dallas", "TX", "75201"),
    ("San Jose", "CA", "95101"), ("Austin", "TX", "73301"), ("Jacksonville", "FL", "32099"),
    ("Fort Worth", "TX", "76101"), ("Columbus", "OH", "43085"), ("Charlotte", "NC", "28201"),
    ("Indianapolis", "IN", "46201"), ("San Francisco", "CA", "94102"), ("Seattle", "WA", "98101"),
    ("Denver", "CO", "80201"), ("Nashville", "TN", "37201"),
]

DEPARTMENTS = ["Engineering", "Marketing", "Sales", "Finance", "HR", "Operations", "Product", "Legal"]
STATUSES = ["active", "active", "active", "inactive", "suspended"]

def random_dob():
    start = date(1960, 1, 1)
    end = date(2000, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def random_phone():
    return f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"

def random_street():
    number = random.randint(1, 9999)
    streets = ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine Rd", "Elm St", "Park Blvd", "Lake Dr"]
    return f"{number} {random.choice(streets)}"

random.seed(42)

rows = []
used_emails = set()

for i in range(1, 101):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    domain = random.choice(DOMAINS)
    base_email = f"{first.lower()}.{last.lower()}"
    email = f"{base_email}@{domain}"
    suffix = 2
    while email in used_emails:
        email = f"{base_email}{suffix}@{domain}"
        suffix += 1
    used_emails.add(email)

    city, state, zip_code = random.choice(CITIES)
    dob = random_dob()

    rows.append({
        "user_id": str(uuid.UUID(int=random.getrandbits(128))),
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone": random_phone(),
        "date_of_birth": dob.isoformat(),
        "street_address": random_street(),
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "country": "US",
        "department": random.choice(DEPARTMENTS),
        "status": random.choice(STATUSES),
        "created_at": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
    })

output_path = "data/users.csv"
import os
os.makedirs("data", exist_ok=True)

fieldnames = list(rows[0].keys())
with open(output_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows -> {output_path}")
