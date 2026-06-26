import asyncio
import websockets
import json

# ==========================================
# SYSTEMATIC TEST SUITE
# ==========================================
WS_URL = "ws://127.0.0.1:4915/api/v1/rag/ws"
AGENT_ID = "e0ac67a4-3e27-4f5b-90dd-d82e28814c1c"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiN2UxZDYzOWEtM2I2Yi00YzJlLWJiYWMtOGYzMzhkYzBiYWFlIiwidGVuYW50X2lkIjoiNTAyZjkxYzUtM2U5Yy00OWZmLTkzODItNGE1MjdmZjkzODFmIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc4MjU2NTk0Nn0.tG2meacfVdk03se4jFQihpF-NzsSLRWyvTrp7OHhrt4"

TEST_CASES = [
    # Parser & Basic Extraction
    "How many Action movies do we have?",
    "Top 5 Action movies ordered by popularity",
    
    # Aggregations
    "What's the average popularity?",
    "Average vote_average of Drama movies",
    "Highest popularity",
    "Lowest rating",
    
    # Grouping
    "Movies grouped by original_language",
    
    # Sorting & Filtering
    "Top 10 movies by popularity",
    "Bottom 5 movies",
    "Action movies with rating above 8",
    
    # Combined Complex Queries
    "Top 5 Action movies released after 2020 ordered by popularity",
    
    # Invalid / Validation
    "Average salary",
    "Average title",
    
    # Security Injection Attempts
    "Count movies'); DROP TABLE document_table_rows;",
    "genre = Action OR TRUE"
]

async def run_query(query: str):
    uri = f"{WS_URL}/{AGENT_ID}?token={TOKEN}"
    print(f"\n{'='*80}\n🧪 RUNNING TEST: {query}\n{'='*80}")
    
    try:
        async with websockets.connect(uri, open_timeout=30) as websocket:
            await websocket.send(json.dumps({"query": query}))
            
            full_answer = ""
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if isinstance(data, dict):
                        if data.get("type") == "metadata":
                            # Skip verbose metadata output for these tests
                            pass
                        elif data.get("type") == "done":
                            print("\n[STREAM COMPLETE]")
                            break
                        elif data.get("error"):
                            print(f"\n❌ [ERROR]: {data['error']}")
                            break
                except json.JSONDecodeError:
                    full_answer += message
                    
            print(f"\n{full_answer}\n")
    except Exception as e:
        print(f"\n❌ [CONNECTION FAILED]: {e}")

async def main():
    print("🚀 Starting Systematic Tabular Analytics Test Suite...")
    print("Ensure the backend is running with DEBUG_ANALYTICS=True in its .env to see full traces.\n")
    for test in TEST_CASES:
        await run_query(test)
        await asyncio.sleep(1) # Small breather between connections

if __name__ == "__main__":
    asyncio.run(main())
