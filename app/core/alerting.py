import logging
import requests
import time
from typing import List, Dict, Tuple
from ..modules.knowledge_bases.models import DocumentIngestionRun
from .config import get_settings

logger = logging.getLogger(__name__)

class BaseAlertChannel:
    def send(self, message: str, severity: str):
        raise NotImplementedError()

class LogAlertChannel(BaseAlertChannel):
    def send(self, message: str, severity: str):
        if severity == "CRITICAL":
            logger.critical(message)
        else:
            logger.warning(message)

class SlackAlertChannel(BaseAlertChannel):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    def send(self, message: str, severity: str):
        if not self.webhook_url:
            return
        
        emoji = "🚨" if severity == "CRITICAL" else "⚠️"
        payload = {"text": f"{emoji} *{severity} ALERT*\n{message}"}
        
        try:
            requests.post(self.webhook_url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

class AlertManager:
    _channels: List[BaseAlertChannel] = []
    _alert_history: Dict[str, float] = {}
    
    @classmethod
    def get_channels(cls) -> List[BaseAlertChannel]:
        if not cls._channels:
            cls._channels.append(LogAlertChannel())
            settings = get_settings()
            if settings.slack_webhook_url:
                cls._channels.append(SlackAlertChannel(settings.slack_webhook_url))
        return cls._channels

    @classmethod
    def emit(cls, message: str, severity: str, dedupe_key: str):
        now = time.time()
        
        # Deduplication check
        if dedupe_key in cls._alert_history:
            last_emitted = cls._alert_history[dedupe_key]
            # Suppress CRITICAL for 1 hour (3600s), WARNING for 15 mins (900s)
            cooldown = 3600 if severity == "CRITICAL" else 900
            if now - last_emitted < cooldown:
                return  # Suppress duplicate alert
        
        # Update history
        cls._alert_history[dedupe_key] = now
        
        for channel in cls.get_channels():
            # Send WARNING to all channels, or restrict based on requirements.
            # Usually CRITICAL goes to Slack, WARNING goes to logs. But we'll route both, or we can restrict.
            if isinstance(channel, SlackAlertChannel) and severity != "CRITICAL":
                continue  # Only critical goes to Slack
            channel.send(message, severity)

    @classmethod
    def evaluate_ingestion(cls, audit_run: DocumentIngestionRun):
        """
        Evaluate an ingestion run for operational anomalies and emit specific alerts.
        """
        chunk_count = audit_run.chunk_count or 1
        
        fallback_rate = audit_run.fallback_count / chunk_count
        retry_rate = audit_run.retry_count / chunk_count
        repair_rate = audit_run.repair_count / chunk_count
        
        # --- CRITICAL ALERTS ---
        if audit_run.status == "FAILED":
            if audit_run.error_message and "neo4j" in audit_run.error_message.lower():
                cls.emit(f"Neo4j Write Failure for document {audit_run.document_id}:\n```{audit_run.error_message}```", "CRITICAL", f"neo4j_fail_{audit_run.document_id}")
            else:
                cls.emit(f"Ingestion FAILED for document {audit_run.document_id}:\n```{audit_run.error_message}```", "CRITICAL", f"ingest_fail_{audit_run.document_id}")
                
        if fallback_rate > 0.05:
            cls.emit(f"Fallback Rate > 5% for document {audit_run.document_id} ({fallback_rate * 100:.1f}%)", "CRITICAL", f"high_fallback_{audit_run.document_id}")
            
        # --- WARNING ALERTS ---
        if retry_rate > 0.10:
            cls.emit(f"Retry Rate > 10% for document {audit_run.document_id} ({retry_rate * 100:.1f}%)", "WARNING", f"high_retry_{audit_run.document_id}")
            
        if repair_rate > 0.20:
            cls.emit(f"Repair Rate > 20% for document {audit_run.document_id} ({repair_rate * 100:.1f}%)", "WARNING", f"high_repair_{audit_run.document_id}")
            
        if audit_run.deviation_percent is not None and audit_run.deviation_percent < -50.0:
            msg = (
                f"Drift Detection Triggered for document {audit_run.document_id}\n"
                f"Current: {audit_run.current_entities_per_chunk:.1f}\n"
                f"Baseline: {audit_run.baseline_entities_per_chunk:.1f}\n"
                f"Deviation: {audit_run.deviation_percent:.1f}%\n"
                f"Documents: {audit_run.baseline_documents}"
            )
            cls.emit(msg, "WARNING", f"drift_{audit_run.document_id}")
