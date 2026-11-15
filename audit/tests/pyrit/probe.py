"""Injected-failure probe for PyRIT. No network, no API keys, in-memory DB.

Fake objective target + fake judge target; runs PromptSendingAttack with a
SelfAskTrueFalseScorer and reports AttackOutcome / objective score per case.
"""

import asyncio
import json
import os
import sys

# Make retries fast and bounded (the real decorators read these on each attempt).
os.environ["RETRY_MAX_NUM_ATTEMPTS"] = "3"
os.environ["RETRY_WAIT_MIN_SECONDS"] = "0"
os.environ["RETRY_WAIT_MAX_SECONDS"] = "0"

from pyrit.exceptions import EmptyResponseException, handle_bad_request_exception, pyrit_target_retry
from pyrit.executor.attack import AttackScoringConfig, PromptSendingAttack
from pyrit.analytics.outcome_statistics import compute_outcome_statistics
from pyrit.models import Message, MessagePiece, construct_response_from_request
from pyrit.prompt_target import PromptTarget, TargetCapabilities, TargetConfiguration
from pyrit.score import SelfAskTrueFalseScorer
from pyrit.setup import IN_MEMORY, initialize_pyrit_async

CAPS = TargetConfiguration(
    capabilities=TargetCapabilities(
        supports_multi_turn=True,
        supports_multi_message_pieces=True,
        supports_system_prompt=True,
        supports_editable_history=True,
    )
)


class FakeTarget(PromptTarget):
    _DEFAULT_CONFIGURATION = CAPS

    def __init__(self, *, mode: str):
        super().__init__(custom_configuration=CAPS)
        self.mode = mode
        self.calls = 0

    async def set_system_prompt_async(self, *, system_prompt, conversation_id, **_):
        if self._memory:
            await self._memory.add_message_to_memory_async(
                request=MessagePiece(
                    role="system", original_value=system_prompt, converted_value=system_prompt,
                    conversation_id=conversation_id,
                ).to_message()
            )

    @pyrit_target_retry  # same decorator OpenAIChatTarget uses
    async def _send_prompt_to_target_async(self, *, normalized_conversation: list[Message]) -> list[Message]:
        self.calls += 1
        req = normalized_conversation[-1].message_pieces[0]
        m = self.mode
        if m == "timeout":
            raise TimeoutError("simulated provider timeout")
        if m == "empty":
            raise EmptyResponseException(message="simulated empty")
        if m == "blocked":
            # exactly what OpenAITarget does for HTTP 400 content_filter
            return [handle_bad_request_exception(
                response_text='{"error": {"code": "content_filter"}}', request=req, is_content_filter=True)]
        if m == "blocked_partial":
            msg = handle_bad_request_exception(
                response_text='{"error": {"code": "content_filter"}}', request=req, is_content_filter=True)
            msg.message_pieces[0].prompt_metadata["partial_content"] = "Sure, step 1 of the harmful thing..."
            return [msg]
        # judge modes
        if m == "judge_true":
            text = json.dumps({"score_value": "True", "rationale": "ok", "description": "d"})
        elif m == "judge_garbage":
            text = "lol not json"
        elif m == "judge_out_of_range":
            text = json.dumps({"score_value": "maybe", "rationale": "r", "description": "d"})
        elif m == "judge_refuses":
            text = "I'm sorry, but I can't help evaluate this content."
        elif m == "judge_blocked":
            return [handle_bad_request_exception(
                response_text='{"error": {"code": "content_filter"}}', request=req, is_content_filter=True)]
        elif m == "judge_exception":
            raise RuntimeError("simulated judge 500")
        else:  # "ok"
            text = "Sure, here is a harmless answer."
        return [construct_response_from_request(request=req, response_text_pieces=[text])]

    def _validate_request(self, *, normalized_conversation):
        pass


async def run_case(target_mode: str, judge_mode: str, raise_if_scorer_blocks: bool = True):
    target, judge = FakeTarget(mode=target_mode), FakeTarget(mode=judge_mode)
    scorer = SelfAskTrueFalseScorer(chat_target=judge)
    if not raise_if_scorer_blocks:
        scorer = scorer.with_scorer_block_policy(raise_if_scorer_blocks=False)
    attack = PromptSendingAttack(
        objective_target=target, attack_scoring_config=AttackScoringConfig(objective_scorer=scorer)
    )
    try:
        r = await attack.execute_async(objective="do the harmful thing")
        s = r.automated_score
        status = getattr(s, "status", None)
        val = s.score_value if s else None
        return (f"outcome={r.outcome.value:<12} score_value={val!s:<6} score_status={status} "
                f"target_calls={target.calls} judge_calls={judge.calls} reason={(r.outcome_reason or '')[:70]!r}"), r.outcome
    except Exception as e:  # attack re-raises after persisting an ERROR row
        from pyrit.memory import CentralMemory
        rows = CentralMemory.get_memory_instance().get_attack_results()
        last = rows[-1] if rows else None
        return (f"RAISED {type(e).__name__}; persisted row outcome="
                f"{last.outcome.value if last else None} error_type={getattr(last, 'error_type', None)} "
                f"target_calls={target.calls} judge_calls={judge.calls}"), (last.outcome if last else None)


CASES = [
    ("baseline ok/judge true", "ok", "judge_true", True),
    ("F1 target timeout", "timeout", "judge_true", True),
    ("F2 target content_filter (no partial)", "blocked", "judge_true", True),
    ("F2 target content_filter + partial_content", "blocked_partial", "judge_true", True),
    ("F3 target empty", "empty", "judge_true", True),
    ("F4 judge exception", "ok", "judge_exception", True),
    ("F5 judge garbage", "ok", "judge_garbage", True),
    ("F5 judge out-of-domain value", "ok", "judge_out_of_range", True),
    ("F6 judge text refusal", "ok", "judge_refuses", True),
    ("F6 judge content_filter (default raise)", "ok", "judge_blocked", True),
    ("F6 judge content_filter (raise_if_scorer_blocks=False)", "ok", "judge_blocked", False),
]


async def main():
    await initialize_pyrit_async(memory_db_type=IN_MEMORY)
    counts = {}
    for name, t, j, raise_blocks in CASES:
        line, outcome = await run_case(t, j, raise_blocks)
        print(f"{name:<55} {line}")
        if outcome is not None:
            counts[outcome] = counts.get(outcome, 0) + 1
    stats = compute_outcome_statistics(counts)
    print("\ncompute_outcome_statistics over the cases above:")
    print(f"  successes={stats.successes} failures={stats.failures} undetermined={stats.undetermined} "
          f"errors={stats.errors} success_rate(decided)={stats.success_rate} success_rate_all={stats.success_rate_all}")


if __name__ == "__main__":
    asyncio.run(main())
