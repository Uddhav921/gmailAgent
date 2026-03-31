"""MongoDB connection management using Motor (async driver)."""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

_client: AsyncIOMotorClient = None


async def connect_db():
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)


async def close_db():
    global _client
    if _client:
        _client.close()


def get_database():
    """Return the gmailAgent database instance."""
    return _client.get_default_database()
