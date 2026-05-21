import logging
from typing import Optional
from app.core.llm.deepinfra_llm import get_llm_client

logger = logging.getLogger(__name__)

class QueryRewriter:
    """
    Modular Query Rewriter using Qwen2.5-72B-Instruct.
    Optimizes vague, misspelled, or shorthand queries for higher-accuracy RAG retrieval.
    """
    def __init__(self):
        self.system_prompt = (
            """
You are a query rewriting assistant for a Retrieval-Augmented Generation (RAG) system.

Your job is to rewrite user queries to improve retrieval quality for vector databases and knowledge graphs.

Rules:
- Correct spelling and grammar mistakes
- Expand abbreviations when clear
- Rewrite vague queries into clearer search-friendly queries
- Preserve the user's original intent exactly
- Do NOT add new meaning or assumptions
- Keep the rewritten query concise and natural
- Keep technical terms unchanged when possible
- If the query is already clear, return it unchanged
- Do NOT answer the question
- Return ONLY the rewritten query text
"""       )

    async def rewrite_query(self, query: str) -> str:
        """
        Takes a user query, enhances it using Qwen-2.5-72B-Instruct,
        and returns the enhanced query. Falls back to the original query on any failure.
        """
        stripped_query = query.strip()
        # Do not rewrite empty or extremely short queries
        if not stripped_query or len(stripped_query) < 3:
            return query
            
        try:
            llm_client = await get_llm_client()
            logger.debug(f"Rewriting query via Qwen-2.5-72B-Instruct: '{query}'")
            
            enhanced_query = await llm_client.generate(
                prompt=stripped_query,
                system_prompt=self.system_prompt,
                temperature=0.1,  # Low temperature for strict adherence
                max_tokens=256,
            )
            print(f"--------------------Original Query: '{query}' -> Enhanced Query: '{enhanced_query}'-------")
            cleaned_query = enhanced_query.strip().strip('"').strip("'")
            if cleaned_query:
                return cleaned_query
            return query
        except Exception as e:
            logger.error(f"⚠️ Query rewriting failed: {e}. Falling back to original query.")
            return query
