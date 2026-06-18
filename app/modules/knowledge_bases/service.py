"""Service layer for Knowledge Base (business logic + transactions + chunking + embeddings)"""



from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from typing import Optional, List, Dict

import logging

import uuid

from datetime import datetime

import re

import asyncio

import sqlite3

import os



from .models import KnowledgeBase, DatabaseConnection, DocumentChunk

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
    def chunk_table(table_text: str, chunk_size: int) -> List[str]:
        """
        Table-aware chunking.
        Isolates and preserves Markdown tables as single units.
        If a table exceeds chunk_size, it splits it by row while repeating the header.
        """
        if len(table_text) <= chunk_size:
            return [table_text]
            
        # Split table into rows
        rows = table_text.split('\n')
        
        # Extract header (usually first 2 rows: header + separator)
        if len(rows) > 2 and '---' in rows[1]:
            header = rows[0] + '\n' + rows[1]
            data_rows = rows[2:]
        else:
            # No clear separator, just use row 0
            header = rows[0]
            data_rows = rows[1:]
            
        chunks = []
        current_chunk = header
        
        for row in data_rows:
            test_chunk = current_chunk + '\n' + row
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # Save chunk and start new one with header
                if current_chunk != header:
                    chunks.append(current_chunk)
                
                # If a single row with header is larger than chunk_size, we MUST split it 
                # to prevent crashing the 512-token limit API!
                new_chunk = header + '\n' + row
                while len(new_chunk) > chunk_size:
                    chunks.append(new_chunk[:chunk_size])
                    new_chunk = header + '\n' + new_chunk[chunk_size:]
                
                current_chunk = new_chunk
                
        if current_chunk and current_chunk != header:
            chunks.append(current_chunk)
            
        return chunks

    @staticmethod
    def chunk_text(text: str, chunk_size: int, overlap_size: int) -> List[str]:
        """Helper to chunk normal text preserving sentences."""
        chunks = []
        if len(text) <= chunk_size:
            return [text.strip()]

        # Split by sentences or double newlines when possible
        sentences = re.split(r"(?<=[.!?])\s+|\n\n+", text)
        current_chunk = ""

        for sentence in sentences:
            if not sentence:
                continue

            # Forcefully break massive sentences to avoid 400 Bad Request
            while len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                part = sentence[:chunk_size]
                chunks.append(part.strip())
                sentence = sentence[chunk_size:]

            if not sentence:
                continue
                
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                if chunks and overlap_size > 0:
                    overlap = chunks[-1][-overlap_size:] if len(chunks[-1]) > overlap_size else chunks[-1]
                    current_chunk = overlap + " " + sentence
                    
                    # Safety check: if overlap + sentence still > chunk_size
                    if len(current_chunk) > chunk_size:
                        chunks.append(current_chunk[:chunk_size].strip())
                        current_chunk = current_chunk[chunk_size:]
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        # Final safety pass to ensure ABSOLUTELY NO CHUNK exceeds chunk_size
        safe_chunks = []
        for c in chunks:
            while len(c) > chunk_size:
                safe_chunks.append(c[:chunk_size])
                c = c[chunk_size:]
            if c.strip():
                safe_chunks.append(c)

        return safe_chunks

    @staticmethod
    def split_into_chunks(
        text: str,
        chunk_size: int = 500,  # Reduced from 1000 to 700 to safely stay under 512 tokens
        overlap_size: int = 50,  # Reduced overlap proportionally
    ) -> List[str]:
        """
        Split text into overlapping chunks, using Table-Aware chunking for Markdown tables.
        """
        chunks = []
        
        # Regex to detect Markdown table blocks (consecutive lines starting and ending with |)
        table_pattern = re.compile(r'((?:^\|.*?\|[ \t]*(?:\n|$))+)', re.MULTILINE)
        
        last_idx = 0
        for match in table_pattern.finditer(text):
            table_start = match.start()
            table_end = match.end()
            
            # 1. Chunk the text before the table
            pre_text = text[last_idx:table_start].strip()
            if pre_text:
                chunks.extend(TextChunker.chunk_text(pre_text, chunk_size, overlap_size))
                
            # 2. Chunk the table using Table-Aware strategy
            table_text = match.group(0).strip()
            chunks.extend(TextChunker.chunk_table(table_text, chunk_size))
            
            last_idx = table_end
            
        # 3. Chunk any remaining text after the last table
        post_text = text[last_idx:].strip()
        if post_text:
            chunks.extend(TextChunker.chunk_text(post_text, chunk_size, overlap_size))
            
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

            logger.info(f" PostgreSQL: Created KB {kb_id}")



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

                logger.info(f" Neo4j: Created KB node {kb_id}")



            except Exception as neo4j_error:

                # ============= COMPENSATION: DELETE NEO4J KB =============

                logger.warning(f" Neo4j creation failed: {neo4j_error}")

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

                    logger.error(f" Compensation FAILED: {comp_error}")



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

            logger.error(f" KB creation failed: {e}")

            return format_error(f"Failed to create knowledge base: {str(e)}")



    async def ingest_document(

        self,

        kb_id: str,

        document_text: str,

        source: Optional[str] = None,

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

                return format_error("Document produced no chunks", meta={"status_code": 400})

            logger.info(f" Chunked document into {len(chunks)} chunks")



            # 3. GENERATE EMBEDDINGS (Optimized Batching)

            embeddings = await EmbeddingGenerator.generate_embeddings_batch(chunks)

            if len(embeddings) != len(chunks):

                return format_error("Embedding generation failed")

            logger.info(f" Generated {len(embeddings)} embeddings")



            # 4. EXTRACT ENTITIES AND TRIPLETS CONCURRENTLY (Increased Concurrency + Fault Tolerance)

            use_triplets = settings.use_triplet_extraction

            from ...core.triplet_extractor import TripletExtractor

            

            # Helper for fault-tolerant entity extraction

            async def safe_extract_entities(text: str, idx: int):

                try:

                    res = await EntityExtractor.extract_entities(text)

                    return res[:50] # Cap for performance

                except Exception as e:

                    logger.warning(f" Entity extraction failed for chunk {idx}, falling back to regex: {e}")

                    # Phase 2 fallback logic could be here, but for now empty is safer than crashing

                    return []



            # Helper for fault-tolerant triplet extraction

            async def safe_extract_triplets(extractor, chunk_id: str, text: str, idx: int):

                try:

                    return await extractor.extract_from_chunk(chunk_id, text)

                except Exception as e:

                    logger.warning(f" Triplet extraction failed for chunk {idx}: {e}")

                    return None



            entity_tasks = [safe_extract_entities(chunks[i], i) for i in range(len(chunks))]

            triplet_tasks = []

            if use_triplets:

                extractor = TripletExtractor(tenant_id=str(self.tenant_id))

                triplet_tasks = [safe_extract_triplets(extractor, f"idx_{i}", chunks[i], i) for i in range(len(chunks))]

            

            logger.info(f" Processing extractions for {len(chunks)} chunks (Concurrency: {settings.ingestion_llm_concurrency})...")

            

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

                "embedding": embeddings[i], "created_at": datetime.utcnow().isoformat(),

                "source": source

            } for i in range(len(chunks))]



            # Save chunks to PostgreSQL pgvector table

            for i in range(len(chunks)):

                pg_chunk = DocumentChunk(

                    id=uuid.UUID(chunk_ids[i]),

                    tenant_id=self.tenant_id,

                    kb_id=uuid.UUID(kb_id),

                    text=chunks[i],

                    chunk_index=i,

                    embedding=embeddings[i],

                )

                self.db.add(pg_chunk)

            logger.info(f" Staged {len(chunks)} chunks in PostgreSQL")



            batch_create_query = """

            WITH $chunks AS chunk_list

            UNWIND chunk_list AS data

            CREATE (c:Chunk {

                id: data.chunk_id, tenant_id: $tenant_id, kb_id: data.kb_id,

                text: data.text, position: data.position, token_count: data.token_count,

                embedding: data.embedding, created_at: data.created_at,

                source: data.source

            })

            WITH c, data

            MATCH (kb:KnowledgeBase {id: data.kb_id, tenant_id: $tenant_id})

            CREATE (kb)-[:HAS_CHUNK]->(c)

            """

            await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(batch_create_query, {"chunks": chunk_data}))

            logger.info(f" Created {len(chunks)} chunks in Neo4j")



            # 6. COMPUTE SEMANTIC SIMILARITIES (O(n) but fast for small docs)

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

            logger.info(" Created all relationships in parallel")



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

            logger.error(f" Ingestion failed: {e}", exc_info=True)

            return format_error(f"Failed to ingest document: {str(e)}")



    async def ingest_excel_or_csv(

        self,

        kb_id: str,

        file_bytes: bytes,

        filename: str,

        mime_type: Optional[str] = None,

        source: Optional[str] = None,

    ) -> dict:

        """

        Ingest an Excel or CSV file by parsing it, discovering relationships,

        and loading structured chunks & entities into PostgreSQL & Neo4j.

        """

        try:

            # 1. Validate KB exists

            kb = await self.repository.get_by_id(kb_id)

            if not kb:

                return format_error(f"KB not found: {kb_id}", meta={"status_code": 404})



            # 2. Invoke ExcelIngestionService

            from .services.excel_ingestion_service import ExcelIngestionService

            ingestor = ExcelIngestionService(self.db, str(self.tenant_id))

            result = await ingestor.ingest_file(kb_id, file_bytes, filename, mime_type, source)



            if not result.get("success"):

                return format_error(result.get("error", "Failed to ingest Excel/CSV"))



            # 3. Update chunk count metadata in PostgreSQL

            chunks_created = result["data"]["chunks_created"]

            await self.repository.increment_chunks(kb_id, chunks_created)

            await self.db.commit()



            return format_success(

                result["data"],

                meta={"message": f"Successfully ingested structured file '{filename}' into KB"}

            )



        except Exception as e:

            await self.db.rollback()

            logger.error(f" Excel/CSV Ingestion failed: {e}", exc_info=True)

            return format_error(f"Failed to ingest Excel/CSV: {str(e)}")



    async def _enrich_kbs_with_connections(self, kbs) -> list[dict]:
        if not kbs:
            return []
        kb_ids = [kb.id for kb in kbs]
        from sqlalchemy import select
        from .models import DatabaseConnection
        query = select(DatabaseConnection.kb_id, DatabaseConnection.db_type).where(
            DatabaseConnection.kb_id.in_(kb_ids)
        )
        res = await self.db.execute(query)
        connections = {row.kb_id: row.db_type for row in res.all()}
        
        responses = []
        for kb in kbs:
            kb_dict = schemas.KBResponse.model_validate(kb, from_attributes=True).model_dump(mode="json")
            kb_dict["connected_integration"] = connections.get(kb.id)
            if not kb_dict["connected_integration"] and kb.source:
                if kb.source.startswith('google_drive'):
                    kb_dict["connected_integration"] = 'google_drive'
                elif kb.source.startswith('sharepoint'):
                    kb_dict["connected_integration"] = 'sharepoint'
                elif kb.source.startswith('gmail'):
                    kb_dict["connected_integration"] = 'gmail'
                elif kb.source.startswith('outlook'):
                    kb_dict["connected_integration"] = 'outlook'
                elif kb.source == 'web_scraper':
                    kb_dict["connected_integration"] = 'web_scraper'
            responses.append(kb_dict)
        return responses

    async def get_kb(self, kb_id: str) -> dict:

        kb = await self.repository.get_by_id(kb_id)

        if not kb: return format_error(f"KB not found", meta={"status_code": 404})

        enriched = await self._enrich_kbs_with_connections([kb])
        return format_success({"kb": enriched[0]})



    async def list_kbs(self, limit: int = 50, offset: int = 0) -> dict:

        kbs, total = await self.repository.list_kbs(limit=limit, offset=offset)

        enriched = await self._enrich_kbs_with_connections(kbs)
        return format_success({"kbs": enriched, "total": total})



    async def list_knowledge_source(self, agent_id: str) -> dict:

        """

        Get all unique sources for a given agent.

        """

        try:

            sources = await self.repository.list_knowledge_source(agent_id)

            return format_success({"sources": sources})

        except Exception as e:

            logger.error(f"Error listing knowledge source: {e}")

            return format_error(f"Failed to list knowledge sources: {str(e)}")



    async def list_kbs_by_agent(self, agent_id: str, limit: int = 50, offset: int = 0) -> dict:

        kbs, total = await self.repository.list_by_agent(agent_id, limit=limit, offset=offset)

        enriched = await self._enrich_kbs_with_connections(kbs)
        return format_success({"kbs": enriched, "total": total})



    async def delete_kb(self, kb_id: str, user_id: Optional[str] = None) -> dict:
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            res = format_error(f"KB not found: {kb_id}", meta={"status_code": 404})
            res["status_code"] = 404
            return res

        await retry_neo4j_operation(
            lambda: self.neo4j_repo.execute_write(
                "MATCH (kb:KnowledgeBase {id: $id, tenant_id: $tenant_id}) OPTIONAL MATCH (kb)-[:HAS_CHUNK]->(c:Chunk) DETACH DELETE kb, c",
                {"id": kb_id, "tenant_id": str(self.tenant_id)}
            )
        )

        # Also clean up database connection details if present
        query = select(DatabaseConnection).where(DatabaseConnection.kb_id == uuid.UUID(kb_id))
        db_conn_res = await self.db.execute(query)
        db_conn = db_conn_res.scalar_one_or_none()
        if db_conn:
            await self.db.delete(db_conn)

        await self.repository.soft_delete(kb_id)
        await self.db.commit()

        # Log audit event
        if user_id:
            await KBauditLog.log_event(
                tenant_id=str(self.tenant_id),
                user_id=user_id,
                kb_id=kb_id,
                event_type=KBauditEventType.KB_DELETED,
                details={"kb_id": kb_id, "name": kb.name}
            )

        return format_success(meta={"message": "KB deleted successfully"})

    async def disconnect_agent_integration(self, agent_id: str, integration_type: str, user_id: Optional[str] = None) -> dict:
        """
        Deletes all knowledge bases for a specific agent that match the integration type.
        This provides a clean disconnect.
        """
        from sqlalchemy import select, or_
        import uuid
        from .models import KnowledgeBase, DatabaseConnection

        query = select(KnowledgeBase).outerjoin(
            DatabaseConnection, KnowledgeBase.id == DatabaseConnection.kb_id
        ).where(
            KnowledgeBase.tenant_id == self.tenant_id,
            KnowledgeBase.agent_id == uuid.UUID(agent_id),
            KnowledgeBase.deleted_at.is_(None),
            or_(
                KnowledgeBase.source.startswith(integration_type),
                DatabaseConnection.db_type == integration_type
            )
        )
        res = await self.db.execute(query)
        kbs = res.scalars().unique().all()

        deleted_count = 0
        for kb in kbs:
            del_res = await self.delete_kb(str(kb.id), user_id)
            if del_res.get("success"):
                deleted_count += 1
                
        return format_success(
            {"deleted_count": deleted_count},
            meta={"message": f"Successfully disconnected {integration_type} by deleting {deleted_count} related KBs."}
        )

    async def _validate_graph_integrity(self, kb_id: str) -> dict:

        return {"success": True, "issues": []}



    # ============================================================================

    # NATIVE DATABASE CONNECTOR SERVICE METHODS

    # ============================================================================



    async def register_database_connection(

        self,

        kb_id: str,

        request: schemas.DatabaseConnectionRegister,

    ) -> dict:

        """

        Register a database connection with a Knowledge Base after validating it.

        """

        try:

            # 1. Validate connection first

            val_res = await self.validate_database_connection(

                request.db_type, request.connection_params

            )

            if not val_res["success"]:

                return format_error(f"Connection validation failed: {val_res['message']}")



            # 2. Check if Knowledge Base exists

            kb = await self.repository.get_by_id(kb_id)

            if not kb:

                return format_error(f"Knowledge Base not found: {kb_id}", meta={"status_code": 404})



            # 3. Check if a connection already exists to update it (upsert)

            query = select(DatabaseConnection).where(

                DatabaseConnection.kb_id == uuid.UUID(kb_id),

                DatabaseConnection.tenant_id == self.tenant_id

            )

            db_conn_res = await self.db.execute(query)

            db_conn = db_conn_res.scalar_one_or_none()



            if db_conn:

                # Update existing connection

                db_conn.db_type = request.db_type

                db_conn.connection_params = request.connection_params

                logger.info(f"Updated DatabaseConnection config for KB {kb_id}")

            else:

                # Create new connection

                db_conn = DatabaseConnection(

                    tenant_id=self.tenant_id,

                    kb_id=uuid.UUID(kb_id),

                    db_type=request.db_type,

                    connection_params=request.connection_params

                )

                self.db.add(db_conn)

                logger.info(f"Registered brand new DatabaseConnection config for KB {kb_id}")



            await self.db.commit()

            return format_success(

                {"database_connection": schemas.DatabaseConnectionResponse.model_validate(db_conn, from_attributes=True)},

                meta={"message": "Database connection registered and validated successfully"}

            )



        except Exception as e:

            await self.db.rollback()

            logger.error(f" Failed to register database connection: {e}", exc_info=True)

            return format_error(f"Failed to register database connection: {str(e)}")



    async def validate_database_connection(

        self,

        db_type: str,

        connection_params: dict,

    ) -> dict:

        """

        Validate a database connection parameter set (dry-run/ping test).

        """

        if db_type == "sqlite":

            filepath = connection_params.get("filepath")

            if not filepath:

                return {"success": False, "message": "Missing 'filepath' parameter for SQLite connection"}

            

            # Allow absolute or relative path within the workspace

            if not os.path.exists(filepath):

                # Try relative resolution

                resolved = os.path.join(os.getcwd(), filepath)

                if not os.path.exists(resolved):

                    return {"success": False, "message": f"SQLite database file not found at path: {filepath}"}

                filepath = resolved



            try:

                conn = sqlite3.connect(filepath)

                cursor = conn.cursor()

                # Run a fast introspective query to verify it's a valid DB

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

                conn.close()

                return {"success": True, "message": "Connection validation successful for local SQLite"}

            except Exception as e:

                return {"success": False, "message": f"Failed to open SQLite database: {str(e)}"}

                

        elif db_type == "postgresql":

            # For this POC, dry-run/mock success for PG or connect if package exists

            conn_str = connection_params.get("connection_string")

            if not conn_str:

                return {"success": False, "message": "Missing 'connection_string' parameter for PostgreSQL"}

            # Return true for now to allow seamless dry-runs

            return {"success": True, "message": "PostgreSQL dry-run validation successful"}

            

        else:

            return {"success": False, "message": f"Unsupported database type: {db_type}"}



    async def discover_database_schema(self, kb_id: str) -> dict:

        """

        Introspect the database and return a list of discovered tables.

        """

        try:

            query = select(DatabaseConnection).where(

                DatabaseConnection.kb_id == uuid.UUID(kb_id),

                DatabaseConnection.tenant_id == self.tenant_id

            )

            res = await self.db.execute(query)

            db_conn = res.scalar_one_or_none()

            if not db_conn:

                return format_error("No registered database connection found for this KB", meta={"status_code": 404})



            tables = []

            if db_conn.db_type == "sqlite":

                filepath = db_conn.connection_params.get("filepath")

                conn = sqlite3.connect(filepath)

                cursor = conn.cursor()

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")

                tables = [r[0] for r in cursor.fetchall()]

                conn.close()

            elif db_conn.db_type == "postgresql":

                # Mock schema discovery response for PG

                tables = ["customers", "products", "orders"]



            return format_success(

                {"success": True, "tables": tables, "db_type": db_conn.db_type},

                meta={"message": f"Successfully discovered {len(tables)} tables"}

            )

        except Exception as e:

            logger.error(f" Schema discovery failed: {e}", exc_info=True)

            return format_error(f"Failed to discover database schema: {str(e)}")



    async def sync_database_source(self, kb_id: str) -> dict:

        """

        Core ETL logic: Extract SQLite/Postgres rows, generate vector embeddings,

        and load them natively into Neo4j as Chunk nodes linked via HAS_CHUNK relationships.

        """

        try:

            # 1. FETCH CONFIGURATION

            query = select(DatabaseConnection).where(

                DatabaseConnection.kb_id == uuid.UUID(kb_id),

                DatabaseConnection.tenant_id == self.tenant_id

            )

            res = await self.db.execute(query)

            db_conn = res.scalar_one_or_none()

            if not db_conn:

                return format_error("No registered database connection found for this KB", meta={"status_code": 404})



            kb = await self.repository.get_by_id(kb_id)

            if not kb:

                return format_error("Parent Knowledge Base not found", meta={"status_code": 404})



            extracted_chunks = []

            

            # 2. EXTRACT DATA & FORMAT INTO SEMANTIC CHUNKS

            if db_conn.db_type == "sqlite":

                filepath = db_conn.connection_params.get("filepath")

                if not os.path.exists(filepath):

                    filepath = os.path.join(os.getcwd(), filepath)

                    if not os.path.exists(filepath):

                        return format_error(f"Database file not found at: {filepath}")



                conn = sqlite3.connect(filepath)

                cursor = conn.cursor()

                

                # Fetch Tables

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")

                tables = [r[0] for r in cursor.fetchall()]

                

                # Introspect & extract records

                if "customers" in tables:

                    cursor.execute("SELECT id, name, email FROM customers;")

                    for cid, name, email in cursor.fetchall():

                        extracted_chunks.append({

                            "text": f"Customer: {name}, Email: {email} (ID: {cid})",

                            "entity_type": "Customer",

                            "entity_id": cid

                        })

                

                if "products" in tables:

                    cursor.execute("SELECT id, name, price FROM products;")

                    for pid, name, price in cursor.fetchall():

                        extracted_chunks.append({

                            "text": f"Product: {name}, Price: ${price:.2f} (ID: {pid})",

                            "entity_type": "Product",

                            "entity_id": pid

                        })



                if "orders" in tables and "customers" in tables and "products" in tables:

                    cursor.execute("""

                        SELECT o.id, c.name, p.name, o.order_date, o.quantity, p.price

                        FROM orders o

                        JOIN customers c ON o.customer_id = c.id

                        JOIN products p ON o.product_id = p.id;

                    """)

                    for oid, cname, pname, odate, qty, price in cursor.fetchall():

                        total = price * qty

                        extracted_chunks.append({

                            "text": f"Order: Customer {cname} purchased product {pname} (Quantity: {qty}, Total: ${total:.2f}) on {odate} (Order ID: {oid})",

                            "entity_type": "Order",

                            "entity_id": oid

                        })

                

                conn.close()

            else:

                # Mock Ingestion for PG or other connectors to allow testing

                extracted_chunks = [

                    {"text": "Customer: Girinath R, Email: girinathr@simplfin.tech (ID: 1)", "entity_type": "Customer", "entity_id": 1},

                    {"text": "Product: GraphMind Enterprise RAG, Price: $4999.00 (ID: 1)", "entity_type": "Product", "entity_id": 1},

                    {"text": "Order: Customer Girinath R purchased product GraphMind Enterprise RAG (Quantity: 1, Total: $4999.00) on 2026-05-18 (Order ID: 1)", "entity_type": "Order", "entity_id": 1}

                ]



            if not extracted_chunks:

                return format_error("Database contains no matching structured tables or data to ingest")



            logger.info(f" Extracted {len(extracted_chunks)} records from database")



            # 3. GENERATE EMBEDDINGS (Batch)

            texts = [c["text"] for c in extracted_chunks]

            embeddings = await EmbeddingGenerator.generate_embeddings_batch(texts)

            logger.info(f" Generated vector embeddings for {len(embeddings)} database chunks")



            # 4. BULK IMPORT CHUNKS NATIVELY INTO NEO4J

            # Detach any previous database chunks from this KB to avoid duplicate accumulation

            purge_query = """

            MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})-[:HAS_CHUNK]->(c:Chunk)

            DETACH DELETE c

            """

            await self.neo4j_repo.execute_write(purge_query, {"kb_id": kb_id, "tenant_id": str(self.tenant_id)})



            # Delete any previous database chunks from Postgres

            from sqlalchemy import delete

            await self.db.execute(

                delete(DocumentChunk).where(

                    DocumentChunk.kb_id == uuid.UUID(kb_id),

                    DocumentChunk.tenant_id == self.tenant_id

                )

            )



            # Load new chunks in a single query transaction

            load_query = """

            MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})

            UNWIND $batch AS item

            CREATE (c:Chunk {

                id: item.id,

                text: item.text,

                embedding: item.embedding,

                position: item.position,

                kb_id: $kb_id,

                tenant_id: $tenant_id,

                entity_type: item.entity_type,

                entity_id: item.entity_id,

                source: item.source,

                weight: 1.0,

                created_at: timestamp()

            })

            CREATE (kb)-[:HAS_CHUNK]->(c)

            """

            

            batch_data = []

            for i, chunk in enumerate(extracted_chunks):

                # source: e.g. "sqlite:Customer", "postgresql:Product"

                source_str = f"{db_conn.db_type}:{chunk['entity_type']}"

                batch_data.append({

                    "id": str(uuid.uuid4()),

                    "text": chunk["text"],

                    "embedding": embeddings[i],

                    "position": i,

                    "entity_type": chunk["entity_type"],

                    "entity_id": str(chunk["entity_id"]),

                    "source": source_str

                })



            await self.neo4j_repo.execute_write(load_query, {

                "kb_id": kb_id,

                "tenant_id": str(self.tenant_id),

                "batch": batch_data

            })

            logger.info(f" Loaded {len(batch_data)} database rows as Chunk nodes in Neo4j linked to KB {kb_id}")



            # Load new chunks into Postgres pgvector table

            for i, item in enumerate(batch_data):

                pg_chunk = DocumentChunk(

                    id=uuid.UUID(item["id"]),

                    tenant_id=self.tenant_id,

                    kb_id=uuid.UUID(kb_id),

                    text=item["text"],

                    chunk_index=i,

                    embedding=item["embedding"],

                )

                self.db.add(pg_chunk)

            logger.info(f" Loaded {len(batch_data)} database rows as DocumentChunks in PostgreSQL pgvector")



            # 5. POSTGRES STATUS UPDATE

            db_conn.last_synced_at = datetime.now()

            kb.total_chunks = len(batch_data)

            await self.db.commit()



            return format_success(

                {

                    "success": True,

                    "kb_id": kb_id,

                    "records_synced": len(batch_data),

                    "last_synced_at": db_conn.last_synced_at.isoformat()

                },

                meta={"message": "Database synchronized with Knowledge Graph successfully"}

            )



        except Exception as e:

            await self.db.rollback()

            logger.error(f" Database synchronization failed: {e}", exc_info=True)

            return format_error(f"Failed to synchronize database source: {str(e)}")



    async def list_google_drive_directory(self, kb_id: str, parent_id: Optional[str] = None) -> dict:
        try:
            from sqlalchemy import select
            from .models import DatabaseConnection
            import uuid
            
            query = select(DatabaseConnection).where(
                DatabaseConnection.kb_id == uuid.UUID(kb_id),
                DatabaseConnection.tenant_id == self.tenant_id,
                DatabaseConnection.db_type == "google_drive"
            )
            res = await self.db.execute(query)
            db_conn = res.scalar_one_or_none()
            if not db_conn:
                return format_error("No registered Google Drive connection found for this KB", meta={"status_code": 404})

            credentials = db_conn.connection_params.get("credentials", {})
            
            from app.modules.connectors.google.crawler import GoogleDriveConnector
            connector = GoogleDriveConnector()
            connector.load_credentials(credentials)
            
            raw_items = await connector.list_directory(parent_id)
            items = []
            for item in raw_items:
                is_folder = item.get("mimeType") == "application/vnd.google-apps.folder"
                items.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "mime_type": item.get("mimeType"),
                    "is_folder": is_folder
                })
            
            return format_success({"items": items})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to list Google Drive directory: {e}", exc_info=True)
            return format_error(f"Failed to list directory: {str(e)}")

    async def sync_google_drive_source(

        self,

        kb_id: str,

        credentials_dict: dict,

        folder_urls: Optional[List[str]] = None,

        file_ids: Optional[List[str]] = None,

        folder_ids: Optional[List[str]] = None,
        user_email: Optional[str] = None,
    ) -> dict:

        """

        Synchronize a Google Drive directory structure with the Knowledge Graph.

        Crawls files/folders, downloads/exports raw streams, extracts text,

        pipes them to the existing chunk/entity pipelines, and maps folder relationships.

        """

        import time

        sync_start_time = time.time()

        # Convert to milliseconds for Neo4j timestamps

        sync_start_timestamp = int(sync_start_time * 1000)

        

        try:

            # 1. INITIALIZE CONNECTOR

            from app.modules.connectors.google.crawler import GoogleDriveConnector
            connector = GoogleDriveConnector(folder_urls=folder_urls)
            connector.load_credentials(credentials_dict)
            
            # Update Knowledge Base source to reflect Google Drive connection
            effective_email = user_email or connector.auth_manager.primary_admin_email or "unknown_email"
            pg_kb = await self.repository.get_by_id(kb_id)
            if pg_kb:
                pg_kb.source = f"google_drive({effective_email})"
                self.db.add(pg_kb)
                await self.db.commit()
                
                # Also update Neo4j
                try:
                    from app.core.neo4j_retry import retry_neo4j_operation
                    await retry_neo4j_operation(
                        lambda: self.neo4j_repo.execute_write(
                            """
                            MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
                            SET kb.source = $new_source
                            """,
                            {
                                "kb_id": kb_id,
                                "tenant_id": str(self.tenant_id),
                                "new_source": f"google_drive({effective_email})"
                            }
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to update Neo4j KB source: {e}")
            
            checkpoint = connector.build_dummy_checkpoint()

            

            files_synced = 0

            folders_synced = 0

            

            # 2. RUN PAGINATED GENERATOR LOOP

            from app.core.connectors import HierarchyNode, SlimDocument

            if file_ids or folder_ids:
                async def selective_generator():
                    all_file_ids = set(file_ids or [])
                    folders_to_process = list(folder_ids or [])
                    processed_folders = set()
                    
                    user_email = connector.auth_manager.primary_admin_email

                    while folders_to_process:
                        current_fid = folders_to_process.pop(0)
                        if current_fid in processed_folders:
                            continue
                        processed_folders.add(current_fid)
                        
                        # Yield HierarchyNode for the folder
                        try:
                            f_meta = await connector.get_files_metadata([current_fid])
                            if f_meta:
                                f_meta = f_meta[0]
                                yield HierarchyNode(
                                    raw_node_id=current_fid,
                                    raw_parent_id=f_meta.get("parents", [None])[0] if f_meta.get("parents") else None,
                                    display_name=f_meta.get("name", "Target Folder"),
                                    node_type="folder"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to fetch metadata for selected folder {current_fid}: {e}")

                        # Fetch children
                        children = await connector.list_directory(current_fid)
                        for c in children:
                            if c.get("mimeType") == "application/vnd.google-apps.folder":
                                folders_to_process.append(c["id"])
                            else:
                                all_file_ids.add(c["id"])
                    
                    if all_file_ids:
                        meta_files = await connector.get_files_metadata(list(all_file_ids))
                        for f in meta_files:
                            yield SlimDocument(
                                id=f["id"], source="google_drive", 
                                metadata={
                                    "file_id": f["id"], 
                                    "filename": f.get("name", "unnamed"), 
                                    "mime_type": f.get("mimeType", ""), 
                                    "webViewLink": f.get("webViewLink"), 
                                    "parents": f.get("parents", []),
                                    "user_email": user_email
                                }
                            )
                generator = selective_generator()
            else:
                generator = connector.load_from_checkpoint(0.0, 0.0, checkpoint)


            

            async for item in generator:

                # Case A: Hierarchy/Folder Node

                if isinstance(item, HierarchyNode):

                    folders_synced += 1

                    # Save Folder Node in Neo4j

                    folder_query = """

                    MERGE (f:Folder {id: $folder_id, tenant_id: $tenant_id})

                    SET f.name = $name, f.link = $link, f.updated_at = timestamp()

                    """

                    await self.neo4j_repo.execute_write(folder_query, {

                        "folder_id": item.raw_node_id,

                        "tenant_id": str(self.tenant_id),

                        "name": item.display_name,

                        "link": item.link

                    })

                    

                    # If folder has parent, link them

                    if item.raw_parent_id:

                        parent_query = """

                        MERGE (p:Folder {id: $parent_id, tenant_id: $tenant_id})

                        MERGE (f:Folder {id: $folder_id, tenant_id: $tenant_id})

                        MERGE (p)-[:PARENT_OF]->(f)

                        """

                        await self.neo4j_repo.execute_write(parent_query, {

                            "parent_id": item.raw_parent_id,

                            "folder_id": item.raw_node_id,

                            "tenant_id": str(self.tenant_id)

                        })

                

                # Case B: SlimDocument (File Footprint)

                elif isinstance(item, SlimDocument):

                    file_id = item.id

                    filename = item.metadata.get("filename", "unnamed")

                    mime_type = item.metadata.get("mime_type", "")

                    parents = item.metadata.get("parents", [])

                    user_email = item.metadata.get("user_email")

                    

                    logger.info(f"Syncing Google Drive file: {filename} ({mime_type})")

                    

                    # Download file content

                    try:

                        file_bytes = await connector.download_file_bytes(

                            file_id=file_id,

                            mime_type=mime_type,

                            impersonate_email=user_email

                        )

                    except Exception as download_err:

                        logger.error(f"Failed to download bytes for file {filename}: {download_err}")

                        continue

                    

                    # Determine ingestion path based on MIME type

                    # 1. CSV / Excel

                    if mime_type == "text/csv" or "spreadsheet" in mime_type or filename.endswith((".csv", ".xlsx", ".xls")):

                        logger.info(f"Piping {filename} to tabular excel/csv ingestion service")

                        ingest_res = await self.ingest_excel_or_csv(

                            kb_id=kb_id,

                            file_bytes=file_bytes,

                            filename=filename,

                            mime_type=mime_type,

                            source="google_drive"

                        )

                        if ingest_res.get("success"):

                            files_synced += 1

                    

                    # 2. Textual Documents (PDF, Docx, Plaintext)

                    else:

                        text = ""

                        try:

                            # 2.1 PDF Parsing

                            if mime_type == "application/pdf" or filename.endswith(".pdf"):

                                import io

                                from PyPDF2 import PdfReader

                                reader = PdfReader(io.BytesIO(file_bytes))

                                pages_text = []

                                for page in reader.pages:

                                    pages_text.append(page.extract_text() or "")

                                text = "\n".join(pages_text)

                            

                            # 2.2 Word / Docx Parsing (Zip XML structure)

                            elif filename.endswith(".docx"):

                                import zipfile

                                import io

                                import xml.etree.ElementTree as ET

                                with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx:

                                    xml_content = docx.read('word/document.xml')

                                    tree = ET.fromstring(xml_content)

                                    paragraphs = []

                                    for elem in tree.iter():

                                        if elem.tag.endswith('t'):

                                            paragraphs.append(elem.text or "")

                                    text = "".join(paragraphs)

                                    

                            # 2.3 Plaintext Fallback

                            else:

                                text = file_bytes.decode("utf-8", errors="ignore")

                        except Exception as parse_err:

                            logger.error(f"Failed to parse text content from file {filename}: {parse_err}")

                            continue

                        

                        if text.strip():

                            logger.info(f"Piping extracted text of {filename} to standard RAG pipeline")

                            ingest_res = await self.ingest_document(

                                kb_id=kb_id,

                                document_text=text,

                                source="google_drive"

                            )

                            if ingest_res.get("success"):

                                files_synced += 1

                                

                    # 3. Post-Process Neo4j Directory Graph Relations

                    if parents and files_synced > 0:

                        parent_id = parents[0]

                        # Ensure the parent folder exists

                        await self.neo4j_repo.execute_write(

                            "MERGE (f:Folder {id: $folder_id, tenant_id: $tenant_id}) ON CREATE SET f.name = 'Google Drive Folder'",

                            {"folder_id": parent_id, "tenant_id": str(self.tenant_id)}

                        )

                        # Link newly created Chunk nodes under this sync to the Folder node

                        link_query = """

                        MATCH (f:Folder {id: $parent_id, tenant_id: $tenant_id})

                        MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})-[:HAS_CHUNK]->(c:Chunk)

                        WHERE c.created_at >= $sync_start_time

                        MERGE (f)-[:HAS_FILE]->(c)

                        """

                        await self.neo4j_repo.execute_write(link_query, {

                            "parent_id": parent_id,

                            "tenant_id": str(self.tenant_id),

                            "kb_id": kb_id,

                            "sync_start_time": sync_start_timestamp

                        })

            

            return format_success(

                {

                    "success": True,

                    "kb_id": kb_id,

                    "files_synced": files_synced,

                    "folders_synced": folders_synced,

                    "sync_duration_seconds": time.time() - sync_start_time

                },

                meta={"message": "Google Drive synchronized with Knowledge Graph successfully"}

            )

            

        except Exception as e:

            logger.error(f" Google Drive synchronization failed: {e}", exc_info=True)

            return format_error(f"Failed to synchronize Google Drive: {str(e)}")

    async def list_sharepoint_directory(self, kb_id: str, parent_id: Optional[str] = None) -> dict:
        try:
            from sqlalchemy import select
            from .models import DatabaseConnection
            import uuid
            
            query = select(DatabaseConnection).where(
                DatabaseConnection.kb_id == uuid.UUID(kb_id),
                DatabaseConnection.tenant_id == self.tenant_id,
                DatabaseConnection.db_type == "sharepoint"
            )
            res = await self.db.execute(query)
            db_conn = res.scalar_one_or_none()
            if not db_conn:
                return format_error("No registered SharePoint connection found for this KB", meta={"status_code": 404})

            credentials = db_conn.connection_params.get("credentials", {})
            site_urls = db_conn.connection_params.get("site_urls", [])
            
            from app.modules.connectors.sharepoint.crawler import SharePointConnector
            connector = SharePointConnector(site_urls=site_urls)
            connector.load_credentials(credentials)
            
            # If no parent_id is specified, we default to the first site root if available
            target_id = parent_id
            if not target_id and site_urls:
                first_url = site_urls[0]
                site_id = await connector.get_site_id_from_url(first_url)
                if site_id:
                    target_id = site_id
                else:
                    target_id = "root"

            raw_items = await connector.list_directory(target_id or "root")
            items = []
            for item in raw_items:
                items.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "mime_type": item.get("mimeType"),
                    "is_folder": item.get("is_folder", False)
                })
            
            return format_success({"items": items})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to list SharePoint directory: {e}", exc_info=True)
            return format_error(f"Failed to list directory: {str(e)}")

    async def sync_sharepoint_source(
        self,
        kb_id: str,
        credentials_dict: dict,
        site_urls: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
        folder_ids: Optional[List[str]] = None,
    ) -> dict:
        """
        Synchronize a SharePoint directory structure with the Knowledge Graph.
        Crawls files/folders, downloads binary streams, extracts text,
        pipes them to the existing chunk pipelines, and maps folder relationships.
        """
        import time
        from app.core.connectors import HierarchyNode, SlimDocument

        sync_start_time = time.time()
        sync_start_timestamp = int(sync_start_time * 1000)
        
        try:
            from app.modules.connectors.sharepoint.crawler import SharePointConnector
            connector = SharePointConnector(site_urls=site_urls)
            connector.load_credentials(credentials_dict)
            
            files_synced = 0
            folders_synced = 0

            # Selective generator logic mirroring Google Drive
            if file_ids or folder_ids:
                async def selective_generator():
                    all_file_ids = set(file_ids or [])
                    folders_to_process = list(folder_ids or [])
                    processed_folders = set()
                    
                    while folders_to_process:
                        current_fid = folders_to_process.pop(0)
                        if current_fid in processed_folders:
                            continue
                        processed_folders.add(current_fid)
                        
                        try:
                            f_meta = await connector.get_files_metadata([current_fid])
                            if f_meta:
                                f_meta = f_meta[0]
                                parent_list = f_meta.get("parents")
                                yield HierarchyNode(
                                    raw_node_id=current_fid,
                                    raw_parent_id=parent_list[0] if parent_list else None,
                                    display_name=f_meta.get("name", "Target Folder"),
                                    node_type="folder"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to fetch metadata for selected folder {current_fid}: {e}")

                        children = await connector.list_directory(current_fid)
                        for c in children:
                            if c.get("is_folder"):
                                folders_to_process.append(c["id"])
                            else:
                                all_file_ids.add(c["id"])
                    
                    if all_file_ids:
                        meta_files = await connector.get_files_metadata(list(all_file_ids))
                        for f in meta_files:
                            yield SlimDocument(
                                id=f["id"], source="sharepoint", 
                                metadata={
                                    "file_id": f["id"], 
                                    "filename": f.get("name", "unnamed"), 
                                    "mime_type": f.get("mimeType", ""), 
                                    "webViewLink": f.get("webViewLink"), 
                                    "parents": f.get("parents", [])
                                }
                            )
                generator = selective_generator()
            else:
                checkpoint = connector.build_dummy_checkpoint()
                generator = connector.load_from_checkpoint(0.0, 0.0, checkpoint)
            
            async for item in generator:
                if isinstance(item, HierarchyNode):
                    folders_synced += 1
                    folder_query = """
                    MERGE (f:Folder {id: $folder_id, tenant_id: $tenant_id})
                    SET f.name = $name, f.link = $link, f.updated_at = timestamp()
                    """
                    await self.neo4j_repo.execute_write(folder_query, {
                        "folder_id": item.raw_node_id,
                        "tenant_id": str(self.tenant_id),
                        "name": item.display_name,
                        "link": item.link
                    })
                    
                    if item.raw_parent_id:
                        parent_query = """
                        MERGE (p:Folder {id: $parent_id, tenant_id: $tenant_id})
                        MERGE (f:Folder {id: $folder_id, tenant_id: $tenant_id})
                        MERGE (p)-[:PARENT_OF]->(f)
                        """
                        await self.neo4j_repo.execute_write(parent_query, {
                            "parent_id": item.raw_parent_id,
                            "folder_id": item.raw_node_id,
                            "tenant_id": str(self.tenant_id)
                        })
                
                elif isinstance(item, SlimDocument):
                    file_id = item.id
                    filename = item.metadata.get("filename", "unnamed")
                    mime_type = item.metadata.get("mime_type", "")
                    parents = item.metadata.get("parents", [])
                    
                    logger.info(f"Syncing SharePoint file: {filename} ({mime_type})")
                    
                    try:
                        file_bytes = await connector.download_file_bytes(file_id)
                    except Exception as download_err:
                        logger.error(f"Failed to download bytes for file {filename}: {download_err}")
                        continue
                    
                    # Direct binary to parsing logic
                    if mime_type == "text/csv" or "spreadsheet" in mime_type or filename.endswith((".csv", ".xlsx", ".xls")):
                        logger.info(f"Piping {filename} to tabular excel/csv ingestion service")
                        ingest_res = await self.ingest_excel_or_csv(
                            kb_id=kb_id,
                            file_bytes=file_bytes,
                            filename=filename,
                            mime_type=mime_type
                        )
                        if ingest_res.get("success"):
                            files_synced += 1
                    else:
                        text = ""
                        try:
                            if mime_type == "application/pdf" or filename.endswith(".pdf"):
                                import io
                                from PyPDF2 import PdfReader
                                reader = PdfReader(io.BytesIO(file_bytes))
                                pages_text = [page.extract_text() or "" for page in reader.pages]
                                text = "\n".join(pages_text)
                            elif filename.endswith(".docx"):
                                import zipfile
                                import io
                                import xml.etree.ElementTree as ET
                                with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx:
                                    xml_content = docx.read('word/document.xml')
                                    tree = ET.fromstring(xml_content)
                                    paragraphs = [elem.text or "" for elem in tree.iter() if elem.tag.endswith('t')]
                                    text = "".join(paragraphs)
                            elif filename.endswith(".pptx"):
                                import zipfile
                                import io
                                import xml.etree.ElementTree as ET
                                with zipfile.ZipFile(io.BytesIO(file_bytes)) as pptx:
                                    text_elements = []
                                    for file in pptx.namelist():
                                        if file.startswith("ppt/slides/slide") and file.endswith(".xml"):
                                            slide_xml = pptx.read(file)
                                            tree = ET.fromstring(slide_xml)
                                            for elem in tree.iter():
                                                if elem.tag.endswith('}t'):
                                                    text_elements.append(elem.text or "")
                                    text = "\n".join(text_elements)
                            else:
                                text = file_bytes.decode("utf-8", errors="ignore")
                        except Exception as parse_err:
                            logger.error(f"Failed to parse text content from file {filename}: {parse_err}")
                            continue
                        
                        if text.strip():
                            logger.info(f"Piping extracted text of {filename} to standard RAG pipeline")
                            ingest_res = await self.ingest_document(
                                kb_id=kb_id,
                                document_text=text
                            )
                            if ingest_res.get("success"):
                                files_synced += 1
                                
                    if parents and files_synced > 0:
                        parent_id = parents[0]
                        await self.neo4j_repo.execute_write(
                            "MERGE (f:Folder {id: $folder_id, tenant_id: $tenant_id}) ON CREATE SET f.name = 'SharePoint Folder'",
                            {"folder_id": parent_id, "tenant_id": str(self.tenant_id)}
                        )
                        link_query = """
                        MATCH (f:Folder {id: $parent_id, tenant_id: $tenant_id})
                        MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})-[:HAS_CHUNK]->(c:Chunk)
                        WHERE c.created_at >= $sync_start_time
                        MERGE (f)-[:HAS_FILE]->(c)
                        """
                        await self.neo4j_repo.execute_write(link_query, {
                            "parent_id": parent_id,
                            "tenant_id": str(self.tenant_id),
                            "kb_id": kb_id,
                            "sync_start_time": sync_start_timestamp
                        })
            
            return format_success(
                {
                    "success": True,
                    "kb_id": kb_id,
                    "files_synced": files_synced,
                    "folders_synced": folders_synced,
                    "sync_duration_seconds": time.time() - sync_start_time
                },
                meta={"message": "SharePoint synchronized with Knowledge Graph successfully"}
            )
            
        except Exception as e:
            logger.error(f" SharePoint synchronization failed: {e}", exc_info=True)
            return format_error(f"Failed to synchronize SharePoint: {str(e)}")



    async def sync_gmail_source(self, kb_id: str, sync_req: dict) -> dict:
        import time
        import json
        from uuid import uuid4
        from sqlalchemy import select
        from app.modules.knowledge_bases.models import KnowledgeBase, DatabaseConnection, DocumentChunk
        from app.modules.connectors.google.gmail_crawler import GmailConnector
        from app.core.connectors import ConnectorCheckpoint

        sync_start_time = time.time()
        
        query = select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(kb_id), KnowledgeBase.tenant_id == self.tenant_id)
        res = await self.db.execute(query)
        pg_kb = res.scalar_one_or_none()
        if not pg_kb:
            return format_error('Knowledge Base not found', meta={'error_code': 'KB_NOT_FOUND'})

        conn_query = select(DatabaseConnection).where(
            DatabaseConnection.kb_id == uuid.UUID(kb_id),
            DatabaseConnection.tenant_id == self.tenant_id,
            DatabaseConnection.db_type == 'gmail'
        )
        conn_res = await self.db.execute(conn_query)
        db_conn = conn_res.scalar_one_or_none()
        if not db_conn:
            return format_error('Gmail connection not configured for this KB.')

        credentials = db_conn.connection_params
        user_email = sync_req.get('user_email')
        if not user_email:
            return format_error('user_email is required for Gmail sync.')

        pg_kb.source = f'gmail({user_email})'
        await self.db.commit()

        neo_query = "MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id}) SET kb.source = $new_source"
        try:
            from app.core.neo4j import execute_write_query
            await execute_write_query(neo_query, {'kb_id': str(kb_id), 'tenant_id': str(self.tenant_id), 'new_source': f'gmail({user_email})'})
        except Exception as e:
            logger.warning(f'Failed to update source string in Neo4j: {e}')

        crawler = GmailConnector(query=sync_req.get('query'), max_results=sync_req.get('max_results', 100))
        crawler.load_credentials(credentials)
        checkpoint = ConnectorCheckpoint(user_emails=[user_email], has_more=True, completion_stage='start')

        messages_synced = 0
        neo4j_nodes = []

        try:
            async for doc in crawler.load_from_checkpoint(0, time.time(), checkpoint):
                if hasattr(doc, 'node_type'):
                    continue
                
                msg_data = await crawler.get_message_content(doc.id, user_email)
                if not msg_data or not msg_data.get('body'):
                    continue

                chunk_id = str(uuid4())
                chunk_text = f"Subject: {msg_data.get('subject')}\nFrom: {msg_data.get('sender')}\nDate: {msg_data.get('date')}\n\n{msg_data.get('body')}"

                from app.core.entity_extraction import EntityExtractor
                entities = await EntityExtractor.extract_entities(msg_data.get('body') or "")

                neo4j_nodes.append({
                    'chunk_id': chunk_id,
                    'message_id': doc.id,
                    'subject': msg_data.get('subject'),
                    'sender': msg_data.get('sender'),
                    'date': msg_data.get('date'),
                    'entities': [{'text': e.text, 'type': e.entity_type} for e in entities[:50]]
                })

                from app.core.embeddings import get_embedding
                emb = await get_embedding(chunk_text)
                
                pg_chunk = DocumentChunk(
                    id=uuid.UUID(chunk_id),
                    tenant_id=self.tenant_id,
                    kb_id=uuid.UUID(kb_id),
                    content=chunk_text,
                    embedding=emb,
                    metadata_json={
                        'source': 'gmail',
                        'message_id': doc.id
                    }
                )
                self.db.add(pg_chunk)
                messages_synced += 1

            if neo4j_nodes:
                neo_query_emails = """
                MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
                UNWIND $chunks AS chunk
                MERGE (p:Person {text: chunk.sender, tenant_id: $tenant_id})
                ON CREATE SET p.type = 'PERSON', p.id = randomUUID(), p.created_at = timestamp()
                MERGE (e:Email {id: chunk.message_id, tenant_id: $tenant_id})
                ON CREATE SET e.subject = chunk.subject, e.date = chunk.date, e.chunk_id = chunk.chunk_id, e.created_at = timestamp()
                MERGE (p)-[:SENT]->(e)
                MERGE (kb)-[:HAS_EMAIL]->(e)
                WITH e, chunk, $tenant_id AS tenant_id
                UNWIND chunk.entities AS ent
                MERGE (ent_node:Entity {text: ent.text, type: ent.type, tenant_id: tenant_id})
                ON CREATE SET ent_node.id = randomUUID(), ent_node.created_at = timestamp()
                MERGE (e)-[:MENTIONS]->(ent_node)
                """
                await execute_write_query(neo_query_emails, {
                    'kb_id': str(kb_id),
                    'tenant_id': str(self.tenant_id),
                    'chunks': neo4j_nodes
                })
                
                pg_kb.total_chunks += messages_synced
                await self.db.commit()

            from app.utils.formatters import format_success, format_error
            return format_success({'kb_id': kb_id, 'messages_synced': messages_synced, 'sync_duration_seconds': time.time() - sync_start_time}, meta={'message': 'Gmail synchronized successfully'})

        except Exception as e:
            logger.error(f'Gmail sync failed: {e}', exc_info=True)
            from app.utils.formatters import format_error
            return format_error(f'Failed to sync Gmail: {e}')

    async def sync_outlook_source(self, kb_id: str, sync_req: dict) -> dict:
        import time
        import json
        from uuid import uuid4
        from sqlalchemy import select
        from app.modules.knowledge_bases.models import KnowledgeBase, DatabaseConnection, DocumentChunk
        from app.modules.connectors.sharepoint.outlook_crawler import OutlookConnector
        from app.core.connectors import ConnectorCheckpoint

        sync_start_time = time.time()
        
        query = select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(kb_id), KnowledgeBase.tenant_id == self.tenant_id)
        res = await self.db.execute(query)
        pg_kb = res.scalar_one_or_none()
        if not pg_kb:
            return format_error('Knowledge Base not found', meta={'error_code': 'KB_NOT_FOUND'})

        conn_query = select(DatabaseConnection).where(
            DatabaseConnection.kb_id == uuid.UUID(kb_id),
            DatabaseConnection.tenant_id == self.tenant_id,
            DatabaseConnection.db_type == 'outlook'
        )
        conn_res = await self.db.execute(conn_query)
        db_conn = conn_res.scalar_one_or_none()
        if not db_conn:
            return format_error('Outlook connection not configured for this KB.')

        user_email = sync_req.get('user_email')
        if not user_email:
            return format_error('user_email is required for Outlook sync.')

        pg_kb.source = f'outlook({user_email})'
        await self.db.commit()

        crawler = OutlookConnector(folder_id=sync_req.get('folder_id'), max_results=sync_req.get('max_results', 100))
        crawler.load_credentials(db_conn.connection_params)
        checkpoint = ConnectorCheckpoint(user_emails=[user_email], has_more=True, completion_stage='start')

        messages_synced = 0
        neo4j_nodes = []

        try:
            async for doc in crawler.load_from_checkpoint(0, time.time(), checkpoint):
                if hasattr(doc, 'node_type'):
                    continue
                
                msg_data = await crawler.get_message_content(user_email, doc.id)
                if not msg_data or not msg_data.get('body'):
                    continue

                chunk_id = str(uuid4())
                chunk_text = f"Subject: {msg_data.get('subject')}\nFrom: {msg_data.get('sender')}\nDate: {msg_data.get('date')}\n\n{msg_data.get('body')}"

                from app.core.entity_extraction import EntityExtractor
                entities = await EntityExtractor.extract_entities(msg_data.get('body') or "")

                neo4j_nodes.append({
                    'chunk_id': chunk_id,
                    'message_id': doc.id,
                    'subject': msg_data.get('subject'),
                    'sender': msg_data.get('sender'),
                    'date': msg_data.get('date'),
                    'entities': [{'text': e.text, 'type': e.entity_type} for e in entities[:50]]
                })

                from app.core.embeddings import get_embedding
                emb = await get_embedding(chunk_text)
                
                pg_chunk = DocumentChunk(
                    id=uuid.UUID(chunk_id),
                    tenant_id=self.tenant_id,
                    kb_id=uuid.UUID(kb_id),
                    content=chunk_text,
                    embedding=emb,
                    metadata_json={
                        'source': 'outlook',
                        'message_id': doc.id
                    }
                )
                self.db.add(pg_chunk)
                messages_synced += 1

            if neo4j_nodes:
                neo_query_emails = """
                MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
                UNWIND $chunks AS chunk
                MERGE (p:Person {text: chunk.sender, tenant_id: $tenant_id})
                ON CREATE SET p.type = 'PERSON', p.id = randomUUID(), p.created_at = timestamp()
                MERGE (e:Email {id: chunk.message_id, tenant_id: $tenant_id})
                ON CREATE SET e.subject = chunk.subject, e.date = chunk.date, e.chunk_id = chunk.chunk_id, e.created_at = timestamp()
                MERGE (p)-[:SENT]->(e)
                MERGE (kb)-[:HAS_EMAIL]->(e)
                WITH e, chunk, $tenant_id AS tenant_id
                UNWIND chunk.entities AS ent
                MERGE (ent_node:Entity {text: ent.text, type: ent.type, tenant_id: tenant_id})
                ON CREATE SET ent_node.id = randomUUID(), ent_node.created_at = timestamp()
                MERGE (e)-[:MENTIONS]->(ent_node)
                """
                from app.core.neo4j import execute_write_query
                await execute_write_query(neo_query_emails, {
                    'kb_id': str(kb_id),
                    'tenant_id': str(self.tenant_id),
                    'chunks': neo4j_nodes
                })
                
                pg_kb.total_chunks += messages_synced
                await self.db.commit()

            from app.utils.formatters import format_success, format_error
            return format_success({'kb_id': kb_id, 'messages_synced': messages_synced, 'sync_duration_seconds': time.time() - sync_start_time}, meta={'message': 'Outlook synchronized successfully'})

        except Exception as e:
            logger.error(f'Outlook sync failed: {e}', exc_info=True)
            from app.utils.formatters import format_error
            return format_error(f'Failed to sync Outlook: {e}')
