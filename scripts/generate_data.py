import os
import json
import csv
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Create directories if they don't exist
os.makedirs(DATA_DIR / "markdown", exist_ok=True)
os.makedirs(DATA_DIR / "slack", exist_ok=True)
os.makedirs(DATA_DIR / "excel", exist_ok=True)
os.makedirs(DATA_DIR / "pdf", exist_ok=True)
os.makedirs(DATA_DIR / "sample", exist_ok=True)


def generate_permissions():
    """Generate permissions.json ACL metadata mapping files to user roles."""
    permissions = {
        "roles": ["engineering", "product", "hr", "finance", "exec", "all"],
        "documents": {
            "engineering-onboarding.md": ["engineering", "hr", "exec"],
            "api-rate-limits.md": ["engineering", "exec"],
            "incident-runbook.md": ["engineering"],
            "product-roadmap-2024.md": ["product", "exec"],
            "hr-leave-policy.md": ["all"],
            "architecture-decisions.md": ["engineering", "product", "exec"],
            "vendor-evaluation.md": ["engineering", "finance", "exec"],
            "company-values.md": ["all"],
            "quarterly-report-q3.pdf": ["finance", "exec"],
            "security-audit-2024.pdf": ["engineering", "exec"],
            "employee-handbook.pdf": ["all"],
            "patent-filing-2024.pdf": ["engineering", "exec"],
            "scanned-policy-doc.pdf": ["hr", "exec"],
            "engineering-general.json": ["engineering"],
            "product-decisions.json": ["product", "engineering", "exec"],
            "all-hands-questions.json": ["all"],
            "leadership-sync.json": ["exec"],
            "employee-directory.csv": ["hr", "exec"],
            "budget-2024.csv": ["finance", "exec"],
            "okr-tracking-q3.csv": ["product", "exec"],
            "vendor-contacts.csv": ["finance", "engineering", "exec"]
        },
        "users": {
            "alice": {"roles": ["engineering"], "name": "Alice Chen", "title": "Senior Engineer"},
            "bob": {"roles": ["product", "exec"], "name": "Bob Martinez", "title": "VP Product"},
            "carol": {"roles": ["hr"], "name": "Carol Williams", "title": "HR Manager"},
            "dave": {"roles": ["finance"], "name": "Dave Kumar", "title": "Finance Analyst"},
            "eve": {"roles": ["engineering", "exec"], "name": "Eve Johnson", "title": "CTO"},
            "frank": {"roles": ["all"], "name": "Frank Intern", "title": "Summer Intern"}
        }
    }
    
    output_path = DATA_DIR / "permissions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(permissions, f, indent=2)
    print(f"Generated permissions configuration: {output_path}")


