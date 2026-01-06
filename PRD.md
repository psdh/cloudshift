# Product Requirements Document: CloudShift

## Cloud File Migration Webapp

**Version:** 1.0
**Date:** 2026-01-06
**Status:** Draft

---

## 1. Overview

### 1.1 Problem Statement

Users with large file collections stored in cloud services face significant challenges when migrating to a different provider. Current solutions are either:
- Manual and time-consuming (download then re-upload)
- Unreliable for large files (no resume capability)
- Lacking visibility into transfer progress
- Unable to handle conflicts intelligently

### 1.2 Solution

CloudShift is a multi-user SaaS webapp that enables seamless file migration between cloud storage providers. Users authenticate with their source and destination accounts, configure their transfer preferences, and let CloudShift handle the rest—with full visibility, reliability, and control.

### 1.3 Scope

**Phase 1:** OneDrive → Google Drive
**Future Phases:** Additional provider pairs (Dropbox, Box, iCloud, AWS S3, etc.)

---

## 2. Target Users

### 2.1 Primary Users
- Individual professionals migrating personal/work files between cloud providers
- Small business owners switching cloud ecosystems
- Users consolidating files from multiple cloud accounts

### 2.2 User Characteristics
- Non-technical to moderately technical
- File collections ranging from hundreds to ~100,000 files
- May have individual files up to 100GB in size

---

## 3. Functional Requirements

### 3.1 Authentication & Authorization

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTH-1 | Users create CloudShift accounts (email/password or social login) | P0 |
| AUTH-2 | Users connect OneDrive accounts via OAuth 2.0 | P0 |
| AUTH-3 | Users connect Google Drive accounts via OAuth 2.0 | P0 |
| AUTH-4 | OAuth tokens auto-refresh in background without user intervention | P0 |
| AUTH-5 | Users can disconnect/reconnect cloud accounts at any time | P1 |

### 3.2 Transfer Configuration

| ID | Requirement | Priority |
|----|-------------|----------|
| CONF-1 | Users select source folders/files from OneDrive | P0 |
| CONF-2 | Users select destination folder in Google Drive | P0 |
| CONF-3 | Folder structure is preserved exactly as source | P0 |
| CONF-4 | Users can filter by file type (e.g., .pdf, .docx, images) | P1 |
| CONF-5 | Users can filter by date range (created/modified) | P1 |
| CONF-6 | Users can filter by folder inclusion/exclusion patterns | P1 |
| CONF-7 | Users can schedule transfers for a specific date/time | P1 |

### 3.3 Conflict Handling

| ID | Requirement | Priority |
|----|-------------|----------|
| CNFL-1 | Detect conflicts (same filename exists at destination) | P0 |
| CNFL-2 | Prompt user per conflict: Skip / Rename / Overwrite | P0 |
| CNFL-3 | Option to apply choice to ALL remaining conflicts | P0 |
| CNFL-4 | Conflict resolution decisions logged in audit trail | P1 |

### 3.4 Transfer Execution

| ID | Requirement | Priority |
|----|-------------|----------|
| EXEC-1 | Files copied via intermediate S3 bucket for redundancy | P0 |
| EXEC-2 | Exactly-once delivery guaranteed (no duplicates, no missed files) | P0 |
| EXEC-3 | S3 intermediate files encrypted at rest | P0 |
| EXEC-4 | S3 intermediate files auto-deleted immediately after confirmed transfer | P0 |
| EXEC-5 | Transfers are resumable—auto-resume after interruption | P0 |
| EXEC-6 | Support files up to 100GB | P0 |
| EXEC-7 | Support migrations up to 100,000 files | P0 |

### 3.5 Dry Run Mode

| ID | Requirement | Priority |
|----|-------------|----------|
| DRY-1 | Preview mode shows what would be transferred without executing | P0 |
| DRY-2 | Dry run displays file count, total size, folder structure preview | P0 |
| DRY-3 | Dry run identifies potential conflicts before transfer | P1 |

### 3.6 Progress & Monitoring

| ID | Requirement | Priority |
|----|-------------|----------|
| PROG-1 | Real-time progress visibility (files completed / total) | P0 |
| PROG-2 | Granular progress for large files: percentage, speed, ETA | P0 |
| PROG-3 | Transfer status dashboard showing all jobs | P0 |
| PROG-4 | Historical view of completed transfers | P1 |

### 3.7 Notifications

| ID | Requirement | Priority |
|----|-------------|----------|
| NOTIF-1 | Email notifications on transfer completion | P0 |
| NOTIF-2 | SMS notifications on transfer completion (via Twilio) | P0 |
| NOTIF-3 | Notification on transfer failure with error details | P0 |
| NOTIF-4 | Users configure notification preferences (email, SMS, both, none) | P1 |

### 3.8 Audit & Logging

