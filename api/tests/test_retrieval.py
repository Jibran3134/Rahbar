"""Offline real-retriever semantics, with read-only Chroma and HTTP doubles."""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.config import Settings
from app.retrieval.chroma import ChromaRetriever


class Client:
    def __init__(self):
        self.calls = []
        self.model = "nomic-embed-text"
        self.dimension = 2
        self.rows = {"ids":[["one"]],"documents":[["Deadline is makeup week."]],
                     "metadatas":[[dict(source="a.pdf",section="4.25",page=23,
                                        doc_version="2026-06",superseded=False)]],"distances":[[.2]]}
    def get_collection(self, name, **kwargs):
        self.calls.append(name)
        if name == "rahbar_active":
            return SimpleNamespace(metadata=dict(collection="rahbar__g_a",generation="a",
                embed_model=self.model,dimension=self.dimension))
        return SimpleNamespace(metadata={"generation":"a","embed_model":self.model,
            "dimension":self.dimension,"hnsw:space":"cosine"},count=lambda:1,query=self.query)
    def query(self, **kwargs):
        self.query_args = kwargs
        return self.rows


def retrieve(client, question="What is the current deadline?", vector=None):
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={"embeddings":[vector if vector is not None else [1,0]]})
    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        result = ChromaRetriever(Settings(),client=client,http_client=http).retrieve(question,5)
    return result, requests


def test_explicit_vector_prefix_cosine_conversion_small_index_and_one_snapshot():
    client = Client()
    hits, requests = retrieve(client)
    assert hits[0].score == .8 and hits[0].page == 23
    assert requests == [dict(model="nomic-embed-text",input=["search_query: What is the current deadline?"],truncate=False)]
    assert client.query_args["query_embeddings"] == [[1,0]]
    assert client.query_args["n_results"] == 1 and client.query_args["where"] == {"superseded":False}
    assert client.calls == ["rahbar_active","rahbar__g_a"]


@pytest.mark.parametrize("question", ["Does CS-2023 need prerequisites?", "I joined in 2023; what is the rule?",
    "Is the fee Rs 2023?", "My exam is on 2023-08-10. What is attendance?", "What are current rules?"])
def test_unrelated_numbers_dates_and_course_codes_keep_current_default(question):
    client = Client()
    retrieve(client,question)
    assert client.query_args["where"] == {"superseded":False}


@pytest.mark.parametrize("question", ["Under the August 2023 undergraduate rules, what was the deadline?",
                                     "According to the 2023-08 handbook, what was the load?"])
def test_explicit_historical_version_filter(question):
    client = Client()
    client.rows["metadatas"][0][0].update(superseded=True,doc_version="2023-08")
    retrieve(client,question)
    assert client.query_args["where"] == {"doc_version":"2023-08"}


def test_empty_results_and_html_logical_page():
    client = Client()
    client.rows = {key:[[]] for key in client.rows}
    assert retrieve(client)[0] == []
    client = Client()
    client.rows["metadatas"][0][0]["source"] = "fee.html"
    assert retrieve(client)[0][0].page is None


@pytest.mark.parametrize("failure", ["model","dimension","nan","metadata","distance"])
def test_conflicts_and_corrupt_hits_fail_closed(failure,caplog):
    client = Client()
    if failure == "model":
        client.model = "other-model"
    if failure == "dimension":
        client.dimension = 3
    if failure == "metadata":
        del client.rows["metadatas"][0][0]["page"]
    if failure == "distance":
        client.rows["distances"][0][0] = float("nan")
    from app.retrieval.index_state import IndexStateError
    with pytest.raises(IndexStateError):
        retrieve(client,vector=[float("nan"),1] if failure == "nan" else None)
    if failure=="model":
        assert any(getattr(r,"actual_model",None)=="other-model" and getattr(r,"expected_model",None)=="nomic-embed-text"
                   for r in caplog.records)


def test_constructor_does_not_connect():
    # Invalid hostname is safe until an explicit dependency operation.
    assert ChromaRetriever(Settings(chroma_host="does-not-exist.invalid")).name == "chroma"
