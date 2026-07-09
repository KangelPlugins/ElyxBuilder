from dataclasses import dataclass
from enum import Enum, auto
from .errors import ParseError

class TokenType(Enum):
    KW_VAL = auto()
    KW_STEP = auto()
    KW_ENGINE = auto()
    KW_IF = auto()
    KW_ELSE = auto()
    KW_PARALLEL = auto()
    KW_TIMEOUT = auto()
    KW_RETRY = auto()
    KW_TRUE = auto()
    KW_FALSE = auto()
    IDENT = auto()
    STRING = auto()
    NUMBER = auto()
    OP_PLUS = auto()
    OP_EQ = auto()
    OP_NEQ = auto()
    OP_AND = auto()
    OP_OR = auto()
    OP_NOT = auto()
    OP_ASSIGN = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    EOF = auto()


KEYWORDS = {
    "val": TokenType.KW_VAL,
    "step": TokenType.KW_STEP,
    "engine": TokenType.KW_ENGINE,
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "parallel": TokenType.KW_PARALLEL,
    "timeout": TokenType.KW_TIMEOUT,
    "retry": TokenType.KW_RETRY,
    "true": TokenType.KW_TRUE,
    "false": TokenType.KW_FALSE,
}

ESCAPE_MAP = {
    '"': '"',
    '\\': '\\',
    'n': '\n',
    't': '\t',
}


@dataclass
class Token:
    type: TokenType
    value: object  # str | int | None
    line: int

def tokenize(source, filename="<input>"):
    tokens = []
    i = 0
    line = 1
    n = len(source)

    while i < n:
        c = source[i]

        # newline
        if c == '\n':
            line += 1
            i += 1
            continue

        # whitespace
        if c in ' \t\r':
            i += 1
            continue

        # comment
        if c == '/' and i + 1 < n and source[i + 1] == '/':
            while i < n and source[i] != '\n':
                i += 1
            continue

        # string literal
        if c == '"':
            start_line = line
            i += 1
            buf = []
            while i < n:
                ch = source[i]
                if ch == '\n':
                    raise ParseError("unterminated string", filename, start_line)
                if ch == '\\':
                    i += 1
                    if i >= n or source[i] == '\n':
                        raise ParseError("unterminated string", filename, start_line)
                    esc = source[i]
                    if esc not in ESCAPE_MAP:
                        raise ParseError(f"unknown escape sequence \\{esc}", filename, line)
                    buf.append(ESCAPE_MAP[esc])
                    i += 1
                    continue
                if ch == '"':
                    i += 1
                    break
                buf.append(ch)
                i += 1
            else:
                raise ParseError("unterminated string", filename, start_line)
            tokens.append(Token(TokenType.STRING, ''.join(buf), start_line))
            continue

        # number
        if c.isdigit():
            start = i
            while i < n and source[i].isdigit():
                i += 1
            tokens.append(Token(TokenType.NUMBER, int(source[start:i]), line))
            continue

        # id or kw
        if c.isalpha() or c == '_':
            start = i
            while i < n and (source[i].isalnum() or source[i] == '_'):
                i += 1
            word = source[start:i]
            ttype = KEYWORDS.get(word, TokenType.IDENT)
            tokens.append(Token(ttype, word, line))
            continue

        # 2-chan(char) ops
        if c == '=' and i + 1 < n and source[i + 1] == '=':
            tokens.append(Token(TokenType.OP_EQ, '==', line))
            i += 2
            continue

        if c == '!' and i + 1 < n and source[i + 1] == '=':
            tokens.append(Token(TokenType.OP_NEQ, '!=', line))
            i += 2
            continue

        if c == '&' and i + 1 < n and source[i + 1] == '&':
            tokens.append(Token(TokenType.OP_AND, '&&', line))
            i += 2
            continue

        if c == '|' and i + 1 < n and source[i + 1] == '|':
            tokens.append(Token(TokenType.OP_OR, '||', line))
            i += 2
            continue

        # 1-chan(char) tokens
        single = {
            '+': TokenType.OP_PLUS,
            '!': TokenType.OP_NOT,
            '=': TokenType.OP_ASSIGN,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            ',': TokenType.COMMA,
        }
        if c in single:
            tokens.append(Token(single[c], c, line))
            i += 1
            continue

        raise ParseError(f"unexpected character: {c!r}", filename, line)

    tokens.append(Token(TokenType.EOF, None, line))
    return tokens
