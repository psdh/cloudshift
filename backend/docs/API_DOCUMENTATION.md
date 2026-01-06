# CloudShift API Documentation

## Overview

CloudShift is a cloud file migration service that transfers files from OneDrive to Google Drive. This document describes the REST API endpoints, authentication, and error handling.

**Base URL:** `http://localhost:8000` (development)

**API Version:** 1.0.0

## Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

## Authentication

CloudShift uses JWT (JSON Web Tokens) for authentication.

### Authentication Flow

1. **Register** or **Login** to receive access and refresh tokens
2. Include the access token in the `Authorization` header for protected endpoints:
   ```
   Authorization: Bearer <access_token>
   ```
3. When the access token expires, use the refresh token to get a new one

### Token Expiration

- **Access Token:** 15 minutes
- **Refresh Token:** 7 days

## Endpoints

### Health Check

#### GET /health

Check if the API is running and database is connected.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

### Authentication

#### POST /api/auth/register

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "StrongPass123!",
  "confirm_password": "StrongPass123!"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

**Response:** `201 Created`
```json
{
  "id": 1,
  "email": "user@example.com",
  "email_notifications": true,
  "sms_notifications": false,
  "phone_number": null,
  "created_at": "2026-01-06T12:00:00Z"
}
```

**Errors:**
- `400` - Email already registered or password validation failed

---

#### POST /api/auth/login

Authenticate and receive JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Errors:**
- `401` - Invalid credentials

---

#### POST /api/auth/refresh

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Errors:**
- `401` - Invalid or expired refresh token

---

### OAuth Integration

#### GET /api/oauth/onedrive/authorize

Initiate OneDrive OAuth flow.

**Response:** `200 OK`
```json
{
  "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?..."
}
```

---

#### GET /api/oauth/onedrive/callback

OAuth callback endpoint (redirect from Microsoft).

**Query Parameters:**
- `code` - Authorization code from Microsoft
- `state` - State token for CSRF protection

**Response:** Redirects to frontend with success/error

---

#### GET /api/oauth/google/authorize

Initiate Google Drive OAuth flow.

**Response:** `200 OK`
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

---

#### GET /api/oauth/google/callback

OAuth callback endpoint (redirect from Google).

**Query Parameters:**
- `code` - Authorization code from Google
- `state` - State token for CSRF protection

**Response:** Redirects to frontend with success/error

---

### Connected Accounts

**Authentication Required:** All endpoints require valid access token

#### GET /api/accounts

List user's connected cloud accounts.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "provider": "onedrive",
    "email": "user@outlook.com",
    "connected_at": "2026-01-06T12:00:00Z"
  },
  {
    "id": 2,
    "provider": "google",
    "email": "user@gmail.com",
    "connected_at": "2026-01-06T12:05:00Z"
  }
]
```

---

#### DELETE /api/accounts/{account_id}

Disconnect a cloud account.

**Response:** `200 OK`
```json
{
  "message": "Account disconnected successfully"
}
```

**Errors:**
- `404` - Account not found
- `403` - Account belongs to another user

---

### Transfers

**Authentication Required:** All endpoints require valid access token

#### POST /api/transfers

Create a new transfer job.

**Request Body:**
```json
{
  "source_provider": "onedrive",
  "dest_provider": "google",
  "source_folder_id": "root",
  "dest_folder_id": "root",
  "config": {
    "conflict_strategy": "ask",
    "filters": {
      "file_types": [".pdf", ".docx"],
      "min_size": 1000,
      "max_size": 10000000
    }
  }
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "status": "pending",
  "source_provider": "onedrive",
  "dest_provider": "google",
  "source_folder_id": "root",
  "dest_folder_id": "root",
  "config": {...},
  "created_at": "2026-01-06T12:00:00Z"
}
```

---

#### GET /api/transfers

List all transfer jobs for the authenticated user.

**Query Parameters:**
- `status` (optional) - Filter by status: `pending`, `running`, `completed`, `failed`, `paused`, `scheduled`
- `limit` (optional) - Number of results (default: 50)
- `offset` (optional) - Pagination offset (default: 0)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "status": "completed",
    "source_provider": "onedrive",
    "dest_provider": "google",
    "started_at": "2026-01-06T12:00:00Z",
    "completed_at": "2026-01-06T12:15:00Z",
    "created_at": "2026-01-06T11:55:00Z"
  }
]
```

---

#### GET /api/transfers/{job_id}

