"""
Celery task definitions for SkyAlert.

Tasks are thin wrappers that instantiate use cases with real infrastructure
adapters and call execute(). No business logic lives here.
"""
