from dataclasses import dataclass, field
from typing import Optional, Union

# type alias for expr nodes
Expr = object
Stmt = object

@dataclass
class StringLit:
    value: str
    line: int

@dataclass
class NumberLit:
    value: int
    line: int

@dataclass
class BoolLit:
    value: bool
    line: int

@dataclass
class IdentExpr:
    name: str
    line: int

@dataclass
class BinaryExpr:
    op: str
    left: object
    right: object
    line: int

@dataclass
class UnaryExpr:
    op: str
    operand: object
    line: int


# context calls
@dataclass
class OsCall:
    line: int

@dataclass
class RootCall:
    line: int

@dataclass
class ScriptdirCall:
    line: int

@dataclass
class EnvCall:
    name: object  # Expr
    line: int

@dataclass
class MetaCall:
    key: object  # Expr
    line: int

@dataclass
class ConfigCall:
    key: object  # Expr
    line: int

@dataclass
class RefmapCall:
    key: object  # Expr
    line: int

@dataclass
class ArgsCall:
    index: int
    line: int

@dataclass
class HasargCall:
    index: int
    line: int

@dataclass
class TimestampCall:
    line: int


# shell calls
@dataclass
class ShCall:
    cmd: object  # Expr
    verbose: bool
    optional: bool
    line: int

@dataclass
class CaptureCall:
    cmd: object  # Expr
    line: int

@dataclass
class SpawnCall:
    cmd: object  # Expr
    line: int

@dataclass
class PromptCall:
    msg: object  # Expr
    secret: bool
    line: int

@dataclass
class ConfirmCall:
    msg: object  # Expr
    line: int

@dataclass
class BackgroundCall:
    id_: object  # Expr (STRING)
    cmd: object  # Expr
    line: int

@dataclass
class WaitCall:
    id_: object  # Expr (STRING)
    line: int

@dataclass
class PipeCall:
    cmds: list  # list[Expr]
    line: int

@dataclass
class PrintCall:
    msg: object  # Expr
    line: int

@dataclass
class OutCall:
    msg: object  # Expr
    code: int
    line: int

@dataclass
class StepCall:
    name: str
    line: int

# statements
@dataclass
class Block:
    stmts: list

@dataclass
class IfStmt:
    cond: object  # Expr
    then: Block
    else_: Optional[Block]
    line: int

@dataclass
class ParallelBlock:
    items: list  # list[ShCall | StepCall]
    line: int

@dataclass
class TimeoutBlock:
    seconds: int
    body: object  # ShCall | SpawnCall
    line: int

@dataclass
class RetryBlock:
    count: int
    body: object  # ShCall
    line: int

@dataclass
class CallStmt:
    call: object  # Call
    line: int

# top-level declarations
@dataclass
class ValDecl:
    name: str
    value: object  # Expr
    line: int

@dataclass
class StepDecl:
    name: str
    body: Block
    line: int

@dataclass
class EngineDecl:
    body: Block
    line: int

@dataclass
class FileNode:
    decls: list