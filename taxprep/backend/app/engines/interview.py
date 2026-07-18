"""Adaptive interview engine: evaluates the question graph against current answers."""
from .rules_loader import load_rules

def next_questions(answers: dict, limit: int = 5) -> list[dict]:
    """Return the next unanswered, visible questions."""
    qs = load_rules("questions")["questions"]
    out = []
    for q in qs:
        if q["id"] in answers:
            continue
        cond = q.get("show_if")
        if cond:
            try:
                if not eval(cond, {"__builtins__": {}}, {"answers": answers}):
                    continue
            except Exception:
                continue
        out.append({k: q[k] for k in ("id", "section", "text", "type") } | ({"options": q["options"]} if "options" in q else {}))
        if len(out) >= limit:
            break
    return out

def progress(answers: dict) -> dict:
    qs = load_rules("questions")["questions"]
    visible = 0
    answered = 0
    for q in qs:
        cond = q.get("show_if")
        show = True
        if cond:
            try:
                show = bool(eval(cond, {"__builtins__": {}}, {"answers": answers}))
            except Exception:
                show = False
        if show:
            visible += 1
            if q["id"] in answers:
                answered += 1
    return {"answered": answered, "visible": visible,
            "pct": round(100 * answered / visible) if visible else 0}
