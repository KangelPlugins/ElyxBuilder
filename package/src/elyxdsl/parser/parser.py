from ..lexer import Token, TokenType
from ..ast_nodes import (
    FileNode, ValDecl, StepDecl, EngineDecl, Block,
    IfStmt, ParallelBlock, TimeoutBlock, RetryBlock, CallStmt,
    ShCall, CaptureCall, SpawnCall, PromptCall, ConfirmCall,
    BackgroundCall, WaitCall, PipeCall, PrintCall, OutCall,
    StepCall, OsCall, RootCall, ScriptdirCall, EnvCall,
    MetaCall, ConfigCall, RefmapCall, ArgsCall, HasargCall,
    TimestampCall, BinaryExpr, UnaryExpr, StringLit, NumberLit,
    BoolLit, IdentExpr,
)
from ..errors import ParseError

_CALL_NAMES = frozenset({
    "sh", "capture", "spawn", "prompt", "confirm",
    "background", "wait", "pipe", "print", "out",
    "os", "root", "scriptdir", "env", "meta",
    "config", "refmap", "args", "hasarg", "timestamp",
})

_SH_FLAGS = frozenset({"verbose", "optional"})

class _Parser:
    def __init__(self, tokens, filename="<input>"):
        self.tokens = tokens
        self.pos = 0
        self.filename = filename

    # tokens acs

    def _peek(self):
        return self.tokens[self.pos]

    def _advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _check(self, *types):
        return self._peek().type in types

    def _match(self, *types):
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, ttype, description):
        tok = self._peek()
        if tok.type != ttype:
            raise ParseError(
                f"expected {description}, got {tok.value!r}",
                self.filename,
                tok.line,
            )
        return self._advance()

    def _error(self, msg, line=None):
        if line is None:
            line = self._peek().line
        raise ParseError(msg, self.filename, line)

    # top lvl

    def parseFile(self):
        decls = []
        engineCount = 0

        while not self._check(TokenType.EOF):
            tok = self._peek()

            if tok.type == TokenType.KW_VAL:
                decls.append(self._parseValDecl())
            elif tok.type == TokenType.KW_STEP:
                decls.append(self._parseStepDecl())
            elif tok.type == TokenType.KW_ENGINE:
                engineCount += 1
                if engineCount > 1:
                    self._error("duplicate engine declaration", tok.line)
                decls.append(self._parseEngineDecl())
            else:
                self._error(
                    f"unexpected token {tok.value!r} at top level", tok.line
                )

        if engineCount == 0:
            self._error("missing engine declaration", self._peek().line)

        self._validateStepRefs(decls)
        return FileNode(decls=decls)

    def _parseValDecl(self):
        tok = self._expect(TokenType.KW_VAL, "\"val\"")
        name = self._expect(TokenType.IDENT, "identifier").value
        self._expect(TokenType.OP_ASSIGN, "\"=\"")
        value = self._parseExpr()
        return ValDecl(name=name, value=value, line=tok.line)

    def _parseStepDecl(self):
        tok = self._expect(TokenType.KW_STEP, "\"step\"")
        name = self._expect(TokenType.STRING, "step name string").value
        body = self._parseBlock()
        return StepDecl(name=name, body=body, line=tok.line)

    def _parseEngineDecl(self):
        tok = self._expect(TokenType.KW_ENGINE, "\"engine\"")
        body = self._parseBlock()
        return EngineDecl(body=body, line=tok.line)

    # top lvl

    def _parseBlock(self):
        open_tok = self._peek()
        if open_tok.type != TokenType.LBRACE:
            self._error(f"expected \"{{\" to open block, got {open_tok.value!r}", open_tok.line)
        self._advance()

        stmts = []
        declared = {}  

        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._peek()

            if tok.type == TokenType.KW_VAL:
                decl = self._parseValDecl()
                if decl.name in declared:
                    self._error(
                        f"val \"{decl.name}\" already declared in this block (first at line {declared[decl.name]})",
                        decl.line,
                    )
                declared[decl.name] = decl.line
                stmts.append(decl)

            elif tok.type == TokenType.KW_IF:
                stmts.append(self._parseIfStmt())
            elif tok.type == TokenType.KW_PARALLEL:
                stmts.append(self._parseParallelBlock())
            elif tok.type == TokenType.KW_TIMEOUT:
                stmts.append(self._parseTimeoutBlock())
            elif tok.type == TokenType.KW_RETRY:
                stmts.append(self._parseRetryBlock())
            elif tok.type == TokenType.IDENT and tok.value in _CALL_NAMES:
                call = self._parseCall()
                stmts.append(CallStmt(call=call, line=call.line))
            elif tok.type == TokenType.IDENT:
                # step call by ident
                self._advance()
                stmts.append(StepCall(name=tok.value, line=tok.line))

            elif tok.type == TokenType.STRING:
                # step call by string name
                self._advance()
                stmts.append(StepCall(name=tok.value, line=tok.line))

            else:
                self._error(
                    f"unexpected token {tok.value!r} inside block", tok.line
                )

        if self._peek().type == TokenType.EOF:
            self._error(
                "unclosed block: expected \"}\"", open_tok.line
            )
        self._advance()  # consume RBRACE
        return Block(stmts=stmts)

    # control flow

    def _parseIfStmt(self):
        tok = self._expect(TokenType.KW_IF, "\"if\"")
        cond = self._parseExpr()
        then = self._parseBlock()
        else_ = None

        if self._match(TokenType.KW_ELSE):
            if self._check(TokenType.KW_IF):
                inner = self._parseIfStmt()
                else_ = Block(stmts=[inner])
            else:
                else_ = self._parseBlock()

        return IfStmt(cond=cond, then=then, else_=else_, line=tok.line)

    # parallel / timeout / retry

    def _parseParallelBlock(self):
        tok = self._expect(TokenType.KW_PARALLEL, "\"parallel\"")
        open_tok = self._peek()
        if open_tok.type != TokenType.LBRACE:
            self._error("expected \"{\" after \"parallel\"", open_tok.line)
        self._advance()

        items = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            t = self._peek()
            if t.type == TokenType.IDENT and t.value == "sh":
                items.append(self._parseShCall())
            elif t.type == TokenType.IDENT:
                self._advance()
                items.append(StepCall(name=t.value, line=t.line))
            elif t.type == TokenType.STRING:
                self._advance()
                items.append(StepCall(name=t.value, line=t.line))
            else:
                self._error(
                    f"only sh() and step calls allowed inside parallel, got {t.value!r}",
                    t.line,
                )

        if self._peek().type == TokenType.EOF:
            self._error("unclosed parallel block", tok.line)
        self._advance()
        return ParallelBlock(items=items, line=tok.line)

    def _parseTimeoutBlock(self):
        tok = self._expect(TokenType.KW_TIMEOUT, "\"timeout\"")
        self._expect(TokenType.LPAREN, "\"(\"")
        seconds_tok = self._expect(TokenType.NUMBER, "timeout seconds")
        self._expect(TokenType.RPAREN, "\")\"")

        open_tok = self._peek()
        if open_tok.type != TokenType.LBRACE:
            self._error("expected \"{\" after timeout(N)", open_tok.line)
        self._advance()

        body = self._parseSingleShOrSpawn()

        if self._peek().type == TokenType.EOF:
            self._error("unclosed timeout block", tok.line)
        self._expect(TokenType.RBRACE, "\"}\"")
        return TimeoutBlock(seconds=seconds_tok.value, body=body, line=tok.line)

    def _parseSingleShOrSpawn(self):
        t = self._peek()
        if t.type == TokenType.IDENT and t.value == "sh":
            call = self._parseShCall()
        elif t.type == TokenType.IDENT and t.value == "spawn":
            call = self._parseSpawnCall()
        else:
            self._error(
                f"timeout body must be sh() or spawn(), got {t.value!r}", t.line
            )
        if not self._check(TokenType.RBRACE):
            self._error("timeout body must contain exactly one sh() or spawn()", self._peek().line)
        return call

    def _parseRetryBlock(self):
        tok = self._expect(TokenType.KW_RETRY, "\"retry\"")
        self._expect(TokenType.LPAREN, "\"(\"")
        count_tok = self._expect(TokenType.NUMBER, "retry count")
        self._expect(TokenType.RPAREN, "\")\"")

        open_tok = self._peek()
        if open_tok.type != TokenType.LBRACE:
            self._error("expected \"{\" after retry(N)", open_tok.line)
        self._advance()

        t = self._peek()
        if not (t.type == TokenType.IDENT and t.value == "sh"):
            self._error(
                f"retry body must be sh(), got {t.value!r}", t.line
            )
        body = self._parseShCall()

        if not self._check(TokenType.RBRACE):
            self._error("retry body must contain exactly one sh()", self._peek().line)
        if self._peek().type == TokenType.EOF:
            self._error("unclosed retry block", tok.line)
        self._advance()
        return RetryBlock(count=count_tok.value, body=body, line=tok.line)

    # someone i s calling you

    def _parseCall(self):
        tok = self._peek()
        name = tok.value

        dispatch = {
            "sh": self._parseShCall,
            "capture": self._parseCaptureCall,
            "spawn": self._parseSpawnCall,
            "prompt": self._parsePromptCall,
            "confirm": self._parseConfirmCall,
            "background": self._parseBackgroundCall,
            "wait": self._parseWaitCall,
            "pipe": self._parsePipeCall,
            "print": self._parsePrintCall,
            "out": self._parseOutCall,
            "os": self._parseOsCall,
            "root": self._parseRootCall,
            "scriptdir": self._parseScriptdirCall,
            "env": self._parseEnvCall,
            "meta": self._parseMetaCall,
            "config": self._parseConfigCall,
            "refmap": self._parseRefmapCall,
            "args": self._parseArgsCall,
            "hasarg": self._parseHasargCall,
            "timestamp": self._parseTimestampCall,
        }
        fn = dispatch.get(name)
        if fn is None:
            self._error(f"unknown call: {name!r}", tok.line)
        return fn()

    def _parseShCall(self):
        tok = self._advance()  # consume sh
        self._expect(TokenType.LPAREN, "\"(\"")
        cmd = self._parseExpr()
        verbose = False
        optional = False
        while self._match(TokenType.COMMA):
            flag = self._peek()
            if flag.type == TokenType.IDENT and flag.value in _SH_FLAGS:
                self._advance()
                if flag.value == "verbose":
                    verbose = True
                else:
                    optional = True
            else:
                self._error(
                    f"sh() flag must be \"verbose\" or \"optional\", got {flag.value!r}",
                    flag.line,
                )
        self._expect(TokenType.RPAREN, "\")\"")
        return ShCall(cmd=cmd, verbose=verbose, optional=optional, line=tok.line)

    def _parseCaptureCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        cmd = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return CaptureCall(cmd=cmd, line=tok.line)

    def _parseSpawnCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        cmd = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return SpawnCall(cmd=cmd, line=tok.line)

    def _parsePromptCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        msg = self._parseExpr()
        secret = False
        if self._match(TokenType.COMMA):
            flag = self._peek()
            if flag.type == TokenType.IDENT and flag.value == "secret":
                self._advance()
                secret = True
            else:
                self._error(
                    f"prompt() second arg must be \"secret\", got {flag.value!r}",
                    flag.line,
                )
        self._expect(TokenType.RPAREN, "\")\"")
        return PromptCall(msg=msg, secret=secret, line=tok.line)

    def _parseConfirmCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        msg = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return ConfirmCall(msg=msg, line=tok.line)

    def _parseBackgroundCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        id_tok = self._expect(TokenType.STRING, "background id string")
        id_ = StringLit(value=id_tok.value, line=id_tok.line)
        self._expect(TokenType.COMMA, "\",\"")
        cmd = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return BackgroundCall(id_=id_, cmd=cmd, line=tok.line)

    def _parseWaitCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        id_tok = self._expect(TokenType.STRING, "wait id string")
        id_ = StringLit(value=id_tok.value, line=id_tok.line)
        self._expect(TokenType.RPAREN, "\")\"")
        return WaitCall(id_=id_, line=tok.line)

    def _parsePipeCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        cmds = [self._parseExpr()]
        self._expect(TokenType.COMMA, "\",\" (pipe requires at least two commands)")
        cmds.append(self._parseExpr())
        while self._match(TokenType.COMMA):
            cmds.append(self._parseExpr())
        self._expect(TokenType.RPAREN, "\")\"")
        return PipeCall(cmds=cmds, line=tok.line)

    def _parsePrintCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        msg = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return PrintCall(msg=msg, line=tok.line)

    def _parseOutCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        msg = self._parseExpr()
        self._expect(TokenType.COMMA, "\",\"")
        code_tok = self._expect(TokenType.NUMBER, "exit code number")
        self._expect(TokenType.RPAREN, "\")\"")
        return OutCall(msg=msg, code=code_tok.value, line=tok.line)

    def _parseOsCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        self._expect(TokenType.RPAREN, "\")\"")
        return OsCall(line=tok.line)

    def _parseRootCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        self._expect(TokenType.RPAREN, "\")\"")
        return RootCall(line=tok.line)

    def _parseScriptdirCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        self._expect(TokenType.RPAREN, "\")\"")
        return ScriptdirCall(line=tok.line)

    def _parseEnvCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        name = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return EnvCall(name=name, line=tok.line)

    def _parseMetaCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        key = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return MetaCall(key=key, line=tok.line)

    def _parseConfigCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        key = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return ConfigCall(key=key, line=tok.line)

    def _parseRefmapCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        key = self._parseExpr()
        self._expect(TokenType.RPAREN, "\")\"")
        return RefmapCall(key=key, line=tok.line)

    def _parseArgsCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        index_tok = self._expect(TokenType.NUMBER, "arg index")
        self._expect(TokenType.RPAREN, "\")\"")
        return ArgsCall(index=index_tok.value, line=tok.line)

    def _parseHasargCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        index_tok = self._expect(TokenType.NUMBER, "arg index")
        self._expect(TokenType.RPAREN, "\")\"")
        return HasargCall(index=index_tok.value, line=tok.line)

    def _parseTimestampCall(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "\"(\"")
        self._expect(TokenType.RPAREN, "\")\"")
        return TimestampCall(line=tok.line)

    # exprs

    def _parseExpr(self):
        return self._parseOr()

    def _parseOr(self):
        left = self._parseAnd()
        while self._check(TokenType.OP_OR):
            op_tok = self._advance()
            right = self._parseAnd()
            left = BinaryExpr(op="||", left=left, right=right, line=op_tok.line)
        return left

    def _parseAnd(self):
        left = self._parseEquality()
        while self._check(TokenType.OP_AND):
            op_tok = self._advance()
            right = self._parseEquality()
            left = BinaryExpr(op="&&", left=left, right=right, line=op_tok.line)
        return left

    def _parseEquality(self):
        left = self._parseConcat()
        while self._check(TokenType.OP_EQ, TokenType.OP_NEQ):
            op_tok = self._advance()
            right = self._parseConcat()
            left = BinaryExpr(op=op_tok.value, left=left, right=right, line=op_tok.line)
        return left

    def _parseConcat(self):
        left = self._parseUnary()
        while self._check(TokenType.OP_PLUS):
            op_tok = self._advance()
            right = self._parseUnary()
            left = BinaryExpr(op="+", left=left, right=right, line=op_tok.line)
        return left

    def _parseUnary(self):
        if self._check(TokenType.OP_NOT):
            op_tok = self._advance()
            operand = self._parseUnary()
            return UnaryExpr(op="!", operand=operand, line=op_tok.line)
        return self._parsePrimary()

    def _parsePrimary(self):
        tok = self._peek()

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parseExpr()
            self._expect(TokenType.RPAREN, "\")\"")
            return expr

        if tok.type == TokenType.STRING:
            self._advance()
            return StringLit(value=tok.value, line=tok.line)

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLit(value=tok.value, line=tok.line)

        if tok.type == TokenType.KW_TRUE:
            self._advance()
            return BoolLit(value=True, line=tok.line)

        if tok.type == TokenType.KW_FALSE:
            self._advance()
            return BoolLit(value=False, line=tok.line)

        if tok.type == TokenType.IDENT:
            if tok.value in _CALL_NAMES:
                return self._parseCall()
            # val ref
            self._advance()
            return IdentExpr(name=tok.value, line=tok.line)

        self._error(
            f"unexpected token {tok.value!r} in expression", tok.line
        )

    # semantic checks

    def _validateStepRefs(self, decls):
        stepNames = set()
        for d in decls:
            if isinstance(d, StepDecl):
                stepNames.add(d.name)

        engine = next((d for d in decls if isinstance(d, EngineDecl)), None)
        if engine is None:
            return

        self._checkStepRefsInBlock(engine.body, stepNames)

    def _checkStepRefsInBlock(self, block, stepNames):
        for stmt in block.stmts:
            if isinstance(stmt, StepCall):
                if stmt.name not in stepNames:
                    raise ParseError(
                        f"step \"{stmt.name}\" is called but not declared",
                        self.filename,
                        stmt.line,
                    )
            elif isinstance(stmt, IfStmt):
                self._checkStepRefsInBlock(stmt.then, stepNames)
                if stmt.else_ is not None:
                    self._checkStepRefsInBlock(stmt.else_, stepNames)
            elif isinstance(stmt, ParallelBlock):
                for item in stmt.items:
                    if isinstance(item, StepCall) and item.name not in stepNames:
                        raise ParseError(
                            f"step \"{item.name}\" is called but not declared",
                            self.filename,
                            item.line,
                        )


def parse(tokens, filename="<input>"):
    p = _Parser(tokens, filename)
    return p.parseFile()
