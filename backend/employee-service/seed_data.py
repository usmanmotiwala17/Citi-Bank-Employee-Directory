"""
Seed script for the Citi-style Employee Directory.

Inserts 3 departments (Banking & Finance, Technology & Operations, HR), one
manager per department, and a set of employees - each employee's manager_id
is set to their department's manager, so the org chart is actually wired up
instead of manager_id being left blank.

Safe to re-run: existing departments/employees (matched by unique
name/email) are left alone instead of erroring out.

Usage:
    python3 seed_data.py
"""

from psycopg.errors import UniqueViolation

import auth_service as auth
import postgres_service as db

# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    {"name": "Banking & Finance", "description": "Retail banking, loans, and financial services"},
    {"name": "Technology & Operations", "description": "IT infrastructure, software, and business operations"},
    {"name": "HR", "description": "Human resources, recruiting, and employee relations"},
]

# One office location per department, plus HQ for the CEOs, so the frontend's
# location filter has real variety to show.
LOCATION_BY_DEPARTMENT = {
    "Banking & Finance": "New York, NY",
    "Technology & Operations": "Tampa, FL",
    "HR": "Jacksonville, FL",
}
HQ_LOCATION = "New York, NY"

# Sample skills per job title, so the frontend's skills filter has real data
# to render immediately instead of empty lists.
SKILLS_BY_JOB_TITLE = {
    "Chief Executive Officer": ["Strategic Planning", "Leadership", "Risk Analysis"],
    "Chief Operating Officer": ["Operations", "Leadership", "Compliance"],
    "Banking & Finance Manager": ["Team Leadership", "Financial Modeling", "Risk Analysis"],
    "Technology & Operations Manager": ["Team Leadership", "Project Management", "SQL"],
    "HR Manager": ["Team Leadership", "Compliance", "Project Management"],
    "Financial Analyst": ["Financial Modeling", "Risk Analysis", "SQL"],
    "Loan Officer": ["Risk Analysis", "Compliance", "Customer Service"],
    "Risk Analyst": ["Risk Analysis", "Compliance", "SQL"],
    "Software Engineer": ["Python", "SQL", "Project Management"],
    "IT Support Specialist": ["SQL", "Customer Service", "Project Management"],
    "Business Operations Analyst": ["Project Management", "SQL", "Compliance"],
    "HR Coordinator": ["Compliance", "Customer Service", "Project Management"],
    "Recruiter": ["Customer Service", "Compliance", "Project Management"],
}

# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------
# Split into three tiers because employees depend on their manager already
# existing (their manager_id has to point at a real row) - so managers must
# be created before employees. One shared password per role tier keeps this
# easy to demo/log in with.

CEO_PASSWORD = "ceopass123"
MANAGER_PASSWORD = "managerpass123"
EMPLOYEE_PASSWORD = "employeepass123"

CEOS = [
    {"first_name": "Robert", "last_name": "Chen", "email": "robert.chen@acme.com",
     "job_title": "Chief Executive Officer", "password": CEO_PASSWORD},
]

# Exactly one manager per department.
MANAGERS = [
    {"first_name": "Sarah", "last_name": "Johnson", "email": "sarah.johnson@acme.com",
     "department": "Banking & Finance", "job_title": "Banking & Finance Manager",
     "password": MANAGER_PASSWORD},
    {"first_name": "Emily", "last_name": "Davis", "email": "emily.davis@acme.com",
     "department": "Technology & Operations", "job_title": "Technology & Operations Manager",
     "password": MANAGER_PASSWORD},
    {"first_name": "Patricia", "last_name": "Garcia", "email": "patricia.garcia@acme.com",
     "department": "HR", "job_title": "HR Manager",
     "password": MANAGER_PASSWORD},
]

# Each employee's manager_id gets filled in automatically at seed time from
# their department's manager (see get_manager_ids_by_department below) -
# that's what used to be a plain None.
EMPLOYEES = [
    # -- Banking & Finance (reports to Sarah Johnson) ------------------------
    {"first_name": "Michael", "last_name": "Brown", "email": "michael.brown@acme.com",
     "department": "Banking & Finance", "job_title": "Financial Analyst", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Carol", "last_name": "White", "email": "carol.white@acme.com",
     "department": "Banking & Finance", "job_title": "Loan Officer", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Kevin", "last_name": "Lee", "email": "kevin.lee@acme.com",
     "department": "Banking & Finance", "job_title": "Financial Analyst", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Nancy", "last_name": "Clark", "email": "nancy.clark@acme.com",
     "department": "Banking & Finance", "job_title": "Risk Analyst", "password": EMPLOYEE_PASSWORD},

    # -- Technology & Operations (reports to Emily Davis) --------------------
    {"first_name": "James", "last_name": "Wilson", "email": "james.wilson@acme.com",
     "department": "Technology & Operations", "job_title": "Software Engineer", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Steven", "last_name": "Lewis", "email": "steven.lewis@acme.com",
     "department": "Technology & Operations", "job_title": "IT Support Specialist", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Angela", "last_name": "Walker", "email": "angela.walker@acme.com",
     "department": "Technology & Operations", "job_title": "Software Engineer", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Brian", "last_name": "Hall", "email": "brian.hall@acme.com",
     "department": "Technology & Operations", "job_title": "IT Support Specialist", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Karen", "last_name": "Young", "email": "karen.young@acme.com",
     "department": "Technology & Operations", "job_title": "Business Operations Analyst", "password": EMPLOYEE_PASSWORD},

    # -- HR (reports to Patricia Garcia) --------------------------------------
    {"first_name": "David", "last_name": "Rodriguez", "email": "david.rodriguez@acme.com",
     "department": "HR", "job_title": "HR Coordinator", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Jason", "last_name": "King", "email": "jason.king@acme.com",
     "department": "HR", "job_title": "Recruiter", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Michelle", "last_name": "Scott", "email": "michelle.scott@acme.com",
     "department": "HR", "job_title": "HR Coordinator", "password": EMPLOYEE_PASSWORD},
    {"first_name": "Daniel", "last_name": "Adams", "email": "daniel.adams@acme.com",
     "department": "HR", "job_title": "Recruiter", "password": EMPLOYEE_PASSWORD},
]


