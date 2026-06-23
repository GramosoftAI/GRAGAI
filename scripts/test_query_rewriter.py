import asyncio
import sys
import os

# Ensure we're in the project root so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables if needed
os.environ["APP_ENV"] = "development"

from app.core.query_rewriter import QueryRewriter

async def main():
    print("=" * 60)
    print("[+] QUERY REWRITING / PROMPT ENHANCER TEST SUITE")
    print("=" * 60)
    
    rewriter = QueryRewriter()
    
    test_queries = [
        "tell abt jaguar speed",
        "wat is gpa limit",
        "capital of franse",
        "how does graphrag work in graphmind",
        "whats the weather like in nyc",
        "define ai",
        "who is the president of the us","who is vishnu"
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n[{idx}] Testing Query: \"{query}\"")
        try:
            enhanced = await rewriter.rewrite_query(query)
            print(f"    -> Enhanced Result: \"{enhanced}\"")
        except Exception as e:
            print(f"    [!] Error during rewriting: {e}")
            
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