def generate_markdown_files():
    """Generate synthetic Confluence Markdown pages in data/markdown/."""
    # 1. Company Values (with a duplicate paragraph)
    company_values = """# BigCorp Company Values

Welcome to the central page for BigCorp's corporate values. These principles guide our day-to-day work, engineering choices, and product definitions.

## 1. Customer First
We prioritize client requirements above all else. Every feature we build starts with a customer pain point and finishes with verification from our active users.

## 2. Build Together
Collaboration is the key to our success. We operate cross-functional project pods consisting of developers, designers, product managers, and testers working closely.

## 3. Move Fast, Stay Safe
We value velocity but never at the expense of stability. Our deployment pipelines run automated checks, linting, and sandbox runs to keep our production system resilient.

## 4. Work-Life Balance Commitments
At BigCorp, we believe that sustainable work practices are the foundation of high-performing teams. We commit to supporting flexible remote schedules, providing comprehensive mental health resources, offering a standard wellness stipend, and enforcing a strict "no after-hours notifications" protocol unless an employee is actively on-call for critical system alerts.

## 5. Transparency by Default
Our design docs, roadmap, meeting summaries, and retrospective results are public to all internal employees. We believe that open sharing leads to smarter decisions and better code.
"""

    # 2. HR Leave Policy (contains the near-duplicate paragraph)
    hr_leave_policy = """# BigCorp Leave Policy
**Effective January 1, 2024**

This page details standard time off policies for full-time and part-time internal staff at BigCorp.

## 1. Paid Time Off (PTO)
- Full-time employees accrue 25 days of paid time off per calendar year.
- A maximum of 5 unused PTO days can be rolled over into the next fiscal year.
- All leave requests must be submitted through BambooHR and approved by your direct manager.

## 2. Sick Leave
- Full-time staff are allocated 12 paid sick days per year.
- Sick leave does not roll over and cannot be cashed out upon termination.

## 3. Parental Leave
- Primary caregivers are eligible for 16 weeks of fully paid leave.
- Secondary caregivers are eligible for 8 weeks of fully paid leave.

## 4. Wellness and balance Commitments
At BigCorp, we believe that sustainable work practices are the foundation of high-performing teams. We commit to supporting flexible remote schedules, providing comprehensive mental health resources, offering a standard wellness stipend, and enforcing a strict "no after-hours notifications" protocol unless an employee is actively on-call for critical system alerts.

## 5. Public Holidays
BigCorp observes 10 standard federal public holidays annually. Please consult the company calendar for exact dates.
"""

    # 3. Engineering Onboarding
    engineering_onboarding = """# Engineering Onboarding Guide

Welcome to the BigCorp engineering team! This guide will help you set up your developer environment and get your first PR merged.

## 1. Laptop Setup & Prerequisites
Before writing code, ensure you have:
- Installed the BigCorp global VPN client and registered your MFA keys.
- Cloned the primary system repositories from `github.com/vansharora156/nexus-rag`.
- Formatted Git to sign your commits.

## 2. Development Environment
Our services run locally using Docker containers.
- VS Code is our recommended IDE. Install the standard Python, ESLint, and Prettier extensions.
- Configure local PostgreSQL client using the credentials in your local `.env` setup.

## 3. Team Contacts
Below are the key contacts for the engineering division:

| Name | Role | Slack Handle | Timezone |
|---|---|---|---|
| Alice Chen | Senior Dev / Team Lead | @alice.chen | PST (San Francisco) |
| Eve Johnson | CTO | @eve.cto | EST (New York) |
| Bob Martinez | VP Product | @bob.prod | PST (San Francisco) |

## 4. Code Reviews & CI/CD
- Every pull request requires at least 2 green reviews from team members.
- Continuous Integration runs automated tests on GitHub Actions. All linting and tests must be green before merging.
- Deployment to staging runs automatically upon merge to main.
"""

    # 4. API Rate Limits
    api_rate_limits = """# API Rate Limiting Policy

To ensure high availability and prevent abuse, BigCorp enforces rate limits on all external API gateway endpoints.

## 1. Default Limits per Tier

| Tier | Rate Limit (Requests/Min) | Burst Limit (Req/Sec) |
|---|---|---|
| Free | 100 | 10 |
| Pro | 1,000 | 50 |
| Enterprise | 10,000 | 200 |

## 2. Rate Limit Headers
Every response from the gateway contains headers indicating current quotas:
- `X-RateLimit-Limit`: Maximum requests allowed in the window.
- `X-RateLimit-Remaining`: Requests left in the current window.
- `X-RateLimit-Reset`: Unix timestamp when the window resets.

## 3. Limit Increase Process
If your application requires a limit increase, submit a ticket in JIRA under the project code `BIGCORP` with a detailed usage forecast.
"""

    # 5. Incident Runbook
    incident_runbook = """# Incident Response Runbook
**System Operations Division (v3.2)**

This page lists quick mitigation paths for standard operations incidents.

## 1. Severity Definitions

| Severity | Response SLA | Action Required |
|---|---|---|
| P1 | 5 Minutes | Database/Gateway failure. Connect to #incident-war-room immediately. |
| P2 | 15 Minutes | Degraded performance / API latency spikes > 2s. |
| P3 | 1 Hour | Single customer degradation or minor service failure. |

## 2. Database Connection Exhaustion (PostgreSQL)
**Symptoms:** Logs displaying `connection pool exhausted` or `Too many clients already`.
**Mitigation Steps:**
1. Log in to the AWS console and check RDS pool metrics.
2. Run the connection terminate script:
   ```bash
   # Terminate inactive backend connections
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';
   ```
3. If pool issues persist, scale up the API gateway connection pool parameters.

## 3. Redis Cache Miss Storm
**Symptoms:** Slow load times and database latency spikes.
**Mitigation:** Verify Redis cache state. Run a flush if cache keys are corrupted, and trigger warming scripts to pre-populate index values.
"""

    # 6. Product Roadmap
    product_roadmap = """# Product Roadmap 2024

This page documents the high-level roadmap for BigCorp's software suite.

## 1. Core Objectives
- **Q1 Foundation**: Modernize authentication pipelines, enabling SSO/OAuth2 logins.
- **Q2 Growth**: Build self-serve onboarding dashboards, lowering time-to-value for new enterprise signups.
- **Q3 Scale**: Implement multi-region deployment and cloud vector database indexing.
- **Q4 AI Search**: Deploy **NexusRAG** internally for advanced corporate knowledge searches.

## 2. Target Deliverables

| Target Quarter | Feature Name | Product Owner | Status |
|---|---|---|---|
| Q1 | SSO revamping | Alice Chen | Completed |
| Q2 | Growth dashboard | Bob Martinez | In Progress |
| Q3 | Qdrant scaling | Alice Chen | Planning |
| Q4 | NexusRAG | Eve Johnson | Researching |
"""

    # 7. System Architecture
    system_architecture = """# BigCorp System Architecture

This page outlines the core architectural components of BigCorp's service cluster.

## 1. High-Level Topology
We operate a microservices cluster hosted on AWS EKS (Kubernetes) spanning `us-east-1` and `eu-west-1` regions.
- **Gateway**: Traefik handles external routing and JWT validation.
- **Databases**: PostgreSQL for transactional state, Qdrant for vector indexes, and Redis for caching.
- **Processing**: Async workloads run in Python workers triggered by Kafka messages.

## 2. Database Deployment Matrix

| Service | DB Engine | Deployment Mode | Backup Policy |
|---|---|---|---|
| User Service | PostgreSQL | Multi-AZ RDS | Daily snapshots, 30-day retention |
| Search Engine | Qdrant Cloud | Clustered | Continuous replication |
| Metrics API | ClickHouse | EC2 Cluster | Weekly cold storage backups |
"""

    # 8. Vendor Evaluation
    vendor_evaluation = """# Monitoring Tool Vendor Evaluation

Our Datadog contract is ending. This document compares monitoring solutions for migration options.

## 1. Requirements Matrix

| Requirement | Must-Have? | Importance (1-5) |
|---|---|---|
| Kubernetes integration | Yes | 5 |
| APM trace profiling | Yes | 4 |
| Custom metrics parsing | Yes | 3 |
| Local agent deployments | No | 2 |

## 2. Comparison Scores

| Tool | Cost Rating | APM Rating | Usability Rating | Recommendation |
|---|---|---|---|---|
| Datadog | 2 / 5 (High Cost) | 5 / 5 | 5 / 5 | Primary Choice (if price is negotiated) |
| Grafana Cloud | 4 / 5 (Affordable) | 4 / 5 | 3 / 5 | Secondary Choice |
| New Relic | 3 / 5 | 3 / 5 | 4 / 5 | Do not proceed |

## 3. Cost Analysis
The leadership team approved a budget of $120,000 annually for APM monitoring services.
"""

    markdown_docs = {
        "company-values.md": company_values,
        "hr-leave-policy.md": hr_leave_policy,
        "engineering-onboarding.md": engineering_onboarding,
        "api-rate-limits.md": api_rate_limits,
        "incident-runbook.md": incident_runbook,
        "product-roadmap-2024.md": product_roadmap,
        "architecture-decisions.md": system_architecture,
        "vendor-evaluation.md": vendor_evaluation
    }

    for name, content in markdown_docs.items():
        path = DATA_DIR / "markdown" / name
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Generated markdown: {path}")


