"""Parser module for Slack thread exports (JSON format).

Reconstructs Slack conversations into threaded hierarchies and resolves user/channel metadata.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import config
from .base import DocumentParser, ParsedDocument, DocumentSection, SourceType

logger = logging.getLogger(__name__)


class SlackParser(DocumentParser):
    """Parser for Slack chat exports.

    Organizes message streams into coherent thread chains (parent + replies),
    maintaining timeline and contextual links.
    """

    def supported_extensions(self) -> List[str]:
        """Supported file extensions.

        Returns:
            List of extensions: ['.json']
        """
        return [".json"]

    def parse(self, file_path: Path) -> List[ParsedDocument]:
        """Parse a Slack export JSON file.

        Args:
            file_path: Absolute path to the JSON file.

        Returns:
            A list containing a single ParsedDocument.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Slack JSON file not found: {file_path}")

        logger.info(f"Parsing Slack JSON file: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            messages: List[Dict[str, Any]] = json.load(f)

        if not isinstance(messages, list):
            raise ValueError(f"Slack JSON export must contain a list of messages: {file_path}")

        # 1. Group messages by threads
        # A thread is keyed by the parent message 'ts'
        threads: Dict[str, Dict[str, Any]] = {}
        standalone_messages: List[Dict[str, Any]] = []

        # Find parent messages first
        for msg in messages:
            ts = msg.get("ts")
            thread_ts = msg.get("thread_ts")
            
            # If thread_ts is null or thread_ts matches ts, it is a parent message
            if not thread_ts or thread_ts == ts:
                threads[ts] = {
                    "parent": msg,
                    "replies": []
                }
            else:
                standalone_messages.append(msg)

        # Place replies in their threads
        for msg in standalone_messages:
            thread_ts = msg.get("thread_ts")
            if thread_ts in threads:
                threads[thread_ts]["replies"].append(msg)
            else:
                # If parent wasn't found in this file, treat reply as parent of a new thread
                threads[thread_ts] = {
                    "parent": msg,
                    "replies": []
                }

        # Sort replies by timestamp inside each thread
        for t_ts in threads:
            threads[t_ts]["replies"].sort(key=lambda x: float(x.get("ts", 0)))

        # 2. Reconstruct threads as document sections
        sections: List[DocumentSection] = []
        all_thread_texts: List[str] = []
        channel_name = file_path.stem

        # Load ACL permissions
        acl_tags = ["all"]
        permissions_path = Path(config.PERMISSIONS_FILE)
        if permissions_path.exists():
            try:
                with open(permissions_path, "r", encoding="utf-8") as pf:
                    perms = json.load(pf)
                    acl_tags = perms.get("documents", {}).get(file_path.name, ["all"])
            except Exception as e:
                logger.warning(f"Failed to load permissions file: {e}")

        # Parse thread contents
        for index, (t_ts, thread_data) in enumerate(threads.items()):
            parent = thread_data["parent"]
            replies = thread_data["replies"]

            parent_user = parent.get("user", "unknown")
            parent_text = parent.get("text", "")
            parent_time = self._format_timestamp(parent.get("ts"))
            channel = parent.get("channel", f"#{channel_name}")

            # Reconstruct layout
            thread_text_parts = [
                f"In channel {channel}, @{parent_user} posted at {parent_time}:",
                f"\"{parent_text}\""
            ]

            if replies:
                thread_text_parts.append("\nThread Replies:")
                for r in replies:
                    r_user = r.get("user", "unknown")
                    r_text = r.get("text", "")
                    r_time = self._format_timestamp(r.get("ts"))
                    thread_text_parts.append(f"  - @{r_user} replied at {r_time}: \"{r_text}\"")

            thread_content = "\n".join(thread_text_parts)
            all_thread_texts.append(thread_content)

            # Cap heading at first 60 chars of parent message
            heading_preview = parent_text[:60] + "..." if len(parent_text) > 60 else parent_text
            heading = f"Thread by @{parent_user}: {heading_preview}"

            sections.append(
                DocumentSection(
                    heading=heading,
                    heading_level=1,
                    heading_path=f"{channel} > {heading}",
                    content=thread_content
                )
            )

        full_content = "\n\n---\n\n".join(all_thread_texts)
        doc_id = hashlib.md5(str(file_path.resolve()).encode("utf-8")).hexdigest()
        title = f"Slack Export: #{channel_name}"

        doc = ParsedDocument(
            doc_id=doc_id,
            content=full_content,
            source_type=SourceType.SLACK,
            title=title,
            source_path=str(file_path.resolve()),
            metadata={"channel": f"#{channel_name}", "thread_count": len(threads)},
            sections=sections,
            tables=[],
            acl_tags=acl_tags,
            is_scanned=False
        )

        return [doc]

    @staticmethod
    def _format_timestamp(ts_str: Optional[str]) -> str:
        """Convert Slack Unix timestamp string to human-readable format."""
        if not ts_str:
            return "unknown time"
        try:
            ts_float = float(ts_str)
            dt = datetime.fromtimestamp(ts_float)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "unknown time"
