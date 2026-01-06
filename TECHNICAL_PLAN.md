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

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] PostgreSQL database created (local or Docker)
- [ ] SQLAlchemy configured with async support
- [ ] Alembic initialized for migrations
- [ ] Database connection pool configured
- [ ] Connection test passes on app startup
- [ ] `docker-compose.yml` for local PostgreSQL (optional)

---

### Task 1.4: Set Up Redis and Celery

**Description:** Configure Redis as message broker and Celery for background task processing.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Redis running (local or Docker)
- [ ] Celery worker starts and connects to Redis
- [ ] Test task executes successfully via Celery
- [ ] Celery beat configured for scheduled tasks
- [ ] Basic task retry configuration in place

---

### Task 1.5: Configure AWS S3 Bucket

**Description:** Set up S3 bucket for intermediate file storage with encryption and lifecycle policies.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] S3 bucket created with unique name
- [ ] Server-side encryption enabled (AES-256)
- [ ] IAM user/role with minimal required permissions
- [ ] Boto3 client configured in backend
- [ ] Test upload/download/delete operations work
- [ ] CORS configured if needed for presigned URLs

---

## Epic 2: User Authentication

### Task 2.1: Create User Database Model

**Description:** Define User model with fields for authentication, profile, and notification preferences.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] User model with: id, email, password_hash, created_at, updated_at
- [ ] Notification preferences fields: email_notifications, sms_notifications, phone_number
- [ ] Alembic migration created and runs successfully
- [ ] Model includes proper indexes on email

---

### Task 2.2: Implement User Registration Endpoint

**Description:** Create API endpoint for user registration with email/password.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `POST /api/auth/register` endpoint
- [ ] Email validation and uniqueness check
- [ ] Password hashing with bcrypt
- [ ] Returns user object (without password)
- [ ] Proper error responses for duplicate email, weak password
- [ ] Unit tests for registration logic

---

### Task 2.3: Implement User Login Endpoint

**Description:** Create API endpoint for user login returning JWT tokens.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `POST /api/auth/login` endpoint
- [ ] Validates email and password
- [ ] Returns JWT access token and refresh token
- [ ] Access token expires in 15 minutes
- [ ] Refresh token expires in 7 days
- [ ] Failed login returns 401 with generic message

---

### Task 2.4: Implement JWT Middleware and Token Refresh

**Description:** Create middleware to validate JWT on protected routes and endpoint to refresh tokens.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Middleware extracts and validates JWT from Authorization header
- [ ] Invalid/expired token returns 401
- [ ] `POST /api/auth/refresh` endpoint accepts refresh token
- [ ] Returns new access token if refresh token valid
- [ ] User object available in request context after auth

---

### Task 2.5: Frontend Auth Pages (Register/Login)

**Description:** Create registration and login pages in Next.js with form validation.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `/register` page with email, password, confirm password fields
- [ ] `/login` page with email, password fields
- [ ] Client-side validation (email format, password length)
- [ ] API integration with error handling
- [ ] Redirect to dashboard on successful auth
- [ ] JWT stored securely (httpOnly cookie or secure storage)

---

### Task 2.6: Frontend Auth Context and Protected Routes

**Description:** Implement authentication context and route protection in Next.js.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Auth context provides user state and auth methods
- [ ] Auto token refresh before expiration
- [ ] Protected route wrapper redirects to login if unauthenticated
- [ ] Logout functionality clears tokens
- [ ] Persists auth state across page refreshes

---

## Epic 3: OAuth Cloud Provider Integration

### Task 3.1: Create Connected Accounts Database Model

**Description:** Define model to store OAuth tokens for connected cloud accounts.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] ConnectedAccount model with: id, user_id, provider (enum), access_token, refresh_token, token_expiry, account_email, created_at
- [ ] Tokens encrypted at rest using Fernet or similar
- [ ] Foreign key to User with cascade delete
- [ ] Unique constraint on (user_id, provider)
- [ ] Migration created and runs successfully

---

### Task 3.2: Implement OneDrive OAuth Flow - Backend

**Description:** Create endpoints to initiate and complete OneDrive OAuth authorization.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `GET /api/oauth/onedrive/authorize` returns OAuth URL with state parameter
- [ ] `GET /api/oauth/onedrive/callback` exchanges code for tokens
- [ ] Tokens encrypted and stored in ConnectedAccount
- [ ] Fetches and stores user's OneDrive email/account info
- [ ] Handles OAuth errors gracefully
- [ ] State parameter validated to prevent CSRF

---

### Task 3.3: Implement Google Drive OAuth Flow - Backend

