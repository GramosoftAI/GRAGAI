import asyncio, websockets, json

async def test():
    uri = "ws://localhost:4915/api/v1/rag/ws/f338beec-de40-4837-983e-59bf3b54dbeb?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYjMwZWIwODEtMTRmYi00N2Q3LTg1NTYtMTUwOGQ5NDY5ZjNkIiwidGVuYW50X2lkIjoiNzIzYmMyMTctNWYzOC00Y2FkLTlmMmMtNDU0ZjVhMjM0OGE2IiwidHlwZSI6ImFjY2VzcyIsImp0aSI6InczNVh1RjZHWE5yMWtyLWZpNHZxck8wenVmMzhHeUFKWUxjLUZsLWFmUGciLCJleHAiOjE3ODA1NTE5MzMsImlhdCI6MTc4MDU0ODMzM30.x7fl-O6RDshik6Nk3Rc8ny6CmNzeMRu_n1Ae4BkeMoA"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"query": "hi"}))
        async for msg in ws:
            print(repr(msg))

asyncio.run(test())
