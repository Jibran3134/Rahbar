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
        self.total = 1
        self.page_rows={'documents':[],'metadatas':[]}
        self.rows = {"ids":[["one"]],"documents":[["Deadline is makeup week."]],
                     "metadatas":[[dict(source="a.pdf",section="4.25",page=23,
                                        doc_version="2026-06",superseded=False)]],"distances":[[.2]]}
    def get_collection(self, name, **kwargs):
        self.calls.append(name)
        if name == "rahbar_active":
            return SimpleNamespace(metadata=dict(collection="rahbar__g_a",generation="a",
                embed_model=self.model,dimension=self.dimension))
        return SimpleNamespace(metadata={"generation":"a","embed_model":self.model,
            "dimension":self.dimension,"hnsw:space":"cosine"},count=lambda:self.total,query=self.query,get=self.get)
    def query(self, **kwargs):
        self.query_args = kwargs
        return self.rows
    def get(self, **kwargs):
        self.page_args=kwargs
        return self.page_rows


def retrieve(client, question="What is the current deadline?", vector=None, k=5):
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={"embeddings":[vector if vector is not None else [1,0]]})
    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        result = ChromaRetriever(Settings(),client=client,http_client=http).retrieve(question,k)
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


def test_title_only_hit_is_replaced_by_real_clause_without_changing_score():
    client=Client()
    client.total=10
    meta=client.rows['metadatas'][0][0]
    client.rows={
        'ids':[['title','clause','numeric']],
        'documents':[['Academic Warning/Probation','Warning is issued when CGPA drops below 2.00.','12,000']],
        'metadatas':[[{**meta,'section':'Academic Warning/Probation'},
                      {**meta,'section':'5.5'},{**meta,'section':'Tuition'}]],
        'distances':[[.1,.2,.3]],
    }
    hits,requests=retrieve(client,question='What is academic warning?',k=1)
    assert [h.chunk_id for h in hits]==['clause']
    assert hits[0].section=='5.5' and hits[0].score==.8
    assert client.query_args['n_results']==3 and len(requests)==1
    hits,_=retrieve(client,k=5)
    assert [h.chunk_id for h in hits]==['clause','numeric']
    assert client.query_args['n_results']==10  # Bounded by actual collection size.


@pytest.mark.parametrize('text,section',[
    ('Academic Warning/Probation','Academic Warning/Probation'),
    ('# 2. Academic warning','2. Academic warning'),
    ('5.4','5.4'),
])
def test_heading_only_normalization(text,section):
    from app.retrieval.chroma import heading_only
    assert heading_only(text,section)


def heading_client():
    client=Client()
    meta=client.rows['metadatas'][0][0]
    meta.update(section='Academic Warning/Probation',page=24)
    client.rows['documents']=[['Academic Warning/Probation']]
    client.page_rows={'documents':['Academic Warning/Probation',
        '5.5 Warning is issued when CGPA drops below 2.00 at the end of a semester.'],
        'metadatas':[dict(meta),{**meta,'section':'5.5'}]}
    return client


def test_matched_heading_expands_to_real_same_page_policy_with_original_score():
    client=heading_client()
    hits,_=retrieve(client)
    assert len(hits)==1 and hits[0].score==.8 and hits[0].chunk_id=='one'
    assert hits[0].section=='Academic Warning/Probation' and hits[0].page==24
    assert 'Section 5.5:' in hits[0].text and 'CGPA drops below 2.00' in hits[0].text
    assert client.page_args['where']=={'$and':[
        {'source':'a.pdf'},{'page':24},{'doc_version':'2026-06'},{'superseded':False}]}
    assert client.page_args['limit']==32 and len(hits[0].text)<=1800


@pytest.mark.parametrize('change',[
    {'source':'another.pdf'},{'page':25},{'page':24.0},
    {'doc_version':'2023-08'},{'superseded':True},
])
def test_parent_context_identity_mismatch_fails_closed(change):
    from app.retrieval.index_state import IndexStateError
    client=heading_client()
    client.page_rows['metadatas'][1].update(change)
    with pytest.raises(IndexStateError):
        retrieve(client)


def test_parent_context_bounds_keep_whole_blocks_and_html_is_not_expanded():
    from app.retrieval.chroma import page_context
    client=heading_client()
    meta=client.rows['metadatas'][0][0]
    client.page_rows={'documents':['Sentence. '*90]*12,
                      'metadatas':[{**meta,'section':f'5.{i}'} for i in range(12)]}
    result=page_context(client,'Academic Warning/Probation',meta)
    assert result and len(result)<=1800 and result.endswith('Sentence. ')
    assert page_context(client,'Heading',{**meta,'source':'page.html'}) is None