**Description:** Create endpoints to initiate and complete Google Drive OAuth authorization.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `GET /api/oauth/google/authorize` returns OAuth URL with state parameter
- [ ] `GET /api/oauth/google/callback` exchanges code for tokens
- [ ] Tokens encrypted and stored in ConnectedAccount
- [ ] Fetches and stores user's Google account email
- [ ] Requests appropriate Drive scopes (files read/write)
- [ ] Handles OAuth errors gracefully

---

### Task 3.4: Implement OAuth Token Auto-Refresh

**Description:** Create service to automatically refresh OAuth tokens before expiration.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Token refresh function for OneDrive tokens
- [ ] Token refresh function for Google tokens
- [ ] Automatically called when token is within 5 minutes of expiry
- [ ] Updates stored tokens on successful refresh
- [ ] Logs warning if refresh fails
- [ ] Returns valid token or raises exception

---

### Task 3.5: Connected Accounts Management Endpoints

**Description:** Create endpoints to list, disconnect, and check status of connected accounts.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `GET /api/accounts` lists user's connected accounts (provider, email, connected_at)
- [ ] `DELETE /api/accounts/:provider` disconnects account and deletes tokens
- [ ] `GET /api/accounts/:provider/status` checks if token is valid
- [ ] Does not expose raw tokens in responses

---

### Task 3.6: Frontend Connected Accounts UI

**Description:** Create UI for users to connect/disconnect cloud storage accounts.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Account settings page shows connected accounts
- [ ] "Connect OneDrive" button initiates OAuth flow
- [ ] "Connect Google Drive" button initiates OAuth flow
- [ ] Shows account email when connected
- [ ] "Disconnect" button with confirmation
- [ ] Handles OAuth callback redirect and shows success/error

---

## Epic 4: Cloud Provider File APIs

### Task 4.1: OneDrive File Listing Service

**Description:** Implement service to list files and folders from OneDrive.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Function to list root folder contents
- [ ] Function to list specific folder contents by path/ID
- [ ] Returns normalized file objects: id, name, type (file/folder), size, modified_at, path
- [ ] Handles pagination for large folders
- [ ] Uses auto-refreshed tokens

---

### Task 4.2: OneDrive File Download Service

**Description:** Implement service to download files from OneDrive with streaming support.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Function to download file by ID
- [ ] Supports streaming download for large files
- [ ] Returns file stream and metadata (size, checksum if available)
- [ ] Handles download errors with retries
- [ ] Reports download progress via callback

---

### Task 4.3: Google Drive File Listing Service

**Description:** Implement service to list files and folders from Google Drive.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Function to list root folder contents
- [ ] Function to list specific folder contents by ID
- [ ] Returns normalized file objects matching OneDrive format
- [ ] Handles pagination
- [ ] Uses auto-refreshed tokens

---

### Task 4.4: Google Drive File Upload Service

**Description:** Implement service to upload files to Google Drive with resumable upload support.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Function to upload file to specified folder
- [ ] Uses resumable upload API for files > 5MB
- [ ] Creates folder if destination path doesn't exist
- [ ] Returns uploaded file metadata
- [ ] Reports upload progress via callback
- [ ] Handles upload errors with retries

---

### Task 4.5: Google Drive Folder Creation Service

**Description:** Implement service to create folder hierarchy in Google Drive.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Function to create single folder in parent
- [ ] Function to create nested folder path (creates all intermediate folders)
- [ ] Returns folder ID after creation
- [ ] Idempotent: returns existing folder if already exists
- [ ] Handles naming conflicts

---

### Task 4.6: Conflict Detection Service

**Description:** Implement service to check if file already exists at destination.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Function to check if file exists by name in destination folder
- [ ] Returns existing file metadata if found
- [ ] Compares by name (case-insensitive option)
- [ ] Used before upload to detect conflicts

---

## Epic 5: Transfer Job Management

### Task 5.1: Create Transfer Job Database Models

**Description:** Define models for transfer jobs, job items, and conflict records.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] TransferJob model: id, user_id, status (enum), source_provider, dest_provider, source_folder_id, dest_folder_id, config (JSON), created_at, started_at, completed_at, scheduled_for
- [ ] TransferItem model: id, job_id, source_file_id, source_path, dest_path, status, size, error_message, started_at, completed_at
- [ ] ConflictRecord model: id, job_id, item_id, resolution (skip/rename/overwrite), resolved_at
- [ ] Proper indexes on foreign keys and status fields
- [ ] Migrations created

---

### Task 5.2: Transfer Job CRUD Endpoints

