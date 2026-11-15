"""Injected-failure probe for TAP / PAIR / Crescendo. No network, in-memory DB."""

import asyncio
import json
import os

os.environ["RETRY_MAX_NUM_ATTEMPTS"] = "2"
os.environ["RETRY_WAIT_MIN_SECONDS"] = "0"
os.environ["RETRY_WAIT_MAX_SECONDS"] = "0"

from probe import FakeTarget  # noqa: E402  (reuses the fake target; -I is not used for this file)

from pyrit.executor.attack import (  # noqa: E402
    AttackAdversarialConfig,
    AttackScoringConfig,
    CrescendoAttack,
    PAIRAttack,
    TreeOfAttacksWithPruningAttack,
)
from pyrit.executor.attack.multi_turn.tree_of_attacks import TAPAttackScoringConfig  # noqa: E402
from pyrit.models import construct_response_from_request  # noqa: E402
from pyrit.score import FloatScaleThresholdScorer, SelfAskScaleScorer, SelfAskTrueFalseScorer  # noqa: E402
from pyrit.setup import IN_MEMORY, initialize_pyrit_async  # noqa: E402


class Adversary(FakeTarget):
    async def _send_prompt_to_target_async(self, *, normalized_conversation):
        self.calls += 1
        req = normalized_conversation[-1].message_pieces[0]
        text = json.dumps({"next_message": f"attack prompt {self.calls}", "rationale": "r",
                           "last_response_summary": "s"})
        return [construct_response_from_request(request=req, response_text_pieces=[text])]


class ScaleJudge(FakeTarget):
    async def _send_prompt_to_target_async(self, *, normalized_conversation):
        self.calls += 1
        req = normalized_conversation[-1].message_pieces[0]
        text = json.dumps({"score_value": "1", "rationale": "low", "description": "d"})
        return [construct_response_from_request(request=req, response_text_pieces=[text])]


class MixedTarget(FakeTarget):
    """First call answers normally, every later call raises (one branch scored, others crash)."""

    async def _send_prompt_to_target_async(self, *, normalized_conversation):
        self.calls += 1
        if self.calls > 1:
            raise TimeoutError("simulated provider timeout")
        req = normalized_conversation[-1].message_pieces[0]
        return [construct_response_from_request(request=req, response_text_pieces=["I won't help."])]


def tap_scoring(judge):
    return TAPAttackScoringConfig(objective_scorer=FloatScaleThresholdScorer(
        scorer=SelfAskScaleScorer.from_scale(chat_target=judge), threshold=0.7))


async def tap(cls, target, **kw):
    adv, judge = Adversary(mode="adv"), ScaleJudge(mode="j")
    extra = dict(tree_width=3, tree_depth=1)
    if cls is TreeOfAttacksWithPruningAttack:
        extra.update(branching_factor=1, on_topic_checking_enabled=False)
    attack = cls(objective_target=target, attack_adversarial_config=AttackAdversarialConfig(target=adv),
                 attack_scoring_config=tap_scoring(judge), **extra)
    r = await attack.execute_async(objective="do the harmful thing")
    return (f"outcome={r.outcome.value:<12} nodes_pruned={r.metadata.get('nodes_pruned')} "
            f"error_message={(r.error_message or '')[:50]!r} target_calls={target.calls} "
            f"reason={(r.outcome_reason or '')[:90]!r}")


async def crescendo(target):
    adv, judge = Adversary(mode="adv"), FakeTarget(mode="judge_true")
    attack = CrescendoAttack(
        objective_target=target, attack_adversarial_config=AttackAdversarialConfig(target=adv),
        attack_scoring_config=AttackScoringConfig(objective_scorer=SelfAskTrueFalseScorer(chat_target=judge)),
        max_turns=2, max_backtracks=2)
    try:
        r = await attack.execute_async(objective="do the harmful thing")
        return (f"outcome={r.outcome.value:<12} backtracks={r.backtrack_count} target_calls={target.calls} "
                f"judge_calls={judge.calls} reason={(r.outcome_reason or '')[:70]!r}")
    except Exception as e:
        return f"RAISED {type(e).__name__}: {str(e)[:120]}"


async def main():
    await initialize_pyrit_async(memory_db_type=IN_MEMORY)
    out = [
        ("TAP all branches timeout", await tap(TreeOfAttacksWithPruningAttack, FakeTarget(mode="timeout"))),
        ("TAP 1 branch scored, 2 timeout", await tap(TreeOfAttacksWithPruningAttack, MixedTarget(mode="x"))),
        ("TAP all branches content_filter", await tap(TreeOfAttacksWithPruningAttack, FakeTarget(mode="blocked"))),
        ("TAP all branches empty", await tap(TreeOfAttacksWithPruningAttack, FakeTarget(mode="empty"))),
        ("PAIR all streams timeout", await tap(PAIRAttack, FakeTarget(mode="timeout"))),
        ("Crescendo content_filter every turn", await crescendo(FakeTarget(mode="blocked"))),
        ("Crescendo empty every turn", await crescendo(FakeTarget(mode="empty"))),
        ("Crescendo timeout", await crescendo(FakeTarget(mode="timeout"))),
    ]
    print()
    for name, line in out:
        print(f"{name:<38} {line}")


if __name__ == "__main__":
    asyncio.run(main())
