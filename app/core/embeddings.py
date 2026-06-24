"""Embedding generation using DeepInfra API for semantic search"""



import httpx

import logging

from typing import List

from functools import lru_cache



from .config import get_settings

from .llm.deepinfra import DeepInfraEmbeddingClient



logger = logging.getLogger(__name__)

settings = get_settings()



# Initialize DeepInfra client (lazy - created on first use)

_deepinfra_client = None





def _get_deepinfra_client():

    """Get or create DeepInfra embedding client (singleton)"""

    global _deepinfra_client

    if _deepinfra_client is None:

        _deepinfra_client = DeepInfraEmbeddingClient()

    return _deepinfra_client





class EmbeddingGenerator:

    """

    Generate text embeddings using DeepInfra API.



    Production-grade embeddings for semantic search and similarity.

    Each embedding is typically a 512-dimensional vector (Production)

    or matches the configured settings.embedding_dimension.

    """



    @staticmethod

    def get_dimension() -> int:

        """Get the configured embedding dimension."""

        return settings.embedding_dimension



    # API endpoint for embeddings

    # Using meta-llama/Llama-2-7b-hf as embedding model is NOT right

    # We need actual embedding model. For now using a simple approach.

    # In production: use sentence-transformers hosted endpoint

    EMBEDDING_API = "https://api.deepinfra.com/v1/openai"



    # Track if we've logged the embedding mode (avoid spam)

    _mode_logged = False



    @staticmethod

    async def generate_embedding(text: str) -> List[float]:

        """

        Generate embedding for text using feature flag for Phase switching.



        PHASE 2 (default): Hash-based embeddings (deterministic, fast, testable)

        PHASE 3 (enabled via flag): Real DeepInfra API (semantic, accurate)



        Feature flag: settings.use_real_embeddings

        - Phase 2: False (hash-based) - fast development, zero cost

        - Phase 3: True (real embeddings from DeepInfra API)



        Args:

            text: Text to embed



        Returns:

            List of 768 floats representing the embedding

        """

        # Log embedding mode on first call (for debugging + rollout monitoring)

        if not EmbeddingGenerator._mode_logged:

            mode = (

                "REAL (DeepInfra API)"

                if settings.use_real_embeddings

                else "HASH (Phase 2)"

            )

            logger.info(f"Using embedding mode: {mode}")

            EmbeddingGenerator._mode_logged = True

        if not text or len(text.strip()) == 0:

            return [0.0] * settings.embedding_dimension



        try:

            # FEATURE FLAG: Switch between hash (Phase 2) and real (Phase 3)

            if settings.use_real_embeddings:

                # Phase 3: Real embeddings from DeepInfra

                return await EmbeddingGenerator._real_embedding(text)

            else:

                # Phase 2: Deterministic hash-based embeddings

                logger.debug(

                    f"Embedding source: Hash (Phase 2) for text: {text[:50]}..."

                )

                return EmbeddingGenerator._hash_to_embedding(text)



        except Exception as e:

            logger.warning(f"Failed to generate embedding: {e}. Falling back to hash.")

            # Graceful fallback: use hash instead of failing

            logger.info(

                f"Embedding source: Fallback Hash (API failed) for text: {text[:50]}..."

            )

            return EmbeddingGenerator._hash_to_embedding(text)



    @staticmethod

    def _hash_to_embedding(text: str) -> List[float]:

        """

        Convert text to deterministic embedding using hash (Phase 2).



        This is NOT production-grade but allows testing without DeepInfra.

        Ensures same text always gets same embedding.



        Phase 3: Replace with actual embedding model call.



        Args:

            text: Text to embed



        Returns:

            Deterministic vector matches settings.embedding_dimension

        """

        import hashlib



        # Create hash of text

        hash_obj = hashlib.sha256(text.encode())

        hash_int = int(hash_obj.hexdigest(), 16)



        # Seed random number generator with hash

        import random



        rng = random.Random(hash_int)



        # Generate 768-dimensional vector from hash

        # All values in range [-1.0, 1.0] (typical for embeddings after normalization)

        embedding = [

            rng.uniform(-1.0, 1.0) for _ in range(settings.embedding_dimension)

        ]



        return embedding



    @staticmethod

    async def _real_embedding(text: str) -> List[float]:

        """

        Generate real embedding from DeepInfra API (Phase 3).



        PRODUCTION IMPLEMENTATION: Calls actual embedding API.



        Uses qwen3-embedd-0.4B model for semantic embeddings.

        Includes automatic retries and timeout protection.



        Args:

            text: Text to embed



        Returns:

            Embedding vector from DeepInfra API



        Safety:

        - Automatic retries (try 3 times)

        - Timeout after 10 seconds

        - Text limited to 2000 chars (prevent overload)

        - Fallback to hash on failure

        """

        try:

            # Get DeepInfra client (singleton)

            client = _get_deepinfra_client()



            # Call API to generate real embedding

            embedding = await client.generate_embedding(text)



            logger.debug(f" Real embedding from DeepInfra ({len(embedding)} dims)")

            return embedding



        except Exception as e:

            # Graceful fallback: use hash-based embedding instead of crashing

            logger.warning(

                f"Failed to get real embedding from DeepInfra: {e}. Falling back to hash-based."

            )

            return EmbeddingGenerator._hash_to_embedding(text)



    @staticmethod

    async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:

        """

        Generate embeddings for multiple texts in parallel (Phase 3.5).

        

        Args:

            texts: List of texts to embed

            

        Returns:

            List of embeddings (optimized via asyncio.gather in client)

        """

        if not texts:

            return []

            

        # Get DeepInfra client (singleton)

        client = _get_deepinfra_client()

        


        try:
            # Call optimized parallel batch method
            return await client.generate_embeddings_batch(texts)
        except Exception as e:
            logger.warning(f"Failed to generate real embeddings batch: {e}. Falling back to hash-based.")
            return [EmbeddingGenerator._hash_to_embedding(text) for text in texts]



    @staticmethod

    def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:

        """

        Calculate cosine similarity between two embeddings.



        CRITICAL for Chunk-[:SIMILAR]->Chunk relationships.



        Args:

            embedding1: First embedding vector

            embedding2: Second embedding vector



        Returns:

            Similarity score in [0, 1] (0=opposite, 1=identical)

        """

        import math



        # Handle zero vectors

        if not embedding1 or not embedding2:

            return 0.0



        # Compute dot product

        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))



        # Compute magnitudes

        magnitude1 = math.sqrt(sum(a * a for a in embedding1))

        magnitude2 = math.sqrt(sum(b * b for b in embedding2))



        # Avoid division by zero

        if magnitude1 == 0 or magnitude2 == 0:

            return 0.0



        # Cosine similarity

        similarity = dot_product / (magnitude1 * magnitude2)



        # Normalize to [0, 1] (cosine similarity is typically in [-1, 1])

        # Map -1 to 0, 1 to 1

        normalized = (similarity + 1) / 2.0



        return max(0.0, min(1.0, normalized))  # Clamp to [0, 1]