def generate_slack_files():
    """Generate Slack message threads in data/slack/."""
    # 1. #engineering-general
    eng_general = [
        {
            "user": "alice.chen",
            "text": "Has anyone completed the database migration to PostgreSQL locally yet? I am seeing connection pool exhaustion on ARM laptops.",
            "ts": "1708531200.000100",
            "thread_ts": None,
            "channel": "#engineering-general"
        },
        {
            "user": "eve.johnson",
            "text": "Hi @alice.chen, yes, I saw that. We need to raise the max connection limit in our postgresql config block. Let me link the incident runbook page: [Incident Runbook](docs/confluence/incident-runbook.md). Make sure to terminate idle backends if it blocks you.",
            "ts": "1708531260.000200",
            "thread_ts": "1708531200.000100",
            "channel": "#engineering-general"
        },
        {
            "user": "alice.chen",
            "text": "Thanks @eve.johnson! Running the pg_terminate_backend SQL command resolved my locks immediately.",
            "ts": "1708531300.000300",
            "thread_ts": "1708531200.000100",
            "channel": "#engineering-general"
        },
        {
            "user": "alice.chen",
            "text": "FYI, I am setting up the CI build scripts for arm64 now. The Docker cache keeps failing.",
            "ts": "1708532000.000100",
            "thread_ts": None,
            "channel": "#engineering-general"
        }
    ]

    # 2. #product-decisions
    prod_decisions = [
        {
            "user": "bob.martinez",
            "text": "Let's review the API gateway tier allocations. Do we agree on the 100 req/min limit for the Free tier? Marketing wants 200.",
            "ts": "1708617600.000100",
            "thread_ts": None,
            "channel": "#product-decisions"
        },
        {
            "user": "alice.chen",
            "text": "From the engineering side, 100 req/min keeps our Redis rate-limiting buffer safe. If we scale to 200, we need to upgrade Redis node sizes. Let's check the API Policy doc.",
            "ts": "1708617700.000200",
            "thread_ts": "1708617600.000100",
            "channel": "#product-decisions"
        },
        {
            "user": "bob.martinez",
            "text": "Okay, let's keep it at 100 req/min for Free tier. We will re-evaluate for Pro and Enterprise later.",
            "ts": "1708617800.000300",
            "thread_ts": "1708617600.000100",
            "channel": "#product-decisions"
        }
    ]

    # 3. #all-hands-questions
    all_hands = [
        {
            "user": "dave.kumar",
            "text": "Will the Q3 budget reflect the Datadog migration? We need to ensure APM monitoring tools are allocated correctly.",
            "ts": "1708704000.000100",
            "thread_ts": None,
            "channel": "#all-hands-questions"
        },
        {
            "user": "eve.johnson",
            "text": "Yes, APM is budgeted under our SaaS monitoring costs. The target limit is $120k annually, which we negotiated with Datadog.",
            "ts": "1708704100.000200",
            "thread_ts": "1708704000.000100",
            "channel": "#all-hands-questions"
        }
    ]

    # 4. #leadership-sync
    leadership = [
        {
            "user": "eve.johnson",
            "text": "We need to finalize the contract for Qdrant Cloud. It is a critical dependency for our internal NexusRAG AI search engine deployment.",
            "ts": "1708790400.000100",
            "thread_ts": None,
            "channel": "#leadership-sync"
        },
        {
            "user": "bob.martinez",
            "text": "Approved. The Q3 product roadmap shows AI Search as our primary deliverable, so having the vector database set up is a priority.",
            "ts": "1708790500.000200",
            "thread_ts": "1708790400.000100",
            "channel": "#leadership-sync"
        }
    ]

    slack_docs = {
        "engineering-general.json": eng_general,
        "product-decisions.json": prod_decisions,
        "all-hands-questions.json": all_hands,
        "leadership-sync.json": leadership
    }

    for name, content in slack_docs.items():
        path = DATA_DIR / "slack" / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2)
        print(f"Generated Slack JSON: {path}")


