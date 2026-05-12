"""Service layer for Knowledge Base (business logic + transactions + chunking + embeddings)"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging
import uuid
from datetime import datetime
import re

from .models import KnowledgeBase
from .repository import KnowledgeBaseRepository
from .audit import KBauditLog, KBauditEventType
from . import schemas
from ...core.neo4j_repository import Neo4jRepository
from ...core.neo4j_retry import retry_neo4j_operation
from ...core.config import get_settings
from ...core.embeddings import EmbeddingGenerator
from ...core.entity_extraction import EntityExtractor
from ...utils.formatters import format_success, format_error

logger = logging.getLogger(__name__)
settings = get_settings()


class TextChunker:
    """
    Split text into chunks with optional overlap.

    CRITICAL: Chunking strategy affects RAG quality.
    - Chunk size: 500-1000 tokens (roughly 2000-4000 characters)
    - Overlap: 50-100 tokens (100-400 characters)
    - Preserves sentence boundaries when possible
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count (rough: split by whitespace).

        CRITICAL: This is approximation. For production:
        Use tiktoken library for accurate OpenAI token counting.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: average 4 chars per token
        return len(text) // 4

    @staticmethod
    def split_into_chunks(
        text: str,
        chunk_size: int = 2000,  # ~500 tokens
        overlap_size: int = 400,  # ~100 tokens
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Characters per chunk (default ~500 tokens)
            overlap_size: Overlap between chunks (default ~100 tokens)

        Returns:
            List of text chunks

        Example:
            text = "Long document text..."
            chunks = TextChunker.split_into_chunks(text)
            # chunks = ["first chunk with overlap...", "second chunk with overlap...", ...]
        """
        chunks = []

        if len(text) <= chunk_size:
            # Single chunk (smaller than min size)
            return [text.strip()]

        # Split by sentences when possible (preserve context)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current_chunk = ""

        for sentence in sentences:
            # Add sentence to current chunk
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # Current chunk is full, save it
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                if chunks and overlap_size > 0:
                    # Keep last overlap_size chars from previous chunk
                    overlap = (
                        chunks[-1][-overlap_size:]
                        if len(chunks[-1]) > overlap_size
                        else chunks[-1]
                    )
                    current_chunk = overlap + " " + sentence
                else:
                    current_chunk = sentence

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


class KnowledgeBaseService:
    """
    Knowledge Base service - coordinates PostgreSQL, Neo4j, and embeddings.

    DISTRIBUTED TRANSACTION PATTERN:
    ================================
    CREATE:
    1. PostgreSQL INSERT (not committed)
    2. Neo4j CREATE KB node + chunk nodes
    3. If Neo4j fails → compensation → rollback PostgreSQL

    DELETE:
    1. Neo4j DELETE (chunks + KB node)
    2. PostgreSQL soft-delete (only if Neo4j succeeds)

    CHUNKING & EMBEDDINGS:
    1. Split text into 500-1000 token chunks
    2. Generate embeddings for each chunk
    3. Store chunks in Neo4j with vector embeddings
    4. Create relationships: KB→Chunk, Chunk→Chunk(NEXT)
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize KB service.

        Args:
            db: Database session (for PostgreSQL)
            tenant_id: Tenant UUID
        """
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id)
        self.repository = KnowledgeBaseRepository(db, str(self.tenant_id))
        self.neo4j_repo = Neo4jRepository(str(self.tenant_id))

    async def create_knowledge_base(
        self,
        user_id: str,
        request: schemas.KBCreate,
    ) -> dict:
        """
        Create a new knowledge base in BOTH PostgreSQL and Neo4j.

        TRANSACTION SAFETY WITH COMPENSATION:
        1. Create KB in PostgreSQL (not committed yet)
        2. Create (:KnowledgeBase) node in Neo4j
        3. Link Agent → KB relationship
        4. If Neo4j fails → Delete Neo4j KB node → Rollback PostgreSQL

        Args:
            user_id: User UUID (who created KB)
            request: KBCreate schema with name, agent_id, description

        Returns:
            Dict with success, KB (KBResponse), or error
        """
        kb_id = None
        try:
            # ============= STEP 1: POSTGRES INSERT (NOT COMMITTED) =============
            pg_kb = await self.repository.create(
                name=request.name,
                agent_id=str(request.agent_id),
                user_id=user_id,
                description=request.description,
                source=request.source or "user_upload",
            )
            kb_id = str(pg_kb.id)
            logger.info(f"✅ PostgreSQL: Created KB {kb_id}")

            # ============= STEP 2: NEO4J CREATE WITH RETRY =============
            neo4j_query = """
            CREATE (kb:KnowledgeBase {
                id: $kb_id,
                tenant_id: $tenant_id,
                agent_id: $agent_id,
                name: $name,
                source: $source,
                created_at: timestamp()
            })
            
            WITH kb
            MATCH (a:Agent {tenant_id: $tenant_id, id: $agent_id})
            CREATE (a)-[:OWNS_KB]->(kb)
            
            RETURN kb
            """

            try:
                await retry_neo4j_operation(
                    lambda: self.neo4j_repo.execute_write(
                        neo4j_query,
                        {
                            "kb_id": kb_id,
                            "tenant_id": str(self.tenant_id),
                            "agent_id": str(request.agent_id),
                            "name": request.name,
                            "source": request.source or "user_upload",
                        },
                    )
                )
                logger.info(f"✅ Neo4j: Created KB node {kb_id}")

            except Exception as neo4j_error:
                # ============= COMPENSATION: DELETE NEO4J KB =============
                logger.warning(f"⚠️ Neo4j creation failed: {neo4j_error}")
                logger.warning(f"   Attempting compensation: delete Neo4j KB {kb_id}")

                try:
                    await retry_neo4j_operation(
                        lambda: self.neo4j_repo.execute_write(
                            """
                            MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
                            DETACH DELETE kb
                            """,
                            {"kb_id": kb_id, "tenant_id": str(self.tenant_id)},
                        )
                    )
                    logger.info(f"✅ Compensation: Deleted orphan Neo4j KB {kb_id}")
                except Exception as comp_error:
                    logger.error(
                        f"❌ Compensation FAILED (orphan KB remains in Neo4j): {comp_error}"
                    )

                # ============= ROLLBACK POSTGRESQL =============
                await self.db.rollback()
                logger.error(f"❌ Rolled back PostgreSQL after Neo4j failure")

                return format_error(
                    f"Failed to create KB in graph: {neo4j_error}",
                    meta={"error_code": "NEO4J_ERROR"},
                )

            # ============= STEP 3: COMMIT BOTH TRANSACTIONS =============
            await self.db.commit()
            logger.info(f"✅ COMMITTED: KB {kb_id} in PostgreSQL + Neo4j")

            # ============= AUDIT LOG =============
            await KBauditLog.log_event(
                tenant_id=str(self.tenant_id),
                user_id=user_id,
                kb_id=kb_id,
                event_type=KBauditEventType.KB_CREATED,
                details={"name": request.name, "agent_id": str(request.agent_id)},
            )

            return format_success(
                {"kb": schemas.KBResponse.model_validate(pg_kb, from_attributes=True)},
                meta={"message": "Knowledge Base created successfully"},
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ KB creation failed: {e}")
            return format_error(
                f"Failed to create knowledge base: {str(e)}",
                meta={"error_code": "CREATION_ERROR"},
            )

    async def ingest_document(
        self,
        kb_id: str,
        document_text: str,
    ) -> dict:
        """
        Ingest a document with FULL RAG INTELLIGENCE:
        1. Chunk text (sentence-aware, overlapping)
        2. Generate embeddings for each chunk (semantic)
        3. Extract entities from chunks (concept linking)
        4. Create Chunk nodes with batch UNWIND (optimized)
        5. Create Chunk-[:SIMILAR]->Chunk relationships (semantic network)
        6. Create Chunk-[:MENTIONS]->Entity relationships (knowledge extraction)
        7. Validate graph integrity (safety check)

        Args:
            kb_id: KB UUID
            document_text: Raw document text to ingest

        Returns:
            Dict with success, chunks/entities created, or error
        """
        try:
            # ============= STEP 1: VALIDATE KB EXISTS =============
            kb = await self.repository.get_by_id(kb_id)
            if not kb:
                return format_error(f"KB not found: {kb_id}", meta={"status_code": 404})

            # ============= STEP 2: CHUNK THE TEXT =============
            chunks = TextChunker.split_into_chunks(
                document_text,
                chunk_size=2000,  # ~500 tokens
                overlap_size=400,  # ~100 tokens
            )
            logger.info(f"✅ Chunked document into {len(chunks)} chunks")

            if not chunks:
                return format_error("Document produced no chunks", status_code=400)

            # ============= STEP 3: GENERATE EMBEDDINGS FOR ALL CHUNKS =============
            logger.info(f"🧠 Generating embeddings for {len(chunks)} chunks...")
            embeddings = await EmbeddingGenerator.generate_embeddings_batch(chunks)

            if len(embeddings) != len(chunks):
                return format_error(
                    "Embedding generation failed", error_code="EMBEDDING_ERROR"
                )
            logger.info(f"✅ Generated {len(embeddings)} embeddings")

            # ============= STEP 4: EXTRACT ENTITIES AND TRIPLETS CONCURRENTLY =============
            logger.info(f"🏷️ Starting concurrent extraction (Entities + Triplets) for {len(chunks)} chunks...")
            
            import asyncio
            from ...core.triplet_extractor import TripletExtractor
            
            # Feature flag check for triplets
            use_triplets = settings.use_triplet_extraction
            
            # Prepare all extraction tasks
            entity_tasks = [EntityExtractor.extract_entities(chunk_text) for chunk_text in chunks]
            
            triplet_tasks = []
            if use_triplets:
                extractor = TripletExtractor()
                chunk_inputs = [{"chunk_id": f"idx_{i}", "text": chunks[i]} for i in range(len(chunks))]
                triplet_tasks = [extractor.extract_from_chunk(c["chunk_id"], c["text"]) for c in chunk_inputs]
            
            # Run everything in parallel
            all_results = await asyncio.gather(*entity_tasks, *triplet_tasks)
            
            # Split results back
            entity_results = all_results[:len(chunks)]
            triplet_results = all_results[len(chunks):] if use_triplets else []
            
            entities_by_chunk = {}
            all_entities = set()
            
            for i, extracted_entities in enumerate(entity_results):
                # OPTIMIZATION: Cap entities per chunk to 50 to prevent graph noise
                capped_entities = extracted_entities[:50]
                entities_by_chunk[i] = [
                    {"text": e.text, "type": e.entity_type, "confidence": e.confidence}
                    for e in capped_entities
                ]
                for entity in capped_entities:
                    all_entities.add(f"{entity.text}|{entity.entity_type}")

            unique_entity_count = len(all_entities)
            logger.info(f"✅ Extracted {unique_entity_count} unique entities and {sum(len(r.triplets) for r in triplet_results)} triplets in parallel")

            # ============= STEP 5: BATCH CREATE CHUNK NODES IN NEO4J (OPTIMIZED) =============
            logger.info(f"⚡ Batch creating {len(chunks)} chunks in Neo4j...")

            chunk_ids = []
            chunk_data = []

            for i, chunk_text in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                chunk_ids.append(chunk_id)
                token_count = TextChunker.estimate_tokens(chunk_text)

                chunk_data.append(
                    {
                        "chunk_id": chunk_id,
                        "tenant_id": str(self.tenant_id),
                        "kb_id": kb_id,
                        "text": chunk_text[:1000],  # Truncate for storage
                        "position": i,
                        "token_count": token_count,
                        "embedding": embeddings[i],
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )

            try:
                # Batch insert all chunks at once (efficient)
                batch_create_query = """
                WITH $chunks AS chunk_list, $tenant_id AS security_guard
                UNWIND chunk_list AS chunk_data
                CREATE (c:Chunk {
                    id: chunk_data.chunk_id,
                    tenant_id: chunk_data.tenant_id,
                    kb_id: chunk_data.kb_id,
                    text: chunk_data.text,
                    position: chunk_data.position,
                    token_count: chunk_data.token_count,
                    embedding: chunk_data.embedding,
                    created_at: chunk_data.created_at
                })
                WITH c, chunk_data, security_guard
                MATCH (kb:KnowledgeBase {id: chunk_data.kb_id, tenant_id: chunk_data.tenant_id})
                CREATE (kb)-[:HAS_CHUNK]->(c)
                RETURN count(c) as created_count
                """

                result = await retry_neo4j_operation(
                    lambda: self.neo4j_repo.execute_write(
                        batch_create_query,
                        {"chunks": chunk_data},
                    )
                )
                logger.info(f"✅ Batch created {len(chunks)} chunks in Neo4j")

            except Exception as neo4j_error:
                logger.error(f"❌ Neo4j batch chunk creation failed: {neo4j_error}")
                return format_error(
                    f"Failed to create chunks: {neo4j_error}",
                    error_code="NEO4J_ERROR",
                )

            # ============= STEP 6: CREATE CHUNK-[:NEXT] SEQUENTIAL RELATIONSHIPS =============
            logger.info(f"🔗 Batch creating sequential chunk relationships...")
            try:
                next_rel_data = [
                    {"id1": chunk_ids[i], "id2": chunk_ids[i + 1]}
                    for i in range(len(chunk_ids) - 1)
                ]
                
                if next_rel_data:
                    next_query = """
                    WITH $rels AS rel_list
                    UNWIND rel_list AS r
                    MATCH (c1:Chunk {id: r.id1, tenant_id: $tenant_id})
                    MATCH (c2:Chunk {id: r.id2, tenant_id: $tenant_id})
                    CREATE (c1)-[:NEXT]->(c2)
                    """

                    await retry_neo4j_operation(
                        lambda: self.neo4j_repo.execute_write(
                            next_query,
                            {
                                "rels": next_rel_data,
                                "tenant_id": str(self.tenant_id),
                            },
                        )
                    )

                logger.info(f"✅ Created {len(next_rel_data)} NEXT relationships in batch")

            except Exception as e:
                logger.warning(f"⚠️ Failed to create NEXT relationships: {e}")
                # Continue - this is not critical

            # ============= STEP 7: CREATE CHUNK-[:SIMILAR] SEMANTIC RELATIONSHIPS =============
            logger.info(f"🧠 Computing semantic similarities...")

            similar_pairs = []

            # HYBRID SIMILARITY MODE: Choose strategy based on chunk count
            # Phase 2: O(n²) for small KBs (accurate), skip for large KBs (performance)
            # Phase 3: Vector index ANN for large KBs
            use_brute_force = (
                len(embeddings) < settings.similarity_brute_force_threshold
            )

            if use_brute_force:
                logger.info(
                    f"   Using O(n²) brute-force similarity "
                    f"({len(embeddings)} chunks < {settings.similarity_brute_force_threshold} threshold)"
                )
                try:
                    # Compute all pairwise similarities
                    all_similarities = []
                    for i in range(len(embeddings)):
                        for j in range(i + 1, len(embeddings)):
                            similarity = EmbeddingGenerator.cosine_similarity(
                                embeddings[i], embeddings[j]
                            )

                            if similarity >= settings.similarity_min_threshold:
                                all_similarities.append(
                                    {
                                        "chunk_1": i,
                                        "chunk_2": j,
                                        "chunk_id_1": chunk_ids[i],
                                        "chunk_id_2": chunk_ids[j],
                                        "similarity": similarity,
                                    }
                                )

                    # SIMILARITY CAP: Limit to max N similar relationships per chunk
                    # Prevents dense graph, keeps only most relevant connections
                    similarity_by_chunk = {}
                    for sim in sorted(
                        all_similarities, key=lambda x: x["similarity"], reverse=True
                    ):
                        chunk_1_id = sim["chunk_1"]
                        chunk_2_id = sim["chunk_2"]

                        # Count existing edges for both chunks
                        count_1 = similarity_by_chunk.get(chunk_1_id, 0)
                        count_2 = similarity_by_chunk.get(chunk_2_id, 0)

                        # Only add if both haven't hit cap
                        if (
                            count_1 < settings.max_similar_per_chunk
                            and count_2 < settings.max_similar_per_chunk
                        ):
                            similar_pairs.append(
                                {
                                    "chunk_id_1": sim["chunk_id_1"],
                                    "chunk_id_2": sim["chunk_id_2"],
                                    "similarity": sim["similarity"],
                                }
                            )
                            similarity_by_chunk[chunk_1_id] = count_1 + 1
                            similarity_by_chunk[chunk_2_id] = count_2 + 1

                    logger.info(
                        f"✅ Found {len(similar_pairs)} semantically similar pairs "
                        f"(capped at max {settings.max_similar_per_chunk} per chunk)"
                    )

                except Exception as e:
                    logger.warning(f"⚠️ Failed to compute similarities: {e}")
                    # Continue without similarities

            else:
                # Large KB: Skip O(n²) computation, defer to Phase 3 vector index
                logger.info(
                    f"   Skipping O(n²) similarity computation "
                    f"({len(embeddings)} chunks ≥ {settings.similarity_brute_force_threshold} threshold)"
                )
                logger.info(
                    f"   Phase 3: Vector index will enable efficient ANN similarity search"
                )

            # Batch create SIMILAR relationships (if any)
            try:
                if similar_pairs:
                    similar_query = """
                    WITH $pairs AS pair_list
                    UNWIND pair_list AS pair_data
                    MATCH (c1:Chunk {id: pair_data.chunk_id_1, tenant_id: $tenant_id})
                    MATCH (c2:Chunk {id: pair_data.chunk_id_2, tenant_id: $tenant_id})
                    CREATE (c1)-[:SIMILAR {similarity: pair_data.similarity}]->(c2)
                    CREATE (c2)-[:SIMILAR {similarity: pair_data.similarity}]->(c1)
                    RETURN count(*) as created_count
                    """

                    await retry_neo4j_operation(
                        lambda: self.neo4j_repo.execute_write(
                            similar_query,
                            {"pairs": similar_pairs, "tenant_id": str(self.tenant_id)},
                        )
                    )
                    logger.info(
                        f"✅ Created {len(similar_pairs) * 2} SIMILAR relationships (bidirectional)"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Failed to create SIMILAR relationships: {e}")
                # Continue - semantic relationships are important but not blocking

            # ============= STEP 8: CREATE ENTITIES AND CHUNK-[:MENTIONS]->ENTITY LINKS =============
            logger.info(f"🏷️ Creating entity nodes and relationships...")
            try:
                # Batch create entities with mentions
                entity_relationships = []
                for chunk_idx, entities in entities_by_chunk.items():
                    chunk_id = chunk_ids[chunk_idx]
                    for entity in entities:
                        entity_relationships.append(
                            {
                                "chunk_id": chunk_id,
                                "entity_text": entity["text"],
                                "entity_type": entity["type"],
                                "confidence": entity["confidence"],
                            }
                        )

                if entity_relationships:
                    entity_query = """
                    WITH $relationships AS rel_list
                    WITH rel_list, $tenant_id AS tenant_id
                    UNWIND rel_list AS rel_data
                    MERGE (e:Entity {
                        tenant_id: tenant_id,
                        text: rel_data.entity_text,
                        type: rel_data.entity_type
                    })
                    WITH e, rel_data, tenant_id
                    MATCH (c:Chunk {id: rel_data.chunk_id, tenant_id: tenant_id})
                    CREATE (c)-[:MENTIONS {confidence: rel_data.confidence}]->(e)
                    RETURN count(*) as mentions_count
                    """

                    await retry_neo4j_operation(
                        lambda: self.neo4j_repo.execute_write(
                            entity_query,
                            {
                                "relationships": entity_relationships,
                                "tenant_id": str(self.tenant_id),
                            },
                        )
                    )
                    logger.info(
                        f"✅ Created {len(entity_relationships)} MENTIONS relationships"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Failed to create entity relationships: {e}")
                # Continue - entity linking is valuable but not blocking

            # ============= STEP 9: VALIDATE GRAPH INTEGRITY =============
            logger.info(f"✓ Validating graph integrity...")
            validation_result = await self._validate_graph_integrity(kb_id)
            if not validation_result["success"]:
                logger.warning(
                    f"⚠️ Graph validation issues: {validation_result['issues']}"
                )
            else:
                logger.info(f"✅ Graph integrity validated")

            # ============= STEP 10: TRIPLET PERSISTENCE (Phase 4A) =============
            triplet_stats = {"triplets_extracted": 0, "triplet_entities": 0, "triplet_relationships": 0}
            if use_triplets and triplet_results:
                try:
                    logger.info("🧩 Phase 4A: Triplet persistence starting...")
                    from ...core.triplet_extractor import TripletGraphWriter
                    
                    # Update triplet results with real chunk IDs (since they were extracted with temporary indices)
                    for i, res in enumerate(triplet_results):
                        res.chunk_id = chunk_ids[i]

                    writer = TripletGraphWriter(str(self.tenant_id))
                    persist_result = await writer.persist_triplets(triplet_results)
                    
                    triplet_stats = {
                        "triplets_extracted": persist_result.get("triplets_created", 0),
                        "triplet_entities": persist_result.get("entities_created", 0),
                        "triplet_relationships": persist_result.get("relationships_created", 0),
                    }
                except Exception as triplet_error:
                    logger.warning(f"⚠️ Triplet persistence failed: {triplet_error}")

            # ============= STEP 11: UPDATE KB METADATA =============
            await self.repository.increment_chunks(kb_id, len(chunks))
            await self.db.commit()

            # ============= AUDIT LOG =============
            await KBauditLog.log_event(
                tenant_id=str(self.tenant_id),
                user_id=str(kb.user_id),
                kb_id=kb_id,
                event_type=KBauditEventType.KB_DOCUMENT_INGESTED,
                details={
                    "chunks_created": len(chunks),
                    "embeddings_generated": len(embeddings),
                    "entities_extracted": unique_entity_count,
                    "similar_relationships": len(similar_pairs),
                    "document_length": len(document_text),
                    **triplet_stats,
                },
            )

            return format_success(
                {
                    "kb_id": kb_id,
                    "chunks_created": len(chunks),
                    "embeddings_generated": len(embeddings),
                    "entities_extracted": unique_entity_count,
                    "similar_relationships": len(similar_pairs),
                    **triplet_stats,
                },
                meta={"message": f"Ingested {len(chunks)} chunks with RAG intelligence"},
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Document ingestion failed: {e}")
            return format_error(f"Failed to ingest document: {str(e)}")

    async def get_kb(self, kb_id: str) -> dict:
        """
        Get KB by ID (PostgreSQL only).

        Args:
            kb_id: KB UUID

        Returns:
            Dict with success, KB, or error
        """
        try:
            kb = await self.repository.get_by_id(kb_id)

            if not kb:
                return format_error(f"KB not found: {kb_id}", meta={"status_code": 404})

            return format_success(
                {"kb": schemas.KBResponse.model_validate(kb, from_attributes=True)}
            )

        except Exception as e:
            logger.error(f"Failed to get KB: {e}")
            return format_error(f"Failed to retrieve KB: {str(e)}")

    async def list_kbs(self, limit: int = 50, offset: int = 0) -> dict:
        """
        List all KBs for tenant (active only).

        Args:
            limit: Max results
            offset: Pagination offset

        Returns:
            Dict with KBs list, count, or error
        """
        try:
            kbs, total = await self.repository.list_kbs(limit=limit, offset=offset)

            return format_success(
                {
                    "kbs": [
                        schemas.KBResponse.model_validate(kb, from_attributes=True)
                        for kb in kbs
                    ],
                    "count": len(kbs),
                    "total": total,
                }
            )

        except Exception as e:
            logger.error(f"Failed to list KBs: {e}")
            return format_error(f"Failed to list KBs: {str(e)}")

    async def list_kbs_by_agent(
        self, agent_id: str, limit: int = 50, offset: int = 0
    ) -> dict:
        """
        List KBs for specific agent (within tenant).

        Args:
            agent_id: Agent UUID
            limit: Max results
            offset: Pagination offset

        Returns:
            Dict with KBs list, count, or error
        """
        try:
            kbs, total = await self.repository.list_by_agent(
                agent_id, limit=limit, offset=offset
            )

            return format_success(
                {
                    "kbs": [
                        schemas.KBResponse.model_validate(kb, from_attributes=True)
                        for kb in kbs
                    ],
                    "count": len(kbs),
                    "total": total,
                }
            )

        except Exception as e:
            logger.error(f"Failed to list agent KBs: {e}")
            return format_error(f"Failed to list KBs: {str(e)}")

    async def delete_kb(self, kb_id: str) -> dict:
        """
        Delete KB from BOTH PostgreSQL and Neo4j.

        CRITICAL DELETE ORDER (Neo4j FIRST):
        1. Neo4j DELETE KB + cascade chunks
        2. PostgreSQL soft-delete (only if Neo4j succeeds)

        Args:
            kb_id: KB UUID

        Returns:
            Dict with success or error
        """
        try:
            # ============= STEP 1: NEO4J DELETE FIRST =============
            delete_query = """
            MATCH (kb:KnowledgeBase {tenant_id: $tenant_id, id: $kb_id})
            OPTIONAL MATCH (kb)-[:HAS_CHUNK]->(c:Chunk {tenant_id: $tenant_id})
            DETACH DELETE kb, c
            RETURN count(kb)
            """

            try:
                await retry_neo4j_operation(
                    lambda: self.neo4j_repo.execute_write(
                        delete_query,
                        {"kb_id": kb_id, "tenant_id": str(self.tenant_id)},
                    )
                )
                logger.info(f"✅ Neo4j: Deleted KB {kb_id} + chunks cascade")

            except Exception as neo4j_error:
                logger.error(f"❌ Neo4j deletion failed: {neo4j_error}")
                return format_error(
                    f"Failed to delete KB from graph: {neo4j_error}",
                    meta={"error_code": "NEO4J_ERROR"},
                )

            # ============= STEP 2: POSTGRES SOFT-DELETE (AFTER NEO4J SUCCESS) =============
            deleted = await self.repository.soft_delete(kb_id)

            if not deleted:
                logger.warning(f"⚠️ KB not found in PostgreSQL: {kb_id}")
                await self.db.commit()
                return format_error(f"KB not found: {kb_id}", meta={"status_code": 404})

            await self.db.commit()
            logger.info(f"✅ COMMITTED: KB {kb_id} soft-deleted from PostgreSQL")

            # ============= AUDIT LOG =============
            await KBauditLog.log_event(
                tenant_id=str(self.tenant_id),
                user_id="unknown",  # User info not available in delete context
                kb_id=kb_id,
                event_type=KBauditEventType.KB_DELETED,
                details={"deleted_at": datetime.utcnow().isoformat()},
            )

            return format_success(
                {"id": kb_id},
                meta={"message": "Knowledge Base deleted successfully"},
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ KB deletion failed: {e}")
            return format_error(f"Failed to delete KB: {str(e)}")

    async def _validate_graph_integrity(self, kb_id: str) -> dict:
        """
        Validate graph integrity after ingestion.

        CHECKS:
        1. All chunks have tenant_id
        2. All chunks linked to KB
        3. No orphaned entities
        4. Embeddings are valid vectors
        5. Token counts are reasonable

        Args:
            kb_id: KB UUID to validate

        Returns:
            Dict with success, issues (if any)
        """
        issues = []

        try:
            # Check 1: All chunks have tenant_id
            check1_query = """
            MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})-[:HAS_CHUNK]->(c:Chunk)
            WHERE c.tenant_id IS NULL
            RETURN count(c) as missing_tenant
            """
            result = await self.neo4j_repo.execute_read(
                check1_query,
                {"kb_id": kb_id, "tenant_id": str(self.tenant_id)},
            )
            if result and result[0]["missing_tenant"] > 0:
                issues.append(
                    f"Found {result[0]['missing_tenant']} chunks without tenant_id (RLS violation!)"
                )

            # Check 2: All chunks linked to KB
            check2_query = """
            MATCH (c:Chunk {kb_id: $kb_id, tenant_id: $tenant_id})
            WHERE NOT ((:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})-[:HAS_CHUNK]->(c))
            RETURN count(c) as unlinked_chunks
            """
            result = await self.neo4j_repo.execute_read(
                check2_query,
                {"kb_id": kb_id, "tenant_id": str(self.tenant_id)},
            )
            if result and result[0]["unlinked_chunks"] > 0:
                issues.append(
                    f"Found {result[0]['unlinked_chunks']} chunks not linked to KB"
                )

            # Check 3: Embeddings are valid (not all zeros, right dimension)
            check3_query = """
            MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})-[:HAS_CHUNK]->(c:Chunk)
            WHERE c.embedding IS NULL OR size(c.embedding) <> $embedding_dimension
            RETURN count(c) as invalid_embeddings
            """
            result = await self.neo4j_repo.execute_read(
                check3_query,
                {
                    "kb_id": kb_id,
                    "tenant_id": str(self.tenant_id),
                    "embedding_dimension": settings.embedding_dimension,
                },
            )
            if result and result[0]["invalid_embeddings"] > 0:
                issues.append(
                    f"Found {result[0]['invalid_embeddings']} chunks with invalid embeddings"
                )

            # Check 4: Token counts are reasonable
            check4_query = """
            MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})-[:HAS_CHUNK]->(c:Chunk)
            WHERE c.token_count IS NULL OR c.token_count <= 0
            RETURN count(c) as invalid_tokens
            """
            result = await self.neo4j_repo.execute_read(
                check4_query,
                {"kb_id": kb_id, "tenant_id": str(self.tenant_id)},
            )
            if result and result[0]["invalid_tokens"] > 0:
                issues.append(
                    f"Found {result[0]['invalid_tokens']} chunks with invalid token counts"
                )

            if issues:
                logger.warning(f"⚠️ Graph validation issues for KB {kb_id}: {issues}")
                return {"success": False, "issues": issues}
            else:
                logger.info(f"✅ Graph integrity validated for KB {kb_id}")
                return {"success": True, "issues": []}

        except Exception as e:
            logger.warning(f"⚠️ Graph validation error: {e}")
            return {"success": False, "issues": [str(e)]}
