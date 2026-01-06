# CloudShift Technical Implementation Plan

**Based on:** PRD.md v1.0
**Created:** 2026-01-06

---

## Task Legend

| Status | Meaning |
|--------|---------|
| `TODO` | Not started |
| `IN_PROGRESS` | Currently being worked on |
| `DONE` | Completed |
| `BLOCKED` | Waiting on dependency |

---

## Epic 1: Project Setup & Infrastructure

### Task 1.1: Initialize Python Backend Project

**Description:** Set up Python backend with FastAPI, project structure, virtual environment, and basic configuration management.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] FastAPI application initializes and runs on `localhost:8000`
- [x] Project structure follows standard layout (`/app`, `/tests`, `/config`)
- [x] `requirements.txt` or `pyproject.toml` with initial dependencies
- [x] Environment variable loading via `.env` file
- [x] Health check endpoint returns 200 OK at `/health`
- [x] `.gitignore` configured for Python projects

---

### Task 1.2: Initialize Next.js Frontend Project

**Description:** Set up Next.js frontend application with TypeScript, Tailwind CSS, and basic project structure.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Next.js app runs on `localhost:3000`
- [x] TypeScript configured and working
- [x] Tailwind CSS installed and configured
- [x] Basic layout component with header/footer placeholder
- [x] ESLint and Prettier configured
- [x] Environment variable setup for API URL

---

### Task 1.3: Set Up PostgreSQL Database

**Description:** Configure PostgreSQL database with connection pooling, create initial migration setup using Alembic.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] PostgreSQL database created (local or Docker)
- [x] SQLAlchemy configured with async support
- [x] Alembic initialized for migrations
- [x] Database connection pool configured
- [x] Connection test passes on app startup
- [x] `docker-compose.yml` for local PostgreSQL (optional)

---

### Task 1.4: Set Up Redis and Celery

**Description:** Configure Redis as message broker and Celery for background task processing.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Redis running (local or Docker)
- [x] Celery worker starts and connects to Redis
- [x] Test task executes successfully via Celery
- [x] Celery beat configured for scheduled tasks
- [x] Basic task retry configuration in place

---

### Task 1.5: Configure AWS S3 Bucket

**Description:** Set up S3 bucket for intermediate file storage with encryption and lifecycle policies.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] S3 bucket created with unique name
- [x] Server-side encryption enabled (AES-256)
- [x] IAM user/role with minimal required permissions
- [x] Boto3 client configured in backend
- [x] Test upload/download/delete operations work
- [x] CORS configured if needed for presigned URLs

---

## Epic 2: User Authentication

### Task 2.1: Create User Database Model

**Description:** Define User model with fields for authentication, profile, and notification preferences.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] User model with: id, email, password_hash, created_at, updated_at
- [x] Notification preferences fields: email_notifications, sms_notifications, phone_number
- [x] Alembic migration created and runs successfully
- [x] Model includes proper indexes on email

---

### Task 2.2: Implement User Registration Endpoint

**Description:** Create API endpoint for user registration with email/password.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `POST /api/auth/register` endpoint
- [x] Email validation and uniqueness check
- [x] Password hashing with bcrypt
- [x] Returns user object (without password)
- [x] Proper error responses for duplicate email, weak password
- [x] Unit tests for registration logic

---

### Task 2.3: Implement User Login Endpoint

**Description:** Create API endpoint for user login returning JWT tokens.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `POST /api/auth/login` endpoint
- [x] Validates email and password
- [x] Returns JWT access token and refresh token
- [x] Access token expires in 15 minutes
- [x] Refresh token expires in 7 days
- [x] Failed login returns 401 with generic message

---

### Task 2.4: Implement JWT Middleware and Token Refresh

**Description:** Create middleware to validate JWT on protected routes and endpoint to refresh tokens.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Middleware extracts and validates JWT from Authorization header
- [x] Invalid/expired token returns 401
- [x] `POST /api/auth/refresh` endpoint accepts refresh token
- [x] Returns new access token if refresh token valid
- [x] User object available in request context after auth