def generate_excel_files():
    """Generate Excel/CSV spreadsheet data in data/excel/."""
    # 1. Employee Directory
    directory = [
        ["employee_id", "name", "email", "department", "title", "location", "manager", "slack_handle"],
        ["EMP001", "Alice Chen", "alice.chen@bigcorp.com", "Engineering", "Senior Developer", "San Francisco", "Eve Johnson", "@alice.chen"],
        ["EMP002", "Bob Martinez", "bob.martinez@bigcorp.com", "Product", "VP Product", "San Francisco", "Eve Johnson", "@bob.prod"],
        ["EMP003", "Carol Williams", "carol.williams@bigcorp.com", "HR", "HR Manager", "New York", "Eve Johnson", "@carol.hr"],
        ["EMP004", "Dave Kumar", "dave.kumar@bigcorp.com", "Finance", "Finance Analyst", "Bangalore", "Bob Martinez", "@dave.fin"],
        ["EMP005", "Eve Johnson", "eve.johnson@bigcorp.com", "Engineering", "CTO", "New York", "CEO", "@eve.cto"],
        ["EMP006", "Frank Intern", "frank.intern@bigcorp.com", "Engineering", "Summer Intern", "Remote", "Alice Chen", "@frank.intern"]
    ]
    
    # 2. Budget 2024
    budget = [
        ["department", "category", "q1_budget", "q2_budget", "q3_budget", "q4_budget", "annual_total", "notes"],
        ["Engineering", "Infrastructure", "50000", "55000", "60000", "65000", "230000", "AWS and cloud environments"],
        ["Engineering", "Monitoring", "30000", "30000", "30000", "30000", "120000", "Datadog monitoring license"],
        ["Product", "User Testing", "5000", "8000", "8000", "5000", "26000", "Usertesting.com contracts"],
        ["Finance", "Operations", "15000", "15000", "15000", "15000", "60000", "Billing tools"],
        ["HR", "Wellness Stipends", "20000", "20000", "20000", "20000", "80000", "Employee health benefits"]
    ]

    # 3. OKR Tracking Q3
    okrs = [
        ["team", "objective", "key_result", "target", "current", "status", "owner"],
        ["Engineering", "Improve API reliability", "Achieve 99.9% uptime on external gateway", "99.9", "99.85", "On Track", "Alice Chen"],
        ["Engineering", "Reduce infrastructure costs", "Optimize Redis cache and decrease cloud costs by 15%", "15", "10", "Needs Work", "Eve Johnson"],
        ["Product", "Launch Growth Hub", "Increase developer signups by 25%", "25", "30", "Completed", "Bob Martinez"],
        ["HR", "Enhance dev onboarding", "Decrease developer time-to-first-PR to under 3 days", "3", "4", "Needs Work", "Carol Williams"]
    ]

    # 4. Vendor Contacts
    vendors = [
        ["vendor_name", "contact_person", "email", "phone", "category", "annual_cost", "status"],
        ["Amazon Web Services", "AWS Sales", "aws-sales@amazon.com", "1-800-555-0199", "Cloud Infrastructure", "230000", "Active"],
        ["Datadog Inc.", "Datadog Support", "support@datadoghq.com", "1-800-555-0155", "SaaS Monitoring", "120000", "Active"],
        ["Qdrant GmbH", "Qdrant Sales", "sales@qdrant.tech", "+49-30-555-0123", "Vector DB Cloud", "15000", "Active"],
        ["BambooHR", "HR Account Manager", "bamboohr@bamboohr.com", "1-800-555-0144", "HR Management", "8000", "Active"]
    ]

    excel_docs = {
        "employee-directory.csv": directory,
        "budget-2024.csv": budget,
        "okr-tracking-q3.csv": okrs,
        "vendor-contacts.csv": vendors
    }

    for name, content in excel_docs.items():
        path = DATA_DIR / "excel" / name
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(content)
        print(f"Generated CSV Excel: {path}")


