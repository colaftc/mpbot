from typing import Generator
from main import app
from models import MPMessage
from fastapi.testclient import TestClient
from tortoise.contrib.test import finalizer, initializer
from tortoise import Tortoise, generate_schema_for_client
import pytest, asyncio

@pytest.fixture(scope='session')
def client() -> Generator:
    initializer(['main'])
    with TestClient(app) as c:
        yield c
    finalizer()

@pytest.fixture(scope='session')
def event_loop(client : TestClient) -> Generator:
    yield client.task.get_loop()

def test_create_message(client : TestClient, event_loop : asyncio.AbstractEventLoop):
    async def create_msg():
        msg = await MPMessage.create(
            publisher='dnwj88cjqiX0a',
            content='fake message content'
        )
        return msg

    msg = event_loop.run_until_complete(create_msg())

    assert msg is not None
    assert msg.id > 0

    async def find_msg():
        return await MPMessage.first()

    msg = event_loop.run_until_complete(find_msg())
    assert msg is not None
    assert msg.id > 0
    assert msg.content == 'fake message content'
    assert not msg.content == 'fuck'
    # msg = await MPMessage_Pydantic.from_tortoise_orm(msg)
    # assert msg.id > 0
    # assert len(msg.content) > 10