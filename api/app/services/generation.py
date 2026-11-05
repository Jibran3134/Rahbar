"""One validation retry; transport failures immediately return a safe fallback."""
import logging

from ..providers.llm.base import MAX_GENERATION_ATTEMPTS, LLMProvider, ProviderError, ProviderFailureKind
from ..schemas import Answer, Passage
from .grounding import validate_grounding
from ..routes import metrics
from .safety import quarantine
from .relevance import abstention

log = logging.getLogger("rahbar.generation")


def generate_verified(question: str, passages: list[Passage], provider: LLMProvider) -> Answer:
    safe_question,safe_passages,removed=quarantine(question,passages)
    if removed:
        log.warning("instruction blocks quarantined",extra={"removed_blocks":removed})
        metrics.field("instruction_blocks_removed",removed)
    if not safe_question or not safe_passages:
        return abstention()
    feedback: str | None = None
    for attempt in range(MAX_GENERATION_ATTEMPTS):
        try:
            if attempt:
                log.info("retry generation after validation failure",extra={"attempt":attempt+1,"provider":provider.name})
            output = (provider.generate(safe_question,safe_passages) if attempt == 0
                      else provider.generate(safe_question,safe_passages,feedback=feedback))
            if provider.name!="ollama":
                metrics.tokens((len(question)+sum(len(p.text) for p in passages)+3)//4,
                               (len(str(output))+3)//4,"estimated")
            return validate_grounding(output,passages)
        except ProviderError as exc:
            log.warning("generation validation/failure",extra={"failure_kind":exc.kind.value,
                        "attempt":attempt+1,"provider":provider.name})
            if exc.kind in {ProviderFailureKind.TIMEOUT,ProviderFailureKind.TRANSPORT}:
                break
            label = f"[{passages[0].source} / {passages[0].section}]" if passages else "[source / section]"
            feedback = (f"{exc.kind.value}: Every factual sentence needs an exact filename citation, "
                        f"e.g. {label}. Never use evidence numbers. Match citation object pages.")
    log.warning("generation fallback",extra={"fallback":True,"provider":provider.name})
    metrics.FALLBACKS.inc()
    metrics.field("fallback",True)
    return Answer(reasoning="Generation could not be verified within the attempt limit.",
                  answer="I could not produce a verified answer from the supplied documents. "
                         "Please check the original policy documents.",
                  citations=[],answered_from_context=False,confidence="low")