Get details of a specific transfer job.

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "status": "completed",
  "source_provider": "onedrive",
  "dest_provider": "google",
  "source_folder_id": "root",
  "dest_folder_id": "root",
  "config": {...},
  "started_at": "2026-01-06T12:00:00Z",
  "completed_at": "2026-01-06T12:15:00Z",
  "created_at": "2026-01-06T11:55:00Z"
}
```

---

#### POST /api/transfers/{job_id}/start

Start a pending transfer job.

**Response:** `200 OK`
```json
{
  "message": "Transfer started",
  "job_id": 1,
  "status": "running"
}
```

---

#### POST /api/transfers/{job_id}/pause

Pause a running transfer job.

**Response:** `200 OK`
```json
{
  "message": "Transfer paused",
  "job_id": 1,
  "status": "paused"
}
```

---

#### POST /api/transfers/{job_id}/resume

Resume a paused transfer job.

**Response:** `200 OK`
```json
{
  "message": "Transfer resumed",
  "job_id": 1,
  "status": "running"
}
```

---

#### POST /api/transfers/{job_id}/cancel

Cancel a running transfer job.

**Response:** `200 OK`
```json
{
  "message": "Transfer cancelled",
  "job_id": 1,
  "status": "cancelled"
}
```

---

#### GET /api/transfers/{job_id}/items

Get all transfer items for a job.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "job_id": 1,
    "source_file_id": "file123",
    "source_path": "documents/report.pdf",
    "dest_path": "documents/report.pdf",
    "status": "completed",
    "size": 524288,
    "started_at": "2026-01-06T12:00:10Z",
    "completed_at": "2026-01-06T12:00:15Z"
  }
]
```

---

#### GET /api/transfers/{job_id}/progress/stream

Stream real-time progress updates via Server-Sent Events (SSE).

**Response:** `200 OK` (text/event-stream)
```
data: {"job_id": 1, "status": "running", "files_completed": 5, "files_total": 100, "bytes_transferred": 5242880, "bytes_total": 104857600, "current_file": "document.pdf"}

data: {"job_id": 1, "status": "running", "files_completed": 6, "files_total": 100, "bytes_transferred": 6291456, "bytes_total": 104857600, "current_file": "image.jpg"}
```

---

#### POST /api/transfers/{job_id}/schedule

Schedule a transfer for future execution.

**Request Body:**
```json
{
  "scheduled_for": "2026-01-07T10:00:00Z"
}
```

**Response:** `200 OK`
```json
{
  "message": "Transfer scheduled",
  "job_id": 1,
  "scheduled_for": "2026-01-07T10:00:00Z"
}
```

---

#### GET /api/transfers/{job_id}/conflicts

List all conflicts for a transfer job.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "job_id": 1,
    "item_id": 5,
    "resolution": null,
    "created_at": "2026-01-06T12:05:00Z",
    "resolved_at": null
  }
]
```

---

#### POST /api/transfers/{job_id}/conflicts/{conflict_id}/resolve

Resolve a single file conflict.

**Request Body:**
```json
{
  "resolution": "rename",
  "new_name": "document (1).pdf"
}
```

**Resolution Options:**
- `skip` - Skip this file
- `rename` - Rename to avoid conflict (provide new_name)
- `overwrite` - Overwrite existing file

**Response:** `200 OK`
```json
{
  "message": "Conflict resolved",
  "conflict_id": 1,
  "resolution": "rename"
}
```

---

#### POST /api/transfers/{job_id}/conflicts/resolve-all

Resolve all pending conflicts with same strategy.

**Request Body:**
```json
{
  "resolution": "skip"
}
```

**Response:** `200 OK`
```json
{
  "message": "All conflicts resolved",
  "resolved_count": 5
}
```

---

### Audit Logs

**Authentication Required:** All endpoints require valid access token

#### GET /api/audit-logs

Get audit logs for the authenticated user.

**Query Parameters:**
- `action` (optional) - Filter by action type
- `resource_type` (optional) - Filter by resource type
- `limit` (optional) - Number of results (default: 50)
- `offset` (optional) - Pagination offset (default: 0)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "action": "transfer_started",
    "resource_type": "transfer_job",
    "resource_id": "1",
    "details": {...},
    "ip_address": "127.0.0.1",
    "user_agent": "Mozilla/5.0...",
    "created_at": "2026-01-06T12:00:00Z"
  }
]
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "status_code": 400,
  "details": {
    "field": "additional context"
  }
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Resource created
- `400` - Bad request (validation error)
- `401` - Unauthorized (authentication required or invalid)
- `403` - Forbidden (insufficient permissions)
- `404` - Resource not found
- `422` - Unprocessable entity (validation error)
- `429` - Too many requests (rate limited)
- `500` - Internal server error

### Common Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `UNAUTHORIZED` | Authentication required or token invalid |
| `FORBIDDEN` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `CONFLICT` | Resource already exists |
| `RATE_LIMITED` | Too many requests |
| `INTERNAL_ERROR` | Server error |

---

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Authentication endpoints:** 5 requests per minute per IP
- **Transfer operations:** 100 requests per hour per user
- **File operations:** 1000 requests per hour per user

When rate limited, you'll receive a `429` response with a `Retry-After` header indicating when you can retry.

---

## Webhooks (Future)

Webhook support for transfer completion notifications will be added in a future release.

---

## Support

For API support or to report issues:
- GitHub: https://github.com/your-org/cloudshift
- Email: support@cloudshift.example.com
