"""Session bounds, isolation and contextual follow-up tests."""
import json

import pytest


class RedisDouble:
    def __init__(self):
        self.data, self.ttls = {}, {}
    def lrange(self,key,start,end):
        return self.data.get(key,[])[start:None if end == -1 else end+1]
    def pipeline(self,**kwargs):
        return self
    def __enter__(self):
        return self
    def __exit__(self,*args):
        pass
    def rpush(self,key,*values):
        self.data.setdefault(key,[]).extend(values)
        return self
    def ltrim(self,key,start,end):
        self.data[key] = self.data[key][start:None if end == -1 else end+1]
        return self
    def expire(self,key,ttl):
        self.ttls[key]=ttl
        return self
    def execute(self):
        return []


def test_followup_uses_prior_question_and_isolated_session_has_no_history():
    from app.services.sessions import SessionStore
    redis = RedisDouble()
    store = SessionStore(redis,ttl=30)
    first = store.prepare("What is the withdrawal deadline?",None)
    store.save(first,"Makeup week.")
    next_turn = store.prepare("And under the old rules?",first.session_id)
    assert next_turn.follow_up and "withdrawal deadline" in next_turn.question
    assert "old rules" in next_turn.question
    other = store.prepare("And under the old rules?",None)
    assert not other.follow_up and other.session_id != first.session_id
    assert list(redis.ttls.values()) == [30]


def test_history_bounds_unknown_ids_and_invalid_ids():
    from app.services.sessions import MAX_TURNS, SessionStore
    store = SessionStore(RedisDouble(),ttl=10)
    turn = store.prepare("Question about policy",None)
    for _ in range(15):
        store.save(turn,"x"*5000)
    raw = store.client.lrange(store.key(turn.session_id),0,-1)
    assert len(raw) == MAX_TURNS and len(json.loads(raw[0])["answer"]) <= 1000
    assert store.prepare("Next question","unknown").session_id != "unknown"
    for bad in ["../secret","", "a"*129]:
        with pytest.raises(ValueError):
            store.prepare("Question",bad)
