"""
Example client for consuming SSE progress updates from CloudShift API.

This demonstrates how to connect to the real-time progress stream endpoint
and handle SSE events.

Usage:
    python sse_client_example.py <job_id> <access_token>
"""

import sys
import requests
import json


def stream_progress(job_id: int, access_token: str, api_url: str = "http://localhost:8000"):
    """
    Connect to SSE stream and print progress updates.

    Args:
        job_id: Transfer job ID to monitor
        access_token: JWT access token for authentication
        api_url: Base URL of the API (default: http://localhost:8000)
    """
    url = f"{api_url}/api/transfers/{job_id}/progress/stream"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "text/event-stream"
    }

    print(f"Connecting to SSE stream for job {job_id}...")
    print(f"URL: {url}")
    print("-" * 80)

    try:
        with requests.get(url, headers=headers, stream=True, timeout=None) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')

                    # SSE events start with "data: "
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # Remove "data: " prefix
                        try:
                            data = json.loads(data_str)

                            # Check if this is a completion event
                            if data.get("event") == "complete":
                                print(f"\n✓ Transfer {data['status']}: {data['message']}")
                                break

                            # Check if this is an error event
                            elif data.get("event") == "error":
                                print(f"\n✗ Error: {data['message']}")
                                break

                            # Regular progress update
                            else:
                                print_progress(data)

                        except json.JSONDecodeError:
                            print(f"Warning: Could not parse event data: {data_str}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Connection error: {e}")
    except KeyboardInterrupt:
        print("\n\nDisconnected by user")


def print_progress(data: dict):
    """
    Print progress data in a formatted way.

    Args:
        data: Progress data dictionary from SSE event
    """
    percent = data.get("percent_complete", 0)
    files_completed = data.get("files_completed", 0)
    total_files = data.get("total_files", 0)
    bytes_transferred = data.get("bytes_transferred", 0)
    total_size = data.get("total_size", 0)
    current_file = data.get("current_file")

    # Format bytes
    mb_transferred = bytes_transferred / (1024 * 1024)
    mb_total = total_size / (1024 * 1024)

    # Create progress bar
    bar_width = 30
    filled = int(bar_width * percent / 100)
    bar = "█" * filled + "░" * (bar_width - filled)

    # Print progress
    print(f"\r[{bar}] {percent:.1f}% | "
          f"Files: {files_completed}/{total_files} | "
          f"Data: {mb_transferred:.1f}/{mb_total:.1f} MB", end="")

    # Print current file on new line if present
    if current_file:
        current_bytes = data.get("current_file_bytes", 0)
        current_total = data.get("current_file_total", 0)
        current_percent = (current_bytes / current_total * 100) if current_total > 0 else 0
        print(f"\n  Current: {current_file} ({current_percent:.1f}%)", end="")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python sse_client_example.py <job_id> <access_token> [api_url]")
        print("\nExample:")
        print("  python sse_client_example.py 123 eyJhbGc...")
        print("  python sse_client_example.py 123 eyJhbGc... http://localhost:8000")
        sys.exit(1)

    job_id = int(sys.argv[1])
    access_token = sys.argv[2]
    api_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

    stream_progress(job_id, access_token, api_url)
