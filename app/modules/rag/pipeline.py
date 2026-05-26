"""
RAG Pipeline - Graph-first retrieval and ranking system
Phase 2 Step 4: Transforms Graph Intelligence into Production RAG
"""

import logging
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.neo4j_repository import Neo4jRepository
from app.core.embeddings import EmbeddingGenerator
from app.core.config import get_settings
from .query_router import QueryRouter, SearchType


logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Chunk retrieved by RAG pipeline with scoring metadata and attribution"""

    chunk_id: str
    text: str
    kb_id: str
    position: int
    embedding_similarity: float
    graph_score: float
    hybrid_score: float
    reason: str = ""  # Why this chunk was retrieved (SIMILAR, ENTITY, NEXT, Seed)
    source: Optional[str] = None  # Source of the chunk (e.g., filename, URL, database table)


@dataclass
class RAGContext:
    """Context retrieved for LLM generation"""

    query: str
    chunks: List[RetrievedChunk]
    entity_mentions: Dict[str, List[str]]  # entity_name -> [chunk_ids]
    total_tokens: int
    triplet_context: str = ""  # Phase 4A: Formatted triplet relationships (additive)
    triplets: List[Dict] = None  # Raw triplets for metadata
    search_type: str = "DEFAULT" # The strategy selected by the router
    personal_memories: List[str] = None # Phase 5: Personal user context (Mem0)


class RAGPipeline:
    """
    Graph-first RAG pipeline: Query → Graph Retrieval → Expansion → Ranking → LLM.

    CRITICAL FLOW:
    1. Query embedding generation
    2. Semantic retrieval (TOP-K similar chunks)
    3. Graph expansion (SIMILAR, MENTIONS, NEXT edges)
    4. Hybrid scoring (embedding similarity + graph connectivity)
    5. Token-limited context selection
    6. Context formatting for LLM

    DESIGN PRINCIPLES:
    - Graph-first: Leverage semantic relationships for intelligent expansion
    - Deterministic: Same query always scores same
    - Efficient: Max depth 2, max 15 chunks, token budgeted
    - Safe: RLS enforced on every query, tenant_id validated everywhere
    """

    def __init__(self, tenant_id: str, db: Optional[AsyncSession] = None):
        """
        Initialize RAG pipeline for tenant.

        Args:
            tenant_id: Tenant UUID (for multi-tenancy enforcement)
            db: Optional PostgreSQL AsyncSession for pgvector search
        """
        self.tenant_id = tenant_id
        self.db = db
        self.neo4j_repo = Neo4jRepository(tenant_id)
        self.settings = get_settings()
        self.router = QueryRouter()

    async def query(
        self,
        query: str,
        agent_id: str,
        kb_id: str | list[str],
        user_id: Optional[str] = None,
        top_k: int = 10,
        max_depth: int = 2,
        max_tokens: int = 3000,
    ) -> RAGContext:
        """
        Execute RAG query on knowledge base.

        FLOW:
        1. Generate query embedding
        2. Retrieve seed chunks (top-k similarity)
        3. Expand via graph (multi-hop)
        4. Score and rank
        5. Select context within token budget

        Args:
            query: User query string
            agent_id: Agent UUID (ownership validation)
            kb_id: Knowledge Base UUID
            top_k: Initial seed chunks to retrieve
            max_depth: Max graph expansion depth (2 = 2-hop)
            max_tokens: Token budget for context

        Returns:
            RAGContext with ranked chunks and metadata
        """
        logger.info(
            f"🧠 RAG Query: agent={agent_id}, kb={kb_id}, query_len={len(query)}"
        )

        # Normalize kb_id to a list for uniform processing
        kb_ids = [kb_id] if isinstance(kb_id, str) else kb_id

        # STEP 0: ROUTE QUERY TO OPTIMAL SEARCH STRATEGY
        search_type = await self.router.route_query(query)
        logger.info(f"🚦 Query Router selected strategy: {search_type.name}")

        # Dynamically adjust retrieval parameters based on the chosen strategy
        if search_type == SearchType.CHUNK_SEARCH:
            max_depth = 0  # No graph expansion needed for direct facts; pure vector
            logger.info("   -> Optimizing for CHUNK_SEARCH: Disabling graph expansion.")
        elif search_type == SearchType.GRAPH_SUMMARY:
            top_k = min(top_k * 2, 30)  # Broader initial sweep for summary
            max_tokens = max_tokens + 1000  # Expand token budget
            logger.info("   -> Optimizing for GRAPH_SUMMARY: Expanding top_k and token budget.")
        elif search_type == SearchType.CHAIN_OF_THOUGHT:
            max_depth = max(max_depth, 3)  # Deeper traversal for complex reasoning
            logger.info("   -> Optimizing for CHAIN_OF_THOUGHT: Increasing graph expansion depth.")
        elif search_type == SearchType.MEMORY_ONLY:
            # For memory-only queries, we prioritize consolidated triplets from chat
            top_k = 5
            max_depth = 1
            logger.info("   -> Optimizing for MEMORY_ONLY: Targeting consolidated chat facts.")
        elif search_type == SearchType.ENTITY_CONNECTION:
            max_depth = max(max_depth, 2)
            top_k = 20 # Broader search to find the bridge
            logger.info("   -> Optimizing for ENTITY_CONNECTION: Broadening search for relationship paths.")
        elif search_type == SearchType.SOCIAL:
            # For social interactions, we don't need many chunks, but we want to allow conversation
            top_k = 1
            max_depth = 0
            logger.info("   -> Optimizing for SOCIAL: Enabling conversational mode.")

        # STEP 1: GENERATE QUERY EMBEDDING
        logger.debug("Step 1: Generating query embedding...")
        query_embedding = await EmbeddingGenerator.generate_embedding(query)
        logger.debug(f"✅ Query embedding generated ({len(query_embedding)} dims)")

        # STEP 1.5: PERSONAL MEMORY RETRIEVAL (Phase 5 — Feature-Flagged)
        personal_memories = []
        if self.settings.use_personal_memory and user_id:
            try:
                from app.core.memory.personalization import PersonalMemoryService
                pm_service = PersonalMemoryService(self.tenant_id)
                personal_memories = await pm_service.get_relevant_memories(
                    user_id=user_id,
                    query_embedding=query_embedding,
                    top_k=3
                )
                if personal_memories:
                    logger.info(f"✅ Retrieved {len(personal_memories)} personal memories for user {user_id[:8]}")
            except Exception as e:
                logger.warning(f"⚠️ Personal memory retrieval failed (non-blocking): {e}")

        # STEP 2: RETRIEVE SEED CHUNKS (SEMANTIC SIMILARITY)
        logger.info(f"Step 2: Retrieving top-{top_k} seed chunks for KBs {kb_ids}...")
        seed_chunks = await self._retrieve_seed_chunks(
            kb_ids=kb_ids,
            query_embedding=query_embedding,
            top_k=top_k,
        )
        
        if not seed_chunks:
            # DIAGNOSTIC: Check if any chunks exist at all
            all_chunks_query = "MATCH (kb:KnowledgeBase)-[:HAS_CHUNK]->(c) WHERE kb.id IN $kb_ids AND kb.tenant_id = $tenant_id RETURN count(c) as count"
            count_res = await self.neo4j_repo.execute_read(
                all_chunks_query, 
                {"kb_ids": kb_ids, "tenant_id": self.tenant_id}
            )
            chunk_count = count_res[0]["count"] if count_res else 0
            
            logger.warning(f"⚠️ No seed chunks found! Total chunks in DB for this KB: {chunk_count}")
            
            # If it's a SOCIAL query, we don't fail, we just continue to allow conversational response
            if search_type == SearchType.SOCIAL:
                logger.info("🚦 Continuing with empty context for SOCIAL query.")
                return RAGContext(
                    query=query, 
                    chunks=[], 
                    entity_mentions={}, 
                    total_tokens=0,
                    personal_memories=personal_memories,
                    search_type=search_type.name
                )

            return RAGContext(
                query=query, 
                chunks=[], 
                entity_mentions={}, 
                total_tokens=0,
                personal_memories=personal_memories,
                search_type=search_type.name
            )

        logger.info(f"✅ Retrieved {len(seed_chunks)} seed chunks")

        # STEP 3: EXPAND VIA GRAPH (MULTI-HOP)
        logger.debug(f"Step 3: Expanding graph (max_depth={max_depth})...")
        seed_chunk_ids = {chunk["chunk_id"] for chunk in seed_chunks}
        expanded_chunks = await self._expand_via_graph(
            seed_chunk_ids=seed_chunk_ids,
            max_depth=max_depth,
        )
        logger.info(
            f"✅ Graph expansion: {len(seed_chunk_ids)} seed → {len(expanded_chunks)} total chunks"
        )

        # STEP 4: SCORE AND RANK (HYBRID SCORING)
        logger.debug("Step 4: Scoring and ranking chunks...")
        scored_chunks = await self._score_chunks(
            seed_chunks=seed_chunks,
            expanded_chunks=expanded_chunks,
            query_embedding=query_embedding,
        )
        logger.info(f"✅ Scored {len(scored_chunks)} chunks")

        # STEP 5: SELECT CONTEXT (TOKEN BUDGET)
        logger.debug(f"Step 5: Selecting context (token_budget={max_tokens})...")
        context_chunks = self._select_context(
            scored_chunks=scored_chunks,
            max_tokens=max_tokens,
        )
        logger.info(
            f"✅ Selected {len(context_chunks)} chunks for context "
            f"({context_chunks[-1].hybrid_score:.3f} - {context_chunks[0].hybrid_score:.3f} score range)"
        )

        # STEP 6: EXTRACT ENTITY MENTIONS
        logger.debug("Step 6: Extracting entity mentions...")
        entity_mentions = await self._extract_entity_mentions(
            chunk_ids={chunk.chunk_id for chunk in context_chunks}
        )
        logger.info(f"✅ Extracted {len(entity_mentions)} unique entities")

        # STEP 7: TRIPLET RETRIEVAL (Phase 4A — Feature-Flagged)
        # Enriches context with knowledge graph relationships
        # SAFETY: Independent step — if disabled or fails, pipeline continues
        triplet_context = ""
        if self.settings.use_triplet_extraction:
            try:
                from app.core.triplet_extractor import TripletRetriever
                retriever = TripletRetriever(self.tenant_id)
                relevant_triplets = await retriever.search_triplets(
                    query_embedding=query_embedding,
                    kb_ids=kb_ids,
                    top_k=self.settings.triplet_retrieval_top_k,
                )
                if relevant_triplets:
                    triplet_context = retriever.format_triplets_as_context(relevant_triplets)
                    logger.info(f"✅ Retrieved {len(relevant_triplets)} relevant triplets")
            except Exception as e:
                logger.warning(f"⚠️ Triplet retrieval failed (non-blocking): {e}")

        # Calculate total tokens in context
        total_tokens = sum(
            len(chunk.text.split()) * 1.3 for chunk in context_chunks
        )  # Rough estimate
        if triplet_context:
            total_tokens += len(triplet_context.split()) * 1.3

        return RAGContext(
            query=query,
            chunks=context_chunks,
            entity_mentions=entity_mentions,
            total_tokens=int(total_tokens),
            triplet_context=triplet_context,
            triplets=relevant_triplets if 'relevant_triplets' in locals() else None,
            search_type=search_type.name,
            personal_memories=personal_memories
        )

    async def _retrieve_seed_chunks(
        self,
        kb_ids: List[str],
        query_embedding: List[float],
        top_k: int,
    ) -> List[Dict]:
        """
        Retrieve top-k chunks by embedding similarity.
        Uses PostgreSQL pgvector if available, with a resilient fallback to Neo4j.

        Args:
            kb_ids: List of Knowledge Base UUIDs
            query_embedding: Query embedding vector
            top_k: Number of chunks to retrieve

        Returns:
            List of chunks sorted by similarity (highest first)
        """
        # ============= STRATEGY 1: POSTGRESQL PGVECTOR =============
        if self.db:
            try:
                from sqlalchemy import select, and_
                from app.modules.knowledge_bases.models import DocumentChunk
                
                # Query using pgvector cosine_distance operator
                # similarity = 1.0 - cosine_distance
                stmt = (
                    select(
                        DocumentChunk.id,
                        DocumentChunk.text,
                        DocumentChunk.chunk_index,
                        DocumentChunk.kb_id,
                        (1.0 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("similarity")
                    )
                    .where(
                        and_(
                            DocumentChunk.tenant_id == UUID(self.tenant_id),
                            DocumentChunk.kb_id.in_([UUID(kb_id) for kb_id in kb_ids])
                        )
                    )
                    .order_by(DocumentChunk.embedding.cosine_distance(query_embedding).asc())
                    .limit(top_k)
                )
                
                result = await self.db.execute(stmt)
                rows = result.fetchall()
                
                pg_chunks = []
                for row in rows:
                    similarity = float(row.similarity)
                    if similarity >= self.settings.similarity_min_threshold:
                        pg_chunks.append({
                            "chunk_id": str(row.id),
                            "text": row.text,
                            "position": row.chunk_index,
                            "kb_id": str(row.kb_id),
                            "embedding": None,  # embedding vector itself not needed downstream
                            "similarity": similarity,
                            "weight": 1.0,
                            "source": None
                        })
                
                logger.info(f"🎯 PostgreSQL pgvector retrieved {len(pg_chunks)} seed chunks")
                if pg_chunks:
                    return pg_chunks
                
                logger.warning("📉 No chunks met similarity threshold in PostgreSQL. Falling back to Neo4j...")
            except Exception as pg_err:
                logger.error(f"⚠️ PostgreSQL pgvector search failed: {pg_err}. Falling back to Neo4j...", exc_info=True)

        # ============= STRATEGY 2: NEO4J VECTOR FALLBACK =============
        query = """
        MATCH (kb:KnowledgeBase)
        WHERE kb.id IN $kb_ids AND kb.tenant_id = $tenant_id
        MATCH (kb)-[:HAS_CHUNK]->(c:Chunk)
        WHERE c.embedding IS NOT NULL AND size(c.embedding) = $dimension
        RETURN c.id as chunk_id, c.text as text, c.position as position, c.kb_id as kb_id, c.embedding as embedding, coalesce(c.weight, 1.0) as weight, c.source as source
        LIMIT 1000
        """

        try:
            results = await self.neo4j_repo.execute_read(
                query,
                {
                    "kb_ids": kb_ids, 
                    "tenant_id": self.tenant_id,
                    "dimension": EmbeddingGenerator.get_dimension()
                },
            )

            if not results:
                logger.warning(f"📉 No chunks found for KBs {kb_ids} in Neo4j.")
                return []

            # LOG CHUNK TEXT (Verification)
            for res in results[:3]:
                logger.info(f"📄 Found chunk in Neo4j: {res['text'][:50]}... (Dim: {len(res['embedding'])})")

            # Compute similarities (Phase 2: brute force)
            chunks_with_similarity = []
            for result in results:
                similarity = EmbeddingGenerator.cosine_similarity(
                    query_embedding, result["embedding"]
                )
                chunks_with_similarity.append(
                    {
                        "chunk_id": result["chunk_id"],
                        "text": result["text"],
                        "position": result["position"],
                        "kb_id": result["kb_id"],
                        "embedding": result["embedding"],
                        "similarity": similarity,
                        "weight": result.get("weight", 1.0),
                        "source": result.get("source"),
                    }
                )

            # Sort by similarity, return top-k
            # Only include chunks above the configured minimum threshold
            sorted_chunks = sorted(
                [c for c in chunks_with_similarity if c["similarity"] >= self.settings.similarity_min_threshold],
                key=lambda x: x["similarity"],
                reverse=True
            )
            
            if chunks_with_similarity:
                max_score = max(c["similarity"] for c in chunks_with_similarity)
                logger.info(f"🎯 Max similarity score found in Neo4j: {max_score:.4f} (Threshold: {self.settings.similarity_min_threshold})")
            else:
                logger.warning("📉 No chunks found in Neo4j (with embeddings) for this Knowledge Base.")

            return sorted_chunks[:top_k]

        except Exception as e:
            logger.error(f"❌ Failed to retrieve seed chunks via Neo4j: {e}")
            return []

    async def _expand_via_graph(
        self,
        seed_chunk_ids: Set[str],
        max_depth: int = 2,
    ) -> Dict[str, Dict]:
        """
        Expand seed chunks via graph relationships.

        EXPANSION STRATEGY:
        - Depth 1: Via SIMILAR (semantic), MENTIONS (entity), NEXT (context)
        - Depth 2: One more hop from Depth 1 neighbors

        Args:
            seed_chunk_ids: Set of seed chunk IDs
            max_depth: Max expansion hops

        Returns:
            Dict mapping chunk_id -> chunk metadata
        """
        expanded = {cid: {"depth": 0, "connection": "seed"} for cid in seed_chunk_ids}

        for depth in range(1, max_depth + 1):
            # Get all IDs from current frontier
            frontier_ids = [
                cid for cid, meta in expanded.items() if meta.get("depth") == depth - 1
            ]

            if not frontier_ids:
                break

            # Expand via all relationship types
            query = """
            WITH $frontier_ids AS frontier
            MATCH (c:Chunk {tenant_id: $tenant_id})
            WHERE c.id IN frontier
            
            WITH c
            MATCH (c)-[r]-(neighbor:Chunk {tenant_id: $tenant_id})
            WHERE neighbor.id NOT IN $existing_ids
            AND NOT (neighbor)-[:HAS_CHUNK]-(:KnowledgeBase)  # Not KB root
            
            RETURN DISTINCT
                neighbor.id as chunk_id,
                type(r) as relationship_type,
                coalesce(neighbor.weight, 1.0) as weight
            LIMIT 50
            """

            try:
                results = await self.neo4j_repo.execute_read(
                    query,
                    {
                        "frontier_ids": frontier_ids,
                        "existing_ids": list(expanded.keys()),
                        "tenant_id": self.tenant_id,
                    },
                )

                for result in results:
                    if result["chunk_id"] not in expanded:
                        expanded[result["chunk_id"]] = {
                            "depth": depth,
                            "connection": result["relationship_type"],
                            "weight": result.get("weight", 1.0),
                        }

            except Exception as e:
                logger.warning(
                    f"⚠️ Graph expansion depth {depth} failed: {e}. Continuing..."
                )
                break

        logger.debug(
            f"Graph expansion: {len(expanded) - len(seed_chunk_ids)} new chunks discovered"
        )
        return expanded

    async def _score_chunks(
        self,
        seed_chunks: List[Dict],
        expanded_chunks: Dict[str, Dict],
        query_embedding: List[float],
    ) -> List[RetrievedChunk]:
        """
        Score chunks using hybrid scoring: semantic + graph connectivity.

        SCORING FORMULA:
        hybrid_score = 0.6 * embedding_similarity + 0.4 * graph_score

        Where:
        - embedding_similarity: Cosine similarity to query (0–1)
        - graph_score: Inverse distance from seed (seed=1.0, depth 1=0.75, depth 2=0.5)

        Args:
            seed_chunks: Seed chunks with similarity scores
            expanded_chunks: All expanded chunks with depth/connection
            query_embedding: Query embedding for similarity

        Returns:
            Sorted list of RetrievedChunk (highest score first)
        """
        scored = []

        # Score seed chunks (already have embedding similarity)
        for seed in seed_chunks:
            # Graph score for seed: 1.0 (closest)
            graph_score = 1.0

            base_hybrid = 0.6 * seed["similarity"] + 0.4 * graph_score
            hybrid_score = min(1.0, base_hybrid * seed["weight"])

            scored.append(
                RetrievedChunk(
                    chunk_id=seed["chunk_id"],
                    text=seed["text"],
                    kb_id=seed["kb_id"],
                    position=seed["position"],
                    embedding_similarity=seed["similarity"],
                    graph_score=graph_score,
                    hybrid_score=hybrid_score,
                    reason="Seed chunk (semantic similarity)",
                    source=seed.get("source"),
                )
            )

        # Score expanded chunks (approximate embedding similarity from neighbors)
        for chunk_id, meta in expanded_chunks.items():
            if meta.get("depth", 0) == 0:
                continue  # Skip seeds (already scored)

            # Graph score based on depth (inverse distance)
            depth = meta.get("depth", 2)
            graph_score = max(0.3, 1.0 - (depth * 0.25))

            # Embedding similarity: interpolate from neighbors (heuristic)
            # For phase 2: Use graph_score as proxy
            embedding_similarity = graph_score * 0.7

            base_hybrid = 0.6 * embedding_similarity + 0.4 * graph_score
            hybrid_score = min(1.0, base_hybrid * meta.get("weight", 1.0))

            # Build reason based on connection type
            connection_type = meta.get("connection", "UNKNOWN")
            reason = f"{connection_type} connection (depth {depth})"

            scored.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text="",  # Will be fetched if needed
                    kb_id="",
                    position=0,
                    embedding_similarity=embedding_similarity,
                    graph_score=graph_score,
                    hybrid_score=hybrid_score,
                    reason=reason,
                )
            )

        # Sort by hybrid score (highest first)
        scored.sort(key=lambda x: x.hybrid_score, reverse=True)
        return scored

    def _select_context(
        self,
        scored_chunks: List[RetrievedChunk],
        max_tokens: int,
    ) -> List[RetrievedChunk]:
        """
        Select top chunks within token budget.

        DIVERSITY IMPROVEMENT:
        - Avoid selecting too many similar chunks (redundancy penalty)
        - Prefer diverse chunks that cover different topics
        - Max Marginal Relevance (MMR) approach

        Args:
            scored_chunks: Ranked chunks
            max_tokens: Token budget

        Returns:
            Selected chunks (ordered by score, highest first)
        """
        # Step 1: Apply diversity penalty (re-score to reduce redundancy)
        selected_with_diversity = self._apply_diversity_penalty(scored_chunks)

        # Step 2: Select top chunks within token budget
        selected = []
        token_count = 0

        for chunk in selected_with_diversity:
            # Estimate tokens (rough: words * 1.3)
            chunk_tokens = int(len(chunk.text.split()) * 1.3) if chunk.text else 0

            if token_count + chunk_tokens <= max_tokens:
                selected.append(chunk)
                token_count += chunk_tokens
            else:
                # Over budget, stop
                break

        return selected

    def _apply_diversity_penalty(
        self,
        scored_chunks: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """
        Apply diversity penalty to reduce redundant chunks.

        ALGORITHM (Max Marginal Relevance):
        1. Start with highest-scored chunk
        2. For each remaining chunk:
           ├─ If too similar to selected chunks: penalize score
           └─ Otherwise: keep original score
        3. Select next highest-scored chunk (accounting for penalties)
        4. Repeat until all scored

        PENALTY FORMULA:
        diversity_adjusted_score = 0.8 * original_score - 0.2 * max_similarity_to_selected

        Intuition:
        - If new chunk is similar to already-selected chunk, reduce its score
        - Prefer chunks that are highly relevant AND different from others
        """
        if not scored_chunks or len(scored_chunks) < 2:
            return scored_chunks

        # Track which chunks we've selected
        selected_indices = []
        adjusted_scores = {
            i: chunk.hybrid_score for i, chunk in enumerate(scored_chunks)
        }

        # Step 1: Always select highest-scored chunk first
        selected_indices.append(0)

        # Step 2: Iteratively select next-best chunk with diversity bonus
        while len(selected_indices) < len(scored_chunks):
            best_idx = None
            best_adjusted_score = -1.0

            for i, chunk in enumerate(scored_chunks):
                if i in selected_indices:
                    continue  # Already selected

                # Compute similarity to selected chunks
                max_similarity_to_selected = 0.0
                for selected_idx in selected_indices:
                    selected_chunk = scored_chunks[selected_idx]

                    # Heuristic: chunks with same reason are likely similar
                    if chunk.reason == selected_chunk.reason:
                        max_similarity_to_selected = max(
                            max_similarity_to_selected, 0.9
                        )  # High similarity
                    # Heuristic: chunks with embedding sim difference
                    elif (
                        abs(
                            chunk.embedding_similarity
                            - selected_chunk.embedding_similarity
                        )
                        < 0.1
                    ):
                        max_similarity_to_selected = max(
                            max_similarity_to_selected, 0.7
                        )  # Moderate similarity

                # Apply diversity penalty
                adjusted_score = (0.8 * adjusted_scores[i]) - (
                    0.2 * max_similarity_to_selected
                )

                if adjusted_score > best_adjusted_score:
                    best_adjusted_score = adjusted_score
                    best_idx = i

            if best_idx is not None:
                selected_indices.append(best_idx)
            else:
                break

        # Return chunks in original score order (highest first)
        result = [scored_chunks[i] for i in sorted(selected_indices)]
        result.sort(key=lambda x: x.hybrid_score, reverse=True)
        return result

    async def _extract_entity_mentions(
        self,
        chunk_ids: Set[str],
    ) -> Dict[str, List[str]]:
        """
        Extract entities mentioned by selected chunks.

        Args:
            chunk_ids: Set of selected chunk IDs

        Returns:
            Dict mapping entity_text -> [chunk_ids mentioning it]
        """
        query = """
        WITH $chunk_ids AS chunk_list
        MATCH (c:Chunk {tenant_id: $tenant_id})
        WHERE c.id IN chunk_list
        MATCH (c)-[:MENTIONS]->(e:Entity {tenant_id: $tenant_id})
        RETURN e.text as entity_text, collect(c.id) as chunk_ids
        """

        try:
            results = await self.neo4j_repo.execute_read(
                query,
                {"chunk_ids": list(chunk_ids), "tenant_id": self.tenant_id},
            )

            entity_mentions = {}
            for result in results:
                entity_mentions[result["entity_text"]] = result["chunk_ids"]

            return entity_mentions

        except Exception as e:
            logger.warning(f"⚠️ Failed to extract entity mentions: {e}")
            return {}
