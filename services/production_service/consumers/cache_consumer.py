from aiokafka import AIOKafkaConsumer
import json
import asyncio
from core.config import settings
from core.database import SessionLocal
from models.cache import ContractCache, CustomerCache
import logging

logger = logging.getLogger(__name__)

async def start_consumer():
    consumer = AIOKafkaConsumer(
        "contract.events",
        "customer.events",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await consumer.start()
    try:
        async for msg in consumer:
            logger.info(f"Received msg: {msg.value} on topic {msg.topic}")
            handle_event(msg.topic, msg.value)
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        await consumer.stop()

def handle_event(topic, event_data):
    db = SessionLocal()
    try:
        if topic == "contract.events":
            if event_data.get("event_name") in ["CONTRACT_CREATED", "CONTRACT_UPDATED", "CONTRACT_APPROVED"]:
                contract = db.query(ContractCache).filter(ContractCache.contract_number == event_data["contract_number"]).first()
                if not contract:
                    contract = ContractCache(**event_data)
                    db.add(contract)
                else:
                    for key, value in event_data.items():
                        if hasattr(contract, key):
                            setattr(contract, key, value)
                db.commit()
        elif topic == "customer.events":
            if event_data.get("event_name") == "CUSTOMER_UPDATED":
                customer = db.query(CustomerCache).filter(CustomerCache.code == event_data["code"]).first()
                if not customer:
                    customer = CustomerCache(**event_data)
                    db.add(customer)
                else:
                    for key, value in event_data.items():
                        if hasattr(customer, key):
                            setattr(customer, key, value)
                db.commit()
    except Exception as e:
        logger.error(f"Error handling event: {e}")
    finally:
        db.close()
