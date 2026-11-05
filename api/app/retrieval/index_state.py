"""Read-only, request-scoped active generation resolution."""
from typing import Any

from ..schemas import ActiveIndex


class IndexStateError(RuntimeError):
    """Absent, incompatible or corrupt published index state."""


def resolve_active(client: Any, base: str) -> tuple[ActiveIndex, Any]:
    try:
        control = client.get_collection(name=base + "_active", embedding_function=None)
        active = ActiveIndex.model_validate(control.metadata)
        if not active.collection.startswith(base + "__g_"):
            raise IndexStateError("Published collection is outside the configured namespace")
        collection = client.get_collection(name=active.collection, embedding_function=None)
        metadata = collection.metadata or {}
        if any(metadata.get(key) != getattr(active, key)
               for key in ("embed_model", "dimension", "generation")):
            raise IndexStateError("Published identity disagrees with collection metadata")
        if metadata.get("hnsw:space") != "cosine" or collection.count() <= 0:
            raise IndexStateError("Published collection must be nonempty cosine data")
        return active, collection
    except IndexStateError:
        raise
    except Exception:
        raise IndexStateError("Published index is unavailable or invalid") from None