**Description:** Create API endpoints to create, read, update, and cancel transfer jobs.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `POST /api/transfers` creates new transfer job
- [ ] `GET /api/transfers` lists user's transfer jobs with pagination
- [ ] `GET /api/transfers/:id` returns job details with item summary
- [ ] `POST /api/transfers/:id/cancel` cancels pending/running job
- [ ] `DELETE /api/transfers/:id` deletes completed job and logs
- [ ] Validates user owns the job

---

### Task 5.3: Transfer Configuration Endpoint

**Description:** Create endpoint to configure transfer options (filters, conflict handling).

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `PATCH /api/transfers/:id/config` updates job configuration
- [ ] Accepts filter config: file_types[], date_range, folder_include[], folder_exclude[]
- [ ] Accepts conflict_strategy: ask | skip_all | rename_all | overwrite_all
- [ ] Validates job is in 'draft' or 'pending' status
- [ ] Returns updated job config

---

### Task 5.4: File Selection and Analysis Endpoint

**Description:** Create endpoint to analyze selected files and return transfer summary.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `POST /api/transfers/:id/analyze` analyzes source selection
- [ ] Applies configured filters
- [ ] Returns: total_files, total_size, folder_count, file_type_breakdown
- [ ] Creates TransferItem records for each file
- [ ] Identifies potential conflicts
- [ ] Stores analysis results on job

---

### Task 5.5: Dry Run Endpoint

**Description:** Create endpoint to perform dry run and return detailed preview.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `POST /api/transfers/:id/dry-run` performs dry run analysis
- [ ] Returns list of files that would be transferred
- [ ] Returns list of detected conflicts with details
- [ ] Returns folder structure that would be created
- [ ] Does not modify any files
- [ ] Returns estimated transfer time (based on size)

---

## Epic 6: Transfer Execution Engine

### Task 6.1: Transfer Worker - Single File Pipeline

**Description:** Implement Celery task to transfer a single file through the pipeline.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Downloads file from OneDrive to memory/temp stream
- [ ] Uploads to S3 intermediate bucket with job_id prefix
- [ ] Downloads from S3 and uploads to Google Drive
- [ ] Verifies file size matches at each step
- [ ] Deletes S3 file after successful Google Drive upload
- [ ] Updates TransferItem status and timestamps
- [ ] Handles errors and updates item with error message

---

### Task 6.2: Transfer Worker - Checksum Verification

**Description:** Add checksum verification to ensure exactly-once delivery.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Calculates MD5/SHA256 hash during OneDrive download
- [ ] Verifies hash after S3 upload
- [ ] Verifies hash after Google Drive upload (if API supports)
- [ ] Fails transfer if checksums don't match
- [ ] Logs checksum values for audit

---

### Task 6.3: Transfer Job Orchestrator

**Description:** Implement Celery task to orchestrate entire transfer job.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Creates folder structure in destination first
- [ ] Queues individual file transfer tasks
- [ ] Limits concurrent transfers (configurable, default 5)
- [ ] Tracks overall job progress
- [ ] Handles job cancellation
- [ ] Updates job status: pending → running → completed/failed
- [ ] Triggers notification on completion

---

### Task 6.4: Transfer Resume Logic

**Description:** Implement logic to resume partially completed transfers.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] On resume, skips items with status 'completed'
- [ ] Re-queues items with status 'failed' or 'pending'
- [ ] Cleans up partial S3 files from previous attempt
- [ ] Preserves original job configuration
- [ ] `POST /api/transfers/:id/resume` endpoint

---

### Task 6.5: Transfer Progress Tracking

**Description:** Implement real-time progress tracking for transfer jobs.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Updates job progress in Redis for fast reads
- [ ] Tracks: files_completed, files_failed, bytes_transferred, current_file
- [ ] For large files: tracks bytes_uploaded for current file
- [ ] Progress updates every 5 seconds max
- [ ] `GET /api/transfers/:id/progress` returns current progress

---

### Task 6.6: WebSocket/SSE Progress Streaming

**Description:** Implement real-time progress streaming to frontend.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] WebSocket or SSE endpoint for progress updates
- [ ] Clients subscribe to specific job_id
- [ ] Pushes progress updates as they occur
- [ ] Sends completion/failure event
- [ ] Handles client disconnection gracefully
- [ ] Authenticates WebSocket connections

---

## Epic 7: Conflict Handling

### Task 7.1: Conflict Detection During Transfer

**Description:** Implement conflict detection before each file upload.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Checks destination for existing file before upload
- [ ] Creates ConflictRecord if conflict detected
- [ ] Pauses job if conflict_strategy is 'ask'
- [ ] Applies automatic resolution if strategy is skip/rename/overwrite_all
- [ ] Logs conflict and resolution in audit

