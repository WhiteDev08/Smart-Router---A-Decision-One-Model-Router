from pymongo import AsyncMongoClient
import os
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("MONGO_URI")

client = AsyncMongoClient(
    connection_string,
    maxPoolSize=50,
    minPoolSize=5
)

db = client["jev"]
collection = db["user_states"]


def get_collection():
    return collection


async def get_state(user_id: str):
    state = await collection.find_one({
        "user_id": user_id
    })

    return state if state else None


async def insert_state(state):
    record = await collection.find_one({
        "user_id": state.user_id
    })

    if record:
        await collection.update_one(
            {"user_id": state.user_id},
            {"$set": state.model_dump()}
        )
    else:
        await collection.insert_one(
            state.model_dump()
        )