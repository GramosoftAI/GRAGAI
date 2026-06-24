"""Outlook Crawler and message export engine"""

import logging
from collections.abc import Generator
from typing import Any, Dict, List, Optional
import json

from app.core.connectors import CheckpointedConnector, SlimDocument, HierarchyNode, ConnectorCheckpoint, StageCompletion
from .auth import SharePointAuthManager, execute_graph_request

logger = logging.getLogger(__name__)


class OutlookConnector(CheckpointedConnector[ConnectorCheckpoint]):
    """
    Checkpointed crawler for Outlook via Microsoft Graph API.
    Fetches messages from a user's mailbox.
    """

    def __init__(self, folder_id: Optional[str] = None, max_results: int = 100) -> None:
        self.auth_manager = SharePointAuthManager()
        self.folder_id = folder_id
        self.max_results = max_results

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

    async def get_message_content(self, user_email: str, message_id: str) -> Dict[str, Any]:
        """Fetch full message payload from Microsoft Graph."""
        endpoint = f"/users/{user_email}/messages/{message_id}"
        try:
            res = await execute_graph_request(self.auth_manager, "GET", endpoint)
            
            body_content = res.get("body", {}).get("content", "")
            subject = res.get("subject", "No Subject")
            sender_dict = res.get("from", {}).get("emailAddress", {})
            sender = sender_dict.get("address", "Unknown Sender")
            date_str = res.get("receivedDateTime", "")
            
            return {
                "id": message_id,
                "subject": subject,
                "sender": sender,
                "date": date_str,
                "snippet": res.get("bodyPreview", ""),
                "body": body_content
            }
        except Exception as e:
            logger.error(f"Failed to fetch Outlook message {message_id}: {e}")
            return {}

    async def load_from_checkpoint(
        self,
        start: float,
        end: float,
        checkpoint: ConnectorCheckpoint,
    ) -> Generator[SlimDocument | HierarchyNode, None, None]:
        emails_to_crawl = checkpoint.user_emails or []
        
        for email in emails_to_crawl:
            if email not in checkpoint.completion_map:
                checkpoint.completion_map[email] = StageCompletion(stage="crawling", completed_until=start)

            completion = checkpoint.completion_map[email]
            if completion.stage == "done":
                continue

            logger.info(f"Starting Outlook crawl for user: {email}")

            has_more_pages = True
            next_link = completion.next_page_token
            messages_fetched = 0
            
            endpoint = f"/users/{email}/mailFolders/{self.folder_id}/messages" if self.folder_id else f"/users/{email}/messages"

            while has_more_pages and messages_fetched < self.max_results:
                url = next_link if next_link else endpoint
                params = None if next_link else {"$top": min(50, self.max_results - messages_fetched)}
                
                try:
                    # execute_graph_request handles full urls if passed
                    res = await execute_graph_request(self.auth_manager, "GET", url, params=params)
                except Exception as e:
                    logger.error(f"Failed to list Outlook messages for {email}: {e}")
                    completion.next_page_token = next_link
                    checkpoint.has_more = True
                    return

                messages = res.get("value", [])
                for msg in messages:
                    msg_id = msg.get("id")
                    if not msg_id or msg_id in checkpoint.all_retrieved_file_ids:
                        continue

                    messages_fetched += 1
                    
                    meta = {
                        "message_id": msg_id,
                        "user_email": email,
                        "source_type": "outlook_message"
                    }

                    yield SlimDocument(
                        id=msg_id,
                        source="outlook",
                        metadata=meta,
                    )

                    checkpoint.all_retrieved_file_ids.add(msg_id)

                next_link = res.get("@odata.nextLink")
                completion.next_page_token = next_link
                has_more_pages = bool(next_link)

            completion.stage = "done"

        all_done = all(comp.stage == "done" for comp in checkpoint.completion_map.values())
        checkpoint.has_more = not all_done
        return
