"""Deterministic regression set from the seed problems (spec 08 "generated").

``python -m mathtutor.verify.mutate [bundle] [out]`` writes ``generated/mutations.jsonl``.
Every case is a MathJSON tree built directly from the seed answer's tree (never by parsing a
string), with a label that holds by construction. The set is regression-only: it is reported
separately and never cited as accuracy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from mathtutor.content.loader import ContentError, LoadedContent, load_bundle
from mathtutor.content.schema import ExpressionAnswer

DEFAULT_CONTENT = Path("content/compiled/problems.json")
DEFAULT_OUT = Path("evals/verifier/generated/mutations.jsonl")
_PRODUCTS = ("InvisibleOperator", "Multiply")

Tree = Any


def _is_int(node: Tree) -> bool:
    return isinstance(node, int) and not isinstance(node, bool)


def _is_literal(node: Tree) -> bool:
    return _is_int(node) or (isinstance(node, dict) and set(node) == {"num"})


def _is_zero(node: Tree) -> bool:
    return bool(node == 0 or node == {"num": "0"})


def _has_symbol(node: Tree, name: str) -> bool:
    if isinstance(node, list):
        return any(_has_symbol(child, name) for child in node)
    return bool(node == name)


def _negate(node: Tree) -> Tree:
    return node[1] if isinstance(node, list) and node[0] == "Negate" else ["Negate", node]


def _terms(node: Tree) -> list[Tree]:
    """Top-level summands, with ``a - b`` read as ``a + (-b)``."""
    if isinstance(node, list) and node[0] == "Add":
        return [term for arg in node[1:] for term in _terms(arg)]
    if isinstance(node, list) and node[0] == "Subtract" and len(node) == 3:
        return [*_terms(node[1]), _negate(node[2])]
    return [node]


def _sum(terms: list[Tree]) -> Tree:
    return terms[0] if len(terms) == 1 else ["Add", *terms]


def _bump_coefficient(term: Tree) -> Tree | None:
    """The term with its integer coefficient raised by one, or None when it has none."""
    if _is_int(term):
        return term + 1
    if isinstance(term, list) and term[0] == "Negate" and len(term) == 2:
        inner = _bump_coefficient(term[1])
        return None if inner is None else ["Negate", inner]
    if isinstance(term, list) and term[0] in _PRODUCTS and len(term) > 2 and _is_int(term[1]):
        return [term[0], term[1] + 1, *term[2:]]
    if isinstance(term, list) and term[0] == "Divide" and len(term) == 3 and _is_int(term[1]):
        return ["Divide", term[1] + 1, term[2]]
    return None


def _drop_factors(term: Tree) -> list[Tree]:
    """The term with each non-numeric factor removed in turn."""
    if not (isinstance(term, list) and term[0] in _PRODUCTS and len(term) > 2):
        return []
    factors = term[1:]
    out: list[Tree] = []
    for j, factor in enumerate(factors):
        if _is_literal(factor):
            continue
        rest = factors[:j] + factors[j + 1 :]
        out.append(rest[0] if len(rest) == 1 else [term[0], *rest])
    return out


def _split_two(term: Tree) -> Tree | None:
    """``2·u`` rewritten as ``u + u``, or None when the term is not of that shape."""
    if isinstance(term, list) and term[0] == "Negate" and len(term) == 2:
        inner = _split_two(term[1])
        return None if inner is None else ["Negate", inner]
    if isinstance(term, list) and term[0] in _PRODUCTS and len(term) > 2 and term[1] == 2:
        rest = term[2:]
        u = rest[0] if len(rest) == 1 else [term[0], *rest]
        return ["Add", u, u]
    if isinstance(term, list) and term[0] == "Divide" and len(term) == 3 and term[1] == 2:
        half = ["Divide", 1, term[2]]
        return ["Add", half, half]
    return None


def _exponent_sites(node: Tree, variable: str, path: tuple[int, ...] = ()) -> list[tuple[int, ...]]:
    """Paths to integer exponents of a power whose base involves the variable."""
    if not isinstance(node, list):
        return []
    sites: list[tuple[int, ...]] = []
    if (
        node[0] == "Power"
        and len(node) == 3
        and _is_int(node[2])
        and _has_symbol(node[1], variable)
    ):
        sites.append((*path, 2))
    for i, child in enumerate(node[1:], 1):
        sites += _exponent_sites(child, variable, (*path, i))
    return sites


def _replace_at(node: Tree, path: tuple[int, ...], value: Tree) -> Tree:
    if not path:
        return value
    copy = list(node)
    copy[path[0]] = _replace_at(node[path[0]], path[1:], value)
    return copy


def _get_at(node: Tree, path: tuple[int, ...]) -> Tree:
    for step in path:
        node = node[step]
    return node


def _variants(tree: Tree, variable: str) -> list[tuple[str, str, Tree]]:
    """(label, rationale, tree) in a fixed order."""
    terms = _terms(tree)
    whole = _sum(terms)
    out: list[tuple[str, str, Tree]] = []
    for i, term in enumerate(terms):
        if not _is_zero(term):
            flipped = [*terms[:i], _negate(term), *terms[i + 1 :]]
            out.append(("incorrect", f"sign of term {i + 1} flipped", _sum(flipped)))
    for i, term in enumerate(terms):
        for dropped in _drop_factors(term):
            changed = [*terms[:i], dropped, *terms[i + 1 :]]
            out.append(
                ("incorrect", f"a non-numeric factor of term {i + 1} dropped", _sum(changed))
            )
    for i, term in enumerate(terms):
        bumped = _bump_coefficient(term)
        if bumped is not None:
            changed = [*terms[:i], bumped, *terms[i + 1 :]]
            out.append(("incorrect", f"coefficient of term {i + 1} raised by one", _sum(changed)))
    for path in _exponent_sites(whole, variable):
        exponent = _get_at(whole, path)
        changed_tree = _replace_at(whole, path, exponent + 1)
        out.append(("incorrect", f"exponent {exponent} raised by one", changed_tree))
    if len(terms) > 1:
        out.append(("correct", "terms reversed (a+b = b+a)", _sum(terms[::-1])))
    for i, term in enumerate(terms):
        split = _split_two(term)
        if split is not None:
            changed = [*terms[:i], split, *terms[i + 1 :]]
            out.append(("correct", f"2u of term {i + 1} written as u+u", _sum(changed)))
    return out


def mutate(content: LoadedContent) -> list[dict[str, Any]]:
    """The generated cases for every expression-kind seed problem, in a stable order."""
    cases: list[dict[str, Any]] = []
    for problem in content.bundle.problems:
        answer = problem.answer
        if not isinstance(answer, ExpressionAnswer):
            continue
        counts = {"correct": 0, "incorrect": 0}
        seen: set[str] = {json.dumps(answer.mathjson, sort_keys=True)}
        for label, rationale, tree in _variants(answer.mathjson, answer.variable):
            key = json.dumps(tree, sort_keys=True)
            if key in seen:  # a repeat, or the answer itself: never mislabel it
                continue
            seen.add(key)
            counts[label] += 1
            cases.append(
                {
                    "id": f"{problem.id}.{label}.{counts[label]}",
                    "family": problem.id,
                    "problem_id": problem.id,
                    "answer": {"mathjson": tree, "latex": ""},
                    "label": label,
                    "rationale": f"generated: {rationale}",
                    "reviewer": "generated",
                }
            )
    return cases


def dump(cases: list[dict[str, Any]]) -> bytes:
    text = "".join(json.dumps(c, sort_keys=True, ensure_ascii=False) + "\n" for c in cases)
    return text.encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    bundle = Path(args[0]) if args else DEFAULT_CONTENT
    out = Path(args[1]) if len(args) > 1 else DEFAULT_OUT
    try:
        content = load_bundle(bundle)
    except ContentError as error:
        print(error)
        return 1
    cases = mutate(content)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(dump(cases))
    print(f"wrote {len(cases)} cases to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
