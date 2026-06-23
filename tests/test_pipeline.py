import asyncio
from app.core.database import AsyncSessionLocal
from app.modules.rag.pipeline import RAGPipeline
import time

async def test_pipeline():
    async with AsyncSessionLocal() as db:
        pipeline = RAGPipeline(tenant_id="12582952-7f59-4565-943a-9c0cde898ba3", db=db)
        
        start = time.time()
        print("Starting query...")
        res = await pipeline.query(
            query="summarize what u know",
            kb_id="9cbce002-3b87-47b8-b962-337aa6657658",
            agent_id="00000000-0000-0000-0000-000000000000"
        )
        print("Pipeline finished in", time.time() - start)
        print("Tokens:", res.total_tokens)
        print("Chunks:", len(res.chunks))

asyncio.run(test_pipeline())
