"""
Infrastructure layer for SkyAlert.

Contains all concrete adapters: PostgreSQL repositories, Playwright scraper,
SendGrid/Twilio notification services, FastAPI routes, and Celery tasks.

This is the only layer allowed to import external libraries.
Dependency direction: infrastructure → application → domain.
"""
