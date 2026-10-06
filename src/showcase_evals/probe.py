"""Small real-inference tool round-trip probe, not an agent safety benchmark."""

import json
import time

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, Target, accuracy, scorer
from inspect_ai.solver import Generate, TaskState, generate, solver, use_tools
from inspect_ai.tool import tool
from inspect_ai.util import store

ORDERS = {
    "sample-a": {
        "order_id": "sample-a",
        "quantity": 3,
        "unit_price_cents": 1250,
        "approval": "pending",
    },
    "sample-b": {
        "order_id": "sample-b",
        "quantity": 2,
        "unit_price_cents": 1875,
        "approval": "approved",
    },
}


@tool
def lookup_order():
    async def execute(order_id: str) -> str:
        """Read a fictional order from the study fixture.

        Args:
            order_id: Exact order identifier from the user's request.
        """
        if order_id not in ORDERS:
            return json.dumps({"error": "unknown order"})
        store().set("looked_up_order", order_id)
        return json.dumps(ORDERS[order_id])

    return execute


@solver
def timed_probe():
    async def solve(state: TaskState, generate_fn: Generate) -> TaskState:
        started = time.perf_counter()
        try:
            state = await use_tools(lookup_order())(state, generate_fn)
            return await generate(tool_calls="loop")(state, generate_fn)
        finally:
            store().set("agent_seconds", time.perf_counter() - started)

    return solve


@scorer(metrics=[accuracy()])
def checked_order():
    async def score(state: TaskState, target: Target) -> Score:
        text = state.output.completion.strip()
        if text.startswith("```") and text.endswith("```"):
            text = "\n".join(text.splitlines()[1:-1]).strip()
        try:
            answer = json.loads(text)
        except (ValueError, TypeError):
            answer = None
        expected = json.loads(target.text)
        used_tool = store().get("looked_up_order") == expected["order_id"]
        passed = answer == expected and used_tool
        return Score(
            value=int(passed),
            answer=state.output.completion,
            explanation="Exact JSON result and actual fixture tool use are required.",
            metadata={"used_tool": used_tool, "expected": expected},
        )

    return score


@task
def provider_probe() -> Task:
    samples = []
    for identifier, order in ORDERS.items():
        expected = {
            "order_id": identifier,
            "total_cents": order["quantity"] * order["unit_price_cents"],
            "can_send": order["approval"] == "approved",
        }
        samples.append(
            Sample(
                id=identifier,
                input=(
                    f"Use lookup_order to read {identifier}. Return only a JSON object with "
                    "order_id, total_cents (quantity times unit_price_cents), and can_send "
                    "(true only if approval is approved). Do not send anything."
                ),
                target=json.dumps(expected),
            )
        )
    return Task(
        dataset=samples,
        solver=timed_probe(),
        scorer=checked_order(),
        message_limit=8,
        metadata={"study_kind": "provider_compatibility_pilot"},
    )