---

### Task 2.5: Frontend Auth Pages (Register/Login)

**Description:** Create registration and login pages in Next.js with form validation.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `/register` page with email, password, confirm password fields
- [x] `/login` page with email, password fields
- [x] Client-side validation (email format, password length)
- [x] API integration with error handling
- [x] Redirect to dashboard on successful auth
- [x] JWT stored securely (httpOnly cookie or secure storage)

---

### Task 2.6: Frontend Auth Context and Protected Routes

**Description:** Implement authentication context and route protection in Next.js.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Auth context provides user state and auth methods
- [x] Auto token refresh before expiration
- [x] Protected route wrapper redirects to login if unauthenticated
- [x] Logout functionality clears tokens
- [x] Persists auth state across page refreshes

---

## Epic 3: OAuth Cloud Provider Integration

### Task 3.1: Create Connected Accounts Database Model

**Description:** Define model to store OAuth tokens for connected cloud accounts.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] ConnectedAccount model with: id, user_id, provider (enum), access_token, refresh_token, token_expiry, account_email, created_at
- [x] Tokens encrypted at rest using Fernet or similar
- [x] Foreign key to User with cascade delete
- [x] Unique constraint on (user_id, provider)
- [x] Migration created and runs successfully

---

### Task 3.2: Implement OneDrive OAuth Flow - Backend

**Description:** Create endpoints to initiate and complete OneDrive OAuth authorization.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `GET /api/oauth/onedrive/authorize` returns OAuth URL with state parameter
- [x] `GET /api/oauth/onedrive/callback` exchanges code for tokens
- [x] Tokens encrypted and stored in ConnectedAccount
- [x] Fetches and stores user's OneDrive email/account info
- [x] Handles OAuth errors gracefully
- [x] State parameter validated to prevent CSRF

---

### Task 3.3: Implement Google Drive OAuth Flow - Backend

**Description:** Create endpoints to initiate and complete Google Drive OAuth authorization.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `GET /api/oauth/google/authorize` returns OAuth URL with state parameter
- [x] `GET /api/oauth/google/callback` exchanges code for tokens
- [x] Tokens encrypted and stored in ConnectedAccount
- [x] Fetches and stores user's Google account email
- [x] Requests appropriate Drive scopes (files read/write)
- [x] Handles OAuth errors gracefully

---

### Task 3.4: Implement OAuth Token Auto-Refresh

**Description:** Create service to automatically refresh OAuth tokens before expiration.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Token refresh function for OneDrive tokens
- [x] Token refresh function for Google tokens
- [x] Automatically called when token is within 5 minutes of expiry
- [x] Updates stored tokens on successful refresh
- [x] Logs warning if refresh fails
- [x] Returns valid token or raises exception

---

### Task 3.5: Connected Accounts Management Endpoints

**Description:** Create endpoints to list, disconnect, and check status of connected accounts.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `GET /api/accounts` lists user's connected accounts (provider, email, connected_at)
- [x] `DELETE /api/accounts/:provider` disconnects account and deletes tokens
- [x] `GET /api/accounts/:provider/status` checks if token is valid
- [x] Does not expose raw tokens in responses

---

### Task 3.6: Frontend Connected Accounts UI

**Description:** Create UI for users to connect/disconnect cloud storage accounts.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Account settings page shows connected accounts
- [x] "Connect OneDrive" button initiates OAuth flow
- [x] "Connect Google Drive" button initiates OAuth flow
- [x] Shows account email when connected
- [x] "Disconnect" button with confirmation
- [x] Handles OAuth callback redirect and shows success/error

---

## Epic 4: Cloud Provider File APIs

### Task 4.1: OneDrive File Listing Service

**Description:** Implement service to list files and folders from OneDrive.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Function to list root folder contents
- [x] Function to list specific folder contents by path/ID
- [x] Returns normalized file objects: id, name, type (file/folder), size, modified_at, path
- [x] Handles pagination for large folders
- [x] Uses auto-refreshed tokens

---

### Task 4.2: OneDrive File Download Service

