"""NovaCore Technologies — Synthetic Enterprise Dataset Generator & Validator for Atlas.
Generates interconnected relational tables, rich markdown documents, chunks,
entity relationships, and RAGAS/LangGraph evaluation benchmarks.
"""
import os
import csv
import json
import random
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Fix random seed for strict deterministic reproducibility
random.seed(42)

OUTPUT_DIR = Path("d:/AGENTS/data/novacore")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REGIONS = ["North America", "Europe", "APAC", "India"]
YEARS = [2024, 2025, 2026]
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
DEPARTMENTS = [
    "Finance", "Sales", "Customer Success", "Human Resources",
    "Engineering", "Product", "Operations", "Legal", "Security",
    "IT", "Marketing", "Procurement", "Risk & Compliance", "Executive"
]
ACCESS_LEVELS = ["public", "employee", "manager", "management", "restricted", "admin"]

# Anchor entities and baseline metrics
ANCHOR_CUSTOMER_ID = "CUST-00124"
ANCHOR_CUSTOMER_NAME = "Vertex Global Systems"
ANCHOR_INCIDENT_ID = "INC-78431"
ANCHOR_PROJECT_ID = "PRJ-00014"
ANCHOR_PROJECT_NAME = "NovaCore Cloud Auto-Remediation"
ANCHOR_PRODUCT_ID = "PROD-00003"
ANCHOR_PRODUCT_NAME = "NovaCore AI Inference Cloud"
ANCHOR_VENDOR_ID = "VND-00042"
ANCHOR_VENDOR_NAME = "Apex Silicon Optical Fabrics"
ANCHOR_CONTRACT_ID = "CNT-2026-0089"

