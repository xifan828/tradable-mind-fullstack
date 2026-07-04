from langgraph_sdk import get_client
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

client = get_client(url="http://localhost:2024")

context = {
    "api_key": os.getenv("GEMINI_API_KEY"),
    "asset_type": "forex",
}

async def main(query: str):
    # Create a thread before streaming
    thread = await client.threads.create()
    thread_id = thread["thread_id"]
    print(f"Created thread: {thread_id}")

    async for chunk in client.runs.stream(
        thread_id,
        "agent",  # Name of assistant. Defined in langgraph.json.
        input={
            "messages": [{
                "role": "human",
                "content": query,
            }],
        },
        context=context,
    ):
        print(f"Receiving new event of type: {chunk.event}...")
        print(chunk.data)
        print("\n\n")

query = "What is the current price of EUR/USD and what is the current market condition ?"

asyncio.run(main(query=query))
