"""Kafka utilities — class-based producer and consumer services."""
from .producer import KafkaProducerService
from .consumer import KafkaConsumerService

# Shared service instances (explicit, class-based API)
producer_service = KafkaProducerService()
consumer_service = KafkaConsumerService()

__all__ = [
    "KafkaProducerService",
    "KafkaConsumerService",
    "producer_service",
    "consumer_service",
]