def seed_departments():
    """Creates each department if it doesn't already exist. Returns {name: id}."""
    by_name = {row["name"]: row["id"] for row in db.list_departments()}

    for department in DEPARTMENTS:
        if department["name"] in by_name:
            continue
        try:
            created = db.create_department(department["name"], department["description"])
            by_name[created["name"]] = created["id"]
            print(f"  created department: {created['name']} (id={created['id']})")
        except UniqueViolation:
            pass

    return by_name


def seed_ceos():
    existing_emails = {row["email"] for row in db.list_employees()}

    for person in CEOS:
        if person["email"] in existing_emails:
            print(f"  skipping (already exists): {person['email']}")
            continue

        data = {
            "first_name": person["first_name"],
            "last_name": person["last_name"],
            "email": person["email"],
            "job_title": person["job_title"],
            "department_id": None,
            "manager_id": None,
            "role": "CEO",
            "skills": SKILLS_BY_JOB_TITLE.get(person["job_title"], []),
            "location": HQ_LOCATION,
        }
        try:
            db.create_employee(data, auth.hash_password(person["password"]))
            print(f"  created CEO: {person['first_name']} {person['last_name']} ({person['email']})")
        except UniqueViolation:
            print(f"  skipping (already exists): {person['email']}")


def seed_managers(department_ids_by_name):
    existing_emails = {row["email"] for row in db.list_employees()}

    for person in MANAGERS:
        if person["email"] in existing_emails:
            print(f"  skipping (already exists): {person['email']}")
            continue

        data = {
            "first_name": person["first_name"],
            "last_name": person["last_name"],
            "email": person["email"],
            "job_title": person["job_title"],
            "department_id": department_ids_by_name[person["department"]],
            "manager_id": None,
            "role": "MANAGER",
            "skills": SKILLS_BY_JOB_TITLE.get(person["job_title"], []),
            "location": LOCATION_BY_DEPARTMENT[person["department"]],
        }
        try:
            db.create_employee(data, auth.hash_password(person["password"]))
            print(f"  created MANAGER: {person['first_name']} {person['last_name']} ({person['email']})")
        except UniqueViolation:
            print(f"  skipping (already exists): {person['email']}")


def get_manager_ids_by_department(department_ids_by_name):
    """
    Looks up the manager actually stored in each department (rather than
    trusting insertion order), so this works whether the managers were just
    created above or already existed from a previous run. Returns
    {department name: manager's employee id}.
    """
    manager_ids = {}
    for name, department_id in department_ids_by_name.items():
        for row in db.list_employees_by_department(department_id):
            if row["role"] == "MANAGER":
                manager_ids[name] = row["id"]
                break
    return manager_ids


def seed_employees(department_ids_by_name, manager_ids_by_department):
    existing_emails = {row["email"] for row in db.list_employees()}

    for person in EMPLOYEES:
        if person["email"] in existing_emails:
            print(f"  skipping (already exists): {person['email']}")
            continue

        data = {
            "first_name": person["first_name"],
            "last_name": person["last_name"],
            "email": person["email"],
            "job_title": person["job_title"],
            "department_id": department_ids_by_name[person["department"]],
            "manager_id": manager_ids_by_department[person["department"]],
            "role": "EMPLOYEE",
            "skills": SKILLS_BY_JOB_TITLE.get(person["job_title"], []),
            "location": LOCATION_BY_DEPARTMENT[person["department"]],
        }

        try:
            db.create_employee(data, auth.hash_password(person["password"]))
            print(f"  created EMPLOYEE: {person['first_name']} {person['last_name']} ({person['email']}), reports to manager id {data['manager_id']}")
        except UniqueViolation:
            print(f"  skipping (already exists): {person['email']}")


def main():
    print("Seeding departments...")
    department_ids_by_name = seed_departments()

    print("\nSeeding CEOs...")
    seed_ceos()

    print("\nSeeding managers...")
    seed_managers(department_ids_by_name)

    manager_ids_by_department = get_manager_ids_by_department(department_ids_by_name)

    print("\nSeeding employees...")
    seed_employees(department_ids_by_name, manager_ids_by_department)

    print("\nDone. Sample logins (see README.md for the full table):")
    print(f"  CEO:      robert.chen@acme.com / {CEO_PASSWORD}")
    print(f"  Manager:  sarah.johnson@acme.com / {MANAGER_PASSWORD}")
    print(f"  Employee: carol.white@acme.com / {EMPLOYEE_PASSWORD}")


if __name__ == "__main__":
    main()
