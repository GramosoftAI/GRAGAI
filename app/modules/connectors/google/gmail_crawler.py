"""Gmail Crawler and message export engine"""

import logging
import base64
from collections.abc import Generator
from typing import Any, Dict, List, Optional

from app.core.connectors import CheckpointedConnector, SlimDocument, HierarchyNode, ConnectorCheckpoint, StageCompletion
from .auth import GoogleAuthManager, execute_google_request

logger = logging.getLogger(__name__)


class GmailConnector(CheckpointedConnector[ConnectorCheckpoint]):
    """
    Checkpointed crawler for Gmail.
    Fetches messages matching an optional query, decoding their base64 bodies.
    """

    def __init__(self, query: Optional[str] = None, max_results: int = 100, label_ids: Optional[list] = None) -> None:
        self.auth_manager = GoogleAuthManager()
        self.query = query or ""
        self.max_results = max_results
        self.label_ids = label_ids
        self.label_ids = label_ids

    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any] | None:
        return self.auth_manager.load_credentials(credentials)

    def build_dummy_checkpoint(self) -> ConnectorCheckpoint:
        return ConnectorCheckpoint(has_more=True, completion_stage="start")

    def validate_checkpoint_json(self, checkpoint_json: str) -> ConnectorCheckpoint:
        try:
            return ConnectorCheckpoint.model_validate_json(checkpoint_json)
        except Exception as e:
            logger.warning(f"Failed to validate checkpoint JSON: {e}, falling back to dummy")
            return self.build_dummy_checkpoint()

    def _decode_body(self, payload: Dict[str, Any]) -> str:
        """Recursively extract and decode base64 body parts from payload"""
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get("mimeType") in ("text/plain", "text/html") or "parts" in part:
                    body += self._decode_body(part)
        elif 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            try:
                # Add base64 padding to avoid binascii.Error: Incorrect padding
                data += '=' * (-len(data) % 4)
                body = base64.urlsafe_b64decode(data).decode('utf-8')
            except Exception as e:
                logger.warning(f"Failed to decode message body: {e}")
        return body

    async def get_message_content(self, message_id: str, impersonate_email: Optional[str] = None) -> Dict[str, Any]:
        """Fetch full message payload and decode its parts."""
        email = impersonate_email or self.auth_manager.primary_admin_email
        async with self.auth_manager.get_client(email) as client:
            res = await execute_google_request(
                client, "GET", f"/gmail/v1/users/{email}/messages/{message_id}", params={"format": "full"}
            )
            
            headers = res.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            body_text = self._decode_body(res.get('payload', {}))
            if not body_text:
                body_text = res.get("snippet", "")
            
            return {
                "id": message_id,
                "subject": subject,
                "sender": sender,
                "date": date_str,
                "snippet": res.get("snippet", ""),
                "body": body_text
            }

    async def load_from_checkpoint(
        self,
        start: float,
        end: float,
        checkpoint: ConnectorCheckpoint,
    ) -> Generator[SlimDocument | HierarchyNode, None, None]:
        emails_to_crawl = checkpoint.user_emails or [self.auth_manager.primary_admin_email]

        for email in emails_to_crawl:
            if email not in checkpoint.completion_map:
                checkpoint.completion_map[email] = StageCompletion(stage="crawling", completed_until=start)

            completion = checkpoint.completion_map[email]
            if completion.stage == "done":
                continue

            logger.info(f"Starting Gmail crawl for user: {email}")

            async with self.auth_manager.get_client(email) as client:
                has_more_pages = True
                page_token = completion.next_page_token
                messages_fetched = 0

                while has_more_pages and messages_fetched < self.max_results:
                    params = {
                        "maxResults": min(50, self.max_results - messages_fetched),
                    }
                    if self.query:
                        params["q"] = self.query
                    if self.label_ids:
                        params["labelIds"] = self.label_ids
                    if page_token:
                        params["pageToken"] = page_token

                    try:
                        res = await execute_google_request(client, "GET", f"/gmail/v1/users/{email}/messages", params=params)
                    except Exception as e:
                        logger.error(f"Failed to list Gmail messages for {email}: {e}")
                        completion.next_page_token = page_token
                        checkpoint.has_more = True
                        return

                    messages = res.get("messages", [])
                    for msg in messages:
                        msg_id = msg.get("id")
                        if not msg_id or msg_id in checkpoint.all_retrieved_file_ids:
                            continue

                        messages_fetched += 1
                        
                        # Yield the slim metadata document; body fetch is deferred or handled immediately
                        # For now, let's include basic metadata
                        meta = {
                            "message_id": msg_id,
                            "user_email": email,
                            "source_type": "gmail_message"
                        }

                        yield SlimDocument(
                            id=msg_id,
                            source="gmail",
                            metadata=meta,
                        )

                        checkpoint.all_retrieved_file_ids.add(msg_id)

                    page_token = res.get("nextPageToken")
                    completion.next_page_token = page_token
                    has_more_pages = bool(page_token)

                completion.stage = "done"

        all_done = all(comp.stage == "done" for comp in checkpoint.completion_map.values())
        checkpoint.has_more = not all_done
        return
