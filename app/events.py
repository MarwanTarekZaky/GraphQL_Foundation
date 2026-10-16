import asyncio


review_subscribers: set[asyncio.Queue] = set()

async def publish_review_created(review: dict):
    for queue in review_subscribers.copy():
        await queue.put(review)


async def subscribe_to_review_created():
    queue: asyncio.Queue = asyncio.Queue()
    review_subscribers.add(queue)
    
    try:
        while True:
            review = await queue.get()
            yield review
    finally:
        review_subscribers.discard(queue)