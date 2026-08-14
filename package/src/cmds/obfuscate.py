import ast
import keyword as _keyword
import os
import random as _random
import string as _string

def _generateDynamicXorKey(value: str, base_key: int) -> bytes:
    value_bytes = value.encode("utf-8")
    seed = base_key + len(value) + sum(value_bytes[:min(8, len(value_bytes))])
    _random.seed(seed)
    return bytes([_random.randint(0, 255) for _ in range(_random.randint(4, 16))])


def _splitString(value: str, parts: int = 3) -> list:
    if len(value) < 20:
        return [value]
    chunk_size = len(value) // parts
    remainder = len(value) % parts
    result = []
    idx = 0
    for i in range(parts):
        size = chunk_size + (1 if i < remainder else 0)
        result.append(value[idx:idx + size])
        idx += size
    return result


def _makeSplitStringExpr(value: str, key: int) -> ast.Call:
    parts = _splitString(value, _random.randint(2, min(5, len(value) // 10 + 2)))
    encoded_parts = []
    keys = []
    for part in parts:
        k = _generateDynamicXorKey(part, key + len(encoded_parts))
        encoded = bytes(b ^ k[i % len(k)] for i, b in enumerate(part.encode("utf-8")))
        encoded_parts.append(encoded)
        keys.append(k)

    # Build: "".join(bytes(b ^ k[i % len(k)] for i, b in enumerate(d)).decode() for d, k in [(...)])
    tuples = []
    for ep, k in zip(encoded_parts, keys):
        data_const = ast.Constant(value=ep)
        key_tuple = ast.Tuple(elts=[ast.Constant(value=b) for b in k], ctx=ast.Load())
        gen = ast.GeneratorExp(
            elt=ast.BinOp(
                left=ast.Name(id="b", ctx=ast.Load()),
                op=ast.BitXor(),
                right=ast.Subscript(
                    value=ast.Name(id="k", ctx=ast.Load()),
                    slice=ast.BinOp(
                        left=ast.Name(id="i", ctx=ast.Load()),
                        op=ast.Mod(),
                        right=ast.Call(func=ast.Name(id="len", ctx=ast.Load()), args=[ast.Name(id="k", ctx=ast.Load())], keywords=[])
                    ),
                    ctx=ast.Load()
                )
            ),
            generators=[ast.comprehension(
                target=ast.Tuple(elts=[
                    ast.Name(id="i", ctx=ast.Store()),
                    ast.Name(id="b", ctx=ast.Store())
                ], ctx=ast.Store()),
                iter=ast.Call(func=ast.Name(id="enumerate", ctx=ast.Load()), args=[data_const], keywords=[]),
                ifs=[],
                is_async=0
            )]
        )
        decode_call = ast.Call(
            func=ast.Attribute(value=ast.Call(func=ast.Name(id="bytes", ctx=ast.Load()), args=[gen], keywords=[]), attr="decode", ctx=ast.Load()),
            args=[],
            keywords=[]
        )
        tuples.append(ast.Tuple(elts=[data_const, key_tuple], ctx=ast.Load()))

    # Join all decoded parts
    list_comp = ast.ListComp(
        elt=ast.Call(func=ast.Lambda(
            args=ast.arguments(posonlyargs=[], args=[ast.arg(arg="d"), ast.arg(arg="k")], kwonlyargs=[], defaults=[]),
            body=ast.Call(func=ast.Name(id="bytes", ctx=ast.Load()), args=[ast.GeneratorExp(
                elt=ast.BinOp(left=ast.Name(id="b", ctx=ast.Load()), op=ast.BitXor(), right=ast.Subscript(...)),
                generators=[]
            )], keywords=[])
        ), args=[], keywords=[]),
        generators=[ast.comprehension(target=ast.Tuple(elts=[], ctx=ast.Store()), iter=ast.List(elts=tuples, ctx=ast.Load()), ifs=[], is_async=0)]
    )

    # Simplified: just use string concatenation
    parts_expr = []
    for i, (ep, k) in enumerate(zip(encoded_parts, keys)):
        key_tuple = ast.Tuple(elts=[ast.Constant(value=b) for b in k], ctx=ast.Load())
        data_const = ast.Constant(value=ep)
        gen = ast.GeneratorExp(
            elt=ast.BinOp(
                left=ast.Name(id="b", ctx=ast.Load()),
                op=ast.BitXor(),
                right=ast.Subscript(
                    value=ast.Name(id="k", ctx=ast.Load()),
                    slice=ast.BinOp(
                        left=ast.Name(id="i", ctx=ast.Load()),
                        op=ast.Mod(),
                        right=ast.Call(func=ast.Name(id="len", ctx=ast.Load()), args=[ast.Name(id="k", ctx=ast.Load())], keywords=[])
                    ),
                    ctx=ast.Load()
                )
            ),
            generators=[ast.comprehension(
                target=ast.Tuple(elts=[ast.Name(id="i", ctx=ast.Store()), ast.Name(id="b", ctx=ast.Store())], ctx=ast.Store()),
                iter=ast.Call(func=ast.Name(id="enumerate", ctx=ast.Load()), args=[data_const], keywords=[]),
                ifs=[],
                is_async=0
            )]
        )
        decode_call = ast.Call(
            func=ast.Attribute(value=ast.Call(func=ast.Name(id="bytes", ctx=ast.Load()), args=[gen], keywords=[]), attr="decode", ctx=ast.Load()),
            args=[],
            keywords=[]
        )
        parts_expr.append(decoder_call)

    join_call = ast.Call(
        func=ast.Attribute(value=ast.Name(id="str", ctx=ast.Load()), attr="join", ctx=ast.Load()),
        args=[ast.List(elts=parts_expr, ctx=ast.Load())],
        keywords=[]
    )
    return join_call


def _generateJunkCode(seed: int) -> list:
    _random.seed(seed)
    junk_funcs = []
    for _ in range(_random.randint(2, 5)):
        func_name = f"_x{_random.randint(10000, 99999)}"
        body = []
        for __ in range(_random.randint(3, 8)):
            choice = _random.randint(0, 2)
            if choice == 0:
                body.append(ast.Assign(
                    targets=[ast.Name(id=f"v{_random.randint(0, 99)}", ctx=ast.Store())],
                    value=ast.Constant(value=_random.randint(0, 1000))
                ))
            elif choice == 1:
                body.append(ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="len", ctx=ast.Load()),
                        args=[ast.List(elts=[ast.Constant(value=_random.randint(0, 99)) for _ in range(_random.randint(1, 5))], ctx=ast.Load())],
                        keywords=[]
                    )
                ))
            else:
                body.append(ast.Pass())
        junk_funcs.append(ast.FunctionDef(
            name=func_name,
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], defaults=[]),
            body=body,
            decorator_list=[],
            returns=None
        ))
    return junk_funcs

