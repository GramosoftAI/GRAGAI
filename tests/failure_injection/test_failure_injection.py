import pytest
import asyncio
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.unified_extractor import UnifiedExtractor
from app.core.entity_extraction import Entity
from app.modules.knowledge_bases.service import KnowledgeBaseService

@pytest.mark.asyncio
async def test_scenario_1_malformed_json_triggers_repair():
    """Scenario 1: Malformed JSON triggers repair_count increment"""
    extractor = UnifiedExtractor(tenant_id="test")
    
    with patch("app.core.llm.deepinfra_llm.DeepInfraLLMClient.generate_with_usage", new_callable=AsyncMock) as mock_generate:
        # Return broken JSON
        mock_generate.return_value = {
            "content": '{"schema_version": "1.0", "entities": [{"text": "apple", "type": "FRUIT"}',  # Missing closing brackets
            "prompt_tokens": 10,
            "completion_tokens": 5
        }
        
        result = await extractor.extract_all("chunk_1", "Apple is a fruit.")
        
        # It should repair the JSON and succeed
        assert result["_metadata"]["repair_used"] is True
        assert result["_metadata"]["fallback_used"] is False

@pytest.mark.asyncio
async def test_scenario_2_retry_failure_triggers_fallback():
    """Scenario 2: Retry Failure triggers fallback_count increment"""
    extractor = UnifiedExtractor(tenant_id="test")
    
    with patch("app.core.llm.deepinfra_llm.DeepInfraLLMClient.generate_with_usage", new_callable=AsyncMock) as mock_generate:
        # Return completely unparseable string
        mock_generate.return_value = {
            "content": 'THIS IS NOT JSON AND CANNOT BE REPAIRED',
            "prompt_tokens": 10,
            "completion_tokens": 5
        }
        
        # Mock fallback so it returns something
        with patch("app.core.entity_extraction.EntityExtractor.extract_entities", new_callable=AsyncMock) as mock_legacy_ent:
            with patch("app.core.triplet_extractor.TripletExtractor.extract_from_chunk", new_callable=AsyncMock) as mock_legacy_trip:
                
                # Setup dummy returns for legacy path
                mock_legacy_ent.return_value = []
                mock_legacy_trip.return_value = MagicMock(triplets=[])
                
                result = await extractor.extract_all("chunk_1", "Apple is a fruit.")
                
                # Should exhaust 2 retries and trigger fallback
                assert result["_metadata"]["fallback_used"] is True
                assert mock_generate.call_count == 2

@pytest.mark.asyncio
async def test_scenario_3_neo4j_offline_triggers_failed_status():
    """Scenario 3: Neo4j Offline triggers FAILED status and AlertManager"""
    db_mock = AsyncMock()
    service = KnowledgeBaseService(db_mock, tenant_id=str(uuid.uuid4()))
    
    service.repository = AsyncMock()
    service.repository.get_by_id.return_value = MagicMock(id=uuid.uuid4())
    service.neo4j_repo = AsyncMock()
    
    # We patch TripletGraphWriter's persist_triplets to simulate Neo4j failure
    with patch("app.core.triplet_extractor.TripletGraphWriter.persist_triplets", new_callable=AsyncMock) as mock_persist:
        mock_persist.side_effect = Exception("Connection refused to Neo4j")
        
        # Mock chunking and embeddings
        with patch("app.core.adaptive_chunker.AdaptiveChunker.chunk", new_callable=AsyncMock) as mock_chunk:
            mock_chunk.return_value = [{"chunk_text": "chunk 1", "metadata": {"chunk_type": "semantic"}}]
            with patch("app.core.embeddings.EmbeddingGenerator.generate_embeddings_batch", new_callable=AsyncMock) as mock_embed:
                mock_embed.return_value = [[0.1] * 1536]
                
                with patch("app.core.unified_extractor.UnifiedExtractor.extract_all", new_callable=AsyncMock) as mock_extract:
                    mock_extract.return_value = {
                        "entities": [],
                        "triplets": [],
                        "structured": {},
                        "_metadata": {"repair_used": False, "retry_used": False, "fallback_used": False, "extraction_duration_ms": 100}
                    }
                    
                    # Mock AlertManager
                    with patch("app.core.alerting.AlertManager.evaluate_ingestion") as mock_alert:
                        # Execute
                        res = await service.ingest_document(str(uuid.uuid4()), "Document Content")
                        
                        # Verify
                        assert res["success"] is False
                        assert "Connection refused to Neo4j" in res["error"]
                        
                        # AlertManager should have received a FAILED audit run
                        assert mock_alert.call_count == 1
                        audit_run = mock_alert.call_args[0][0]
                        assert audit_run.status == "FAILED"
                        assert "Connection refused to Neo4j" in audit_run.error_message

