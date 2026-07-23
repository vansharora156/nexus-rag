"""Script to generate a 100-question Golden Dataset for AskTheCompany RAG Evaluation.
Spans 4 categories: factual, multi-hop, table-lookup, discussion.
"""

import json
from pathlib import Path

golden_questions = [
    # -------------------------------------------------------------------------
    # 1. FACTUAL QUESTIONS (30)
    # -------------------------------------------------------------------------
    {
        "id": "Q001",
        "category": "factual",
        "source_type": "markdown",
        "question": "What are the core values of BigCorp?",
        "expected_answer": "Customer First and Build Together.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "company-values.md"
    },
    {
        "id": "Q002",
        "category": "factual",
        "source_type": "markdown",
        "question": "What are the core work hours at BigCorp?",
        "expected_answer": "10:00 AM to 4:00 PM in your local timezone.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "employee-handbook.pdf"
    },
    {
        "id": "Q003",
        "category": "factual",
        "source_type": "markdown",
        "question": "How many days of paid time off (PTO) do full-time employees accrue per year?",
        "expected_answer": "25 days per calendar year.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "hr-leave-policy.md"
    },
    {
        "id": "Q004",
        "category": "factual",
        "source_type": "markdown",
        "question": "How many paid sick days do employees receive per year?",
        "expected_answer": "12 paid sick days per calendar year.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "hr-leave-policy.md"
    },
    {
        "id": "Q005",
        "category": "factual",
        "source_type": "markdown",
        "question": "What is the primary IDE recommended in the Engineering Onboarding Guide?",
        "expected_answer": "VS Code.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-onboarding.md"
    },
    {
        "id": "Q006",
        "category": "factual",
        "source_type": "markdown",
        "question": "What local database engine is used in development for BigCorp microservices?",
        "expected_answer": "PostgreSQL.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-onboarding.md"
    },
    {
        "id": "Q007",
        "category": "factual",
        "source_type": "markdown",
        "question": "What is the P1 incident response SLA defined in the Incident Response Runbook?",
        "expected_answer": "5 Minutes.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "incident-runbook.md"
    },
    {
        "id": "Q008",
        "category": "factual",
        "source_type": "markdown",
        "question": "What is the P2 incident response SLA?",
        "expected_answer": "15 Minutes.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "incident-runbook.md"
    },
    {
        "id": "Q009",
        "category": "factual",
        "source_type": "markdown",
        "question": "What is the P3 incident response SLA?",
        "expected_answer": "1 Hour.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "incident-runbook.md"
    },
    {
        "id": "Q010",
        "category": "factual",
        "source_type": "markdown",
        "question": "What is the default API rate limit for the Free tier per minute?",
        "expected_answer": "100 requests per minute.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "api-rate-limits.md"
    },
    {
        "id": "Q011",
        "category": "factual",
        "source_type": "markdown",
        "question": "What is the burst limit per second for the Enterprise API tier?",
        "expected_answer": "200 requests per second.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "api-rate-limits.md"
    },
    {
        "id": "Q012",
        "category": "factual",
        "source_type": "markdown",
        "question": "What JIRA project code is used for submitting API limit increase tickets?",
        "expected_answer": "BIGCORP.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "api-rate-limits.md"
    },
    {
        "id": "Q013",
        "category": "factual",
        "source_type": "markdown",
        "question": "What is the Q1 target objective in the 2024 Product Roadmap?",
        "expected_answer": "Modernize authentication pipelines, enabling SSO/OAuth2 logins.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-roadmap-2024.md"
    },
    {
        "id": "Q014",
        "category": "factual",
        "source_type": "markdown",
        "question": "What internal AI search system is scheduled for Q4 deployment?",
        "expected_answer": "NexusRAG.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-roadmap-2024.md"
    },
    {
        "id": "Q015",
        "category": "factual",
        "source_type": "markdown",
        "question": "Who is the product owner for the Q1 SSO revamping feature?",
        "expected_answer": "Alice Chen.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-roadmap-2024.md"
    },
    {
        "id": "Q016",
        "category": "factual",
        "source_type": "markdown",
        "question": "What cloud Kubernetes platform hosts BigCorp microservices?",
        "expected_answer": "AWS EKS in us-east-1 and eu-west-1.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "architecture-decisions.md"
    },
    {
        "id": "Q017",
        "category": "factual",
        "source_type": "markdown",
        "question": "What gateway is used for external routing and JWT validation?",
        "expected_answer": "Traefik.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "architecture-decisions.md"
    },
    {
        "id": "Q018",
        "category": "factual",
        "source_type": "markdown",
        "question": "What database engine is used for metrics analytics?",
        "expected_answer": "ClickHouse.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "architecture-decisions.md"
    },
    {
        "id": "Q019",
        "category": "factual",
        "source_type": "pdf",
        "question": "What minimum password length is required by the Information Security Policy?",
        "expected_answer": "14 characters.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "scanned-policy-doc.pdf"
    },
    {
        "id": "Q020",
        "category": "factual",
        "source_type": "pdf",
        "question": "How frequently must passwords be reset according to the security policy?",
        "expected_answer": "Every 90 days.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "scanned-policy-doc.pdf"
    },
    {
        "id": "Q021",
        "category": "factual",
        "source_type": "pdf",
        "question": "Within how many minutes must a suspected data breach be reported?",
        "expected_answer": "15 minutes to @eve.johnson.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "scanned-policy-doc.pdf"
    },
    {
        "id": "Q022",
        "category": "factual",
        "source_type": "pdf",
        "question": "What encryption requirement applies to database backups?",
        "expected_answer": "Database backups must be encrypted at rest and in transit.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "scanned-policy-doc.pdf"
    },
    {
        "id": "Q023",
        "category": "factual",
        "source_type": "pdf",
        "question": "What protocol must connections to Qdrant vector database use?",
        "expected_answer": "HTTPS with verified TLS certificates.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "scanned-policy-doc.pdf"
    },
    {
        "id": "Q024",
        "category": "factual",
        "source_type": "markdown",
        "question": "What annual budget was approved by leadership for APM monitoring services?",
        "expected_answer": "$120,000 annually.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "vendor-evaluation.md"
    },
    {
        "id": "Q025",
        "category": "factual",
        "source_type": "markdown",
        "question": "Which monitoring vendor is rated as secondary choice after Datadog?",
        "expected_answer": "Grafana Cloud.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "vendor-evaluation.md"
    },
    {
        "id": "Q026",
        "category": "factual",
        "source_type": "pdf",
        "question": "What is the health wellness reimbursement stipend limit per year?",
        "expected_answer": "$500 per calendar year.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "employee-handbook.pdf"
    },
    {
        "id": "Q027",
        "category": "factual",
        "source_type": "pdf",
        "question": "How many days per week is remote work permitted under the hybrid model?",
        "expected_answer": "Up to 3 days per week.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "employee-handbook.pdf"
    },
    {
        "id": "Q028",
        "category": "factual",
        "source_type": "markdown",
        "question": "What message queue is used for processing asynchronous workloads in Python?",
        "expected_answer": "Kafka.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "architecture-decisions.md"
    },
    {
        "id": "Q029",
        "category": "factual",
        "source_type": "markdown",
        "question": "How many consecutive days of unexcused absence constitute voluntary resignation?",
        "expected_answer": "3 consecutive business days.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "hr-leave-policy.md"
    },
    {
        "id": "Q030",
        "category": "factual",
        "source_type": "pdf",
        "question": "Which monitoring vendor is marked as 'Do not proceed' in the evaluation?",
        "expected_answer": "New Relic.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "vendor-evaluation.md"
    },

    # -------------------------------------------------------------------------
    # 2. MULTI-HOP QUESTIONS (30)
    # -------------------------------------------------------------------------
    {
        "id": "Q031",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who is the manager of the VP of Product?",
        "expected_answer": "Eve Johnson (CTO).",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },
    {
        "id": "Q032",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the annual monitoring budget, and which Slack channel discussed its approval?",
        "expected_answer": "$120,000 annually, discussed in #all-hands-questions.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "vendor-evaluation.md + all-hands-questions.json"
    },
    {
        "id": "Q033",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who owns the Q3 Qdrant scaling objective, and what is their job title?",
        "expected_answer": "Alice Chen, Senior Developer.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-roadmap-2024.md + employee-directory.csv"
    },
    {
        "id": "Q034",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What SQL command terminates idle connections for PostgreSQL, and where is it documented in runbooks?",
        "expected_answer": "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle'; documented in Incident Response Runbook Section 2.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "incident-runbook.md"
    },
    {
        "id": "Q035",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Which employee is responsible for NexusRAG research in Q4, and who do they report to?",
        "expected_answer": "Eve Johnson, reports to CEO.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-roadmap-2024.md + employee-directory.csv"
    },
    {
        "id": "Q036",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the rate limit for the Pro tier, and what is the burst limit?",
        "expected_answer": "1,000 requests/min and 50 requests/sec burst limit.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "api-rate-limits.md"
    },
    {
        "id": "Q037",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the annual total budget for Engineering Infrastructure across all 4 quarters?",
        "expected_answer": "$230,000.",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q038",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who is the owner of the OKR to 'Improve API reliability', and what is their current progress metric?",
        "expected_answer": "Alice Chen, current progress is 99.85% (target 99.9%).",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "okr-tracking-q3.csv"
    },
    {
        "id": "Q039",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the annual total budget for HR Wellness Stipends?",
        "expected_answer": "$80,000 ($20,000 per quarter).",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q040",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who is the vendor contact for AWS Cloud, and what is their email?",
        "expected_answer": "John Smith, Email: jsmith@aws.example.com.",
        "authorized_user": "dave",
        "unauthorized_user": "carol",
        "expected_source": "vendor-contacts.csv"
    },
    {
        "id": "Q041",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the contract end date for Datadog in vendor contacts?",
        "expected_answer": "2024-12-31.",
        "authorized_user": "dave",
        "unauthorized_user": "carol",
        "expected_source": "vendor-contacts.csv"
    },
    {
        "id": "Q042",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who approved the Qdrant Cloud contract in leadership sync, and what roadmap objective does it support?",
        "expected_answer": "Bob Martinez approved it; supports AI Search (NexusRAG) Q4 deliverable.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "leadership-sync.json + product-roadmap-2024.md"
    },
    {
        "id": "Q043",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the Slack handle for Dave Kumar, and what department is he in?",
        "expected_answer": "@dave.fin, Finance department.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },
    {
        "id": "Q044",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What security requirement applies to PII before vector storage, and which document defines it?",
        "expected_answer": "PII must be scrubbed before vector storage; defined in Information Security Policy.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "scanned-policy-doc.pdf"
    },
    {
        "id": "Q045",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who is the primary contact for Datadog vendor management, and what is their phone number?",
        "expected_answer": "Sarah Connor, Phone: +1-555-0199.",
        "authorized_user": "dave",
        "unauthorized_user": "carol",
        "expected_source": "vendor-contacts.csv"
    },
    {
        "id": "Q046",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What key result is associated with reducing infrastructure costs in Q3 OKRs?",
        "expected_answer": "Optimize Redis cache and decrease cloud costs by 15%.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "okr-tracking-q3.csv"
    },
    {
        "id": "Q047",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who is the intern at BigCorp, who is their manager, and what role tag do they hold?",
        "expected_answer": "Frank Intern, managed by Alice Chen, holds 'all' role.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },
    {
        "id": "Q048",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What backup policy applies to PostgreSQL User Service in the architecture matrix?",
        "expected_answer": "Daily snapshots with 30-day retention.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "architecture-decisions.md"
    },
    {
        "id": "Q049",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What backup policy applies to ClickHouse Metrics API in the architecture matrix?",
        "expected_answer": "Weekly cold storage backups.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "architecture-decisions.md"
    },
    {
        "id": "Q050",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the status of the 'Launch Growth Hub' OKR for the Product team?",
        "expected_answer": "Completed (target 25%, current 30%).",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "okr-tracking-q3.csv"
    },
    {
        "id": "Q051",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who owns the HR OKR to enhance dev onboarding, and what is the target?",
        "expected_answer": "Carol Williams, target is decreasing time-to-first-PR to under 3 days.",
        "authorized_user": "bob",
        "unauthorized_user": "frank",
        "expected_source": "okr-tracking-q3.csv"
    },
    {
        "id": "Q052",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the annual total budget for Product User Testing?",
        "expected_answer": "$26,000.",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q053",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the annual total budget for Finance Operations?",
        "expected_answer": "$60,000 ($15,000 per quarter).",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q054",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What action is required for P1 severity incidents according to the runbook?",
        "expected_answer": "Connect to #incident-war-room immediately.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "incident-runbook.md"
    },
    {
        "id": "Q055",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What symptoms indicate a Redis Cache Miss Storm?",
        "expected_answer": "Slow load times and database latency spikes.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "incident-runbook.md"
    },
    {
        "id": "Q056",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What mitigation action should be taken for a Redis Cache Miss Storm?",
        "expected_answer": "Verify Redis cache state, run a flush if cache keys are corrupted, and trigger warming scripts.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "incident-runbook.md"
    },
    {
        "id": "Q057",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Who is the vendor contact for Qdrant Vector DB, and what is their email?",
        "expected_answer": "Alex Rivera, Email: arivera@qdrant.example.com.",
        "authorized_user": "dave",
        "unauthorized_user": "carol",
        "expected_source": "vendor-contacts.csv"
    },
    {
        "id": "Q058",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "Which employee is located in Bangalore, and who is their manager?",
        "expected_answer": "Dave Kumar, managed by Bob Martinez.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },
    {
        "id": "Q059",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the location and title of Carol Williams?",
        "expected_answer": "HR Manager, located in New York.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },
    {
        "id": "Q060",
        "category": "multi-hop",
        "source_type": "mixed",
        "question": "What is the location and title of Alice Chen?",
        "expected_answer": "Senior Developer, located in San Francisco.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },

    # -------------------------------------------------------------------------
    # 3. TABLE-LOOKUP QUESTIONS (20)
    # -------------------------------------------------------------------------
    {
        "id": "Q061",
        "category": "table",
        "source_type": "csv",
        "question": "What is the Q1 budget for Engineering Infrastructure?",
        "expected_answer": "$50,000.",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q062",
        "category": "table",
        "source_type": "csv",
        "question": "What is the Q2 budget for Engineering Infrastructure?",
        "expected_answer": "$55,000.",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q063",
        "category": "table",
        "source_type": "csv",
        "question": "What is the Q3 budget for Engineering Infrastructure?",
        "expected_answer": "$60,000.",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q064",
        "category": "table",
        "source_type": "csv",
        "question": "What is the Q4 budget for Engineering Infrastructure?",
        "expected_answer": "$65,000.",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q065",
        "category": "table",
        "source_type": "csv",
        "question": "What is the annual total budget for Engineering Monitoring?",
        "expected_answer": "$120,000.",
        "authorized_user": "dave",
        "unauthorized_user": "alice",
        "expected_source": "budget-2024.csv"
    },
    {
        "id": "Q066",
        "category": "table",
        "source_type": "csv",
        "question": "What is the employee ID of Eve Johnson?",
        "expected_answer": "EMP005.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },
    {
        "id": "Q067",
        "category": "table",
        "source_type": "csv",
        "question": "What is the employee ID of Frank Intern?",
        "expected_answer": "EMP006.",
        "authorized_user": "carol",
        "unauthorized_user": "frank",
        "expected_source": "employee-directory.csv"
    },
    {
        "id": "Q068",
        "category": "table",
        "source_type": "markdown",
        "question": "In the Vendor Evaluation table, what is the cost rating of Datadog?",
        "expected_answer": "2 / 5 (High Cost).",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "vendor-evaluation.md"
    },
    {
        "id": "Q069",
        "category": "table",
        "source_type": "markdown",
        "question": "In the Vendor Evaluation table, what is the APM rating of Datadog?",
        "expected_answer": "5 / 5.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "vendor-evaluation.md"
    },
    {
        "id": "Q070",
        "category": "table",
        "source_type": "markdown",
        "question": "In the Vendor Evaluation table, what is the cost rating of Grafana Cloud?",
        "expected_answer": "4 / 5 (Affordable).",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "vendor-evaluation.md"
    },
    {
        "id": "Q071",
        "category": "table",
        "source_type": "markdown",
        "question": "In the API Rate Limiting Policy table, what is the rate limit for the Enterprise tier?",
        "expected_answer": "10,000 requests per minute.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "api-rate-limits.md"
    },
    {
        "id": "Q072",
        "category": "table",
        "source_type": "csv",
        "question": "What is the target metric for the OKR 'Reduce infrastructure costs'?",
        "expected_answer": "15% reduction in cloud costs.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "okr-tracking-q3.csv"
    },
    {
        "id": "Q073",
        "category": "table",
        "source_type": "csv",
        "question": "What is the current metric value for the OKR 'Reduce infrastructure costs'?",
        "expected_answer": "10%.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "okr-tracking-q3.csv"
    },
    {
        "id": "Q074",
        "category": "table",
        "source_type": "csv",
        "question": "What is the status of the OKR 'Reduce infrastructure costs'?",
        "expected_answer": "Needs Work.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "okr-tracking-q3.csv"
    },
    {
        "id": "Q075",
        "category": "table",
        "source_type": "csv",
        "question": "What is the contract end date for Grafana Labs in vendor contacts?",
        "expected_answer": "2025-06-30.",
        "authorized_user": "dave",
        "unauthorized_user": "carol",
        "expected_source": "vendor-contacts.csv"
    },
    {
        "id": "Q076",
        "category": "table",
        "source_type": "csv",
        "question": "What is the payment terms value for AWS Cloud in vendor contacts?",
        "expected_answer": "Net 30.",
        "authorized_user": "dave",
        "unauthorized_user": "carol",
        "expected_source": "vendor-contacts.csv"
    },
    {
        "id": "Q077",
        "category": "table",
        "source_type": "csv",
        "question": "What is the payment terms value for Qdrant Vector DB in vendor contacts?",
        "expected_answer": "Net 15.",
        "authorized_user": "dave",
        "unauthorized_user": "carol",
        "expected_source": "vendor-contacts.csv"
    },
    {
        "id": "Q078",
        "category": "table",
        "source_type": "markdown",
        "question": "What is the deployment mode for Search Engine Qdrant Cloud in the architecture table?",
        "expected_answer": "Clustered.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "architecture-decisions.md"
    },
    {
        "id": "Q079",
        "category": "table",
        "source_type": "markdown",
        "question": "In the Product Roadmap deliverables table, who is the owner of Growth Dashboard?",
        "expected_answer": "Bob Martinez.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-roadmap-2024.md"
    },
    {
        "id": "Q080",
        "category": "table",
        "source_type": "markdown",
        "question": "In the Product Roadmap deliverables table, what is the status of SSO revamping?",
        "expected_answer": "Completed.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-roadmap-2024.md"
    },

    # -------------------------------------------------------------------------
    # 4. DISCUSSION / SLACK THREAD QUESTIONS (20)
    # -------------------------------------------------------------------------
    {
        "id": "Q081",
        "category": "discussion",
        "source_type": "slack",
        "question": "How do I fix PostgreSQL connection pool exhaustion on ARM laptops?",
        "expected_answer": "Run the SQL command: SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-general.json"
    },
    {
        "id": "Q082",
        "category": "discussion",
        "source_type": "slack",
        "question": "What SQL query terminates idle backend connections in PostgreSQL?",
        "expected_answer": "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-general.json"
    },
    {
        "id": "Q083",
        "category": "discussion",
        "source_type": "slack",
        "question": "What issue is Alice encountering with CI/CD builds on arm64?",
        "expected_answer": "The Docker cache keeps failing with a cache miss on Python dependency layers.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-general.json"
    },
    {
        "id": "Q084",
        "category": "discussion",
        "source_type": "slack",
        "question": "What was the decision on the API gateway Free tier rate limit in product decisions?",
        "expected_answer": "Free tier API rate limit stays at 100 requests per minute.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-decisions.json"
    },
    {
        "id": "Q085",
        "category": "discussion",
        "source_type": "slack",
        "question": "Why did engineering recommend keeping the Free tier API rate limit at 100 req/min instead of 200?",
        "expected_answer": "Increasing to 200 req/min would require upgrading Redis node sizes from r6g.large to r6g.xlarge, adding ~$800/month.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-decisions.json"
    },
    {
        "id": "Q086",
        "category": "discussion",
        "source_type": "slack",
        "question": "What rate limit did Marketing request for the Free tier?",
        "expected_answer": "200 requests per minute.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-decisions.json"
    },
    {
        "id": "Q087",
        "category": "discussion",
        "source_type": "slack",
        "question": "What question did Dave Kumar ask in the all-hands meeting?",
        "expected_answer": "He asked whether the Q3 budget reflects the Datadog migration costs for APM tools.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "all-hands-questions.json"
    },
    {
        "id": "Q088",
        "category": "discussion",
        "source_type": "slack",
        "question": "What response did Eve Johnson provide regarding the Datadog APM budget in all-hands?",
        "expected_answer": "She confirmed the APM budget is $120,000 annually under SaaS monitoring costs.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "all-hands-questions.json"
    },
    {
        "id": "Q089",
        "category": "discussion",
        "source_type": "slack",
        "question": "What question did Frank Intern ask in the all-hands channel?",
        "expected_answer": "He asked about the standard annual leave policy for new employees.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "all-hands-questions.json"
    },
    {
        "id": "Q090",
        "category": "discussion",
        "source_type": "slack",
        "question": "What answer did Carol Williams give to Frank Intern regarding PTO accrual?",
        "expected_answer": "Full-time employees accrue 25 days of PTO per calendar year, pro-rated for start date, plus 12 sick days.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "all-hands-questions.json"
    },
    {
        "id": "Q091",
        "category": "discussion",
        "source_type": "slack",
        "question": "What contract topic was discussed in leadership sync by Eve Johnson?",
        "expected_answer": "Finalizing the contract for Qdrant Cloud as a dependency for NexusRAG.",
        "authorized_user": "eve",
        "unauthorized_user": "carol",
        "expected_source": "leadership-sync.json"
    },
    {
        "id": "Q092",
        "category": "discussion",
        "source_type": "slack",
        "question": "Who approved the Qdrant Cloud contract in leadership sync?",
        "expected_answer": "Bob Martinez approved it.",
        "authorized_user": "eve",
        "unauthorized_user": "carol",
        "expected_source": "leadership-sync.json"
    },
    {
        "id": "Q093",
        "category": "discussion",
        "source_type": "slack",
        "question": "Which budget line item should Qdrant Cloud costs be categorized under according to Bob Martinez?",
        "expected_answer": "Engineering Infrastructure line.",
        "authorized_user": "eve",
        "unauthorized_user": "carol",
        "expected_source": "leadership-sync.json"
    },
    {
        "id": "Q094",
        "category": "discussion",
        "source_type": "slack",
        "question": "What error message does Alice see when PostgreSQL pool exhaustion occurs on ARM?",
        "expected_answer": "FATAL: remaining connection slots are reserved for non-replication superuser connections.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-general.json"
    },
    {
        "id": "Q095",
        "category": "discussion",
        "source_type": "slack",
        "question": "What postgresql.conf setting does Eve Johnson suggest raising?",
        "expected_answer": "max_connections limit.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-general.json"
    },
    {
        "id": "Q096",
        "category": "discussion",
        "source_type": "slack",
        "question": "How long are arm64 CI builds taking due to Docker cache misses?",
        "expected_answer": "8 minutes each instead of 2 minutes.",
        "authorized_user": "alice",
        "unauthorized_user": "carol",
        "expected_source": "engineering-general.json"
    },
    {
        "id": "Q097",
        "category": "discussion",
        "source_type": "slack",
        "question": "What Redis node upgrade would be required to support 200 req/min for Free tier?",
        "expected_answer": "Upgrade from r6g.large to r6g.xlarge.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-decisions.json"
    },
    {
        "id": "Q098",
        "category": "discussion",
        "source_type": "slack",
        "question": "When will Pro and Enterprise tier API rate limits be re-evaluated according to Bob Martinez?",
        "expected_answer": "In Q3 planning.",
        "authorized_user": "bob",
        "unauthorized_user": "carol",
        "expected_source": "product-decisions.json"
    },
    {
        "id": "Q099",
        "category": "discussion",
        "source_type": "slack",
        "question": "What APM features does the $120k Datadog contract cover?",
        "expected_answer": "APM trace profiling, Kubernetes integration, and custom metrics parsing.",
        "authorized_user": "alice",
        "unauthorized_user": "frank",
        "expected_source": "all-hands-questions.json"
    },
    {
        "id": "Q100",
        "category": "discussion",
        "source_type": "slack",
        "question": "What target deliverable quarter is listed for NexusRAG AI Search in the leadership sync thread?",
        "expected_answer": "Q4 deliverable.",
        "authorized_user": "eve",
        "unauthorized_user": "carol",
        "expected_source": "leadership-sync.json"
    }
]

def main():
    target_path = Path(__file__).resolve().parent.parent / "data" / "golden_dataset.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(golden_questions, f, indent=2)
    print(f"Generated 100-question Golden Dataset at: {target_path}")

if __name__ == "__main__":
    main()
