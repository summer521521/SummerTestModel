"""Generic deterministic tool-loop engine. Formal tool schemas remain architect-owned."""
from __future__ import annotations
from typing import Any, Callable

class ToolLoopEngine:
    def __init__(self, registry: dict[str, Callable[[dict[str, Any]], Any]], max_rounds: int = 3):
        self.registry, self.max_rounds = registry, max_rounds

    def run(self, messages: list[dict[str, Any]], assistant_turn: Callable[[list[dict[str, Any]]], dict[str, Any]]) -> dict[str, Any]:
        history = list(messages)
        for round_index in range(1, self.max_rounds + 1):
            turn = assistant_turn(history)
            calls = turn.get("tool_calls") or []
            history.append({"role": "assistant", **turn})
            if not calls: return {"status": "completed", "rounds": round_index, "messages": history, "final_answer": turn.get("content")}
            for call in calls:
                name = (call.get("function") or {}).get("name") or call.get("name")
                args = (call.get("function") or {}).get("arguments", call.get("arguments", {}))
                if name not in self.registry: return {"status":"tool_not_found","rounds":round_index,"messages":history,"error":name}
                if not isinstance(args, dict): return {"status":"tool_call_invalid","rounds":round_index,"messages":history,"error":"arguments must be object"}
                try: result = self.registry[name](args)
                except Exception as exc: return {"status":"tool_execution_error","rounds":round_index,"messages":history,"error":f"{type(exc).__name__}: {exc}"}
                history.append({"role":"tool","name":name,"content":result})
        return {"status":"tool_loop_limit","rounds":self.max_rounds,"messages":history}