@pytest.mark.asyncio
async def test_scenario_4_deepinfra_timeout():
    """Scenario 4: DeepInfra Timeout is caught and triggers fallback/retry"""
    extractor = UnifiedExtractor(tenant_id="test")
    
    with patch("app.core.llm.deepinfra_llm.DeepInfraLLMClient.generate_with_usage", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = TimeoutError("DeepInfra API Timeout")
        
        # Mock fallback so it doesn't hang
        with patch("app.core.entity_extraction.EntityExtractor.extract_entities", new_callable=AsyncMock) as mock_legacy_ent:
            with patch("app.core.triplet_extractor.TripletExtractor.extract_from_chunk", new_callable=AsyncMock) as mock_legacy_trip:
                mock_legacy_ent.return_value = []
                mock_legacy_trip.return_value = MagicMock(triplets=[])
                
                result = await extractor.extract_all("chunk_1", "Apple is a fruit.")
                
                # Since generate throws TimeoutError, it exhausts retries and triggers fallback
                assert result["_metadata"]["fallback_used"] is True
                assert mock_generate.call_count == 2

@pytest.mark.asyncio
async def test_scenario_5_partial_ingestion_failure():
    """Scenario 5: Partial Failure sets status to PARTIAL_SUCCESS"""
    db_mock = AsyncMock()
    service = KnowledgeBaseService(db_mock, tenant_id=str(uuid.uuid4()))
    
    service.repository = AsyncMock()
    service.repository.get_by_id.return_value = MagicMock(id=uuid.uuid4())
    service.neo4j_repo = AsyncMock()
    
    # Mock chunking and embeddings
    with patch("app.core.adaptive_chunker.AdaptiveChunker.chunk", new_callable=AsyncMock) as mock_chunk:
        mock_chunk.return_value = [
            {"chunk_text": "chunk 1", "metadata": {"chunk_type": "semantic"}},
            {"chunk_text": "chunk 2", "metadata": {"chunk_type": "semantic"}}
        ]
        with patch("app.core.embeddings.EmbeddingGenerator.generate_embeddings_batch", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1536, [0.1] * 1536]
            
            with patch("app.core.unified_extractor.UnifiedExtractor.extract_all", new_callable=AsyncMock) as mock_extract:
                # First chunk succeeds, second chunk fails
                mock_extract.side_effect = [
                    {
                        "entities": [Entity(text="apple", entity_type="CONCEPT", confidence=1.0)],
                        "triplets": [],
                        "structured": {},
                        "_metadata": {"repair_used": False, "retry_used": False, "fallback_used": False, "extraction_duration_ms": 100}
                    },
                    Exception("Unrecoverable error on chunk 2")
                ]
                
                with patch("app.core.triplet_extractor.TripletGraphWriter.persist_triplets", new_callable=AsyncMock) as mock_persist:
                    mock_persist.return_value = {"entities_created": 1, "relationships_created": 0, "triplets_created": 0}
                    
                    with patch("app.core.alerting.AlertManager.evaluate_ingestion") as mock_alert:
                        res = await service.ingest_document(str(uuid.uuid4()), "Document Content")
                        
                        assert res["success"] is True
                        
                        # Verify audit run was updated to PARTIAL_SUCCESS
                        added_objects = [call[0][0] for call in db_mock.add.call_args_list]
                        audit_run = next(obj for obj in added_objects if hasattr(obj, "status") and hasattr(obj, "document_id"))
                        assert audit_run.status == "PARTIAL_SUCCESS"
