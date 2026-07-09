import os
import sys

from elyb.cmds.build import findRefmap
from elyb.elyxdsl.lexer import tokenize
from elyb.elyxdsl.parser import parse
from elyb.elyxdsl.errors import ParseError, ElyxRuntimeError, ScriptExit

RED = "\033[31m"
RESET = "\033[0m"


def runScript(scriptName: str, scriptArgs: list):
    cwd = os.getcwd()
    refmapResult = findRefmap(cwd)
    if not refmapResult:
        print(f"{RED}error: refmap.yml not found in current directory{RESET}")
        sys.exit(1)

    refmapPath, refmap = refmapResult
    builderRelPath = refmap.get("elyxbuilder")
    if not builderRelPath:
        print(f"{RED}error: refmap.yml missing key: elyxbuilder{RESET}")
        sys.exit(1)

    scriptPath = os.path.join(cwd, builderRelPath, "scripts", scriptName + ".edsl")
    if not os.path.exists(scriptPath):
        print(f"{RED}error: script \"{scriptName}\" not found{RESET}")
        sys.exit(1)

    with open(scriptPath, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tokens = tokenize(source, scriptPath)
        ast = parse(tokens, scriptPath)
    except ParseError as e:
        print(str(e))
        sys.exit(1)

    try:
        from elyb.elyxdsl.interpreter import run
        run(ast, scriptPath, scriptArgs)
    except ParseError as e:
        print(str(e))
        sys.exit(1)
    except ElyxRuntimeError as e:
        print(str(e))
        sys.exit(1)
    except ScriptExit as e:
        sys.exit(e.code)