def _makeXorStringExpr(value: str, key: int) -> ast.Call:
    dynamic_key = _generateDynamicXorKey(value, key)
    encoded = bytes(b ^ dynamic_key[i % len(dynamic_key)] for i, b in enumerate(value.encode("utf-8")))
    bytesNode = ast.Constant(value=encoded)
    bVar = ast.Name(id="b", ctx=ast.Load())
    keyVar = ast.Name(id="k", ctx=ast.Load())
    
    # Create key tuple
    keyTuple = ast.Tuple(elts=[ast.Constant(value=k) for k in dynamic_key], ctx=ast.Load())
    
    # XOR operation: b ^ k[i % len(k)]
    indexOp = ast.Subscript(value=keyVar, slice=ast.BinOp(
        left=ast.Name(id="i", ctx=ast.Load()),
        op=ast.Mod(),
        right=ast.Call(func=ast.Name(id="len", ctx=ast.Load()), args=[keyVar], keywords=[])
    ), ctx=ast.Load())
    
    xorOp = ast.BinOp(left=bVar, op=ast.BitXor(), right=indexOp)
    
    # Generator: (b ^ k[i % len(k)] for i, b in enumerate(data))
    generator = ast.GeneratorExp(
        elt=xorOp,
        generators=[ast.comprehension(
            target=ast.Tuple(elts=[
                ast.Name(id="i", ctx=ast.Store()),
                ast.Name(id="b", ctx=ast.Store())
            ], ctx=ast.Store()),
            iter=ast.Call(func=ast.Name(id="enumerate", ctx=ast.Load()), args=[bytesNode], keywords=[]),
            ifs=[],
            is_async=0,
        )],
    )
    
    # bytes(...) with key assignment
    bytesCall = ast.Call(
        func=ast.Name(id="bytes", ctx=ast.Load()),
        args=[generator],
        keywords=[]
    )
    
    # Wrap in exec to hide key and decoding logic
    decodeLambda = ast.Lambda(
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="d", annotation=None), ast.arg(arg="k", annotation=None)],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[]
        ),
        body=ast.Call(
            func=ast.Attribute(value=bytesCall, attr="decode", ctx=ast.Load()),
            args=[],
            keywords=[]
        )
    )
    
    # Return: (lambda d, k: bytes(b ^ k[i % len(k)] for i, b in enumerate(d)).decode())(data, (key_tuple))
    return ast.Call(func=decodeLambda, args=[bytesNode, keyTuple], keywords=[])


