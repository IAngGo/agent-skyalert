"""
FastAPI exception handlers that translate domain exceptions to HTTP responses.

Registered on the app in main.py. Keeps error translation out of route handlers.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.application.exceptions import (
    AlertNotFoundError,
    InsufficientPriceHistoryError,
    InvalidThresholdError,
    NotificationFailedError,
    PurchaseFailedError,
    SearchInactiveError,
    SearchNotFoundError,
    SkyAlertError,
    UserNotFoundError,
)


async def skyalert_exception_handler(request: Request, exc: SkyAlertError) -> JSONResponse:
    """
    Translate any SkyAlertError subclass to an appropriate HTTP error response.

    Args:
        request: The incoming FastAPI Request.
        exc: The domain exception that was raised.

    Returns:
        A JSONResponse with the correct status code and error detail.
    """
    status_map = {
        UserNotFoundError: 404,
        SearchNotFoundError: 404,
        AlertNotFoundError: 404,
        SearchInactiveError: 409,
        InvalidThresholdError: 422,
        InsufficientPriceHistoryError: 409,
        NotificationFailedError: 502,
        PurchaseFailedError: 502,
    }
    status_code = status_map.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Translate ValueError (raised by use cases for rule violations) to 422.

    Args:
        request: The incoming FastAPI Request.
        exc: The ValueError that was raised.

    Returns:
        A 422 JSONResponse with the error message.
    """
    return JSONResponse(status_code=422, content={"detail": str(exc)})