---

### Task 7.2: Conflict Resolution Endpoints

**Description:** Create endpoints for users to resolve conflicts.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `GET /api/transfers/:id/conflicts` lists pending conflicts
- [ ] `POST /api/transfers/:id/conflicts/:conflict_id/resolve` resolves single conflict
- [ ] `POST /api/transfers/:id/conflicts/resolve-all` applies resolution to all pending
- [ ] Accepts resolution: skip | rename | overwrite
- [ ] Resumes job after conflicts resolved
- [ ] Validates user owns the job

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

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] TransferJob.scheduled_for field stores scheduled datetime
- [ ] `POST /api/transfers/:id/schedule` sets schedule time
- [ ] Validates scheduled time is in the future
- [ ] Job status set to 'scheduled'
- [ ] Celery beat checks for due scheduled jobs every minute

---

### Task 8.2: Scheduled Job Executor

**Description:** Implement Celery beat task to start scheduled transfers.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Periodic task runs every minute
- [ ] Finds jobs where scheduled_for <= now and status = 'scheduled'
- [ ] Starts transfer orchestrator for each due job
- [ ] Handles timezone correctly (store in UTC)
- [ ] Updates job status to 'running'

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

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] AWS SES client configured with credentials
- [ ] SES sending domain verified
- [ ] HTML email template for transfer completion
- [ ] HTML email template for transfer failure
- [ ] Includes: job summary, files transferred, duration, errors if any
- [ ] Sends to user's registered email
- [ ] Handles send failures gracefully

---

### Task 9.2: SMS Notification Service

**Description:** Implement SMS sending service via Twilio.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Twilio client configured with credentials
- [ ] SMS template for transfer completion
- [ ] SMS template for transfer failure
- [ ] Respects user's SMS notification preference
- [ ] Validates phone number format
- [ ] Handles send failures gracefully

---

### Task 9.3: Notification Trigger Integration

**Description:** Integrate notification services with transfer completion events.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Notifications triggered on job completion (success or failure)
- [ ] Respects user's notification preferences (email, SMS, both, none)
- [ ] Notifications sent asynchronously (Celery task)
- [ ] Notification history logged
- [ ] Does not block transfer completion

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

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] AuditLog model: id, user_id, action (enum), resource_type, resource_id, details (JSON), ip_address, user_agent, created_at
- [ ] Actions: login, logout, transfer_created, transfer_started, transfer_completed, conflict_resolved, account_connected, account_disconnected, settings_changed
- [ ] Index on user_id and created_at
- [ ] Migration created

---

### Task 10.2: Audit Logging Service

**Description:** Implement service to create audit log entries throughout the application.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Function to log action with context
- [ ] Automatically captures IP and user agent from request
- [ ] Async logging to not block requests
- [ ] Captures relevant details per action type
- [ ] Integrated at key points: auth, transfers, account management

---

### Task 10.3: Audit Log Endpoints

**Description:** Create endpoints for users to view their audit logs.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] `GET /api/audit-logs` lists user's audit logs
- [ ] Supports pagination (limit, offset)
- [ ] Supports filtering by action type, date range
- [ ] `GET /api/audit-logs/export` exports as CSV
- [ ] 30-day retention enforced (older logs not returned)

---

### Task 10.4: Audit Log Cleanup Job

**Description:** Implement scheduled job to clean up old audit logs.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Celery beat task runs daily
- [ ] Deletes audit logs older than 30 days
- [ ] Logs number of records deleted
- [ ] Handles large deletes in batches

---

### Task 10.5: Audit Log UI

**Description:** Create UI for viewing audit log history.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Audit log page with table view
- [ ] Columns: date, action, details, IP address
- [ ] Filter by action type
- [ ] Date range filter
- [ ] Export button (CSV download)
- [ ] Pagination

---

## Epic 11: Frontend - Dashboard & Transfer Flow

### Task 11.1: Dashboard Page

**Description:** Create main dashboard showing transfer overview.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Shows active transfers with real-time progress
- [ ] Shows scheduled transfers with countdown
- [ ] Shows recent completed transfers
- [ ] "New Transfer" CTA button
- [ ] Quick stats: total files migrated, data transferred
- [ ] Empty state for new users

---

### Task 11.2: New Transfer - Source Selection

**Description:** Create UI for selecting source files/folders from OneDrive.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] File browser showing OneDrive contents
- [ ] Navigate into folders
- [ ] Select entire folders or individual files
- [ ] Shows file size and count for selection
- [ ] Breadcrumb navigation
- [ ] "Select All" option

