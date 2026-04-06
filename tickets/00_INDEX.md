# Implementation Tickets — Index

> **Status:** Ready for implementation  
> **Total Tickets:** 16  
> **Canonical References:**  
> - Product scope: `PRD Shared Household Grocery App.md`  
> - Architecture: `Technical Architecture.md`  
> - Routes: `Route_Contract.md`  
> - Duplicate merge: `Concurrency_Duplicate_Merge_Design.md`  
> - Schema / API / UI specs: `Schema_API_UI_sub_specs.md`  
> - Deployment: `Production_Cutover_Runbook.md`, `Hostinger_Deployment_Reference.md`

---

## How to Read These Tickets

Each ticket is self-contained. Read it top to bottom. Complete every task in the order listed unless stated otherwise. When you are done, run through the **Acceptance Criteria** checklist at the bottom of the ticket — every item must pass before the ticket is considered done.

**Key rules for all tickets:**

1. Never commit secrets (`.env`, passwords) to git.
2. All code must be concise, readable, and use declarative variable naming.
3. Follow the file/folder structure exactly as specified.
4. If a ticket says "see Reference," open that file in the workspace and follow what it says.
5. Ask questions **before** guessing. If something is ambiguous, flag it.

---

## Phase Overview

| Phase | Focus | Tickets |
|-------|-------|---------|
| **Phase 1** | Foundation | 1 – 3 |
| **Phase 2** | Core Backend | 4 – 8 |
| **Phase 3** | Frontend & UI | 9 – 11 |
| **Phase 4** | DevOps & Deployment | 12 – 14 |
| **Phase 5** | Hardening & Polish | 15 – 16 |

**Critical path:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10 → 12 → 15

---

## Ticket Files

| # | File | Title | Phase |
|---|------|-------|-------|
| 1 | [01_project_structure_app_factory.md](01_project_structure_app_factory.md) | Project Structure & App Factory Setup | Foundation |
| 2 | [02_database_setup.md](02_database_setup.md) | Database Setup — PostgreSQL, SQLAlchemy & Alembic | Foundation |
| 3 | [03_common_utilities.md](03_common_utilities.md) | Common Utilities — Validators, Authorization & Exceptions | Foundation |
| 4 | [04_auth_module.md](04_auth_module.md) | Auth Module — Registration, Login & Household Creation | Core Backend |
| 5 | [05_grocery_module.md](05_grocery_module.md) | Grocery Module — Add, Toggle, Confirm & Search | Core Backend |
| 6 | [06_favorites_module.md](06_favorites_module.md) | Favorites Module — Quick-Add & Management | Core Backend |
| 7 | [07_household_module.md](07_household_module.md) | Household Module — Invite Codes & Member Management | Core Backend |
| 8 | [08_testing.md](08_testing.md) | Testing — Unit & Integration Tests | Core Backend |
| 9 | [09_tailwind_base_templates.md](09_tailwind_base_templates.md) | Tailwind CSS Setup & Base Templates | Frontend & UI |
| 10 | [10_grocery_list_page_ui.md](10_grocery_list_page_ui.md) | Grocery List Page — Main UI | Frontend & UI |
| 11 | [11_favorites_page_auth_styling.md](11_favorites_page_auth_styling.md) | Favorites Page & Auth Templates Styling | Frontend & UI |
| 12 | [12_docker_compose_setup.md](12_docker_compose_setup.md) | Docker & Docker Compose Setup | DevOps & Deployment |
| 13 | [13_production_deployment.md](13_production_deployment.md) | Production Deployment Configuration | DevOps & Deployment |
| 14 | [14_backup_monitoring.md](14_backup_monitoring.md) | Backup Strategy & Health Monitoring | DevOps & Deployment |
| 15 | [15_security_hardening.md](15_security_hardening.md) | Security Hardening & Rate Limiting | Hardening & Polish |
| 16 | [16_documentation_polish.md](16_documentation_polish.md) | Documentation & Final Polish | Hardening & Polish |

---

## Ticket Dependency Graph

```
Ticket 1  (Project Structure)
   ├── Ticket 2  (Database)
   │      └── Ticket 3  (Common Utilities)
   │             ├── Ticket 4  (Auth)
   │             │      ├── Ticket 5  (Grocery)
   │             │      │      ├── Ticket 6  (Favorites)
   │             │      │      └── Ticket 8  (Tests)
   │             │      └── Ticket 7  (Household)
   │             │             └── Ticket 8  (Tests)
   │             └──────────────── Ticket 8  (Tests)
   ├── Ticket 9  (Tailwind & Templates)
   │      └── Ticket 10 (Grocery UI)
   │             └── Ticket 11 (Favorites UI & Auth Styling)
   └── Ticket 12 (Docker)
          ├── Ticket 13 (Production Deploy)
          └── Ticket 14 (Backups & Monitoring)

Ticket 15 (Security Hardening)  ← depends on all above
Ticket 16 (Documentation & Polish) ← depends on all above
```

---

## Definition of Done (v1)

The v1 release is complete when **all** of the following are true:

- [ ] A household can be created and joined by up to 5 users
- [ ] Grocery items can be added, viewed, checked, unchecked, and confirmed for removal
- [ ] Duplicate items merge quantities atomically (no race conditions)
- [ ] Favorites can be managed and used for one-tap quick-add
- [ ] The mobile UI is comfortable for daily grocery shopping use
- [ ] All core tests pass (`pytest` green)
- [ ] Database migrations are reproducible from an empty database
- [ ] Docker Compose starts both services with health checks passing
- [ ] Production deployment follows the Cutover Runbook successfully
- [ ] Security hardening checklist completed
- [ ] `README.md` and deployment docs are written
