import logging
from typing import Dict, Any, List
from app.core.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

async def graph_update_job(ctx: Dict[Any, Any], kb_id: str, tenant_id: str, chunks: List[Dict[str, Any]]):
    logger.info(f"Starting graph_update_job for {len(chunks)} chunks")
    
    if not chunks:
        return {"status": "success", "processed": 0}
        
    neo4j_repo = Neo4jRepository(tenant_id)
    
    neo_query = """
    MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
    UNWIND $chunks AS chunk
    
    // Create Chunk
    MERGE (c:Chunk {id: chunk.chunk_id})
    ON CREATE SET c.text = chunk.text, c.created_at = timestamp(), c.tenant_id = $tenant_id
    
    // Create Person (Sender)
    MERGE (p:Person {text: chunk.sender, tenant_id: $tenant_id})
    ON CREATE SET p.type = 'PERSON', p.id = randomUUID(), p.created_at = timestamp()
    
    // Create Thread
    MERGE (t:Thread {id: chunk.thread_id, tenant_id: $tenant_id})
    ON CREATE SET t.created_at = timestamp()
    
    // Create Email
    MERGE (e:Email {id: chunk.message_id, tenant_id: $tenant_id})
    ON CREATE SET e.subject = chunk.subject, e.date = chunk.date, e.chunk_id = chunk.chunk_id, e.created_at = timestamp()
    
    // Relationships
    MERGE (kb)-[:HAS_CHUNK]->(c)
    MERGE (c)-[:EXTRACTED_FROM]->(e)
    MERGE (p)-[:SENT]->(e)
    MERGE (e)-[:BELONGS_TO]->(t)
    """
    
    try:
        await neo4j_repo.execute_write(neo_query, {
            'kb_id': kb_id,
            'tenant_id': tenant_id,
            'chunks': chunks
        })
        logger.info("Successfully updated Neo4j graph")
    except Exception as e:
        logger.error(f"Failed to update graph: {e}")
        raise e
        
    return {"status": "success", "nodes_processed": len(chunks)}