---

### Task 11.3: New Transfer - Destination Selection

**Description:** Create UI for selecting destination folder in Google Drive.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] File browser showing Google Drive folders
- [ ] Navigate into folders
- [ ] Create new folder option
- [ ] Select destination folder
- [ ] Shows current path
- [ ] Validates both accounts connected

---

### Task 11.4: New Transfer - Filter Configuration

**Description:** Create UI for configuring transfer filters.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] File type filter (checkboxes or multi-select)
- [ ] Date range filter (from/to date pickers)
- [ ] Folder include/exclude patterns (text input)
- [ ] Preview updates as filters change
- [ ] Clear filters option

---

### Task 11.5: New Transfer - Review & Confirm

**Description:** Create review page showing transfer summary before starting.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Summary: source, destination, file count, total size
- [ ] Folder structure preview
- [ ] Detected conflicts listed
- [ ] Conflict handling option selection
- [ ] Schedule option with date/time picker
- [ ] "Run Dry Run" button
- [ ] "Start Transfer" / "Schedule Transfer" buttons

---

### Task 11.6: Transfer Progress Page

**Description:** Create real-time transfer progress view.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Overall progress bar (files completed / total)
- [ ] Bytes transferred / total bytes
- [ ] Current file being transferred with individual progress
- [ ] Transfer speed (MB/s)
- [ ] Estimated time remaining
- [ ] List of completed files (collapsible)
- [ ] List of failed files with errors
- [ ] Cancel button
- [ ] Auto-updates via WebSocket/SSE

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

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Wrapper for cloud API calls with retry logic
- [ ] 3 retry attempts with exponential backoff (1s, 2s, 4s)
- [ ] Identifies transient errors (rate limits, timeouts, 5xx)
- [ ] Does not retry permanent errors (404, 403)
- [ ] Logs retry attempts

---

### Task 12.2: Rate Limit Handling

**Description:** Implement rate limit detection and backoff for cloud APIs.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Detects 429 responses from OneDrive/Google
- [ ] Reads Retry-After header if present
- [ ] Implements global rate limiting per provider
- [ ] Queues requests when near limit
- [ ] Logs rate limit events

---

### Task 12.3: Graceful Job Failure Handling

**Description:** Implement handling for unrecoverable job failures.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Job marked as 'failed' after max retries exceeded
- [ ] Partial progress preserved (completed files stay completed)
- [ ] Cleanup of S3 intermediate files
- [ ] User notified of failure with details
- [ ] Job can be retried (resumes from failure point)

---

### Task 12.4: API Error Response Standardization

**Description:** Standardize error responses across all API endpoints.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Consistent error format: { error: string, code: string, details?: object }
- [ ] Appropriate HTTP status codes
- [ ] User-friendly error messages
- [ ] Internal errors logged with stack trace
- [ ] Sensitive info not exposed in responses

---

## Epic 13: Testing

### Task 13.1: Backend Unit Tests - Auth

**Description:** Write unit tests for authentication services.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Tests for registration (valid, duplicate email, weak password)
- [ ] Tests for login (valid, wrong password, unknown email)
- [ ] Tests for JWT generation and validation
- [ ] Tests for token refresh
- [ ] 90%+ coverage for auth module

---

### Task 13.2: Backend Unit Tests - Transfer Logic

**Description:** Write unit tests for transfer orchestration logic.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Tests for job state transitions
- [ ] Tests for conflict detection
- [ ] Tests for filter application
- [ ] Tests for progress calculation
- [ ] Mock cloud API calls

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

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] OpenAPI/Swagger spec generated from FastAPI
- [ ] All endpoints documented with examples
- [ ] Authentication documented
- [ ] Error codes documented
- [ ] Accessible at /docs endpoint

---

### Task 14.2: Environment Configuration Documentation

**Description:** Document all required environment variables and configuration.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] List of all env vars with descriptions
- [ ] Example .env.example file
- [ ] Required vs optional clearly marked
- [ ] Setup instructions for local development

---

### Task 14.3: Deployment Configuration

**Description:** Create deployment configuration for production.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Docker files for backend and frontend
- [ ] Docker Compose for full stack
- [ ] Production environment configuration
- [ ] Database migration strategy
- [ ] Health check endpoints configured

---

### Task 14.4: CI/CD Pipeline

**Description:** Set up continuous integration and deployment pipeline.

**Status:** `TODO`

**Acceptance Criteria:**
- [ ] Runs tests on PR
- [ ] Linting and type checking
- [ ] Builds Docker images
- [ ] Deploys to staging on merge to main
- [ ] Manual promotion to production

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