**Description:** Implement service to download files from OneDrive with streaming support.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Function to download file by ID
- [x] Supports streaming download for large files
- [x] Returns file stream and metadata (size, checksum if available)
- [x] Handles download errors with retries
- [x] Reports download progress via callback

---

### Task 4.3: Google Drive File Listing Service

**Description:** Implement service to list files and folders from Google Drive.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Function to list root folder contents
- [x] Function to list specific folder contents by ID
- [x] Returns normalized file objects matching OneDrive format
- [x] Handles pagination
- [x] Uses auto-refreshed tokens

---

### Task 4.4: Google Drive File Upload Service

**Description:** Implement service to upload files to Google Drive with resumable upload support.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Function to upload file to specified folder
- [x] Uses resumable upload API for files > 5MB
- [x] Creates folder if destination path doesn't exist
- [x] Returns uploaded file metadata
- [x] Reports upload progress via callback
- [x] Handles upload errors with retries

---

### Task 4.5: Google Drive Folder Creation Service

**Description:** Implement service to create folder hierarchy in Google Drive.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Function to create single folder in parent
- [x] Function to create nested folder path (creates all intermediate folders)
- [x] Returns folder ID after creation
- [x] Idempotent: returns existing folder if already exists
- [x] Handles naming conflicts

---

### Task 4.6: Conflict Detection Service

**Description:** Implement service to check if file already exists at destination.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Function to check if file exists by name in destination folder
- [x] Returns existing file metadata if found
- [x] Compares by name (case-insensitive option)
- [x] Used before upload to detect conflicts

---

## Epic 5: Transfer Job Management

### Task 5.1: Create Transfer Job Database Models

**Description:** Define models for transfer jobs, job items, and conflict records.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] TransferJob model: id, user_id, status (enum), source_provider, dest_provider, source_folder_id, dest_folder_id, config (JSON), created_at, started_at, completed_at, scheduled_for
- [x] TransferItem model: id, job_id, source_file_id, source_path, dest_path, status, size, error_message, started_at, completed_at
- [x] ConflictRecord model: id, job_id, item_id, resolution (skip/rename/overwrite), resolved_at
- [x] Proper indexes on foreign keys and status fields
- [x] Migrations created

---

### Task 5.2: Transfer Job CRUD Endpoints

**Description:** Create API endpoints to create, read, update, and cancel transfer jobs.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `POST /api/transfers` creates new transfer job
- [x] `GET /api/transfers` lists user's transfer jobs with pagination
- [x] `GET /api/transfers/:id` returns job details with item summary
- [x] `POST /api/transfers/:id/cancel` cancels pending/running job
- [x] `DELETE /api/transfers/:id` deletes completed job and logs
- [x] Validates user owns the job

---

### Task 5.3: Transfer Configuration Endpoint

**Description:** Create endpoint to configure transfer options (filters, conflict handling).

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `PATCH /api/transfers/:id/config` updates job configuration
- [x] Accepts filter config: file_types[], date_range, folder_include[], folder_exclude[]
- [x] Accepts conflict_strategy: ask | skip_all | rename_all | overwrite_all
- [x] Validates job is in 'draft' or 'pending' status
- [x] Returns updated job config

---

### Task 5.4: File Selection and Analysis Endpoint

**Description:** Create endpoint to analyze selected files and return transfer summary.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `POST /api/transfers/:id/analyze` analyzes source selection
- [x] Applies configured filters
- [x] Returns: total_files, total_size, folder_count, file_type_breakdown
- [x] Creates TransferItem records for each file
- [x] Identifies potential conflicts
- [x] Stores analysis results on job

---

### Task 5.5: Dry Run Endpoint

**Description:** Create endpoint to perform dry run and return detailed preview.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `POST /api/transfers/:id/dry-run` performs dry run analysis
- [x] Returns list of files that would be transferred
- [x] Returns list of detected conflicts with details
- [x] Returns folder structure that would be created
- [x] Does not modify any files
- [x] Returns estimated transfer time (based on size)

---

## Epic 6: Transfer Execution Engine

