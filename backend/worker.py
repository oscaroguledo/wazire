"""Wazire background worker — class-based lifecycle.

Runs the KafkaConsumerService in a managed event loop with explicit
start / run / stop lifecycle methods and OS signal handling.

Usage:
    python worker.py
"""
from __future__ import annotations

import asyncio
import signal
from typing import Optional

from core.utils.logger import logger
from core.utils.kafka import consumer_service


class Worker:
    """Class-based Kafka worker with explicit lifecycle management.

    Attributes:
        _consumer: The shared KafkaConsumerService instance.
        _stop_event: asyncio.Event set when the worker should stop.
        _task: The background asyncio Task running the consumer.
    """

    def __init__(self) -> None:
        self._consumer = consumer_service
        self._stop_event: asyncio.Event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the Kafka consumer."""
        logger.info("Worker starting Kafka consumer...")
        try:
            await self._consumer.start()
            logger.info("Worker: Kafka consumer started")
        except Exception:
            logger.exception("Worker: failed to start Kafka consumer")
            raise

    async def run(self) -> None:
        """Block until a stop signal is received.

        Registers SIGINT and SIGTERM handlers so the worker shuts down
        gracefully when the container or process is stopped.
        """
        loop = asyncio.get_running_loop()

        def _handle_signal(sig: signal.Signals) -> None:
            logger.info("Worker received signal %s — initiating shutdown", sig.name)
            self._stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handle_signal, sig)
            except (NotImplementedError, RuntimeError):
                # Windows / environments that don't support add_signal_handler
                pass

        logger.info("Worker running — waiting for stop signal")
        await self._stop_event.wait()
        logger.info("Worker stop event received")

    async def stop(self) -> None:
        """Signal the worker to stop and shut down the consumer."""
        self._stop_event.set()
        logger.info("Worker stopping Kafka consumer...")
        try:
            await self._consumer.stop()
        except Exception:
            logger.exception("Worker: error stopping Kafka consumer")
        logger.info("Worker stopped")

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @classmethod
    def main(cls) -> None:
        """Synchronous entry point — creates and runs a Worker instance."""
        worker = cls()

        async def _run() -> None:
            await worker.start()
            try:
                await worker.run()
            finally:
                await worker.stop()

        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            logger.info("Worker interrupted by KeyboardInterrupt")


if __name__ == "__main__":
    Worker.main()
