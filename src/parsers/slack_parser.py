"""
Parser module for Slack thread exports (JSON format).

Reconstructs Slack conversations into threaded hierarchies while
preserving chronological ordering, metadata and ACL information.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import config
from .base import (
    DocumentParser,
    ParsedDocument,
    DocumentSection,
    SourceType,
)

logger = logging.getLogger(__name__)


class SlackParser(DocumentParser):
    """
    Parser for Slack JSON exports.

    Every Slack thread becomes a DocumentSection.
    The complete channel becomes one ParsedDocument.
    """

    def supported_extensions(self) -> List[str]:
        """
        Supported extensions.
        """
        return [".json"]

    @staticmethod
    def _format_timestamp(
        ts_str: Optional[str],
    ) -> str:
        """
        Convert Slack Unix timestamp into a human-readable datetime.

        Args:
            ts_str:
                Slack timestamp string
                (example: "1718022010.123456")

        Returns:
            Formatted datetime string.
        """

        if not ts_str:
            return "Unknown Time"

        try:
            timestamp = float(ts_str)
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, OverflowError):
            logger.warning(
                "Invalid Slack timestamp: %s",
                ts_str,
            )
            return "Unknown Time"

    def parse(
        self,
        file_path: Path,
    ) -> List[ParsedDocument]:

        file_path = Path(file_path)

        if not file_path.exists():

            raise FileNotFoundError(
                f"Slack JSON file not found: {file_path}"
            )

        logger.info(
            f"Parsing Slack export: {file_path.name}"
        )

        logger.info(
            "File size: %.2f KB",
            file_path.stat().st_size / 1024,
        )

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as f:

            messages: List[Dict[str, Any]] = json.load(f)

        if not isinstance(messages, list):

            logger.warning(
                "Skipping non-Slack JSON file: %s",
                file_path.name,
            )

            return []

        logger.info(
            "Loaded %d Slack messages",
            len(messages),
        )

        # --------------------------------------------------
        # Build Thread Dictionary
        # --------------------------------------------------

        threads: Dict[str, Dict[str, Any]] = {}

        orphan_messages: List[Dict[str, Any]] = []

        for msg in messages:

            ts = msg.get("ts")

            thread_ts = msg.get("thread_ts")

            if not thread_ts or thread_ts == ts:

                threads[ts] = {

                    "parent": msg,

                    "replies": [],

                }

            else:

                orphan_messages.append(msg)

        for msg in orphan_messages:

            thread_ts = msg.get("thread_ts")

            if thread_ts in threads:

                threads[thread_ts]["replies"].append(msg)

            else:

                threads[thread_ts] = {

                    "parent": msg,

                    "replies": [],

                }

        for thread in threads.values():

            thread["replies"].sort(
                key=lambda x: float(
                    x.get("ts", 0)
                )
            )

        sorted_threads = sorted(
            threads.items(),
            key=lambda x: float(x[0]),
        )

        # --------------------------------------------------
        # Load ACL
        # --------------------------------------------------

        acl_tags = ["all"]

        permissions_path = Path(
            config.PERMISSIONS_FILE
        )

        if permissions_path.exists():

            try:

                with open(
                    permissions_path,
                    "r",
                    encoding="utf-8",
                ) as fp:

                    permissions = json.load(fp)

                    acl_tags = (
                        permissions
                        .get("documents", {})
                        .get(
                            file_path.name,
                            ["all"],
                        )
                    )

            except Exception as exc:

                logger.warning(
                    f"ACL loading failed: {exc}"
                )

        sections: List[DocumentSection] = []

        all_thread_texts: List[str] = []

        channel_name = file_path.stem
        
                # --------------------------------------------------
        # Reconstruct Conversations
        # --------------------------------------------------

        for index, (thread_ts, thread_data) in enumerate(
            sorted_threads
        ):

            parent = thread_data["parent"]

            replies = thread_data["replies"]

            parent_user = parent.get(
                "user",
                "unknown",
            )

            parent_text = parent.get(
                "text",
                "",
            )

            parent_time = self._format_timestamp(
                parent.get("ts")
            )

            channel = parent.get(
                "channel",
                f"#{channel_name}",
            )

            thread_lines = [

                f"Channel: {channel}",

                f"Conversation Started: {parent_time}",

                "",

                f"@{parent_user}:",

                parent_text,

            ]

            if replies:

                thread_lines.append("")
                thread_lines.append("Replies")

                for reply in replies:

                    reply_user = reply.get(
                        "user",
                        "unknown",
                    )

                    reply_text = reply.get(
                        "text",
                        "",
                    )

                    reply_time = (
                        self._format_timestamp(
                            reply.get("ts")
                        )
                    )

                    thread_lines.extend(

                        [

                            "",

                            f"@{reply_user}",

                            f"Time: {reply_time}",

                            reply_text,

                        ]

                    )

            thread_content = "\n".join(
                thread_lines
            ).strip()

            all_thread_texts.append(
                thread_content
            )

            preview = (
                parent_text[:60] + "..."
                if len(parent_text) > 60
                else parent_text
            )

            heading = (
                f"Conversation {index + 1}: "
                f"{preview}"
            )

            sections.append(

                DocumentSection(

                    heading=heading,

                    heading_level=1,

                    heading_path=(
                        f"{channel_name}"
                        f" > Conversation {index + 1}"
                    ),

                    content=thread_content,

                )

            )

        # --------------------------------------------------
        # Build ParsedDocument
        # --------------------------------------------------

        full_content = (
            "\n\n-------------------------\n\n"
            .join(all_thread_texts)
            .strip()
        )

        if not full_content:

            raise ValueError(
                f"No readable Slack messages found "
                f"in {file_path}"
            )

        logger.info(

            "Generated %d conversation sections",

            len(sections),

        )

        title = (

            channel_name

            .replace("-", " ")

            .replace("_", " ")

            .title()

        )

        doc_id = hashlib.sha256(

            full_content.encode("utf-8")

        ).hexdigest()

        document = ParsedDocument(

            doc_id=doc_id,

            content=full_content,

            source_type=SourceType.SLACK,

            title=title,

            source_path=str(
                file_path.resolve()
            ),

            metadata={

                "source_file": file_path.name,

                "file_size": file_path.stat().st_size,

                "parser": "slack",

                "channel": f"#{channel_name}",

                "thread_count": len(sorted_threads),

                "message_count": len(messages),

                "section_count": len(sections),

                "extension": file_path.suffix,

            },

            sections=sections,

            tables=[],

            acl_tags=acl_tags,

            is_scanned=False,

        )

        return [document]