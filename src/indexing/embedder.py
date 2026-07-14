"""Embedding generation module for NexusRAG.

Supports two backends, selected via ``config.EMBEDDING_BACKEND``:

* ``"gemini"`` (default) — calls the Google ``text-embedding-004`` API.
  No local model download, no RAM pressure, 768-dimensional vectors.
  Requires ``GEMINI_API_KEY`` in the environment / ``.env`` file.

* ``"local"`` — wraps ``sentence-transformers`` (e.g. BAAI/bge-small-en-v1.5).
  Needs ~600 MB+ RAM and a local model download.
"""

import logging
import re
import time
from typing import List, Union

import numpy as np

from src.config import config

logger = logging.getLogger(__name__)

# gemini-embedding-001 produces 3072-dimensional vectors.
_GEMINI_DIMENSION = 3072
# Sensible fallback when bge-small-en-v1.5 dimension cannot be queried.
_LOCAL_DIMENSION_FALLBACK = 384


# ---------------------------------------------------------------------------
# Gemini embedding backend (API, no local model)
# ---------------------------------------------------------------------------

class _GeminiBackend:
    """Calls the Gemini Embedding REST API using only ``requests``.

    No ``google.generativeai`` SDK is imported — grpc and protobuf pull in
    hundreds of MB of bytecode that triggers MemoryError on low-RAM machines.
    Plain HTTP + JSON uses negligible memory.

    REST endpoints used:
    * ``batchEmbedContents`` — embeds a list of texts in one round-trip.
    * ``embedContent``       — embeds a single text (query).
    """

    _BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self._api_key = api_key
        self._session = None  # requests.Session, created lazily

    def _get_session(self):
        if self._session is None:
            if not self._api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set.\n"
                    "Create a .env file in the project root with:\n"
                    "    GEMINI_API_KEY=your-key-here\n"
                    "Get a free key at: https://aistudio.google.com/apikey"
                )
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                # Disable gzip: prevents urllib3 holding compressed + decompressed
                # data in RAM simultaneously, which causes MemoryError on low-RAM machines.
                "Accept-Encoding": "identity",
            })
            logger.info("Gemini REST backend ready (model=%s)", self.model_name)
        return self._session

    def _post(self, endpoint: str, body: dict) -> dict:
        """POST *body* to *endpoint* and return the parsed JSON response."""
        session = self._get_session()
        url = f"{self._BASE}/{endpoint}?key={self._api_key}"
        resp = session.post(url, json=body, timeout=15)
        if not resp.ok:
            raise RuntimeError(
                f"Gemini API error {resp.status_code}: {resp.text[:400]}"
            )
        return resp.json()

    def encode(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 32,
    ) -> np.ndarray:
        """Embed *texts* via ``embedContent`` calls and return (N, 768) float32."""
        all_vectors: List[List[float]] = []
        model_id = self.model_name.split('/')[-1]
        total = len(texts)

        for idx, text in enumerate(texts):
            body = {
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
            }
            data = self._post(f"models/{model_id}:embedContent", body)
            all_vectors.append(data["embedding"]["values"])
            if (idx + 1) % 5 == 0 or idx == 0 or (idx + 1) == total:
                logger.info("  embedded %d / %d chunks", idx + 1, total)

        arr = np.array(all_vectors, dtype=np.float32)
        # L2-normalise for reliable cosine similarity
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return arr / norms

    def encode_single(self, text: str, task_type: str = "RETRIEVAL_QUERY") -> np.ndarray:
        """Embed a single string via ``embedContent``."""
        model_id = self.model_name.split('/')[-1]
        body = {
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        }
        data = self._post(f"models/{model_id}:embedContent", body)
        vec = np.array(data["embedding"]["values"], dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    @property
    def dimension(self) -> int:
        return _GEMINI_DIMENSION


# ---------------------------------------------------------------------------
# Local SentenceTransformer backend
# ---------------------------------------------------------------------------

class _LocalBackend:
    """Lazy-loading sentence-transformers backend."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._dimension: int | None = None

    @property
    def _st_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading local embedding model: %s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
                logger.info(
                    "Local model loaded — dimension: %d",
                    self._model.get_sentence_embedding_dimension(),
                )
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Run: pip install sentence-transformers"
                ) from exc
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load local embedding model '{self.model_name}': {exc}"
                ) from exc
        return self._model

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True,
    ) -> np.ndarray:
        return self._st_model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    def encode_single(self, text: str) -> np.ndarray:
        return self._st_model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            try:
                self._dimension = self._st_model.get_sentence_embedding_dimension()
            except Exception:
                self._dimension = _LOCAL_DIMENSION_FALLBACK
        return self._dimension


# ---------------------------------------------------------------------------
# Public Embedder class
# ---------------------------------------------------------------------------

class Embedder:
    """Generates dense vector embeddings for NexusRAG.

    The active backend is selected from ``config.EMBEDDING_BACKEND``:

    * ``"gemini"`` — Google ``text-embedding-004`` API (default, no RAM cost).
    * ``"local"`` — local SentenceTransformer model.

    All public methods share the same interface regardless of backend.
    """

    def __init__(self, model_name: str = None, backend: str = None):
        self._backend_name = (backend or config.EMBEDDING_BACKEND).lower()

        if self._backend_name == "gemini":
            _model = model_name or config.GEMINI_EMBEDDING_MODEL
            self.model_name = _model
            self._backend = _GeminiBackend(
                model_name=_model,
                api_key=config.GEMINI_API_KEY,
            )
        elif self._backend_name == "local":
            _model = model_name or config.EMBEDDING_MODEL
            self.model_name = _model
            self._backend = _LocalBackend(model_name=_model)
        else:
            raise ValueError(
                f"Unknown EMBEDDING_BACKEND '{self._backend_name}'. "
                "Choose 'gemini' or 'local'."
            )

        logger.info("Embedder initialised (backend=%s, model=%s)", self._backend_name, self.model_name)

    # ------------------------------------------------------------------
    # Health / info
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        """Return True if the backend has been initialised / connected."""
        if self._backend_name == "gemini":
            return self._backend._session is not None
        return self._backend._model is not None

    @property
    def dimension(self) -> int:
        """Embedding vector dimensionality (768 for Gemini, 384 for bge-small)."""
        return self._backend.dimension

    @property
    def info(self) -> dict:
        """Return a summary dict — useful for logging and health-check endpoints.

        Example::

            >>> embedder.info
            {'backend': 'gemini', 'model': 'models/text-embedding-004', 'dimension': 768}
        """
        return {
            "backend": self._backend_name,
            "model": self.model_name,
            "dimension": self.dimension,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(text: str) -> str:
        """Collapse whitespace and strip leading/trailing spaces."""
        return re.sub(r"\s+", " ", text).strip()

    # ------------------------------------------------------------------
    # Embedding methods
    # ------------------------------------------------------------------

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = None,
        show_progress: bool = True,
        return_numpy: bool = False,
    ) -> Union[List[List[float]], np.ndarray]:
        """Generate normalised dense embeddings for a list of text strings.

        Empty or whitespace-only strings are silently dropped before encoding.

        Args:
            texts: List of text inputs to embed.
            batch_size: Batch size for inference. Defaults to
                ``config.EMBED_BATCH_SIZE``.
            show_progress: Show a progress bar (local backend only).
            return_numpy: Return a 2-D ``numpy.ndarray`` instead of a list of
                float lists (useful when Qdrant prefers NumPy arrays).

        Returns:
            A list of float lists (default) or a 2-D ``numpy.ndarray``.
        """
        if not texts:
            return np.empty((0,), dtype=np.float32) if return_numpy else []

        # Clean and drop blank inputs
        cleaned: List[str] = [self._clean(t) for t in texts]
        cleaned = [t for t in cleaned if t]

        if not cleaned:
            logger.warning("embed_texts: all input texts were empty after cleaning.")
            return np.empty((0,), dtype=np.float32) if return_numpy else []

        effective_batch = batch_size if batch_size is not None else config.EMBED_BATCH_SIZE
        logger.info(
            "Embedding %d texts via '%s' backend (batch_size=%d)…",
            len(cleaned), self._backend_name, effective_batch,
        )

        t0 = time.perf_counter()

        if self._backend_name == "gemini":
            embeddings = self._backend.encode(
                cleaned, batch_size=effective_batch
            )
        else:
            embeddings = self._backend.encode(
                cleaned,
                batch_size=effective_batch,
                show_progress=show_progress,
            )

        elapsed = time.perf_counter() - t0
        logger.info(
            "Generated embeddings — count: %d | dimension: %d | time: %.2f s",
            embeddings.shape[0], embeddings.shape[1], elapsed,
        )

        return embeddings if return_numpy else embeddings.tolist()

    def embed_chunks(
        self,
        chunks,
        batch_size: int = None,
        show_progress: bool = True,
        return_numpy: bool = False,
    ) -> Union[List[List[float]], np.ndarray]:
        """Generate embeddings for a list of ``Chunk`` objects.

        Extracts ``chunk.content`` from each chunk and delegates to
        :meth:`embed_texts`.  This is the canonical method to call from
        the indexing pipeline.

        Args:
            chunks: Iterable of ``Chunk`` dataclass instances.
            batch_size: Forwarded to :meth:`embed_texts`.
            show_progress: Forwarded to :meth:`embed_texts`.
            return_numpy: Forwarded to :meth:`embed_texts`.

        Returns:
            Same as :meth:`embed_texts`.
        """
        texts = [c.content for c in chunks]
        return self.embed_texts(
            texts,
            batch_size=batch_size,
            show_progress=show_progress,
            return_numpy=return_numpy,
        )

    def embed_query(self, query: str) -> List[float]:
        """Generate a normalised dense embedding for a single query string.

        Uses ``retrieval_query`` task type when the Gemini backend is active,
        which improves retrieval accuracy.

        Args:
            query: User search query. Must be non-empty.

        Returns:
            A list of floats representing the normalised embedding vector.

        Raises:
            ValueError: If *query* is empty or contains only whitespace.
        """
        cleaned = self._clean(query)
        if not cleaned:
            raise ValueError("Query cannot be empty.")

        embedding: np.ndarray = self._backend.encode_single(cleaned)
        return embedding.tolist()