### Task 6.1: Transfer Worker - Single File Pipeline

**Description:** Implement Celery task to transfer a single file through the pipeline.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Downloads file from OneDrive to memory/temp stream
- [x] Uploads to S3 intermediate bucket with job_id prefix
- [x] Downloads from S3 and uploads to Google Drive
- [x] Verifies file size matches at each step
- [x] Deletes S3 file after successful Google Drive upload
- [x] Updates TransferItem status and timestamps
- [x] Handles errors and updates item with error message

---

### Task 6.2: Transfer Worker - Checksum Verification

**Description:** Add checksum verification to ensure exactly-once delivery.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Calculates MD5/SHA256 hash during OneDrive download
- [x] Verifies hash after S3 upload
- [x] Verifies hash after Google Drive upload (if API supports)
- [x] Fails transfer if checksums don't match
- [x] Logs checksum values for audit

---

### Task 6.3: Transfer Job Orchestrator

**Description:** Implement Celery task to orchestrate entire transfer job.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Creates folder structure in destination first
- [x] Queues individual file transfer tasks
- [x] Limits concurrent transfers (configurable, default 5)
- [x] Tracks overall job progress
- [x] Handles job cancellation
- [x] Updates job status: pending → running → completed/failed
- [x] Triggers notification on completion

---

### Task 6.4: Transfer Resume Logic

**Description:** Implement logic to resume partially completed transfers.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] On resume, skips items with status 'completed'
- [x] Re-queues items with status 'failed' or 'pending'
- [x] Cleans up partial S3 files from previous attempt
- [x] Preserves original job configuration
- [x] `POST /api/transfers/:id/resume` endpoint

---

### Task 6.5: Transfer Progress Tracking

**Description:** Implement real-time progress tracking for transfer jobs.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Updates job progress in Redis for fast reads
- [x] Tracks: files_completed, files_failed, bytes_transferred, current_file
- [x] For large files: tracks bytes_uploaded for current file
- [x] Progress updates every 5 seconds max
- [x] `GET /api/transfers/:id/progress` returns current progress

---

### Task 6.6: WebSocket/SSE Progress Streaming

**Description:** Implement real-time progress streaming to frontend.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] WebSocket or SSE endpoint for progress updates
- [x] Clients subscribe to specific job_id
- [x] Pushes progress updates as they occur
- [x] Sends completion/failure event
- [x] Handles client disconnection gracefully
- [x] Authenticates WebSocket connections

---

## Epic 7: Conflict Handling

### Task 7.1: Conflict Detection During Transfer

**Description:** Implement conflict detection before each file upload.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Checks destination for existing file before upload
- [x] Creates ConflictRecord if conflict detected
- [x] Pauses job if conflict_strategy is 'ask'
- [x] Applies automatic resolution if strategy is skip/rename/overwrite_all
- [x] Logs conflict and resolution in audit

---

### Task 7.2: Conflict Resolution Endpoints

**Description:** Create endpoints for users to resolve conflicts.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `GET /api/transfers/:id/conflicts` lists pending conflicts
- [x] `POST /api/transfers/:id/conflicts/:conflict_id/resolve` resolves single conflict
- [x] `POST /api/transfers/:id/conflicts/resolve-all` applies resolution to all pending
- [x] Accepts resolution: skip | rename | overwrite
- [x] Resumes job after conflicts resolved
- [x] Validates user owns the job

---

### Task 7.3: Conflict Resolution UI

**Description:** Create frontend UI for resolving file conflicts.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Modal/page shows conflict details (filename, source size, dest size, dates)
- [ ] Buttons: Skip, Rename, Overwrite
- [ ] Checkbox: "Apply to all remaining conflicts"
- [ ] Shows preview of renamed filename
- [ ] Updates in real-time as conflicts are resolved
- [ ] Allows resuming transfer after resolution

---

## Epic 8: Scheduling

### Task 8.1: Scheduled Transfer Support