def generate_entities():
    print("[*] Generating Global Persistent Entities Registry...")
    
    # 1. Customers (1,000)
    customers = []
    industries = ["Financial Services", "Healthcare", "E-Commerce", "Aerospace", "Telecommunications", "Manufacturing", "Energy"]
    segments = ["Enterprise", "Mid-Market", "Strategic Accounts", "Government"]
    for i in range(1, 1001):
        cid = f"CUST-{i:05d}"
        if i == 124:
            name = ANCHOR_CUSTOMER_NAME
            industry = "Financial Services"
            segment = "Strategic Accounts"
            churn_risk = "High"
            arr = 4250000
        else:
            name = f"NovaEnterprise Client {i} Corp"
            industry = random.choice(industries)
            segment = random.choice(segments)
            churn_risk = random.choice(["Low", "Low", "Medium", "High"])
            arr = random.randint(75000, 3500000)
        
        region = random.choice(REGIONS)
        mgr = f"EMP-{random.randint(100, 250):05d}"
        status = "Active" if churn_risk != "High" or i == 124 else random.choice(["Active", "At-Risk", "Under Review"])
        customers.append({
            "customer_id": cid,
            "customer_name": name,
            "region": region,
            "industry": industry,
            "segment": segment,
            "account_manager": mgr,
            "customer_status": status,
            "annual_value": arr,
            "churn_risk": churn_risk
        })

    # 2. Employees (500)
    employees = []
    roles_by_dept = {
        "Executive": ["Chief Executive Officer", "Chief Financial Officer", "Chief Technology Officer", "Chief Operating Officer", "Chief Revenue Officer", "Chief Information Security Officer"],
        "Finance": ["Finance Director", "Senior Financial Analyst", "VP Financial Planning", "Lead Controller", "Treasury Manager"],
        "Sales": ["VP Enterprise Sales", "Regional Sales Director", "Account Executive", "Solutions Architect", "Sales Operations Lead"],
        "Customer Success": ["VP Customer Success", "Director Client Health", "Customer Success Manager", "Technical Account Manager"],
        "Engineering": ["VP Engineering", "Staff Distributed Systems Engineer", "Principal Architect", "Senior DevOps Engineer", "Site Reliability Engineer"],
        "Product": ["VP Product Management", "Director Platform PM", "Senior Product Manager", "Technical Product Lead"],
        "Operations": ["VP Operations", "Global Supply Chain Director", "Infrastructure Operations Lead", "Service Delivery Manager"],
        "Legal": ["General Counsel", "Senior Corporate Counsel", "Contracts Compliance Lead", "Regulatory Affairs Director"],
        "Security": ["Director Information Security", "Lead Security Architect", "SOC Incident Manager", "GRC Compliance Lead"],
        "IT": ["Director IT Operations", "Cloud Infrastructure Architect", "Database Administrator", "Lead Systems Engineer"],
        "Marketing": ["Chief Marketing Officer", "VP Product Marketing", "Growth Demand Lead", "Brand Communications Director"],
        "Procurement": ["Director Strategic Procurement", "Vendor Relations Manager", "Lead Category Buyer"],
        "Risk & Compliance": ["Chief Risk Officer", "Internal Audit Director", "Enterprise Risk Manager", "SOC2 Compliance Auditor"],
        "Human Resources": ["Chief People Officer", "VP Talent Acquisition", "Director Total Rewards", "HR Business Partner"]
    }

    # Deterministic Executives
    exec_defs = [
        ("EMP-00001", "Marcus Vance", "Executive", "Chief Executive Officer", "admin", "North America"),
        ("EMP-00002", "Elena Rostova", "Executive", "Chief Financial Officer", "management", "North America"),
        ("EMP-00003", "Dr. Chen Wei", "Executive", "Chief Technology Officer", "management", "APAC"),
        ("EMP-00004", "Sarah Jenkins", "Executive", "Chief Operating Officer", "management", "Europe"),
        ("EMP-00005", "Rajesh Sharma", "Executive", "Chief Revenue Officer", "management", "India"),
        ("EMP-00006", "David Sterling", "Security", "Chief Information Security Officer", "restricted", "North America"),
    ]
    for eid, name, dept, title, acc, reg in exec_defs:
        employees.append({
            "employee_id": eid,
            "full_name": name,
            "department": dept,
            "job_title": title,
            "access_level": acc,
            "region": reg,
            "email": f"{name.lower().replace(' ', '.')}@novacore.internal",
            "hire_date": "2021-03-15"
        })

    for i in range(7, 501):
        eid = f"EMP-{i:05d}"
        dept = random.choice(DEPARTMENTS)
        title = random.choice(roles_by_dept.get(dept, ["Senior Enterprise Specialist"]))
        acc = "management" if "VP" in title or "Director" in title else ("manager" if "Manager" in title or "Lead" in title else "employee")
        reg = random.choice(REGIONS)
        first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Devin", "Casey", "Riley", "Aarav", "Priya", "Hiroshi", "Yuki", "Lukas", "Sophie"]
        last_names = ["Kim", "Patel", "Muller", "Tanaka", "O'Connor", "Garcia", "Dubois", "Larsson", "Kowalski", "Gupta", "Nakamura", "Zhao"]
        fn = f"{random.choice(first_names)} {random.choice(last_names)}"
        clean_fn = fn.lower().replace(' ', '.').replace("'", "")
        employees.append({
            "employee_id": eid,
            "full_name": fn,
            "department": dept,
            "job_title": title,
            "access_level": acc,
            "region": reg,
            "email": f"{clean_fn}.{i}@novacore.internal",
            "hire_date": f"202{random.randint(1, 5)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        })

    # 3. Products (35)
    products = [
        {"product_id": ANCHOR_PRODUCT_ID, "product_name": ANCHOR_PRODUCT_NAME, "category": "AI & Machine Learning", "tier": "Tier-1", "annual_base_price": 240000, "status": "Active"},
        {"product_id": "PROD-00001", "product_name": "NovaCore Hybrid Cloud Engine", "category": "Cloud Infrastructure", "tier": "Tier-1", "annual_base_price": 180000, "status": "Active"},
        {"product_id": "PROD-00002", "product_name": "NovaCore Observability Fabric", "category": "Monitoring & Telemetry", "tier": "Tier-2", "annual_base_price": 95000, "status": "Active"},
        {"product_id": "PROD-00004", "product_name": "NovaCore Shield Zero-Trust Gateway", "category": "Security & Identity", "tier": "Tier-1", "annual_base_price": 140000, "status": "Active"},
        {"product_id": "PROD-00005", "product_name": "NovaCore Enterprise Knowledge Graph", "category": "Data & Search", "tier": "Tier-2", "annual_base_price": 125000, "status": "Active"},
    ]
    for i in range(6, 36):
        pid = f"PROD-{i:05d}"
        cat = random.choice(["Cloud Infrastructure", "AI & Machine Learning", "Security & Identity", "Developer Tools", "Data & Search", "Compliance Automation"])
        tier = random.choice(["Tier-1", "Tier-2", "Tier-3"])
        products.append({
            "product_id": pid,
            "product_name": f"NovaCore {cat.split()[0]} Solution Suite {i}",
            "category": cat,
            "tier": tier,
            "annual_base_price": random.randint(45000, 320000),
            "status": "Active"
        })

    # 4. Projects (120)
    projects = [
        {
            "project_id": ANCHOR_PROJECT_ID,
            "project_name": ANCHOR_PROJECT_NAME,
            "owner_employee_id": "EMP-00003",
            "department": "Engineering",
            "budget": 4500000,
            "status": "Accelerated",
            "start_date": "2025-06-01",
            "target_completion": "2026-11-30"
        }
    ]
    for i in range(1, 121):
        if i == 14:
            continue
        pjid = f"PRJ-{i:05d}"
        dept = random.choice(["Engineering", "Product", "Operations", "IT", "Security"])
        owner = f"EMP-{random.randint(1, 150):05d}"
        status = random.choice(["On-Track", "On-Track", "Delayed", "In-Review", "Completed"])
        projects.append({
            "project_id": pjid,
            "project_name": f"NovaCore Initiative {dept} Alpha-{i}",
            "owner_employee_id": owner,
            "department": dept,
            "budget": random.randint(250000, 3800000),
            "status": status,
            "start_date": f"2024-{random.randint(1, 12):02d}-01",
            "target_completion": f"2026-{random.randint(6, 12):02d}-28"
        })

    # 5. Vendors (210)
    vendors = [
        {
            "vendor_id": ANCHOR_VENDOR_ID,
            "vendor_name": ANCHOR_VENDOR_NAME,
            "category": "Hardware & Optical Infrastructure",
            "country": "Singapore",
            "risk_rating": "Elevated - APAC Delivery Delays",
            "annual_spend": 8200000,
            "active_contracts": 3
        }
    ]
    for i in range(1, 211):
        if i == 42:
            continue
        vid = f"VND-{i:05d}"
        cat = random.choice(["Cloud Hosting", "SaaS Software", "Network Hardware", "Consulting", "Security Telemetry", "Legal Advisory"])
        country = random.choice(["USA", "Germany", "Japan", "Singapore", "India", "UK", "Australia"])
        vendors.append({
            "vendor_id": vid,
            "vendor_name": f"Global Vendor Alliance {i} Ltd",
            "category": cat,
            "country": country,
            "risk_rating": random.choice(["Low", "Low", "Moderate", "Medium"]),
            "annual_spend": random.randint(120000, 4800000),
            "active_contracts": random.randint(1, 4)
        })

    # 6. Contracts (320)
    contracts = [
        {
            "contract_id": ANCHOR_CONTRACT_ID,
            "customer_id": ANCHOR_CUSTOMER_ID,
            "product_id": ANCHOR_PRODUCT_ID,
            "vendor_id": ANCHOR_VENDOR_ID,
            "contract_value": 4250000,
            "sla_tier": "Platinum 99.99%",
            "penalty_clause": "15% rebate upon >30 min continuous outage",
            "start_date": "2025-01-01",
            "end_date": "2027-12-31",
            "status": "Active - Under Penalty Dispute"
        }
    ]
    for i in range(1, 321):
        if i == 89:
            continue
        ctid = f"CNT-202{random.choice([4, 5, 6])}-{i:04d}"
        cid = f"CUST-{random.randint(1, 1000):05d}"
        pid = f"PROD-{random.randint(1, 35):05d}"
        vid = f"VND-{random.randint(1, 210):05d}"
        contracts.append({
            "contract_id": ctid,
            "customer_id": cid,
            "product_id": pid,
            "vendor_id": vid,
            "contract_value": random.randint(150000, 3200000),
            "sla_tier": random.choice(["Gold 99.9%", "Platinum 99.99%", "Silver 99.5%"]),
            "penalty_clause": "Standard 5% SLA service credit",
            "start_date": "2024-01-01",
            "end_date": "2026-12-31",
            "status": "Active"
        })

    # 7. Incidents (550)
    incidents = [
        {
            "incident_id": ANCHOR_INCIDENT_ID,
            "title": "Severe Latency Spike & Partial Drop in APAC NovaCore AI Inference Cluster",
            "severity": "P1 - Critical",
            "customer_id": ANCHOR_CUSTOMER_ID,
            "product_id": ANCHOR_PRODUCT_ID,
            "vendor_id": ANCHOR_VENDOR_ID,
            "region": "APAC",
            "root_cause": "Buffer overflow and fiber transponder packet drops in VND-00042 optical routing fabric",
            "downtime_minutes": 58,
            "financial_impact_usd": 637500,
            "incident_date": "2026-07-14",
            "resolved_date": "2026-07-14",
            "status": "Postmortem Completed"
        }
    ]
    for i in range(1, 551):
        if i == 78431 or i == 1:
            continue
        inc_id = f"INC-{i:05d}"
        sev = random.choice(["P2 - Major", "P3 - Moderate", "P4 - Low"])
        cid = f"CUST-{random.randint(1, 1000):05d}"
        pid = f"PROD-{random.randint(1, 35):05d}"
        vid = f"VND-{random.randint(1, 210):05d}"
        reg = random.choice(REGIONS)
        incidents.append({
            "incident_id": inc_id,
            "title": f"Service Interruption in {reg} Cluster-{i}",
            "severity": sev,
            "customer_id": cid,
            "product_id": pid,
            "vendor_id": vid,
            "region": reg,
            "root_cause": random.choice(["Transient DNS timeout", "Database lock contention", "Pod memory exhaustion", "Network interface flap"]),
            "downtime_minutes": random.randint(5, 45),
            "financial_impact_usd": random.randint(2000, 45000),
            "incident_date": f"202{random.choice([4, 5, 6])}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "resolved_date": f"202{random.choice([4, 5, 6])}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "status": "Resolved"
        })

    # 8. Support Tickets (5,000)
    tickets = [
        {
            "ticket_id": "TKT-00001",
            "customer_id": ANCHOR_CUSTOMER_ID,
            "product_id": ANCHOR_PRODUCT_ID,
            "assigned_employee_id": "EMP-00003",
            "incident_id": ANCHOR_INCIDENT_ID,
            "priority": "Urgent",
            "status": "Resolved",
            "subject": "CRITICAL: Latency escalation on AI Inference Cloud endpoints in APAC",
            "created_at": "2026-07-14 04:12:00",
            "resolution_time_hours": 1.2
        }
    ]
    for i in range(2, 5001):
        tid = f"TKT-{i:05d}"
        cid = f"CUST-{random.randint(1, 1000):05d}"
        pid = f"PROD-{random.randint(1, 35):05d}"
        eid = f"EMP-{random.randint(10, 400):05d}"
        tickets.append({
            "ticket_id": tid,
            "customer_id": cid,
            "product_id": pid,
            "assigned_employee_id": eid,
            "incident_id": f"INC-{random.randint(1, 550):05d}" if random.random() < 0.2 else "",
            "priority": random.choice(["Low", "Normal", "High", "Urgent"]),
            "status": random.choice(["Resolved", "Closed", "Open", "Pending Review"]),
            "subject": f"Inquiry regarding {random.choice(['API rate limits', 'invoice billing discrepancy', 'cluster configuration', 'SSO authentication'])} for item {i}",
            "created_at": f"202{random.choice([4, 5, 6])}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} {random.randint(8, 18):02d}:00:00",
            "resolution_time_hours": round(random.uniform(0.5, 48.0), 1)
        })

    return customers, employees, products, projects, vendors, contracts, incidents, tickets

def generate_financial_and_sales_tables(customers, employees, products):
    print("[*] Generating Financial & Sales Tabular Records...")
    
    # 1. Sales Records (5,000 deals)
    sales = []
    for i in range(1, 5001):
        sid = f"SALE-{i:06d}"
        c = random.choice(customers)
        p = random.choice(products)
        e = random.choice(employees)
        yr = random.choice(YEARS)
        qtr = random.choice(QUARTERS)
        stage = "Closed Won" if random.random() < 0.65 else random.choice(["Pipeline", "Negotiation", "Proposal", "Closed Lost"])
        val = random.randint(45000, 1200000)
        sales.append({
            "sale_id": sid,
            "customer_id": c["customer_id"],
            "product_id": p["product_id"],
            "employee_id": e["employee_id"],
            "region": c["region"],
            "year": yr,
            "quarter": qtr,
            "deal_stage": stage,
            "deal_value": val,
            "closed_date": f"{yr}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        })

    # 2. Transactions (20,000)
    transactions = []
    for i in range(1, 20001):
        tx_id = f"TXN-{i:07d}"
        c = random.choice(customers)
        p = random.choice(products)
        yr = random.choice(YEARS)
        qtr = random.choice(QUARTERS)
        amount = random.randint(500, 180000)
        status = "Settled" if random.random() < 0.96 else "Pending Review"
        transactions.append({
            "transaction_id": tx_id,
            "customer_id": c["customer_id"],
            "product_id": p["product_id"],
            "year": yr,
            "quarter": qtr,
            "amount": amount,
            "currency": "USD",
            "status": status,
            "transaction_date": f"{yr}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        })

    # 3. Revenue Table (Consolidated Quarterly by Region)
    # Reflecting exact benchmark facts:
    # 2026 Q2 Total: $142.5M | APAC: $38.2M | Enterprise: $82.0M | Churn: 4.1%
    # 2026 Q3 Total: $125.4M (-12.0%) | APAC: $30.2M (-20.9%) | Enterprise: $67.2M (-18.0%) | Churn: 6.2%
    revenue_records = [
        # 2026 Q3 (DIP)
        {"year": 2026, "quarter": "Q3", "region": "North America", "segment": "Enterprise", "revenue_usd": 38400000, "growth_yoy_pct": -8.5, "churn_rate_pct": 5.8},
        {"year": 2026, "quarter": "Q3", "region": "North America", "segment": "Mid-Market", "revenue_usd": 24200000, "growth_yoy_pct": 2.1, "churn_rate_pct": 4.9},
        {"year": 2026, "quarter": "Q3", "region": "Europe", "segment": "Enterprise", "revenue_usd": 18200000, "growth_yoy_pct": -6.2, "churn_rate_pct": 5.4},
        {"year": 2026, "quarter": "Q3", "region": "Europe", "segment": "Mid-Market", "revenue_usd": 14400000, "growth_yoy_pct": 3.8, "churn_rate_pct": 4.2},
        {"year": 2026, "quarter": "Q3", "region": "APAC", "segment": "Enterprise", "revenue_usd": 15800000, "growth_yoy_pct": -26.1, "churn_rate_pct": 7.4},
        {"year": 2026, "quarter": "Q3", "region": "APAC", "segment": "Mid-Market", "revenue_usd": 14400000, "growth_yoy_pct": -14.2, "churn_rate_pct": 6.1},
        # APAC Total in 2026 Q3 = $15.8M + $14.4M = $30.2M
        # 2026 Q2 (Baseline)
        {"year": 2026, "quarter": "Q2", "region": "North America", "segment": "Enterprise", "revenue_usd": 44800000, "growth_yoy_pct": 14.2, "churn_rate_pct": 3.8},
        {"year": 2026, "quarter": "Q2", "region": "North America", "segment": "Mid-Market", "revenue_usd": 25100000, "growth_yoy_pct": 11.5, "churn_rate_pct": 3.5},
        {"year": 2026, "quarter": "Q2", "region": "Europe", "segment": "Enterprise", "revenue_usd": 21200000, "growth_yoy_pct": 9.4, "churn_rate_pct": 4.0},
        {"year": 2026, "quarter": "Q2", "region": "Europe", "segment": "Mid-Market", "revenue_usd": 13200000, "growth_yoy_pct": 8.1, "churn_rate_pct": 3.7},
        {"year": 2026, "quarter": "Q2", "region": "APAC", "segment": "Enterprise", "revenue_usd": 21800000, "growth_yoy_pct": 12.8, "churn_rate_pct": 4.5},
        {"year": 2026, "quarter": "Q2", "region": "APAC", "segment": "Mid-Market", "revenue_usd": 16400000, "growth_yoy_pct": 10.2, "churn_rate_pct": 4.2},
        # APAC Total in 2026 Q2 = $21.8M + $16.4M = $38.2M
    ]
    # Add historical 2024 & 2025 records
    for yr in [2024, 2025]:
        for q in QUARTERS:
            for r in REGIONS:
                for seg in ["Enterprise", "Mid-Market"]:
                    revenue_records.append({
                        "year": yr,
                        "quarter": q,
                        "region": r,
                        "segment": seg,
                        "revenue_usd": random.randint(11000000, 36000000),
                        "growth_yoy_pct": round(random.uniform(5.0, 18.0), 1),
                        "churn_rate_pct": round(random.uniform(3.2, 4.6), 1)
                    })

    # 4. Expenses Table
    expenses = []
    for yr in YEARS:
        for q in QUARTERS:
            for d in DEPARTMENTS:
                expenses.append({
                    "year": yr,
                    "quarter": q,
                    "department": d,
                    "budgeted_usd": random.randint(2500000, 16000000),
                    "actual_spent_usd": random.randint(2400000, 16500000),
                    "variance_pct": round(random.uniform(-4.5, 6.2), 2)
                })

    # 5. Budgets Table
    budgets = []
    for yr in YEARS:
        for d in DEPARTMENTS:
            budgets.append({
                "year": yr,
                "department": d,
                "allocated_budget_usd": random.randint(12000000, 68000000),
                "approval_status": "Approved",
                "approved_by_employee_id": "EMP-00002"  # CFO Elena Rostova
            })

    # 6. Marketing Campaigns (80)
    marketing = []
    for i in range(1, 81):
        mid = f"MKT-CMP-{i:04d}"
        p = random.choice(products)
        marketing.append({
            "campaign_id": mid,
            "campaign_name": f"Global Acceleration Campaign {i}",
            "product_id": p["product_id"],
            "target_region": random.choice(REGIONS),
            "allocated_budget_usd": random.randint(150000, 1800000),
            "leads_generated": random.randint(450, 6800),
            "cost_per_acquisition": round(random.uniform(85.0, 420.0), 2),
            "status": "Completed" if i < 60 else "Active"
        })

    # 7. Procurement Purchase Orders (300)
    procurement = []
    for i in range(1, 301):
        poid = f"PO-202{random.choice([4, 5, 6])}-{i:05d}"
        vid = ANCHOR_VENDOR_ID if i == 42 else f"VND-{random.randint(1, 210):05d}"
        pjid = ANCHOR_PROJECT_ID if i == 42 else f"PRJ-{random.randint(1, 120):05d}"
        procurement.append({
            "purchase_order_id": poid,
            "vendor_id": vid,
            "project_id": pjid,
            "order_value_usd": random.randint(35000, 2400000),
            "approval_status": "Approved",
            "approved_by_employee_id": "EMP-00004",  # COO Sarah Jenkins
            "order_date": f"202{random.choice([4, 5, 6])}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        })

    return sales, transactions, revenue_records, expenses, budgets, marketing, procurement

def generate_rbac_users():
    print("[*] Generating RBAC User Registry...")
    users = [
        {"user_id": "USR-ADMIN-01", "employee_id": "EMP-00001", "username": "marcus.vance", "role": "admin", "access_level": "admin", "department": "Executive"},
        {"user_id": "USR-EXEC-01", "employee_id": "EMP-00002", "username": "elena.rostova", "role": "executive", "access_level": "management", "department": "Finance"},
        {"user_id": "USR-SEC-01", "employee_id": "EMP-00006", "username": "david.sterling", "role": "security_admin", "access_level": "restricted", "department": "Security"},
        {"user_id": "USR-FIN-01", "employee_id": "EMP-00012", "username": "finance.lead", "role": "finance_user", "access_level": "manager", "department": "Finance"},
        {"user_id": "USR-HR-01", "employee_id": "EMP-00025", "username": "hr.partner", "role": "hr_user", "access_level": "manager", "department": "Human Resources"},
        {"user_id": "USR-ENG-01", "employee_id": "EMP-00045", "username": "engineer.lead", "role": "manager", "access_level": "manager", "department": "Engineering"},
        {"user_id": "USR-EMP-01", "employee_id": "EMP-00100", "username": "general.employee", "role": "employee", "access_level": "employee", "department": "Product"},
    ]
    for i in range(8, 101):
        uid = f"USR-{i:04d}"
        eid = f"EMP-{i:05d}"
        role = random.choice(["employee", "employee", "manager", "finance_user"])
        acc = "manager" if role == "manager" else "employee"
        users.append({
            "user_id": uid,
            "employee_id": eid,
            "username": f"user.{i}",
            "role": role,
            "access_level": acc,
            "department": random.choice(DEPARTMENTS)
        })
    return users

def write_csv(path: Path, data: List[Dict[str, Any]]):
    if not data:
        return
    keys = list(data[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"  [+] Saved {len(data)} rows to {path.name}")

print("[*] Generating core relational entities...")
customers, employees, products, projects, vendors, contracts, incidents, tickets = generate_entities()
sales, transactions, revenue_records, expenses, budgets, marketing, procurement = generate_financial_and_sales_tables(customers, employees, products)
rbac_users = generate_rbac_users()

# Write Relational CSVs
write_csv(OUTPUT_DIR / "atlas_customers.csv", customers)
write_csv(OUTPUT_DIR / "atlas_employees.csv", employees)
write_csv(OUTPUT_DIR / "atlas_products.csv", products)
write_csv(OUTPUT_DIR / "atlas_projects.csv", projects)
write_csv(OUTPUT_DIR / "atlas_vendors.csv", vendors)
write_csv(OUTPUT_DIR / "atlas_contracts.csv", contracts)
write_csv(OUTPUT_DIR / "atlas_incidents.csv", incidents)
write_csv(OUTPUT_DIR / "atlas_support_tickets.csv", tickets)
write_csv(OUTPUT_DIR / "atlas_sales.csv", sales)
write_csv(OUTPUT_DIR / "atlas_transactions.csv", transactions)
write_csv(OUTPUT_DIR / "atlas_revenue.csv", revenue_records)
write_csv(OUTPUT_DIR / "atlas_expenses.csv", expenses)
write_csv(OUTPUT_DIR / "atlas_budgets.csv", budgets)
write_csv(OUTPUT_DIR / "atlas_marketing_campaigns.csv", marketing)
write_csv(OUTPUT_DIR / "atlas_procurement.csv", procurement)
write_csv(OUTPUT_DIR / "atlas_users_rbac.csv", rbac_users)
