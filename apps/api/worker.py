"""
TerahBank BullMQ Worker Process
================================
Run this as a SEPARATE process alongside the API server.

Usage:
    cd apps/api
    venv/Scripts/activate
    python worker.py

Queues processed:
  queue:momo   — MTN MoMo deposit (request-to-pay) + timeout-check jobs

NEVER run inside the API process — this must be a standalone process.
"""

import asyncio
import logging
import signal
import sys

# Import all ORM models so SQLAlchemy can resolve every foreign key before queries run.
import modules.auth.models          # noqa: F401
import modules.accounts.models      # noqa: F401
import modules.transactions.models  # noqa: F401
import modules.cards.models         # noqa: F401
import modules.kyc.models           # noqa: F401
import modules.notifications.models # noqa: F401
import modules.admin.models         # noqa: F401
import modules.insurance.models     # noqa: F401

from core.redis import init_redis
from modules.jobs.momo_payment_processor import create_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("terahbank.worker")


async def main() -> None:
    logger.info("Starting TerahBank MoMo worker (queue:momo) ...")
    await init_redis()
    worker = create_worker()
    logger.info("Worker ready — waiting for jobs. Press Ctrl+C to stop.")

    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def _shutdown(sig: signal.Signals) -> None:
        logger.info("Received %s — shutting down ...", sig.name)
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown, sig)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for all signals
            pass

    try:
        await stop
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await worker.close()
        logger.info("Worker stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
