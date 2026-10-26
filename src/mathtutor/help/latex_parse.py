"""Allowlisted LaTeX -> MathJSON for the leak guard. Pure Python: runs in the web process.

Model-written hint math is parsed here; the SymPy checker (in verifier workers) then decides
whether a candidate equals the reference answer. Only an explicit command allowlist is read,
by recursive descent; anything else is ``ParseRejected``. Nothing is ever evaluated.

Reading rules (parser version 1):

- Juxtaposition multiplies (``2x``, ``x(x+1)``); ``\\left``/``\\right``, ``\\,``, ``\\!`` and
  sizing commands are layout only. ``-ab`` is ``-(ab)``.
- Ambiguous forms are rejected (unchecked), not guessed: a juxtaposed factor after the right
  operand of an inline ``/`` or ``\\div`` (``1/2x``); a number after a factor (``x2``, ``x^23``,
  ``1e5``, as translate rejects it); digits split by spacing (``2\\,3``).
- One-token arguments follow TeX: ``\\frac12``, ``x^2``.
- ``\\sin^n x`` is ``Power(Sin(x), n)`` for an integer n >= 1 (``\\sin^{-1}`` is rejected).
- A function input in parentheses (or ``|..|``) is that group; without them it is the run of
  juxtaposed factors up to the next function, operator or sign: ``\\sin 7x`` = ``Sin(7x)``,
  ``\\sec x\\tan x`` = ``Sec(x)Tan(x)``.
- Single letters other than the variable and ``e`` (and ``\\pi``) are foreign, as are Greek
  letters, primed or subscripted names, letter applications ``f(x)`` and ``\\frac{d}{dx}``-style
  operators (``d/dx``, ``dy/dx``). A tree with foreign names is never sent to the checker.

Rejection reasons are fixed strings: they never echo the input.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from pydantic import JsonValue

PARSER_VERSION = "1"
# Equal to help_config.json guard limits (max_candidate_bytes, max_nodes, max_depth).
MAX_BYTES = 400
MAX_NODES = 200
MAX_DEPTH = 24
MAX_DIGITS = 30


@dataclass(frozen=True)
class ParsedMath:
    tree: JsonValue
    foreign: frozenset[str]


@dataclass(frozen=True)
class ParseRejected:
    reason: str


class _Reject(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


Token = tuple[str, str]  # ("cmd", name) or ("ch", character)

_FUNCTIONS = {
    "sin": "Sin",
    "cos": "Cos",
    "tan": "Tan",
    "sec": "Sec",
    "csc": "Csc",
    "cot": "Cot",
    "ln": "Ln",
    "log": "Log",
    "exp": "Exp",
}
_FRACS = frozenset({"frac", "dfrac", "tfrac"})
_GREEK = frozenset(
    {
        "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "theta", "vartheta",
        "lambda", "mu", "sigma", "tau", "phi", "varphi", "omega", "Delta",
    }
)  # fmt: skip
_LAYOUT = frozenset(
    {
        ",", "!", ";", ":", " ", "quad", "qquad", "displaystyle", "textstyle",
        "big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr",
        "biggl", "biggr", "Biggl", "Biggr",
    }
)  # fmt: skip
_COMMANDS = (
    frozenset(_FUNCTIONS)
    | _FRACS
    | _GREEK
    | {"sqrt", "pi", "left", "right", "cdot", "times", "div", "lvert", "rvert"}
)
_CHARS = frozenset("0123456789+-*/^_{}()[]|.'")
_UNICODE: dict[str, Token] = {
    "−": ("ch", "-"),
    "·": ("cmd", "cdot"),
    "×": ("cmd", "times"),
    "π": ("cmd", "pi"),
}
# \operatorname{sin}, \mathrm{e}, and MathLive's \operatorname{\mathrm{sin}}.
_WRAPPED = re.compile(r"\s*\{\s*(?:\\mathrm\s*\{\s*([A-Za-z]+)\s*\}|([A-Za-z]+))\s*\}")
_DERIV_NUM = re.compile(r"d(?:\^(?:\d|\{\d\}))?[A-Za-z]?")
_DERIV_DEN = re.compile(r"d[A-Za-z](?:\^(?:\d|\{\d\}))?")

_PLUS, _MINUS = ("ch", "+"), ("ch", "-")
_TIMES = frozenset({("ch", "*"), ("cmd", "cdot"), ("cmd", "times")})
_OVER = frozenset({("ch", "/"), ("cmd", "div")})
# After \left: the opener and the closers \right may take.
_LEFT = {
    ("ch", "("): frozenset({("ch", ")"), ("ch", "]")}),
    ("ch", "["): frozenset({("ch", ")"), ("ch", "]")}),
    ("ch", "|"): frozenset({("ch", "|"), ("cmd", "rvert")}),
    ("cmd", "lvert"): frozenset({("ch", "|"), ("cmd", "rvert")}),
}


def _is_letter(c: str) -> bool:
    return c.isascii() and c.isalpha()


def _numeric(token: Token) -> bool:
    return token[0] == "ch" and (token[1].isdigit() or token[1] == ".")


def _tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    gap = False  # spacing was dropped since the last token
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace() or c == "~":
            gap = True
            i += 1
            continue
        if c != "\\":
            mapped = _UNICODE.get(c)
            if mapped is not None:
                tokens.append(mapped)
            elif _is_letter(c) or c in _CHARS:
                if gap and tokens and _numeric(tokens[-1]) and _numeric(("ch", c)):
                    # "2 3", "2\,3": spacing would silently join two numbers.
                    raise _Reject("spaced digits")
                tokens.append(("ch", c))
            else:
                raise _Reject("unsupported character")
            gap = False
            i += 1
            continue
        j = i + 1
        while j < n and _is_letter(src[j]):
            j += 1
        if j == i + 1:
            if j >= n:
                raise _Reject("dangling backslash")
            j += 1
        name = src[i + 1 : j]
        i = j
        if name in _LAYOUT:
            gap = True
            continue
        gap = False
        if name == "vert":
            tokens.append(("ch", "|"))
        elif name in ("operatorname", "mathrm"):
            match = _WRAPPED.match(src, i)
            if match is None:
                raise _Reject("unsupported command")
            word = match.group(1) or match.group(2)
            i = match.end()
            if word in _FUNCTIONS:
                tokens.append(("cmd", word))
            elif len(word) == 1:
                tokens.append(("ch", word))
            else:
                raise _Reject("unsupported command")
        elif name in _COMMANDS:
            tokens.append(("cmd", name))
        else:
            raise _Reject("unsupported command")
    return tokens


def _product(factors: list[JsonValue]) -> JsonValue:
    return factors[0] if len(factors) == 1 else ["Multiply", *factors]


class _Parser:
    def __init__(self, tokens: list[Token], variable: str) -> None:
        self.tokens = tokens
        self.pos = 0
        self.variable = variable
        self.foreign: set[str] = set()
        self.depth = 0
        self.bars = 0  # open |..| groups whose closing bar ends the current expression

    # -- cursor ------------------------------------------------------------------------------

    def peek(self, ahead: int = 0) -> Token | None:
        index = self.pos + ahead
        return self.tokens[index] if index < len(self.tokens) else None

    def take(self) -> Token:
        token = self.peek()
        if token is None:
            raise _Reject("unexpected end of input")
        self.pos += 1
        return token

    def expect(self, allowed: frozenset[Token], reason: str) -> None:
        if self.peek() not in allowed:
            raise _Reject(reason)
        self.pos += 1

    @contextmanager
    def nested(self) -> Iterator[None]:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise _Reject("nested too deeply")
        try:
            yield
        finally:
            self.depth -= 1

    def starts_factor(self, token: Token | None, *, in_argument: bool = False) -> bool:
        """Whether ``token`` begins a factor multiplied by juxtaposition."""
        if token is None:
            return False
        kind, value = token
        if kind == "cmd":
            if value in _FUNCTIONS:
                return not in_argument
            return value in _FRACS or value in _GREEK or value in ("sqrt", "pi", "left", "lvert")
        if value.isdigit() or _is_letter(value) or value in "([{":
            return True
        if value == ".":
            following = self.peek(1)
            return following is not None and following[1].isdigit()
        return value == "|" and self.bars == 0

    # -- grammar -----------------------------------------------------------------------------

    def expression(self) -> JsonValue:
        tree = self.term()
        own_sum = False
        while (token := self.peek()) in (_PLUS, _MINUS):
            self.pos += 1
            rhs = self.term()
            if token == _MINUS:
                tree, own_sum = ["Subtract", tree, rhs], False
            elif own_sum:
                assert isinstance(tree, list)
                tree.append(rhs)
            else:
                tree, own_sum = ["Add", tree, rhs], True
        return tree

    def signs(self) -> int:
        """Consume leading signs; the number of minus signs."""
        minus = 0
        while (token := self.peek()) in (_PLUS, _MINUS):
            self.pos += 1
            minus += token == _MINUS
        return minus

    @staticmethod
    def negated(tree: JsonValue, minus: int) -> JsonValue:
        for _ in range(minus):
            tree = ["Negate", tree]
        return tree

    def term(self) -> JsonValue:
        minus = self.signs()
        return self.negated(self.product(), minus)

    def juxtaposed(self) -> JsonValue:
        """A factor multiplied by juxtaposition; a number there is rejected, as translate does."""
        if _numeric(self.take()):
            raise _Reject("number after a factor")
        self.pos -= 1
        return self.power()

    def product(self) -> JsonValue:
        factors = [self.power()]
        divided = False  # the last factor is the right operand of an inline / or \div
        while True:
            token = self.peek()
            if token in _TIMES:
                self.pos += 1
                minus = self.signs()
                factors.append(self.negated(self.power(), minus))
                divided = False
            elif token in _OVER:
                self.pos += 1
                minus = self.signs()
                factors = [["Divide", _product(factors), self.negated(self.power(), minus)]]
                divided = True
            elif self.starts_factor(token):
                if divided:
                    # 1/2x: x/2 or 1/(2x)? Unchecked rather than guessed.
                    raise _Reject("ambiguous inline division")
                factors.append(self.juxtaposed())
            else:
                return _product(factors)

    def power(self) -> JsonValue:
        base = self.primary()
        if self.peek() == ("ch", "^"):
            self.pos += 1
            base = ["Power", base, self.argument()]
            if self.peek() == ("ch", "^"):
                raise _Reject("double superscript")
        if self.peek() in (("ch", "_"), ("ch", "'")):
            raise _Reject("misplaced subscript or prime")
        return base

    def argument(self) -> JsonValue:
        """A braced group or one token, as TeX reads ``\\frac12`` and ``x^2``."""
        token = self.take()
        kind, value = token
        if token == ("ch", "{"):
            return self.group("}")
        if kind == "ch" and value.isdigit():
            return int(value)
        if kind == "ch" and _is_letter(value):
            return self.symbol(value)
        if kind == "cmd" and (value == "pi" or value in _GREEK):
            return self.command_symbol(value)
        raise _Reject("unsupported argument")

    def group(self, close: str) -> JsonValue:
        """The expression after an opener, through ``close``."""
        with self.nested():
            saved, self.bars = self.bars, 0
            tree = self.expression()
            self.expect(frozenset({("ch", close)}), "unbalanced group")
            self.bars = saved
            return tree

    def primary(self) -> JsonValue:
        token = self.take()
        kind, value = token
        if kind == "ch":
            if value.isdigit() or value == ".":
                self.pos -= 1
                return self.number()
            if _is_letter(value):
                return self.letter(value)
            if value in "([{":
                return self.group({"(": ")", "[": "]", "{": "}"}[value])
            if value == "|":
                return self.bars_abs()
            raise _Reject("missing operand")
        if value == "left":
            return self.left_group()
        if value == "lvert":
            with self.nested():
                saved, self.bars = self.bars, 0
                tree = self.expression()
                self.expect(frozenset({("cmd", "rvert")}), "unbalanced absolute value")
                self.bars = saved
                return ["Abs", tree]
        if value in _FRACS:
            return self.fraction()
        if value == "sqrt":
            return self.root()
        if value in _FUNCTIONS:
            return self.function(value)
        if value == "pi" or value in _GREEK:
            return self.command_symbol(value)
        raise _Reject("missing operand")

    def bars_abs(self) -> JsonValue:
        with self.nested():
            self.bars += 1
            tree = self.expression()
            self.expect(frozenset({("ch", "|")}), "unbalanced absolute value")
            self.bars -= 1
            return ["Abs", tree]

    def left_group(self) -> JsonValue:
        opener = self.take()
        closers = _LEFT.get(opener)
        if closers is None:
            raise _Reject("unsupported delimiter")
        with self.nested():
            saved, self.bars = self.bars, 0
            tree = self.expression()
            self.expect(frozenset({("cmd", "right")}), "unbalanced \\left")
            self.expect(closers, "unbalanced \\left")
            self.bars = saved
        return ["Abs", tree] if opener in (("ch", "|"), ("cmd", "lvert")) else tree

    def number(self) -> JsonValue:
        start = self.pos
        while (token := self.peek()) is not None and token[0] == "ch" and token[1].isdigit():
            self.pos += 1
        following = self.peek(1)
        if self.peek() == ("ch", ".") and following is not None and following[1].isdigit():
            self.pos += 1
            while (token := self.peek()) is not None and token[0] == "ch" and token[1].isdigit():
                self.pos += 1
        text = "".join(t[1] for t in self.tokens[start : self.pos])
        if text in ("", "."):
            raise _Reject("missing operand")
        if sum(c.isdigit() for c in text) > MAX_DIGITS:
            raise _Reject("number too long")
        if "." in text:
            return {"num": "0" + text if text.startswith(".") else text}
        return int(text)

    def symbol(self, name: str) -> JsonValue:
        if name == self.variable:
            return name
        if name == "e":
            return "ExponentialE"
        self.foreign.add(name)
        return name

    def command_symbol(self, name: str) -> JsonValue:
        if name == "pi":
            return "Pi"
        self.foreign.add(name)
        return name

    def letter(self, c: str) -> JsonValue:
        name = c
        if self.peek() == ("ch", "_"):
            self.pos += 1
            name += "_" + self.subscript()
        while self.peek() == ("ch", "'"):
            self.pos += 1
            name += "'"
        tree = self.symbol(name)
        foreign = name != self.variable and name != "e"
        opens = self.peek() == ("ch", "(") or (
            self.peek() == ("cmd", "left") and self.peek(1) == ("ch", "(")
        )
        if foreign and opens:
            # f(x), h'(x): a function of something; foreign, never checked.
            return ["Apply", tree, self.primary()]
        return tree

    def subscript(self) -> str:
        token = self.take()
        if token == ("ch", "{"):
            text = ""
            while (inner := self.take()) != ("ch", "}"):
                if inner[0] != "ch" or not inner[1].isalnum():
                    raise _Reject("unsupported subscript")
                text += inner[1]
            if not text:
                raise _Reject("unsupported subscript")
            return text
        if token[0] == "ch" and token[1].isalnum():
            return token[1]
        raise _Reject("unsupported subscript")

    def raw_argument(self, start: int) -> tuple[str, int]:
        """Text of the braced group or token at ``start`` and the index after it."""
        if start >= len(self.tokens):
            raise _Reject("unexpected end of input")
        if self.tokens[start] != ("ch", "{"):
            kind, value = self.tokens[start]
            return (value if kind == "ch" else "\\" + value), start + 1
        level, end = 0, start
        while end < len(self.tokens):
            level += self.tokens[end] == ("ch", "{")
            level -= self.tokens[end] == ("ch", "}")
            end += 1
            if level == 0:
                break
        else:
            raise _Reject("unbalanced group")
        inner = self.tokens[start + 1 : end - 1]
        return "".join(v if k == "ch" else "\\" + v for k, v in inner), end

    def fraction(self) -> JsonValue:
        num, after = self.raw_argument(self.pos)
        den, end = self.raw_argument(after)
        if _DERIV_NUM.fullmatch(num) and _DERIV_DEN.fullmatch(den):
            # d/dx, dy/dx, d^2y/dx^2: a derivative operator or quotient; foreign.
            self.pos = end
            name = (num + "/" + den).replace("{", "").replace("}", "")
            self.foreign.add(name)
            return name
        with self.nested():
            return ["Divide", self.argument(), self.argument()]

    def root(self) -> JsonValue:
        with self.nested():
            if self.peek() == ("ch", "["):
                self.pos += 1
                index = self.group("]")
                return ["Root", self.argument(), index]
            return ["Sqrt", self.argument()]

    def function(self, name: str) -> JsonValue:
        base: JsonValue = None
        exponent: JsonValue = None
        with self.nested():
            while (token := self.peek()) in (("ch", "_"), ("ch", "^")):
                self.pos += 1
                if token == ("ch", "_"):
                    if name != "log" or base is not None:
                        raise _Reject("unsupported subscript")
                    base = self.argument()
                else:
                    if exponent is not None:
                        raise _Reject("double superscript")
                    exponent = self.argument()
                    if isinstance(exponent, bool) or not isinstance(exponent, int):
                        raise _Reject("inverse or non-integer function power")
                    if exponent < 1:
                        raise _Reject("inverse or non-integer function power")
            token = self.peek()
            if token in (("ch", "("), ("ch", "["), ("cmd", "left"), ("cmd", "lvert")) or (
                token == ("ch", "|")
            ):
                arg = self.primary()
            else:
                arg = self.run()
        tree: JsonValue = [_FUNCTIONS[name], arg] if base is None else ["Log", arg, base]
        return tree if exponent is None else ["Power", tree, exponent]

    def run(self) -> JsonValue:
        """An unparenthesized function input: juxtaposed factors up to the next function."""
        minus = self.signs()
        factors = [self.power()]
        while self.starts_factor(self.peek(), in_argument=True):
            factors.append(self.juxtaposed())
        return self.negated(_product(factors), minus)


def _check_size(tree: JsonValue) -> None:
    """Nodes and depth counted as ``verify.structure.check_structure`` counts them."""
    nodes = 0
    stack: list[tuple[JsonValue, int]] = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES:
            raise _Reject("too many nodes")
        if isinstance(node, list):
            if depth + 1 > MAX_DEPTH:
                raise _Reject("nested too deeply")
            stack.extend((operand, depth + 1) for operand in node[1:])


def parse_latex(src: str, *, variable: str = "x") -> ParsedMath | ParseRejected:
    """Parse ``src`` through the allowlist. Never raises."""
    try:
        if len(src.encode("utf-8")) > MAX_BYTES:
            return ParseRejected("input too long")
        tokens = _tokenize(src)
        if not tokens:
            return ParseRejected("empty input")
        parser = _Parser(tokens, variable)
        tree = parser.expression()
        if parser.peek() is not None:
            return ParseRejected("unexpected token")
        _check_size(tree)
        return ParsedMath(tree, frozenset(parser.foreign))
    except _Reject as rejection:
        return ParseRejected(rejection.reason)
    except Exception as error:  # any surprise is a rejection, never a crash
        return ParseRejected(f"internal error ({type(error).__name__})")
