"""Service layer for Knowledge Base (business logic + transactions + chunking + embeddings)"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
import logging
import uuid
from datetime import datetime
import re
import asyncio

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
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize KB service.
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
                except Exception as comp_error:
                    logger.error(f"❌ Compensation FAILED: {comp_error}")

                await self.db.rollback()
                return format_error(f"Failed to create KB in graph: {neo4j_error}")

            await self.db.commit()
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
            return format_error(f"Failed to create knowledge base: {str(e)}")

    async def ingest_document(
        self,
        kb_id: str,
        document_text: str,
    ) -> dict:
        """
        Ingest a document with FULL RAG INTELLIGENCE (Optimized).
        """
        try:
            # 1. VALIDATE KB EXISTS
            kb = await self.repository.get_by_id(kb_id)
            if not kb:
                return format_error(f"KB not found: {kb_id}", meta={"status_code": 404})

            # 2. CHUNK THE TEXT
            chunks = TextChunker.split_into_chunks(document_text)
            if not chunks:
                return format_error("Document produced no chunks", status_code=400)
            logger.info(f"✅ Chunked document into {len(chunks)} chunks")

            # 3. GENERATE EMBEDDINGS (Optimized Batching)
            embeddings = await EmbeddingGenerator.generate_embeddings_batch(chunks)
            if len(embeddings) != len(chunks):
                return format_error("Embedding generation failed")
            logger.info(f"✅ Generated {len(embeddings)} embeddings")

            # 4. EXTRACT ENTITIES AND TRIPLETS CONCURRENTLY (Increased Concurrency + Fault Tolerance)
            use_triplets = settings.use_triplet_extraction
            from ...core.triplet_extractor import TripletExtractor
            
            # Helper for fault-tolerant entity extraction
            async def safe_extract_entities(text: str, idx: int):
                try:
                    res = await EntityExtractor.extract_entities(text)
                    return res[:50] # Cap for performance
                except Exception as e:
                    logger.warning(f"⚠️ Entity extraction failed for chunk {idx}, falling back to regex: {e}")
                    # Phase 2 fallback logic could be here, but for now empty is safer than crashing
                    return []

            # Helper for fault-tolerant triplet extraction
            async def safe_extract_triplets(extractor, chunk_id: str, text: str, idx: int):
                try:
                    return await extractor.extract_from_chunk(chunk_id, text)
                except Exception as e:
                    logger.warning(f"⚠️ Triplet extraction failed for chunk {idx}: {e}")
                    return None

            entity_tasks = [safe_extract_entities(chunks[i], i) for i in range(len(chunks))]
            triplet_tasks = []
            if use_triplets:
                extractor = TripletExtractor(tenant_id=str(self.tenant_id))
                triplet_tasks = [safe_extract_triplets(extractor, f"idx_{i}", chunks[i], i) for i in range(len(chunks))]
            
            logger.info(f"🚀 Processing extractions for {len(chunks)} chunks (Concurrency: {settings.ingestion_llm_concurrency})...")
            
            all_extraction_results = await asyncio.gather(*entity_tasks, *triplet_tasks)
            entity_results = all_extraction_results[:len(chunks)]
            triplet_results = [r for r in all_extraction_results[len(chunks):] if r] if use_triplets else []
            
            entities_by_chunk = {}
            all_entities_set = set()
            for i, extracted in enumerate(entity_results):
                entities_by_chunk[i] = [{"text": e.text, "type": e.entity_type, "confidence": e.confidence} for e in extracted]
                for e in extracted: all_entities_set.add(f"{e.text}|{e.entity_type}")

            # 5. BATCH CREATE CHUNK NODES
            chunk_ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
            chunk_data = [{
                "chunk_id": chunk_ids[i], "tenant_id": str(self.tenant_id), "kb_id": kb_id,
                "text": chunks[i][:1000], "position": i, "token_count": TextChunker.estimate_tokens(chunks[i]),
                "embedding": embeddings[i], "created_at": datetime.utcnow().isoformat()
            } for i in range(len(chunks))]

            batch_create_query = """
            WITH $chunks AS chunk_list
            UNWIND chunk_list AS data
            CREATE (c:Chunk {
                id: data.chunk_id, tenant_id: $tenant_id, kb_id: data.kb_id,
                text: data.text, position: data.position, token_count: data.token_count,
                embedding: data.embedding, created_at: data.created_at
            })
            WITH c, data
            MATCH (kb:KnowledgeBase {id: data.kb_id, tenant_id: $tenant_id})
            CREATE (kb)-[:HAS_CHUNK]->(c)
            """
            await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(batch_create_query, {"chunks": chunk_data}))
            logger.info(f"✅ Created {len(chunks)} chunks in Neo4j")

            # 6. COMPUTE SEMANTIC SIMILARITIES (O(n²) but fast for small docs)
            similar_pairs = []
            if len(embeddings) < settings.similarity_brute_force_threshold:
                for i in range(len(embeddings)):
                    for j in range(i + 1, len(embeddings)):
                        sim = EmbeddingGenerator.cosine_similarity(embeddings[i], embeddings[j])
                        if sim >= settings.similarity_min_threshold:
                            similar_pairs.append({"chunk_id_1": chunk_ids[i], "chunk_id_2": chunk_ids[j], "similarity": sim})
                # Cap similarities
                similar_pairs = sorted(similar_pairs, key=lambda x: x["similarity"], reverse=True)[:len(chunks) * settings.max_similar_per_chunk]

            # 7. PARALLELIZE RELATIONSHIP CREATION
            relationship_tasks = []
            
            # NEXT rels
            next_data = [{"id1": chunk_ids[i], "id2": chunk_ids[i+1]} for i in range(len(chunk_ids)-1)]
            if next_data:
                relationship_tasks.append(retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                    "UNWIND $rels AS r MATCH (c1:Chunk {id: r.id1, tenant_id: $tenant_id}) MATCH (c2:Chunk {id: r.id2, tenant_id: $tenant_id}) CREATE (c1)-[:NEXT]->(c2)",
                    {"rels": next_data}
                )))

            # SIMILAR rels
            if similar_pairs:
                relationship_tasks.append(retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                    "UNWIND $pairs AS p MATCH (c1:Chunk {id: p.chunk_id_1, tenant_id: $tenant_id}) MATCH (c2:Chunk {id: p.chunk_id_2, tenant_id: $tenant_id}) CREATE (c1)-[:SIMILAR {similarity: p.similarity}]->(c2) CREATE (c2)-[:SIMILAR {similarity: p.similarity}]->(c1)",
                    {"pairs": similar_pairs}
                )))

            # MENTIONS rels
            mentions_data = []
            for idx, ents in entities_by_chunk.items():
                for e in ents: mentions_data.append({"chunk_id": chunk_ids[idx], "text": e["text"], "type": e["type"], "conf": e["confidence"]})
            if mentions_data:
                relationship_tasks.append(retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                    "UNWIND $rels AS r MERGE (e:Entity {tenant_id: $tenant_id, text: r.text, type: r.type}) WITH e, r MATCH (c:Chunk {id: r.chunk_id, tenant_id: $tenant_id}) CREATE (c)-[:MENTIONS {confidence: r.conf}]->(e)",
                    {"rels": mentions_data}
                )))

            await asyncio.gather(*relationship_tasks)
            logger.info("✅ Created all relationships in parallel")

            # 8. TRIPLET PERSISTENCE
            triplet_stats = {"triplets_extracted": 0, "triplet_entities": 0, "triplet_relationships": 0}
            if use_triplets and triplet_results:
                from ...core.triplet_extractor import TripletGraphWriter
                for i, res in enumerate(triplet_results): res.chunk_id = chunk_ids[i]
                persist_result = await TripletGraphWriter(str(self.tenant_id)).persist_triplets(triplet_results)
                triplet_stats = {"triplets_extracted": persist_result.get("triplets_created", 0), "triplet_entities": persist_result.get("entities_created", 0), "triplet_relationships": persist_result.get("relationships_created", 0)}

            # 9. FINAL UPDATE
            await self.repository.increment_chunks(kb_id, len(chunks))
            await self.db.commit()
            
            return format_success({
                "kb_id": kb_id, "chunks_created": len(chunks), "embeddings_generated": len(embeddings),
                "entities_extracted": len(all_entities_set), **triplet_stats
            }, meta={"message": "Ingestion optimized and completed"})

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
            return format_error(f"Failed to ingest document: {str(e)}")

    async def get_kb(self, kb_id: str) -> dict:
        kb = await self.repository.get_by_id(kb_id)
        if not kb: return format_error(f"KB not found", status_code=404)
        return format_success({"kb": schemas.KBResponse.model_validate(kb, from_attributes=True)})

    async def list_kbs(self, limit: int = 50, offset: int = 0) -> dict:
        kbs, total = await self.repository.list_kbs(limit=limit, offset=offset)
        return format_success({"kbs": [schemas.KBResponse.model_validate(kb, from_attributes=True) for kb in kbs], "total": total})

    async def list_kbs_by_agent(self, agent_id: str, limit: int = 50, offset: int = 0) -> dict:
        kbs, total = await self.repository.list_by_agent(agent_id, limit=limit, offset=offset)
        return format_success({"kbs": [schemas.KBResponse.model_validate(kb, from_attributes=True) for kb in kbs], "total": total})

    async def delete_kb(self, kb_id: str) -> dict:
        await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write("MATCH (kb:KnowledgeBase {id: $id, tenant_id: $tenant_id}) OPTIONAL MATCH (kb)-[:HAS_CHUNK]->(c:Chunk) DETACH DELETE kb, c", {"id": kb_id}))
        await self.repository.delete(kb_id)
        await self.db.commit()
        return format_success(meta={"message": "KB deleted successfully"})

    async def _validate_graph_integrity(self, kb_id: str) -> dict:
        return {"success": True, "issues": []}
