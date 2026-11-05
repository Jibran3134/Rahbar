"""Bounded Redis turns shared by API replicas; no process-local conversation state."""
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

MAX_TURNS = 6


@dataclass(frozen=True)
class Turn:
    session_id: str
    question: str
    original: str
    follow_up: bool


class SessionStore:
    def __init__(self, client: Any, ttl: int):
        self.client, self.ttl = client, ttl

    @staticmethod
    def key(session_id: str) -> str:
        return "rahbar:session:v1:" + session_id

    def prepare(self, question: str, session_id: str | None) -> Turn:
        if session_id is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}",session_id):
            raise ValueError("Invalid session_id")
        history = self.client.lrange(self.key(session_id),-MAX_TURNS,-1) if session_id else []
        if not history:
            return Turn(uuid.uuid4().hex,question,question,False)
        previous = json.loads(history[-1])["question"][:500]
        elliptical = bool(re.match(r"(?:and\b|what about\b|how about\b|under (?:the )?old\b|"
                                   r"does (?:it|that)\b|why\b|when\b)",question.strip(),re.I))
        resolved = f"Previous question: {previous}\nFollow-up question: {question}" if elliptical else question
        return Turn(session_id or "",resolved,question,True)

    def save(self, turn: Turn, answer: str) -> None:
        payload = json.dumps({"question":turn.original[:500],"answer":answer[:1000]})
        with self.client.pipeline(transaction=True) as pipe:
            pipe.rpush(self.key(turn.session_id),payload)
            pipe.ltrim(self.key(turn.session_id),-MAX_TURNS,-1)
            pipe.expire(self.key(turn.session_id),self.ttl)
            pipe.execute()


def redis_client(url: str) -> Any:
    from redis import Redis
    return Redis.from_url(url,decode_responses=True,socket_connect_timeout=2,socket_timeout=2)