**Description:** Implement ability to schedule transfers for future execution.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] TransferJob.scheduled_for field stores scheduled datetime
- [x] `POST /api/transfers/:id/schedule` sets schedule time
- [x] Validates scheduled time is in the future
- [x] Job status set to 'scheduled'
- [x] Celery beat checks for due scheduled jobs every minute

---

### Task 8.2: Scheduled Job Executor

**Description:** Implement Celery beat task to start scheduled transfers.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Periodic task runs every minute
- [x] Finds jobs where scheduled_for <= now and status = 'scheduled'
- [x] Starts transfer orchestrator for each due job
- [x] Handles timezone correctly (store in UTC)
- [x] Updates job status to 'running'

---

### Task 8.3: Schedule Management UI

**Description:** Create UI for scheduling and managing scheduled transfers.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Date/time picker in transfer configuration
- [ ] Shows scheduled time in user's timezone
- [ ] "Start Now" vs "Schedule" options
- [ ] Scheduled transfers visible in dashboard with countdown
- [ ] Ability to cancel or reschedule

---

## Epic 9: Notifications

### Task 9.1: Email Notification Service

**Description:** Implement email sending service via AWS SES for transfer notifications.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] AWS SES client configured with credentials
- [x] SES sending domain verified
- [x] HTML email template for transfer completion
- [x] HTML email template for transfer failure
- [x] Includes: job summary, files transferred, duration, errors if any
- [x] Sends to user's registered email
- [x] Handles send failures gracefully

---

### Task 9.2: SMS Notification Service

**Description:** Implement SMS sending service via Twilio.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Twilio client configured with credentials
- [x] SMS template for transfer completion
- [x] SMS template for transfer failure
- [x] Respects user's SMS notification preference
- [x] Validates phone number format
- [x] Handles send failures gracefully

---

### Task 9.3: Notification Trigger Integration

**Description:** Integrate notification services with transfer completion events.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Notifications triggered on job completion (success or failure)
- [x] Respects user's notification preferences (email, SMS, both, none)
- [x] Notifications sent asynchronously (Celery task)
- [x] Notification history logged
- [x] Does not block transfer completion

---

### Task 9.4: Notification Preferences UI

**Description:** Create UI for managing notification preferences.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Settings page section for notifications
- [ ] Toggle for email notifications
- [ ] Toggle for SMS notifications
- [ ] Phone number input with validation
- [ ] Test notification button
- [ ] Saves preferences to user profile

---

## Epic 10: Audit Logging

### Task 10.1: Audit Log Database Model

**Description:** Create model for storing audit log entries.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] AuditLog model: id, user_id, action (enum), resource_type, resource_id, details (JSON), ip_address, user_agent, created_at
- [x] Actions: login, logout, transfer_created, transfer_started, transfer_completed, conflict_resolved, account_connected, account_disconnected, settings_changed
- [x] Index on user_id and created_at
- [x] Migration created

---

### Task 10.2: Audit Logging Service

**Description:** Implement service to create audit log entries throughout the application.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Function to log action with context
- [x] Automatically captures IP and user agent from request
- [x] Async logging to not block requests
- [x] Captures relevant details per action type
- [x] Integrated at key points: auth, transfers, account management

---

### Task 10.3: Audit Log Endpoints

**Description:** Create endpoints for users to view their audit logs.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] `GET /api/audit-logs` lists user's audit logs
- [x] Supports pagination (limit, offset)
- [x] Supports filtering by action type, date range
- [x] `GET /api/audit-logs/export` exports as CSV
- [x] 30-day retention enforced (older logs not returned)

---

### Task 10.4: Audit Log Cleanup Job

**Description:** Implement scheduled job to clean up old audit logs.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Celery beat task runs daily
- [x] Deletes audit logs older than 30 days
- [x] Logs number of records deleted
- [x] Handles large deletes in batches

---

### Task 10.5: Audit Log UI

**Description:** Create UI for viewing audit log history.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Audit log page with table view
- [x] Columns: date, action, details, IP address
- [x] Filter by action type
- [x] Date range filter
- [x] Export button (CSV download)
- [x] Pagination

---