| ID | Requirement | Priority |
|----|-------------|----------|
| AUDIT-1 | All user actions logged (login, transfer start, config changes) | P0 |
| AUDIT-2 | Transfer logs include file-level success/failure details | P0 |
| AUDIT-3 | Logs retained for 30 days | P0 |
| AUDIT-4 | Users can view/export their audit logs | P1 |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| PERF-1 | Concurrent transfers per user | Up to 5 parallel file transfers |
| PERF-2 | Large file transfer speed | Limited by cloud provider APIs |
| PERF-3 | Dashboard load time | < 2 seconds |
| PERF-4 | Real-time progress update frequency | Every 5 seconds |

### 4.2 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| REL-1 | Service availability | 99.5% uptime |
| REL-2 | Transfer success rate (non-user-error) | 99.9% |
| REL-3 | Auto-retry on transient failures | 3 attempts with exponential backoff |

### 4.3 Security

| ID | Requirement |
|----|-------------|
| SEC-1 | OAuth tokens encrypted at rest |
| SEC-2 | All data in transit over TLS 1.3 |
| SEC-3 | S3 intermediate storage encrypted (AES-256) |
| SEC-4 | No permanent storage of user files (pass-through only) |
| SEC-5 | Respect data residency requirements |

### 4.4 Compliance

| ID | Requirement |
|----|-------------|
| COMP-1 | Respect data residency (process in same region as user preference) |
| COMP-2 | Users can request data deletion |
| COMP-3 | Privacy policy and ToS clearly displayed |

---

## 5. Technical Architecture

### 5.1 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (React) |
| Backend | Python |
| Database | PostgreSQL |
| File Queue | Redis / Celery |
| Intermediate Storage | AWS S3 (encrypted) |
| SMS Provider | Twilio |
| Email Provider | AWS SES |
| Hosting | AWS |

### 5.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  - Dashboard, Transfer Config, Progress View, Account Settings  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (Python)                        │
│  - Auth, Transfer Jobs, Progress Streaming, Notifications       │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │ PostgreSQL  │ │   Redis     │ │    S3       │
        │ (metadata)  │ │ (job queue) │ │ (temp files)│
        └─────────────┘ └─────────────┘ └─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Worker Pool (Celery)                         │
│  - OneDrive Download → S3 → Google Drive Upload                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
        ┌─────────────┐                 ┌─────────────┐
        │  OneDrive   │                 │Google Drive │
        │    API      │                 │    API      │
        └─────────────┘                 └─────────────┘
```

### 5.3 Transfer Flow

1. User configures transfer (source, destination, filters, conflict rules)
2. System runs dry-run analysis (optional)
3. User confirms and starts transfer (or schedules for later)
4. Worker downloads file from OneDrive → streams to S3
5. Worker uploads from S3 → Google Drive
6. System verifies checksum match (exactly-once guarantee)
7. S3 file immediately deleted after confirmation
8. Progress updated in real-time via WebSocket/SSE
9. Notification sent on completion/failure

---

## 6. User Interface

### 6.1 Key Screens

1. **Dashboard** - Overview of all transfers (active, scheduled, completed)
2. **New Transfer** - Wizard to configure source, destination, filters
3. **Conflict Resolution** - Modal/page to handle detected conflicts
4. **Transfer Progress** - Real-time view of ongoing transfer
5. **Transfer History** - Log of past transfers with details
6. **Account Settings** - Connected accounts, notification preferences
7. **Audit Log** - Searchable log of user actions

### 6.2 UX Principles

- Mobile-responsive design
- Progress visible without constant page refresh
- Clear error messages with actionable next steps
- Minimal clicks to start a basic transfer

---

## 7. Business Model

### 7.1 Pricing

- **Model:** Usage-based (pay per GB transferred)
- **Goal:** Affordable pricing to encourage adoption
- **Details:** To be determined

### 7.2 Account Type

- Individual accounts only (no team/org features in Phase 1)

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Transfer success rate | > 99% |
| User task completion (start → finish transfer) | > 80% |
| Average time to first transfer | < 5 minutes |
| NPS score | > 40 |
| Support tickets per 100 transfers | < 5 |

---

## 9. Out of Scope (Phase 1)

- Bi-directional sync (one-time migration only)
- Team/organization accounts
- Providers other than OneDrive → Google Drive
- Desktop/mobile native apps
- API for programmatic access

---

## 10. Open Questions

1. ~~Email service provider selection~~ → AWS SES
2. ~~Hosting infrastructure decision~~ → AWS
3. Specific pricing tiers and rates (deferred)

---

## 11. Appendix

### 11.1 Glossary

| Term | Definition |
|------|------------|
| Dry run | Preview mode that shows what would happen without executing |
| Exactly-once | Guarantee that each file is transferred exactly one time |
| Conflict | When a file with the same name exists at the destination |

### 11.2 References

- [OneDrive API Documentation](https://docs.microsoft.com/en-us/onedrive/developer/)
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [Twilio SMS API](https://www.twilio.com/docs/sms)

---

*Document version: 1.0 | Last updated: 2026-01-06*
