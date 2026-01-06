from app.core.celery_app import celery_app
import time


@celery_app.task(name="app.services.tasks.test_task")
def test_task(message: str = "Hello from Celery!") -> dict:
    """
    Test task to verify Celery is working correctly.

    Args:
        message: Test message to process

    Returns:
        dict: Result with message and timestamp
    """
    time.sleep(2)  # Simulate some work
    return {
        "status": "success",
        "message": message,
        "processed_at": time.time(),
    }


@celery_app.task(name="app.services.tasks.add_numbers")
def add_numbers(x: int, y: int) -> int:
    """
    Simple test task that adds two numbers.

    Args:
        x: First number
        y: Second number

    Returns:
        int: Sum of x and y
    """
    return x + y
