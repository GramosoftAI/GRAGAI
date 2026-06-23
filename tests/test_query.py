import asyncio
from app.modules.rag.query_router import QueryRouter

async def test_router():
    router = QueryRouter()
    res = await router.route_query("summarize what u know")
    print("Intent:", res.intent)
    print("Rewritten:", res.rewritten)

asyncio.run(test_router())