def generate_pdf_files():
    """Generate synthetic PDF documents, including native text PDFs and scanned PDFs."""
    # 1. Native Employee Handbook text PDF (we write simple layouts via ReportLab if possible,
    # or fallback to generating text-rich files. Since ReportLab is not in requirements.txt,
    # let's check if we can write a simple PDF file format. Wait! Writing a PDF file manually
    # from binary strings is possible but complex. Is there a library installed we can use?
    # Wait, requirements.txt has 'pymupdf' and 'pdfplumber'. Let's see if we can use PyMuPDF (fitz)
    # to CREATE a PDF! Yes! fitz (PyMuPDF) supports creating empty PDFs and writing text directly
    # onto pages. That is incredibly clean and doesn't require extra installs!)
    # Let's write a helper to generate PyMuPDF text PDFs.
    try:
        import fitz
        print("PyMuPDF (fitz) is available for native PDF creation.")
        
        # 1. employee-handbook.pdf (Native text PDF)
        doc = fitz.open()
        page = doc.new_page()
        
        text = """BigCorp Employee Handbook
Version 2024.1

Welcome to BigCorp! This handbook outlines the rules, guidelines, and work culture of our enterprise.

1. Work Hours & Remote Policy
Our core work hours are 10:00 AM to 4:00 PM in your local timezone. We operate on a hybrid model, allowing remote work up to 3 days per week with manager approval.

2. Equipment & Tech Support
BigCorp provides standard corporate laptops, monitors, VPN accounts, and Slack licenses. For all hardware issues, submit a ticket in JIRA under IT Support.

3. Code of Conduct
We maintain a safe, welcoming, and inclusive professional environment. Harrassment or discriminatory behavior of any kind is strictly prohibited and subject to immediate disciplinary actions.

4. Performance Reviews
We conduct annual performance evaluations in Q4, where managers and employees discuss growth objectives, roadmap results, and career path progressions.
"""
        rect = fitz.Rect(50, 50, 550, 750)
        page.insert_textbox(rect, text, fontsize=12, fontname="helv")
        
        # Save document
        path1 = DATA_DIR / "pdf" / "employee-handbook.pdf"
        doc.save(path1)
        doc.close()
        print(f"Generated native PDF: {path1}")

        # 2. quarterly-report-q3.pdf (Native text PDF with a table)
        doc = fitz.open()
        page = doc.new_page()
        
        report_text = """BigCorp Q3 Executive Quarterly Report
Date: October 15, 2024

I. Executive Summary
BigCorp achieved record user growth and infrastructure stability in Q3 2024. The product team successfully launched the Growth Hub, raising dev signups by 30%.

II. Financial Performance
The APM monitoring migration to Datadog was finalized under the target limit of $120,000. Overall cloud costs were optimized, resulting in a 10% decrease.

III. Department Budget Summary (Q3 Actuals)
- Engineering Infrastructure: $60,000
- Engineering APM APM License: $30,000
- Product Testing Services: $8,000
- HR wellness Allocations: $20,000
"""
        rect = fitz.Rect(50, 50, 550, 750)
        page.insert_textbox(rect, report_text, fontsize=11, fontname="helv")
        
        path2 = DATA_DIR / "pdf" / "quarterly-report-q3.pdf"
        doc.save(path2)
        doc.close()
        print(f"Generated native PDF: {path2}")

    except Exception as e:
        print(f"PyMuPDF creation failed: {e}. Falling back to copying templates if available, or simple file generation.")

    # 3. scanned-policy-doc.pdf (Scanned PDF - Image containing text)
    # Use PyMuPDF to render clean text onto an image page, then save as PDF.
    # This ensures the OCR engine can read the text correctly during ingestion.
    try:
        import fitz  # PyMuPDF

        # Create a new blank PDF page (A4 dimensions in points: 595 x 842)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        policy_text = """\
