
import asyncio
from core.utils import logger
from core.utils.kafka import consumer_service


async def _run_consumer() -> None:
	"""Start the Kafka consumer and keep it running until interrupted."""
	try:
		await consumer_service.start()
	except Exception:
		logger.exception("Failed to start Kafka consumer")
		return

	try:
		# Keep the process alive until cancelled
		while True:
			await asyncio.sleep(3600)
	except asyncio.CancelledError:
		pass
	finally:
		try:
			await consumer_service.stop()
		except Exception:
			logger.exception("Error stopping Kafka consumer")


def main() -> None:
	try:
		asyncio.run(_run_consumer())
	except KeyboardInterrupt:
		logger.info("Worker interrupted by KeyboardInterrupt")


if __name__ == "__main__":
	main()