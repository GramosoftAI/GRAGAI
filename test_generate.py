import asyncio
from app.core.llm.deepinfra_llm import DeepInfraLLMClient

async def test_generate():
    client = DeepInfraLLMClient()
    print("Sending request to LLM...")
    try:
        res = await client.generate("Return exactly {\"test\": 1} and nothing else", max_tokens=50)
        print("Response:", repr(res))
    except Exception as e:
        print("Error:", e)

asyncio.run(test_generate())
