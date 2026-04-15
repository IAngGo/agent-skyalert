"""
FastAPI HTTP adapter for SkyAlert.

Contains the app factory, Pydantic schemas, and route handlers.
Route handlers are thin: they validate input, call a use case, and return a schema.
No business logic lives here.
"""
