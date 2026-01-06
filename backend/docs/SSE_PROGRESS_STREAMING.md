# SSE Progress Streaming

## Overview

CloudShift provides real-time progress updates for transfer jobs using **Server-Sent Events (SSE)**. This allows frontend applications to display live progress without polling.

## Endpoint

```
GET /api/transfers/{job_id}/progress/stream
```

### Authentication

Requires JWT token in Authorization header:

```
Authorization: Bearer <access_token>
```

### Response Type

```
Content-Type: text/event-stream
```

## Event Format

Events are sent in SSE format with JSON data:

```
data: {"job_id": 123, "percent_complete": 45.2, ...}

```

### Progress Event

Regular progress updates are sent every 2 seconds when data changes:

```json
{
  "job_id": 123,
  "total_files": 100,
  "total_size": 524288000,
  "files_completed": 45,
  "files_failed": 2,
  "bytes_transferred": 234881024,
  "current_file": "document.pdf",
  "current_file_bytes": 1048576,
  "current_file_total": 5242880,
  "percent_complete": 44.8,
  "started_at": "2026-01-06T12:00:00",
  "last_update": "2026-01-06T12:05:23"
}
```

### Completion Event

Sent when the job reaches a terminal state (completed, failed, or cancelled):

```json
{
  "event": "complete",
  "job_id": 123,
  "status": "completed",
  "message": "Transfer job completed"
}
```

After this event, the stream automatically closes.

### Error Event

Sent if an error occurs during streaming:

```json
{
  "event": "error",
  "job_id": 123,
  "message": "An error occurred while streaming progress"
}
```

## Client Implementation

### JavaScript (Browser)

```javascript
const eventSource = new EventSource(
  `http://localhost:8000/api/transfers/${jobId}/progress/stream`,
  {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.event === 'complete') {
    console.log('Transfer completed!');
    eventSource.close();
  } else if (data.event === 'error') {
    console.error('Stream error:', data.message);
    eventSource.close();
  } else {
    // Update UI with progress
    updateProgressBar(data.percent_complete);
    updateFileCount(data.files_completed, data.total_files);
  }
};

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();
};
```

### Python

See `examples/sse_client_example.py` for a complete Python client implementation.

```python
import requests
import json

url = f"http://localhost:8000/api/transfers/{job_id}/progress/stream"
headers = {"Authorization": f"Bearer {access_token}"}

with requests.get(url, headers=headers, stream=True) as response:
    for line in response.iter_lines():
        if line and line.startswith(b"data: "):
            data = json.loads(line[6:])
            print(f"Progress: {data['percent_complete']}%")
```

### React (using EventSource)

```typescript
import { useEffect, useState } from 'react';

function TransferProgress({ jobId, accessToken }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    const eventSource = new EventSource(
      `/api/transfers/${jobId}/progress/stream`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.event === 'complete') {
        setProgress({ ...data, isComplete: true });
        eventSource.close();
      } else {
        setProgress(data);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId, accessToken]);

  if (!progress) return <div>Connecting...</div>;

  return (
    <div>
      <div>Progress: {progress.percent_complete}%</div>
      <div>Files: {progress.files_completed}/{progress.total_files}</div>
      {progress.current_file && (
        <div>Current: {progress.current_file}</div>
      )}
    </div>
  );
}
```

## Features

### Automatic Stream Closure

The stream automatically closes when:
- The job completes successfully
- The job fails
- The job is cancelled
- A streaming error occurs

### Client Disconnection Handling

If the client disconnects, the server gracefully handles the cancellation without affecting the transfer job.

### Efficient Updates

- Updates are only sent when progress data changes
- Update frequency is limited to every 2 seconds to avoid overwhelming clients
- Progress is stored in Redis for fast reads

### Authentication

- Each connection is authenticated via JWT
- Users can only subscribe to their own jobs
- Invalid or expired tokens receive 401/403 responses

## Error Handling

| Error Code | Meaning |
|------------|---------|
| 401 | Unauthorized - missing or invalid token |
| 403 | Forbidden - token valid but lacks permissions |
| 404 | Not found - job doesn't exist or user doesn't own it |

## Limitations

- Maximum of one connection per client per job (browser EventSource limitation)
- Connections are automatically closed after job completion
- Progress data is retained in Redis for 24 hours after job completion

## Testing

To test the SSE endpoint:

1. Start the backend server
2. Create a transfer job and note the job ID
3. Run the example client:

```bash
python examples/sse_client_example.py <job_id> <access_token>
```

Or use curl:

```bash
curl -N -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/transfers/123/progress/stream
```

The `-N` flag disables buffering for real-time output.