def collectLocalClassNames(sourceDir: str) -> frozenset[str]:
    names: set[str] = set()
    for root, dirs, files in os.walk(sourceDir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            if not file.endswith(".py"):
                continue
            absPath = os.path.join(root, file)
            try:
                with open(absPath, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=absPath)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    names.add(node.name)
    return frozenset(names)


def _hasExternalBase(classNode: ast.ClassDef, localClassNames: frozenset[str]) -> bool:
    for base in classNode.bases:
        if isinstance(base, ast.Call):
            return True
        if isinstance(base, ast.Name) and base.id not in localClassNames:
            return True
        if isinstance(base, ast.Attribute):
            return True
    return False


def collectProtectedNames(sourceDir: str) -> frozenset[str]:
    names: set[str] = set()
    importedFuncNames: set[str] = set()
    trees: list[ast.Module] = []

    for root, dirs, files in os.walk(sourceDir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            if not file.endswith(".py"):
                continue
            absPath = os.path.join(root, file)
            try:
                with open(absPath, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=absPath)
            except SyntaxError:
                continue
            trees.append(tree)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        names.add(alias.asname or alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        importedFuncNames.add(alias.name)
                        names.add(alias.asname or alias.name)
                elif isinstance(node, ast.Name):
                    if node.id.startswith("__") and node.id.endswith("__"):
                        names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if node.attr.startswith("__") and node.attr.endswith("__"):
                        names.add(node.attr)

    # are u are u, cuming on the tree bruh
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name not in importedFuncNames:
                continue
            args = node.args
            for arg in args.args + args.posonlyargs + args.kwonlyargs:
                names.add(arg.arg)
            if args.vararg:
                names.add(args.vararg.arg)
            if args.kwarg:
                names.add(args.kwarg.arg)

    allKwUsed: set[str] = set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg is not None:
                        allKwUsed.add(kw.arg)
    if allKwUsed:
        for tree in trees:
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                args = node.args
                for arg in args.args + args.posonlyargs + args.kwonlyargs:
                    if arg.arg in allKwUsed:
                        names.add(arg.arg)
                if args.vararg and args.vararg.arg in allKwUsed:
                    names.add(args.vararg.arg)
                if args.kwarg and args.kwarg.arg in allKwUsed:
                    names.add(args.kwarg.arg)
    return frozenset(names)


def _hasNoObfDecorator(node: ast.AST) -> bool:
    decorators = getattr(node, "decorator_list", [])
    for d in decorators:
        if isinstance(d, ast.Name) and d.id == "ELYBNoObf":
            return True
    return getattr(node, "_elyb_no_obf", False)

def _stripNoObfDecorator(node: ast.AST) -> None:
    if hasattr(node, "decorator_list"):
        node.decorator_list = [
            d for d in node.decorator_list
            if not (isinstance(d, ast.Name) and d.id == "ELYBNoObf")
        ]

# elybnoobf dec
class MarkNoObfNodes(ast.NodeVisitor):
    def _mark(self, node: ast.AST) -> None:
        for d in getattr(node, "decorator_list", []):
            if isinstance(d, ast.Name) and d.id == "ELYBNoObf":
                node._elyb_no_obf = True
                break
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._mark(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._mark(node)
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._mark(node)


class StripDocstrings(ast.NodeTransformer):
    def _stripBody(self, node: ast.AST) -> ast.AST:
        if _hasNoObfDecorator(node):
            _stripNoObfDecorator(node)
            return node
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
        return self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> ast.Module:
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        return self._stripBody(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self._stripBody(node)
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        return self._stripBody(node)

# tests
def applyStripDocstrings(source: str) -> str:
    tree = ast.parse(source)
    tree = StripDocstrings().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _scanCommentLines(source: str) -> dict[str, frozenset[int]]:
    markers = ("# ELYBsaveLog", "# ELYBnoStrobf", "# ELYBnoIntObf")
    result: dict[str, set[int]] = {m: set() for m in markers}
    for i, line in enumerate(source.splitlines(), start=1):
        for marker in markers:
            if marker in line:
                result[marker].add(i)
    return {m: frozenset(v) for m, v in result.items()}


class RemoveLogs(ast.NodeTransformer):
    def __init__(self, saveLogLines: frozenset[int]) -> None:
        self.saveLogLines = saveLogLines

    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        if not isinstance(node.value, ast.Call):
            return node
        call = node.value
        if getattr(node, "lineno", None) in self.saveLogLines:
            return node
        # log(...) direct call
        if isinstance(call.func, ast.Name) and call.func.id == "log":
            return ast.Pass()
        # *.log(...) attribute call
        if isinstance(call.func, ast.Attribute) and call.func.attr == "log":
            if isinstance(call.func.value, ast.Name) and call.func.value.id == "_au":
                return ast.Pass()
        return node


def applyRemoveLogs(source: str) -> str:
    commentLines = _scanCommentLines(source)
    tree = ast.parse(source)
    tree = RemoveLogs(commentLines["# ELYBsaveLog"]).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _collectNestedLocals(funcNode: ast.AST) -> set[str]:
    localNames: set[str] = set()
    args = getattr(funcNode, "args", None)
    if args:
        for arg in args.args + args.posonlyargs + args.kwonlyargs:
            localNames.add(arg.arg)
        if args.vararg:
            localNames.add(args.vararg.arg)
        if args.kwarg:
            localNames.add(args.kwarg.arg)
    if isinstance(funcNode, ast.Lambda):
        return localNames
    stack = list(getattr(funcNode, "body", []))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            localNames.add(node.id)
        if isinstance(node, ast.ExceptHandler) and node.name:
            localNames.add(node.name)
        for child in ast.iter_child_nodes(node):
            stack.append(child)
    return localNames


def _renameClosure(funcNode: ast.AST, outerRenameMap: dict[str, str]) -> None:
    if not outerRenameMap:
        return
    localNames = _collectNestedLocals(funcNode)

    class ClosureRenamer(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.Name:
            if node.id in outerRenameMap and node.id not in localNames:
                node.id = outerRenameMap[node.id]
            return node

        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
            filtered = {k: v for k, v in outerRenameMap.items() if k not in localNames}
            _renameClosure(node, filtered)
            return node

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
            filtered = {k: v for k, v in outerRenameMap.items() if k not in localNames}
            _renameClosure(node, filtered)
            return node

        def visit_Lambda(self, node: ast.Lambda) -> ast.Lambda:
            # creates its own scope
            filtered = {k: v for k, v in outerRenameMap.items() if k not in localNames}
            _renameClosure(node, filtered)
            return node

        def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
            node.decorator_list = [self.visit(d) for d in node.decorator_list]
            # like dynamic_proxy(TextWatcherInterface)
            node.bases = [self.visit(base) for base in node.bases]
            # i dont remember what its comment says (
            for stmt in node.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _renameClosure(stmt, outerRenameMap)
                elif isinstance(stmt, ast.ClassDef):
                    ClosureRenamer().visit(stmt)
            return node

    if isinstance(funcNode, ast.ClassDef):
        renamer = ClosureRenamer()
        funcNode.decorator_list = [renamer.visit(d) for d in funcNode.decorator_list]
        funcNode.bases = [renamer.visit(base) for base in funcNode.bases]

    class OuterScopeRenamer(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.Name:
            if node.id in outerRenameMap:
                node.id = outerRenameMap[node.id]
            return node
    args = getattr(funcNode, "args", None)
    if args:
        defaultRenamer = OuterScopeRenamer()
        args.defaults = [defaultRenamer.visit(d) for d in args.defaults]
        args.kw_defaults = [defaultRenamer.visit(d) if d is not None else None for d in args.kw_defaults]
    if isinstance(funcNode, ast.Lambda):
        funcNode.body = ClosureRenamer().visit(funcNode.body)
        return
    for stmt in getattr(funcNode, "body", []):
        ClosureRenamer().visit(stmt)


_OBFNAME_CHARS = _string.ascii_letters + _string.digits

def _makeObfName(usedNames: set[str]) -> str:
    # gen a random ident
    while True:
        length = _random.randint(4, 12)
        name = _random.choice(_string.ascii_letters) + "".join(_random.choices(_OBFNAME_CHARS, k=length - 1))
        if name not in usedNames and not _keyword.iskeyword(name):
            usedNames.add(name)
            return name


class RenameLocals(ast.NodeTransformer):
    def __init__(self, protectedNames: frozenset[str], localClassNames: frozenset[str] = frozenset()) -> None:
        self.protectedNames = protectedNames
        self.localClassNames = localClassNames
        self._usedNames: set[str] = set()

    def _renameFunction(self, node: ast.AST) -> ast.AST:
        if _hasNoObfDecorator(node):
            _stripNoObfDecorator(node)
            return node

        nonlocalNames: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, (ast.Nonlocal, ast.Global)):
                nonlocalNames.update(child.names)

        renameMap: dict[str, str] = {}
        usedNames = self._usedNames

        def nextName() -> str:
            return _makeObfName(usedNames)

        def shouldRename(name: str) -> bool:
            if name in ("self", "cls"):
                return False
            if name.startswith("__") and name.endswith("__"):
                return False
            if name in self.protectedNames:
                return False
            if name in nonlocalNames:
                return False
            return True

        def getMapped(name: str) -> str:
            if name not in renameMap:
                renameMap[name] = nextName()
            return renameMap[name]

        args = node.args
        for arg in args.args + args.posonlyargs + args.kwonlyargs:
            if shouldRename(arg.arg):
                arg.arg = getMapped(arg.arg)
        if args.vararg and shouldRename(args.vararg.arg):
            args.vararg.arg = getMapped(args.vararg.arg)
        if args.kwarg and shouldRename(args.kwarg.arg):
            args.kwarg.arg = getMapped(args.kwarg.arg)

        nestedFunctions: list[ast.AST] = []

        class BodyRenamer(ast.NodeTransformer):
            def visit_Name(self, n: ast.Name) -> ast.Name:
                if isinstance(n.ctx, (ast.Store, ast.Load, ast.Del)) and n.id in renameMap:
                    n.id = renameMap[n.id]
                    return n
                if isinstance(n.ctx, ast.Store) and shouldRename(n.id):
                    n.id = getMapped(n.id)
                return n

            def visit_ExceptHandler(self, n: ast.ExceptHandler) -> ast.ExceptHandler:
                if n.name and shouldRename(n.name):
                    mapped = getMapped(n.name)
                    n.name = mapped
                return self.generic_visit(n)

            def _visitComprehension(self, n: ast.AST) -> ast.AST:
                for gen in n.generators:  # type: ignore[attr-defined]
                    for child in ast.walk(gen.target):
                        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                            if shouldRename(child.id):
                                getMapped(child.id)
                return self.generic_visit(n)

            def visit_ListComp(self, n: ast.ListComp) -> ast.ListComp:
                return self._visitComprehension(n)
            def visit_SetComp(self, n: ast.SetComp) -> ast.SetComp:
                return self._visitComprehension(n)
            def visit_GeneratorExp(self, n: ast.GeneratorExp) -> ast.GeneratorExp:
                return self._visitComprehension(n)
            def visit_DictComp(self, n: ast.DictComp) -> ast.DictComp:
                return self._visitComprehension(n)

            def visit_FunctionDef(self, n: ast.FunctionDef) -> ast.FunctionDef:
                if shouldRename(n.name):
                    n.name = getMapped(n.name)
                nestedFunctions.append(n)
                return n

            def visit_AsyncFunctionDef(self, n: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
                if shouldRename(n.name):
                    n.name = getMapped(n.name)
                nestedFunctions.append(n)
                return n

            def visit_Lambda(self, n: ast.Lambda) -> ast.Lambda:
                nestedFunctions.append(n)
                return n

            def visit_ClassDef(self, n: ast.ClassDef) -> ast.ClassDef:
                if shouldRename(n.name):
                    n.name = getMapped(n.name)
                nestedFunctions.append(n)
                return n

        node.body = [BodyRenamer().visit(stmt) for stmt in node.body]
        for fn in nestedFunctions:
            _renameClosure(fn, renameMap)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        return self._renameFunction(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self._renameFunction(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        if _hasNoObfDecorator(node):
            _stripNoObfDecorator(node)
            return node
        if _hasExternalBase(node, self.localClassNames):
               # external base
            return self._visitClassWithExternalBase(node)
        return self.generic_visit(node)

    def _visitClassWithExternalBase(self, node: ast.ClassDef) -> ast.ClassDef:
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._renameFunctionBodyOnly(stmt)
            elif isinstance(stmt, ast.ClassDef):
                self.visit_ClassDef(stmt)
        return node

    def _renameFunctionBodyOnly(self, node: ast.AST) -> ast.AST:
        if _hasNoObfDecorator(node):
            _stripNoObfDecorator(node)
            return node

        nonlocalNames: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, (ast.Nonlocal, ast.Global)):
                nonlocalNames.update(child.names)
        renameMap: dict[str, str] = {}
        usedNames = self._usedNames

        def nextName() -> str:
            return _makeObfName(usedNames)

        def shouldRename(name: str) -> bool:
            if name in ("self", "cls"):
                return False
            if name.startswith("__") and name.endswith("__"):
                return False
            if name in self.protectedNames:
                return False
            if name in nonlocalNames:
                return False
            return True

        def getMapped(name: str) -> str:
            if name not in renameMap:
                renameMap[name] = nextName()
            return renameMap[name]

        # collect params
        args = node.args
        for arg in args.args + args.posonlyargs + args.kwonlyargs:
            renameMap[arg.arg] = arg.arg
        if args.vararg:
            renameMap[args.vararg.arg] = args.vararg.arg
        if args.kwarg:
            renameMap[args.kwarg.arg] = args.kwarg.arg
        nestedFunctions: list[ast.AST] = []

        class BodyRenamer(ast.NodeTransformer):
            def visit_Name(self, n: ast.Name) -> ast.Name:
                if isinstance(n.ctx, (ast.Store, ast.Load, ast.Del)) and n.id in renameMap:
                    n.id = renameMap[n.id]
                    return n
                if isinstance(n.ctx, ast.Store) and shouldRename(n.id):
                    n.id = getMapped(n.id)
                return n

            def visit_ExceptHandler(self, n: ast.ExceptHandler) -> ast.ExceptHandler:
                if n.name and shouldRename(n.name):
                    mapped = getMapped(n.name)
                    n.name = mapped
                return self.generic_visit(n)

            def _visitComprehension(self, n: ast.AST) -> ast.AST:
                for gen in n.generators:  # type: ignore[attr-defined]
                    for child in ast.walk(gen.target):
                        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                            if shouldRename(child.id):
                                getMapped(child.id)
                return self.generic_visit(n)

            def visit_ListComp(self, n: ast.ListComp) -> ast.ListComp:
                return self._visitComprehension(n)
            def visit_SetComp(self, n: ast.SetComp) -> ast.SetComp:
                return self._visitComprehension(n)
            def visit_GeneratorExp(self, n: ast.GeneratorExp) -> ast.GeneratorExp:
                return self._visitComprehension(n)
            def visit_DictComp(self, n: ast.DictComp) -> ast.DictComp:
                return self._visitComprehension(n)

            def visit_FunctionDef(self, n: ast.FunctionDef) -> ast.FunctionDef:
                if shouldRename(n.name):
                    n.name = getMapped(n.name)
                nestedFunctions.append(n)
                return n

            def visit_AsyncFunctionDef(self, n: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
                if shouldRename(n.name):
                    n.name = getMapped(n.name)
                nestedFunctions.append(n)
                return n

            def visit_Lambda(self, n: ast.Lambda) -> ast.Lambda:
                nestedFunctions.append(n)
                return n

            def visit_ClassDef(self, n: ast.ClassDef) -> ast.ClassDef:
                if shouldRename(n.name):
                    n.name = getMapped(n.name)
                nestedFunctions.append(n)
                return n
        node.body = [BodyRenamer().visit(stmt) for stmt in node.body]
        for fn in nestedFunctions:
            _renameClosure(fn, renameMap)
        return self.generic_visit(node)


def applyRenameLocals(source: str, protectedNames: frozenset[str]) -> str:
    tree = ast.parse(source)
    tree = RenameLocals(protectedNames).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _isDocstringNode(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        )


class EncodeStringsAdvanced(ast.NodeTransformer):
    def __init__(self, skipLines: frozenset[int], protectedNames: frozenset[str], key: int, skipDocstrings: bool = False, useStringSplitting: bool = False) -> None:
        self.skipLines = skipLines
        self.protectedNames = protectedNames
        self.key = key
        self.skipDocstrings = skipDocstrings
        self.useStringSplitting = useStringSplitting

    def _visitBody(self, node: ast.AST) -> ast.AST:
        if _hasNoObfDecorator(node):
            return node
        if self.skipDocstrings:
            body = getattr(node, "body", None)
            if body and _isDocstringNode(body[0]):
                rest = [self.visit(stmt) for stmt in body[1:]]
                node.body = [body[0]] + rest
                return node
        return self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> ast.Module:
        if self.skipDocstrings and node.body and _isDocstringNode(node.body[0]):
            rest = [self.visit(stmt) for stmt in node.body[1:]]
            node.body = [node.body[0]] + rest
            return node
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        return self._visitBody(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self._visitBody(node)
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        return self._visitBody(node)
    def visit_Import(self, node: ast.Import) -> ast.Import:
        return node
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if not isinstance(node.value, str):
            return node
        value = node.value
        if not value:
            return node
        if value in self.protectedNames:
            return node
        if value.startswith("__") and value.endswith("__"):
            return node
        if getattr(node, "lineno", None) in self.skipLines:
            return node
        # Use enhanced XOR encoding with dynamic multi-byte key
        return ast.copy_location(_makeXorStringExpr(value, self.key), node)


class EncodeStrings(ast.NodeTransformer):

    def __init__(self, skipLines: frozenset[int], protectedNames: frozenset[str], key: int, skipDocstrings: bool = False) -> None:
        self.skipLines = skipLines
        self.protectedNames = protectedNames
        self.key = key
        self.skipDocstrings = skipDocstrings

    def _visitBody(self, node: ast.AST) -> ast.AST:
        if _hasNoObfDecorator(node):
            return node
        if self.skipDocstrings:
            body = getattr(node, "body", None)
            if body and _isDocstringNode(body[0]):
                rest = [self.visit(stmt) for stmt in body[1:]]
                node.body = [body[0]] + rest
                return node
        return self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> ast.Module:
        if self.skipDocstrings and node.body and _isDocstringNode(node.body[0]):
            rest = [self.visit(stmt) for stmt in node.body[1:]]
            node.body = [node.body[0]] + rest
            return node
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        return self._visitBody(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self._visitBody(node)
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        return self._visitBody(node)
    def visit_Import(self, node: ast.Import) -> ast.Import:
        return node
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if not isinstance(node.value, str):
            return node
        value = node.value
        if not value:
            return node
        if value in self.protectedNames:
            return node
        if value.startswith("__") and value.endswith("__"):
            return node
        if getattr(node, "lineno", None) in self.skipLines:
            return node
        return ast.copy_location(_makeXorStringExpr(value, self.key), node)

def _makeXorIntExpr(value: int) -> ast.BinOp:
    import random
    mask = random.randint(1, 0xFFFF)
    return ast.BinOp(
        left=ast.Constant(value=value ^ mask),
        op=ast.BitXor(),
        right=ast.Constant(value=mask),
    )


class EncodeNumbers(ast.NodeTransformer):
    def __init__(self, skipLines: frozenset[int]) -> None:
        self.skipLines = skipLines

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if _hasNoObfDecorator(node):
            return node
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        if _hasNoObfDecorator(node):
            return node
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        if _hasNoObfDecorator(node):
            return node
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if not isinstance(node.value, int) or isinstance(node.value, bool):
            return node
        value = node.value
        if value in (0, 1, -1):
            return node
        if getattr(node, "lineno", None) in self.skipLines:
            return node
        return ast.copy_location(_makeXorIntExpr(value), node)

def stripNoObfDecorator(source: str) -> str:
    # remove @ELYBNoObf lines without touching anything else
    lines = source.splitlines(keepends=True)
    result = []
    for line in lines:
        if line.lstrip().startswith("@ELYBNoObf"):
            continue
        result.append(line)
    return "".join(result)

def applyCleanupPipeline(source: str, removeLogs: bool) -> str:
    commentLines = _scanCommentLines(source)
    tree = ast.parse(source)
    MarkNoObfNodes().visit(tree)

    class StripNoObfDecorators(ast.NodeTransformer):
        def _strip(self, node: ast.AST) -> ast.AST:
            _stripNoObfDecorator(node)
            return self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
            return self._strip(node)
        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
            return self._strip(node)
        def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
            return self._strip(node)

    tree = StripNoObfDecorators().visit(tree)
    if removeLogs:
        tree = RemoveLogs(commentLines["# ELYBsaveLog"]).visit(tree)
    ast.fix_missing_locations(tree)
    result = ast.unparse(tree)
    return result


def _collectTopLevelSymbols(tree: ast.Module) -> list[dict]:
    # collect top-level func & cls
    symbols: list[dict] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [arg.arg for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs]
            if node.args.vararg:
                params.append(node.args.vararg.arg)
            if node.args.kwarg:
                params.append(node.args.kwarg.arg)
            symbols.append({"kind": "function", "name": node.name, "params": params})
        elif isinstance(node, ast.ClassDef):
            methods: list[dict] = []
            for stmt in node.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mParams = [arg.arg for arg in stmt.args.args + stmt.args.posonlyargs + stmt.args.kwonlyargs]
                    if stmt.args.vararg:
                        mParams.append(stmt.args.vararg.arg)
                    if stmt.args.kwarg:
                        mParams.append(stmt.args.kwarg.arg)
                    methods.append({"name": stmt.name, "params": mParams})
            symbols.append({"kind": "class", "name": node.name, "methods": methods})
    return symbols


def collectFileMapping(originalSource: str, obfuscatedSource: str) -> dict:
    originalTree = ast.parse(originalSource)
    obfuscatedTree = ast.parse(obfuscatedSource)
    originalSymbols = _collectTopLevelSymbols(originalTree)
    obfuscatedSymbols = _collectTopLevelSymbols(obfuscatedTree)
    functions: list[dict] = []
    classes: list[dict] = []

    for i, orig in enumerate(originalSymbols):
        if i >= len(obfuscatedSymbols):
            break
        obf = obfuscatedSymbols[i]
        if orig["kind"] != obf["kind"]:
            continue
        if orig["kind"] == "function":
            renamed = orig["name"] != obf["name"]
            paramMap: list[dict] = []
            for j, p in enumerate(orig["params"]):
                if j < len(obf["params"]):
                    obfP = obf["params"][j]
                    if p != obfP:
                        paramMap.append({"original": p, "obfuscated": obfP})
            entry: dict = {"original": orig["name"], "obfuscated": obf["name"], "renamed": renamed}
            if paramMap:
                entry["params"] = paramMap
            functions.append(entry)
        elif orig["kind"] == "class":
            classRenamed = orig["name"] != obf["name"]
            methodMappings: list[dict] = []
            for j, origMethod in enumerate(orig["methods"]):
                if j >= len(obf["methods"]):
                    break
                obfMethod = obf["methods"][j]
                methodRenamed = origMethod["name"] != obfMethod["name"]
                paramMap = []
                for k, p in enumerate(origMethod["params"]):
                    if k < len(obfMethod["params"]):
                        obfP = obfMethod["params"][k]
                        if p != obfP:
                            paramMap.append({"original": p, "obfuscated": obfP})
                mEntry: dict = {"original": origMethod["name"], "obfuscated": obfMethod["name"], "renamed": methodRenamed}
                if paramMap:
                    mEntry["params"] = paramMap
                methodMappings.append(mEntry)
            cEntry: dict = {"original": orig["name"], "obfuscated": obf["name"], "renamed": classRenamed, "methods": methodMappings}
            classes.append(cEntry)

    return {"functions": functions, "classes": classes}


def applyObfuscationPipelineWithMapping(source: str, protectedNames: frozenset[str], xorKey: int, localClassNames: frozenset[str] = frozenset(), obfConfig: dict | None = None) -> tuple[str, dict]:
    obfuscated = applyObfuscationPipeline(source, protectedNames, xorKey, localClassNames, obfConfig)
    if obfConfig is not None and obfConfig.get("loaderStub", False):
        # the payload lives inside the loader blob — top-level symbols aren't mappable
        return obfuscated, {"functions": [], "classes": []}
    mapping = collectFileMapping(source, obfuscated)
    return obfuscated, mapping


def applyZlibCompression(source: str) -> str:
    import zlib as _zlib
    import base64 as _base64
    compressed = _zlib.compress(source.encode("utf-8"), level=9)
    encoded = _base64.b64encode(compressed)[::-1]
    line1 = "_ = lambda __ : __import__('zlib').decompress(__import__('base64').b64decode(__[::-1]))"
    line2 = f"exec((_)(b'{encoded.decode('ascii')}'), globals(), locals())"
    return line1 + "\n" + line2


_LOADER_NAME_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"

def _makeLoaderName(rng: _random.Random, used: set[str]) -> str:
    # long mangled identifiers like the ones in the reversed loader stub
    while True:
        length = rng.randint(22, 34)
        name = "_" + rng.choice(_string.ascii_lowercase) + "".join(rng.choice(_LOADER_NAME_CHARS) for _ in range(length))
        if name not in used:
            used.add(name)
            return name


def _splitAlphabetChunks(alpha: str, rng: _random.Random) -> tuple[str, ...]:
    cuts = sorted(rng.sample(range(1, len(alpha)), rng.randint(2, 4)))
    parts: list[str] = []
    start = 0
    for c in cuts:
        parts.append(alpha[start:c])
        start = c
    parts.append(alpha[start:])
    return tuple(parts)


_LOADER_STD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

def _extractMetadataHeader(tree: ast.Module) -> tuple[list[tuple[str, ast.AST]], list[ast.AST]]:
    # metadata (__id__, __name__, __requirements__, ...) is AST-parsed from the
    # entry module by the host (see plugins.exteragram.app/docs/plugin-class), so it
    # must stay as plain top-level literals and be pulled out of the payload.
    header: list[tuple[str, ast.AST]] = []
    body: list[ast.AST] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.startswith("__")
            and node.targets[0].id.endswith("__")
        ):
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError):
                body.append(node)
                continue
            header.append((node.targets[0].id, node.value))
            continue
        body.append(node)
    return header, body


def applyLoaderStub(source: str, xorKey: int = 7) -> str:
    # ports the loader-stub obfuscation observed in the reversed plugin:
    # preserved metadata header, mangled import aliases, disguised b64 alphabet,
    # string table + dec(i) helper, getattr hiding, XORed payload + exec.
    import zlib as _zlib
    import base64 as _base64

    tree = ast.parse(source)
    header, body = _extractMetadataHeader(tree)
    payload_source = ast.unparse(ast.Module(body=body, type_ignores=[]))
    compressed = _zlib.compress(payload_source.encode("utf-8"), level=9)
    payload_b64 = _base64.b64encode(compressed).decode("ascii")

    rng = _random.Random((hash(source) ^ xorKey) & 0xFFFFFFFF)
    used: set[str] = set()
    n1 = _makeLoaderName(rng, used)  # base64
    n2 = _makeLoaderName(rng, used)  # zlib
    nA = _makeLoaderName(rng, used)  # disguised alphabet chunks
    nT = _makeLoaderName(rng, used)  # string table
    nK = _makeLoaderName(rng, used)  # string-table xor key
    nD = _makeLoaderName(rng, used)  # dec(i)
    nG = _makeLoaderName(rng, used)  # getattr helper
    nP = _makeLoaderName(rng, used)  # payload chunks
    nQ = _makeLoaderName(rng, used)  # payload xor key
    nR = _makeLoaderName(rng, used)  # decrypt+exec helper
    nJ = _makeLoaderName(rng, used)  # dead-xor junk

    # string table: b64(s) xor round-key
    tbl_key = bytes(rng.randint(0, 255) for _ in range(rng.randint(6, 10)))
    tbl_entries = []
    for s in ("decompress", "b64decode"):
        enc = _base64.b64encode(s.encode()).decode("ascii")
        xored = bytes(b ^ tbl_key[i % len(tbl_key)] for i, b in enumerate(enc.encode()))
        tbl_entries.append(xored)
    table_repr = "(" + ", ".join(repr(e) for e in tbl_entries) + ",)"
    key_repr = "(" + ", ".join(str(b) for b in tbl_key) + ",)"

    # payload: b64(compressed source) xor round-key, split into chunks
    payload_key = [rng.randint(0, 255) for _ in range(rng.randint(8, 16))]
    xored_payload = bytes(b ^ payload_key[i % len(payload_key)] for i, b in enumerate(payload_b64.encode()))
    nchunks = rng.randint(3, 6)
    chunk_len = max(1, len(xored_payload) // nchunks)
    chunks = [xored_payload[i * chunk_len:(i + 1) * chunk_len] for i in range(nchunks)]
    chunks[-1] = xored_payload[(nchunks - 1) * chunk_len:]
    chunks = [c for c in chunks if c]
    payload_chunks_repr = "(" + ", ".join(repr(c) for c in chunks) + ",)"
    payload_key_repr = "(" + ", ".join(str(b) for b in payload_key) + ",)"

    alpha_repr = repr(_splitAlphabetChunks(_LOADER_STD_ALPHABET, rng))

    lines: list[str] = []
    for name, const in header:
        lines.append(f"{name} = {repr(ast.literal_eval(const))}")
    if header:
        lines.append("")

    lines.append(f"import base64 as {n1}")
    lines.append(f"import zlib as {n2}")
    lines.append("")
    lines.append(f"{nA} = {alpha_repr}")
    lines.append(f"{nT} = {table_repr}")
    lines.append(f"{nK} = {key_repr}")
    lines.append(f"{nJ} = lambda b: bytes(c ^ 0x55 ^ 0x55 for c in b)")
    lines.append(f"{nD} = lambda i, t={nT}, k={nK}, b64={n1}.b64decode: b64(bytes(c ^ k[i % len(k)] for i, c in enumerate(t[i]))).decode()")
    lines.append(f"{nG} = lambda m, i: getattr(m, {nD}(i))")
    lines.append(f"{nP} = {payload_chunks_repr}")
    lines.append(f"{nQ} = {payload_key_repr}")
    lines.append(
        f"{nR} = lambda p, q, b64={n1}.b64decode, dec={nD}, z={n2}, j={nJ}: "
        f"getattr(z, dec(0))(b64(bytes(c ^ q[i % len(q)] for i, c in enumerate(b''.join(p)))))"
    )
    lines.append(f"exec(({nR})({nP}, {nQ}), globals(), globals())")
    return "\n".join(lines)


def applyObfuscationPipeline(source: str, protectedNames: frozenset[str], xorKey: int, localClassNames: frozenset[str] = frozenset(), obfConfig: dict | None = None) -> str:
    if obfConfig is None:
        obfConfig = {}
    doStripDocstrings: bool = obfConfig.get("stripDocstrings", True)
    doRemoveLogs: bool = obfConfig.get("removeLogs", True)
    doRenameLocals: bool = obfConfig.get("renameLocals", True)
    doEncodeStrings: bool = obfConfig.get("encodeStrings", True)
    doEncodeNumbers: bool = obfConfig.get("encodeNumbers", True)
    doZlibCompression: bool = obfConfig.get("zlibCompression", False)
    doJunkCode: bool = obfConfig.get("junkCode", False)
    doStringSplitting: bool = obfConfig.get("stringSplitting", False)
    doLoaderStub: bool = obfConfig.get("loaderStub", False)

    commentLines = _scanCommentLines(source)
    tree = ast.parse(source)

    # Metadata (__id__, __name__, __requirements__, ...) is AST-parsed from the
    # entry module by the host (plugins.exteragram.app/docs/plugin-class). Pull the
    # plain top-level literals out BEFORE any pass so encodeStrings/encodeNumbers
    # cannot turn them into expressions, then re-attach them verbatim at the end.
    metadataHeader, metadataBody = _extractMetadataHeader(tree)
    tree = ast.Module(body=metadataBody, type_ignores=[])
    headerText = ""
    if metadataHeader:
        headerText = "\n".join(f"{name} = {repr(ast.literal_eval(const))}" for name, const in metadataHeader) + "\n\n"

    fstringNames: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    fstringNames.add(child.id)
    allProtected = protectedNames | frozenset(fstringNames)
    fstringMap: dict[str, str] = {}
    placeholderCounter = [0]

    class ExtractFStrings(ast.NodeTransformer):
        def visit_JoinedStr(self, node: ast.JoinedStr) -> ast.Constant:
            key = f"__ELYBF{placeholderCounter[0]}__"
            placeholderCounter[0] += 1
            original = ast.get_source_segment(source, node)
            if original is not None:
                original = original.strip().splitlines()[0].strip()
            fstringMap[key] = original if original is not None else ast.unparse(node)
            return ast.copy_location(ast.Constant(value=key), node)
    tree = ExtractFStrings().visit(tree)
    placeholderKeys = frozenset(fstringMap.keys())

    # Inject junk code at module level to confuse reverse engineers
    if doJunkCode:
        seed = hash(source + str(xorKey)) & 0xFFFFFFFF
        junk_funcs = _generateJunkCode(seed)
        # Insert junk functions at the beginning of the module body
        for junk_func in reversed(junk_funcs):
            tree.body.insert(0, junk_func)

    MarkNoObfNodes().visit(tree)
    if doStripDocstrings:
        tree = StripDocstrings().visit(tree)
    if doRemoveLogs:
        tree = RemoveLogs(commentLines["# ELYBsaveLog"]).visit(tree)
    if doRenameLocals:
        tree = RenameLocals(allProtected, localClassNames).visit(tree)
    if doEncodeStrings:
        # Use enhanced string encoder with dynamic multi-byte XOR
        tree = EncodeStringsAdvanced(commentLines["# ELYBnoStrobf"], allProtected | placeholderKeys, xorKey, skipDocstrings=not doStripDocstrings, useStringSplitting=doStringSplitting).visit(tree)
    if doEncodeNumbers:
        tree = EncodeNumbers(commentLines["# ELYBnoIntObf"]).visit(tree)
    ast.fix_missing_locations(tree)
    result = ast.unparse(tree)
    result = headerText + result
    for key, original in fstringMap.items():
        result = result.replace(f"'{key}'", original)
    if doZlibCompression:
        result = applyZlibCompression(result)
    if doLoaderStub:
        result = applyLoaderStub(result, xorKey)
    return result