## Epic 11: Frontend - Dashboard & Transfer Flow

### Task 11.1: Dashboard Page

**Description:** Create main dashboard showing transfer overview.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Shows active transfers with real-time progress
- [x] Shows scheduled transfers with countdown
- [x] Shows recent completed transfers
- [x] "New Transfer" CTA button
- [x] Quick stats: total files migrated, data transferred
- [x] Empty state for new users

---

### Task 11.2: New Transfer - Source Selection

**Description:** Create UI for selecting source files/folders from OneDrive.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] File browser showing OneDrive contents
- [x] Navigate into folders
- [x] Select entire folders or individual files
- [x] Shows file size and count for selection
- [x] Breadcrumb navigation
- [x] "Select All" option

---

### Task 11.3: New Transfer - Destination Selection

**Description:** Create UI for selecting destination folder in Google Drive.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] File browser showing Google Drive folders
- [x] Navigate into folders
- [x] Create new folder option
- [x] Select destination folder
- [x] Shows current path
- [x] Validates both accounts connected

---

### Task 11.4: New Transfer - Filter Configuration

**Description:** Create UI for configuring transfer filters.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] File type filter (checkboxes or multi-select)
- [x] Date range filter (from/to date pickers)
- [x] Folder include/exclude patterns (text input)
- [x] Preview updates as filters change
- [x] Clear filters option

---

### Task 11.5: New Transfer - Review & Confirm

**Description:** Create review page showing transfer summary before starting.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Summary: source, destination, file count, total size
- [x] Folder structure preview
- [x] Detected conflicts listed
- [x] Conflict handling option selection
- [x] Schedule option with date/time picker
- [x] "Run Dry Run" button
- [x] "Start Transfer" / "Schedule Transfer" buttons

---

### Task 11.6: Transfer Progress Page

**Description:** Create real-time transfer progress view.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Overall progress bar (files completed / total)
- [x] Bytes transferred / total bytes
- [x] Current file being transferred with individual progress
- [x] Transfer speed (MB/s)
- [x] Estimated time remaining
- [x] List of completed files (collapsible)
- [x] List of failed files with errors
- [x] Cancel button
- [x] Auto-updates via WebSocket/SSE

---

### Task 11.7: Transfer History Page

**Description:** Create page showing past transfer jobs.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Table: date, source, destination, files, size, status, duration
- [ ] Click to view details
- [ ] Filter by status (completed, failed, cancelled)
- [ ] Date range filter
- [ ] Pagination
- [ ] Delete completed jobs option

---

### Task 11.8: Transfer Detail Page

**Description:** Create detailed view of a specific transfer job.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Job metadata: dates, duration, configuration
- [ ] File list with status (searchable)
- [ ] Error details for failed files
- [ ] Conflict resolutions made
- [ ] Option to retry failed files
- [ ] Download job report

---

## Epic 12: Error Handling & Resilience

### Task 12.1: Retry Logic for Transient Failures

**Description:** Implement retry logic with exponential backoff for API calls.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Wrapper for cloud API calls with retry logic
- [x] 3 retry attempts with exponential backoff (1s, 2s, 4s)
- [x] Identifies transient errors (rate limits, timeouts, 5xx)
- [x] Does not retry permanent errors (404, 403)
- [x] Logs retry attempts

---

### Task 12.2: Rate Limit Handling

**Description:** Implement rate limit detection and backoff for cloud APIs.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Detects 429 responses from OneDrive/Google
- [x] Reads Retry-After header if present
- [x] Implements global rate limiting per provider
- [x] Queues requests when near limit
- [x] Logs rate limit events

---

### Task 12.3: Graceful Job Failure Handling

**Description:** Implement handling for unrecoverable job failures.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Job marked as 'failed' after max retries exceeded
- [x] Partial progress preserved (completed files stay completed)
- [x] Cleanup of S3 intermediate files
- [x] User notified of failure with details
- [x] Job can be retried (resumes from failure point)

---

### Task 12.4: API Error Response Standardization

