# Cloud File Migration Webapp - PRD Progress

## Project Overview
Building a multi-user SaaS webapp to move files from one cloud provider to another.
Phase 1: OneDrive → Google Drive

---

## Confirmed Requirements

### Scale & Usage
- ~100K files expected
- Largest file: 100GB
- Multi-user SaaS

### Tech Stack
- Backend: Python
- Frontend: Next.js
- Database: PostgreSQL
- SMS: Twilio

### Core Features
- **Folder structure**: Preserved exactly
- **Conflict handling**: Ask per conflict, with option to apply skip/rename/overwrite to ALL remaining
- **Filters**: By file type, date, folder, etc.
- **Resumable**: Auto-resume partially finished migrations
- **Dry run mode**: Yes, preview what would be transferred
- **Notifications**: Email AND SMS

### Architecture
- Intermediate S3 bucket for redundancy
  - Encrypted at rest: Yes
  - Auto-delete: Immediately after confirming exactly-once transfer
- Ensure files are copied exactly once
- Real-time progress visibility
- Granular progress for large files (%, speed, ETA)

### Authentication
- Users authenticate with their own OneDrive/Google accounts via OAuth
- OAuth token handling: Auto-refresh in background

### Operations
- Log retention: 30 days
- Scheduled transfers: Yes, users can pick date/time
- Audit logs: Yes (for individual accounts)

### Compliance
- No specific certifications required for now
- Respect data residency requirements

### Business Model
- Usage-based pricing (affordable rates to encourage adoption)
- No team/organization accounts (individual only)

---

## Pending Questions (Need Answers)

### Pricing Details (Deferred)
- To be determined later

---

## Next Steps
1. ~~Answer the pending questions above~~ ✓
2. ~~Finalize pricing details~~ (deferred)
3. ~~Draft full PRD~~ ✓ (see PRD.md)
4. ~~Create technical plan~~ ✓ (see TECHNICAL_PLAN.md)
5. Review and finalize documents
6. Begin implementation

---

*Last updated: 2026-01-06*
