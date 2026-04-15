"""
Celery tasks for flight price scraping.

scrape_all_searches: called by beat every 5 minutes.
  Fetches all active searches and enqueues one scrape_search task per search.

scrape_search: called per search.
  Instantiates RunPriceScrape with real adapters and executes it.
"""

import logging

from backend.application.commands import RunPriceScrapeCommand
from backend.application.exceptions import InsufficientPriceHistoryError, SearchInactiveError
from backend.application.use_cases.evaluate_price_drop import EvaluatePriceDrop
from backend.application.use_cases.run_price_scrape import RunPriceScrape
from backend.infrastructure.persistence.alert_repository import PostgresAlertRepository
from backend.infrastructure.persistence.database import SessionLocal
from backend.infrastructure.persistence.price_history_repository import PostgresPriceHistoryRepository
from backend.infrastructure.persistence.search_repository import PostgresSearchRepository
from backend.infrastructure.scraper.google_flights import GoogleFlightsScraper
from backend.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.infrastructure.tasks.scrape_tasks.scrape_all_searches")
def scrape_all_searches() -> dict:
    """
    Fan out one scrape_search task per active Search.

    Returns:
        Dict with count of enqueued tasks.
    """
    with SessionLocal() as session:
        repo = PostgresSearchRepository(session)
        active_searches = repo.find_active()

    for search in active_searches:
        scrape_search.delay(str(search.id))

    logger.info("Enqueued %d scrape tasks.", len(active_searches))
    return {"enqueued": len(active_searches)}


@celery_app.task(
    name="backend.infrastructure.tasks.scrape_tasks.scrape_search",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
)
def scrape_search(search_id: str) -> dict:
    """
    Run a price scrape for a single Search and evaluate for price drops.

    Args:
        search_id: String UUID of the Search to scrape.

    Returns:
        Dict with search_id and count of price records persisted.
    """
    from uuid import UUID

    with SessionLocal() as session:
        searches = PostgresSearchRepository(session)
        price_history = PostgresPriceHistoryRepository(session)
        alerts = PostgresAlertRepository(session)
        scraper = GoogleFlightsScraper()

        evaluate = EvaluatePriceDrop(
            searches=searches,
            price_history=price_history,
            alerts=alerts,
            scraper=scraper,
        )
        use_case = RunPriceScrape(
            searches=searches,
            price_history=price_history,
            scraper=scraper,
            evaluate_price_drop=evaluate,
        )

        try:
            records = use_case.execute(RunPriceScrapeCommand(search_id=UUID(search_id)))
            session.commit()
            logger.info("Search %s: %d price records saved.", search_id, len(records))
            return {"search_id": search_id, "records": len(records)}
        except SearchInactiveError:
            logger.warning("Search %s is no longer active — skipping.", search_id)
            return {"search_id": search_id, "records": 0}
        except InsufficientPriceHistoryError as exc:
            logger.info("Search %s: insufficient history (%s) — skipping alert.", search_id, exc)
            session.commit()
            return {"search_id": search_id, "records": 0}
        except Exception:
            session.rollback()
            logger.exception("Scrape failed for search %s.", search_id)
            raise