**Description:** Standardize error responses across all API endpoints.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Consistent error format: { error: string, code: string, details?: object }
- [x] Appropriate HTTP status codes
- [x] User-friendly error messages
- [x] Internal errors logged with stack trace
- [x] Sensitive info not exposed in responses

---

## Epic 13: Testing

### Task 13.1: Backend Unit Tests - Auth

**Description:** Write unit tests for authentication services.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Tests for registration (valid, duplicate email, weak password)
- [x] Tests for login (valid, wrong password, unknown email)
- [x] Tests for JWT generation and validation
- [x] Tests for token refresh
- [x] 90%+ coverage for auth module

---

### Task 13.2: Backend Unit Tests - Transfer Logic

**Description:** Write unit tests for transfer orchestration logic.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Tests for job state transitions
- [x] Tests for conflict detection
- [x] Tests for filter application
- [x] Tests for progress calculation
- [x] Mock cloud API calls

---

### Task 13.3: Backend Integration Tests

**Description:** Write integration tests for API endpoints.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Tests for complete auth flow
- [ ] Tests for transfer CRUD operations
- [ ] Tests for OAuth callback handling
- [ ] Uses test database
- [ ] Runs in CI pipeline

---

### Task 13.4: Frontend Component Tests

**Description:** Write tests for key React components.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Tests for file browser component
- [ ] Tests for progress display
- [ ] Tests for conflict resolution modal
- [ ] Tests for form validation
- [ ] Uses React Testing Library

---

### Task 13.5: End-to-End Tests

**Description:** Write E2E tests for critical user flows.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Test: Register → Login → Connect accounts
- [ ] Test: Create transfer → Configure → Start
- [ ] Test: View progress → Completion
- [ ] Uses Playwright or Cypress
- [ ] Runs against staging environment

---

## Epic 14: Documentation & Deployment

### Task 14.1: API Documentation

**Description:** Generate and publish API documentation.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] OpenAPI/Swagger spec generated from FastAPI
- [x] All endpoints documented with examples
- [x] Authentication documented
- [x] Error codes documented
- [x] Accessible at /docs endpoint

---

### Task 14.2: Environment Configuration Documentation

**Description:** Document all required environment variables and configuration.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] List of all env vars with descriptions
- [x] Example .env.example file
- [x] Required vs optional clearly marked
- [x] Setup instructions for local development

---

### Task 14.3: Deployment Configuration

**Description:** Create deployment configuration for production.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Docker files for backend and frontend
- [x] Docker Compose for full stack
- [x] Production environment configuration
- [x] Database migration strategy
- [x] Health check endpoints configured

---

### Task 14.4: CI/CD Pipeline

**Description:** Set up continuous integration and deployment pipeline.

**Status:** `DONE`

**Acceptance Criteria:**
- [x] Runs tests on PR
- [x] Linting and type checking
- [x] Builds Docker images
- [x] Deploys to staging on merge to main
- [x] Manual promotion to production

---

## Summary

| Epic | Tasks | Description |
|------|-------|-------------|
| 1. Project Setup | 5 | Initialize projects, databases, queues |
| 2. User Authentication | 6 | User accounts, JWT, frontend auth |
| 3. OAuth Integration | 6 | OneDrive/Google OAuth, token management |
| 4. Cloud APIs | 6 | File listing, upload, download services |
| 5. Transfer Jobs | 5 | Job models, CRUD, configuration, analysis |
| 6. Transfer Engine | 6 | Worker pipeline, orchestration, progress |
| 7. Conflict Handling | 3 | Detection, resolution, UI |
| 8. Scheduling | 3 | Scheduled transfers |
| 9. Notifications | 4 | Email, SMS, preferences |
| 10. Audit Logging | 5 | Logging, retention, UI |
| 11. Frontend | 8 | Dashboard, transfer flow, history |
| 12. Error Handling | 4 | Retries, rate limits, graceful failures |
| 13. Testing | 5 | Unit, integration, E2E tests |
| 14. Documentation | 4 | API docs, deployment |

**Total Tasks: 70**

---

*Plan version: 1.0 | Created: 2026-01-06*
