"""Publication identity must remain compatible with the API's strict wire shape."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pipeline.models import ActiveIndex


def test_publication_identity_is_immutable_and_serializable() -> None:
    identity = ActiveIndex("rahbar-g1", "g1", "nomic-embed-text", 768)
    assert identity.metadata() == {"collection": "rahbar-g1", "generation": "g1",
                                   "embed_model": "nomic-embed-text", "dimension": 768}
    with pytest.raises(FrozenInstanceError):
        identity.generation = "g2"


@pytest.mark.parametrize("changes", [
    {"collection": ""}, {"generation": " "}, {"embed_model": ""},
    {"dimension": 0}, {"dimension": -1}, {"dimension": True},
])
def test_invalid_publication_identity_rejected(changes: dict) -> None:
    data = {"collection": "rahbar-g1", "generation": "g1",
            "embed_model": "nomic-embed-text", "dimension": 768}
    with pytest.raises(ValueError):
        ActiveIndex(**{**data, **changes})
