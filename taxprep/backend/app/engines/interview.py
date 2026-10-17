"""Adaptive interview engine: evaluates the question graph (rules/<year>/questions.yaml) against answers.

`show_if` conditions are evaluated with a tiny whitelisted AST interpreter (no eval), because the
rule packs are editable from the admin panel.  Supported: answers.get('id') / answers.get('id', default),
string/number/bool/None literals, ==, !=, <, <=, >, >=, in, not in, and, or, not, parentheses.
"""
import ast
from .rules_loader import load_rules

_CMP = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b,
        ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
        ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}


def _ev(node, answers):
    if isinstance(node, ast.Expression):
        return _ev(node.body, answers)
    if isinstance(node, ast.BoolOp):
        vals = (_ev(v, answers) for v in node.values)
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _ev(node.operand, answers)
    if isinstance(node, ast.Compare):
        left = _ev(node.left, answers)
        for op, comp in zip(node.ops, node.comparators):
            right = _ev(comp, answers)
            fn = _CMP.get(type(op))
            if fn is None or not fn(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_ev(e, answers) for e in node.elts]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "answers"
            and not node.keywords and 1 <= len(node.args) <= 2):
        args = [_ev(a, answers) for a in node.args]
        return answers.get(*args)
    raise ValueError(f"Unsupported expression: {ast.dump(node)[:80]}")


def evaluate(cond: str, answers: dict) -> bool:
    return bool(_ev(ast.parse(cond, mode="eval"), answers))


def _visible(q, answers) -> bool:
    cond = q.get("show_if")
    if not cond:
        return True
    try:
        return evaluate(cond, answers)
    except Exception:
        return False


def next_questions(answers: dict, limit: int = 5) -> list[dict]:
    """Return the next unanswered, visible questions."""
    out = []
    for q in load_rules("questions")["questions"]:
        if q["id"] in answers or not _visible(q, answers):
            continue
        out.append({k: q[k] for k in ("id", "section", "text", "type") if k in q}
                   | ({"options": q["options"]} if "options" in q else {})
                   | ({"help": q["help"]} if "help" in q else {}))
        if len(out) >= limit:
            break
    return out


def progress(answers: dict) -> dict:
    visible = answered = 0
    for q in load_rules("questions")["questions"]:
        if _visible(q, answers):
            visible += 1
            answered += q["id"] in answers
    return {"answered": answered, "visible": visible,
            "pct": round(100 * answered / visible) if visible else 100}