RESTRICTED POLICY: INFORMATION SECURITY POLICY
BIGCORP INTERNAL OPERATIONS ONLY

1. ACCESS CONTROL AND PASSWORDS
- All systems must require multi-factor authentication (MFA).
- Passwords must be at least 14 characters long and reset every 90 days.
- Sharing credentials or access keys in public Slack channels is strictly prohibited.

2. CLOUD ENVIRONMENT AND DATA PROTECTION
- Database backups must be encrypted at rest and in transit.
- Ingestion pipelines must scrub personally identifiable information (PII) before vector storage.
- All connections to Qdrant vector database must run over HTTPS with verified TLS certificates.

3. POLICY COMPLIANCE AND RESPONSIBILITY
- Any suspected data breach or leakage must be reported within 15 minutes to @eve.johnson.
- Failure to follow security protocols will result in immediate loss of network permissions.

Approved by CTO Eve Johnson on May 12, 2024.
"""
        # Render the text on the page using a clean Helvetica font
        rect = fitz.Rect(50, 50, 545, 800)
        page.insert_textbox(rect, policy_text, fontsize=11, fontname="helv")

        # Rasterize the PDF page to a high-DPI PNG image (300 DPI = zoom 300/72 ≈ 4.17)
        mat = fitz.Matrix(4.17, 4.17)  # scale factor for 300 DPI
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

        # Create a new PDF with the rasterized image embedded (making it a true "scanned" PDF)
        img_doc = fitz.open()
        img_page = img_doc.new_page(width=595, height=842)
        img_rect = fitz.Rect(0, 0, 595, 842)

        # Save pixmap to PNG bytes, then insert into new PDF page as image
        png_bytes = pix.tobytes("png")
        img_page.insert_image(img_rect, stream=png_bytes)

        path3 = DATA_DIR / "pdf" / "scanned-policy-doc.pdf"
        img_doc.save(str(path3))
        img_doc.close()
        doc.close()
        print(f"Generated scanned image PDF via PyMuPDF rasterisation: {path3}")

    except Exception as e:
        print(f"PyMuPDF scanned PDF creation failed: {e}. Falling back to PIL.")
        try:
            img = Image.new("RGB", (2000, 2800), "white")
            draw = ImageDraw.Draw(img)
            try:
                from PIL import ImageFont
                # Try to load a system font at a readable size
                font = ImageFont.truetype("arial.ttf", 40)
                font_bold = ImageFont.truetype("arialbd.ttf", 44)
            except Exception:
                font = ImageFont.load_default()
                font_bold = font

            text_lines = [
                ("RESTRICTED POLICY: INFORMATION SECURITY POLICY", font_bold),
                ("BIGCORP INTERNAL OPERATIONS ONLY", font_bold),
                ("", font),
                ("1. ACCESS CONTROL AND PASSWORDS", font_bold),
                ("- All systems must require multi-factor authentication (MFA).", font),
                ("- Passwords must be at least 14 characters long and reset every 90 days.", font),
                ("- Sharing credentials or access keys in public Slack channels is strictly prohibited.", font),
                ("", font),
                ("2. CLOUD ENVIRONMENT AND DATA PROTECTION", font_bold),
                ("- Database backups must be encrypted at rest and in transit.", font),
                ("- Ingestion pipelines must scrub PII before vector storage.", font),
                ("- All connections to Qdrant must run over HTTPS with verified TLS certificates.", font),
                ("", font),
                ("3. POLICY COMPLIANCE AND RESPONSIBILITY", font_bold),
                ("- Any suspected data breach must be reported within 15 minutes to @eve.johnson.", font),
                ("- Failure to follow security protocols results in immediate loss of network permissions.", font),
                ("", font),
                ("Approved by CTO Eve Johnson on May 12, 2024.", font),
            ]

            y = 150
            for line, fnt in text_lines:
                draw.text((100, y), line, fill="black", font=fnt)
                y += 80

            path3 = DATA_DIR / "pdf" / "scanned-policy-doc.pdf"
            img.save(str(path3), "PDF")
            print(f"Generated scanned image PDF via PIL fallback: {path3}")
        except Exception as e2:
            print(f"PIL scanned PDF creation also failed: {e2}")


def main():
    print("Generating NexusRAG synthetic enterprise data...")
    generate_permissions()
    generate_markdown_files()
    generate_slack_files()
    generate_excel_files()
    generate_pdf_files()
    print("All sample enterprise datasets created successfully!")


if __name__ == "__main__":
    main()
