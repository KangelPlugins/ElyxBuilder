import ast
import fnmatch
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import zipfile
import yaml

from elyb.cmds.stats import incrementBuildStats, incrementFailedBuildStats, loadStats
from elyb.cmds.components.progress import ProgressBar, countBuildWork

def loadYaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def loadJson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def findRefmap(cwd: str) -> tuple[str, dict] | None:
    # yaml has priority; fall back to json
    for name in ("refmap.yml", "refmap.yaml", "refmap.json"):
        path = os.path.join(cwd, name)
        if os.path.exists(path):
            data = loadJson(path) if name.endswith(".json") else loadYaml(path)
            return path, data
    return None

def loadMetainfo(metaPath: str) -> dict:
    if metaPath.endswith(".json"):
        return loadJson(metaPath)
    return loadYaml(metaPath)

def resolveBuildName(template: str, meta: dict) -> str:
    def replace(match):
        key = match.group(1)
        value = meta.get(key)
        if value is None:
            raise KeyError(f"meta.yml missing field: {key}")
        return str(value)
    return re.sub(r"\{(\w+)\}", replace, template)

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"

ENCRYPTION_METHODS: dict[str, tuple[str, int | None]] = {
    "zipcrypto": ("zipcrypto", None),
    "aes-128":   ("aes", 128),
    "aes-192":   ("aes", 192),
    "aes-256":   ("aes", 256),
}

def printEncryptionHelp() -> None:
    print("Available encryption methods:\n")
    print("  zipcrypto   Standard ZIP encryption, compatible with most archivers")
    print("  aes-128     AES encryption, 128-bit key")
    print("  aes-192     AES encryption, 192-bit key")
    print("  aes-256     AES encryption, 256-bit key (recommended)")
    print("\nUsage: elyb build -p <method> <password>")

def resolveEncryption(method: str, password: str) -> tuple[bool, object, int | None]:
    if method not in ENCRYPTION_METHODS:
        print(f"{RED}error: unknown encryption method: {method!r}{RESET}\n")
        printEncryptionHelp()
        return False, None, None
    try:
        import pyzipper
    except ImportError:
        print("pyzipper is required for encryption.")
        print("Install it with: pip install pyzipper")
        return False, None, None
    _, aesStrength = ENCRYPTION_METHODS[method]
    return True, pyzipper, aesStrength


def openArchive(archivePath: str, encryptMethod: str | None, password: str | None, pyzipper: object):
    if encryptMethod is None:
        return zipfile.ZipFile(archivePath, "w", zipfile.ZIP_DEFLATED)
    _, aesStrength = ENCRYPTION_METHODS[encryptMethod]
    if aesStrength is not None:
        zf = pyzipper.AESZipFile(archivePath, "w", compression=pyzipper.ZIP_DEFLATED)
        zf.setencryption(pyzipper.WZ_AES, nbits=aesStrength)
    else:
        zf = pyzipper.AESZipFile(archivePath, "w", compression=pyzipper.ZIP_DEFLATED)
        zf.setencryption(pyzipper.WZ_ZIP2)
    zf.setpassword(password.encode())
    return zf

def findPython311() -> str | None:
    candidates = ["python3.11", "python3", "python"]
    if sys.platform == "win32":
        candidates = ["python3.11", "python3", "python", "py"]
    for name in candidates:
        try:
            result = subprocess.run(
                [name, "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and "3.11" in result.stdout + result.stderr:
                return name
        except FileNotFoundError:
            continue
    return None

def loadManifest(manifestPath: str) -> dict:
    if not os.path.exists(manifestPath):
        return {}
    with open(manifestPath, "r", encoding="utf-8") as f:
        return json.load(f)

def saveManifest(manifestPath: str, manifest: dict) -> None:
    os.makedirs(os.path.dirname(manifestPath), exist_ok=True)
    with open(manifestPath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

OBF_CONFIG_KEYS: list[str] = [
    "stripDocstrings",
    "removeLogs",
    "renameLocals",
    "encodeStrings",
    "encodeNumbers",
    "zlibCompression",
    "junkCode",
    "stringSplitting",
    "loaderStub",
    "loaderStubDynamic",
    "loaderStubDynamicKey",
    "saveMapping",
]

OBF_CONFIG_DEFAULTS: dict[str, bool | None] = {
    "zlibCompression": False,
    "junkCode": True,
    "stringSplitting": True,
    "loaderStub": False,
    "loaderStubDynamic": False,
    "loaderStubDynamicKey": None,
}

def loadObfuscationConfig(config: dict, configPath: str) -> dict:
    raw = config.get("obfuscationConfig")
    if not isinstance(raw, dict):
        raw = {}
    changed = False
    for key in OBF_CONFIG_KEYS:
        if key not in raw and key in OBF_CONFIG_DEFAULTS:
            raw[key] = OBF_CONFIG_DEFAULTS[key]
            changed = True
    if changed:
        config["obfuscationConfig"] = raw
        with open(configPath, "r", encoding="utf-8") as f:
            text = f.read()
        parsed = yaml.safe_load(text)
        parsed["obfuscationConfig"] = raw
        parsed.pop("RemoveLogs", None)
        with open(configPath, "w", encoding="utf-8") as f:
            yaml.dump(parsed, f, allow_unicode=True, sort_keys=False)
    return raw


def buildMetaInfo(metaPath: str, compiled: bool, buildNum: int, compilePythonVer: str, staticVersion: str | None, staticClient: str | None = None) -> str:
    with open(metaPath, "r", encoding="utf-8") as f:
        original = f.read()
    try:
        version = importlib.metadata.version("ElyxBuilder")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    import datetime
    import hashlib
    buildDate = datetime.date.today().isoformat()
    sourceDir = os.path.dirname(metaPath)
    hasher = hashlib.sha256()
    for root, dirs, files in os.walk(sourceDir):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for file in sorted(files):
            if file.endswith(".py"):
                absPath = os.path.join(root, file)
                with open(absPath, "rb") as f:
                    hasher.update(f.read())
    sourceHash = hasher.hexdigest()
    meta = json.loads(original) if metaPath.endswith(".json") else yaml.safe_load(original)
    meta["elyxbuilder"] = {
        "compiled": compiled,
        "buildNum": buildNum,
        "buildDate": buildDate,
        "pythonVer": compilePythonVer,
        "sourceHash": sourceHash,
        "elybVer": version,
    }

    if staticVersion is not None:
        meta["elyxbuilder"]["staticVer"] = staticVersion
    if staticClient is not None:
        meta["elyxbuilder"]["client"] = staticClient

    return json.dumps(meta, indent=2, ensure_ascii=False) if metaPath.endswith(".json") else yaml.dump(meta, allow_unicode=True, sort_keys=False)

def compileSourceFiles(sourceDir: str, cacheDir: str, ignoreAbsPaths: set[str], log, bar: "ProgressBar | None" = None, obfuscateAll: bool = False, obfuscateFiles: frozenset[str] = frozenset(), protectedNames: frozenset[str] = frozenset(), localClassNames: frozenset[str] = frozenset(), obfConfig: dict | None = None, optimizeLevel: int = 1, obfIgnoreAbsPaths: set[str] | None = None, obfuscatedSources: dict[str, bytes] | None = None, obfuscationMapping: dict[str, dict] | None = None, arcBase: str | None = None) -> tuple[bool, dict]:
    if obfConfig is None:
        obfConfig = {}
    if optimizeLevel not in (0, 1, 2):
        print(f"{RED}error: invalid optimize level {optimizeLevel!r}. Must be 0, 1, or 2.{RESET}")
        return False, {}
    import random
    from .obfuscate import applyObfuscationPipeline
    python311 = findPython311()
    if python311 is None:
        print(
            "Please install Python3.11 for compilation. "
            "After installation, reinstall the ElyxBuilder package."
        )
        return False, {}

    manifestPath = os.path.join(cacheDir, "manifest.json")
    manifest = loadManifest(manifestPath)
    compiled = 0
    cached = 0

    for root, dirs, files in os.walk(sourceDir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            if not file.endswith(".py"):
                continue
            absPath = os.path.join(root, file)
            normalizedAbs = os.path.normpath(absPath)
            if normalizedAbs in ignoreAbsPaths:
                log(f"  compile: skip {os.path.relpath(absPath, sourceDir)}")
                # Even skipped-from-compile files can be obfuscated (compilationIgnore ≠ obfuscationIgnore)
                _obfSkip2 = obfIgnoreAbsPaths if obfIgnoreAbsPaths is not None else ignoreAbsPaths
                if normalizedAbs in _obfSkip2:
                    continue
                # This file is compiled-but-not-compiled; obfuscate source and write to arc
                relPath = os.path.relpath(absPath, sourceDir).replace(os.sep, "/")
                if obfuscateAll or relPath in obfuscateFiles:
                    from .obfuscate import applyObfuscationPipelineWithMapping
                    with open(absPath, "r", encoding="utf-8") as f:
                        source = f.read()
                    xorKey = random.randint(1, 254)
                    obfuscated, fileMapping = applyObfuscationPipelineWithMapping(source, protectedNames, xorKey, localClassNames, obfConfig)
                    arcKey = os.path.relpath(absPath, arcBase).replace(os.sep, "/") if arcBase else relPath
                    obfuscatedSources[arcKey] = obfuscated.encode("utf-8")
                    obfuscationMapping[relPath] = fileMapping
                    log(f"  obfuscated (source): {relPath}")
                continue
            relPath = os.path.relpath(absPath, sourceDir).replace(os.sep, "/")
            # files in compilationIgnore are never obfuscated (In the glow of starry sky, seven nights I would lie Now I know I wanna stay, I will never go away In the moonlight)
            _obfSkip = obfIgnoreAbsPaths if obfIgnoreAbsPaths is not None else ignoreAbsPaths
            shouldObfuscate = (
                normalizedAbs not in _obfSkip
                and (obfuscateAll or relPath in obfuscateFiles)
            )

            stat = os.stat(absPath)
            entry = manifest.get(relPath)

            pycRelPath = relPath[:-3] + ".pyc"
            pycAbsPath = os.path.join(cacheDir, pycRelPath.replace("/", os.sep))

            if not shouldObfuscate:
                cacheHit = (
                    entry is not None
                    and entry.get("mtime") == stat.st_mtime
                    and entry.get("size") == stat.st_size
                    and entry.get("optimizeLevel") == optimizeLevel
                    and os.path.exists(pycAbsPath)
                )
                if cacheHit:
                    log(f"  compile: cached {relPath}")
                    cached += 1
                    if bar:
                        bar.advance()
                    continue
            os.makedirs(os.path.dirname(pycAbsPath), exist_ok=True)
            
            if shouldObfuscate:
                with open(absPath, "r", encoding="utf-8") as f:
                    source = f.read()
                xorKey = random.randint(1, 254)
                source = applyObfuscationPipeline(source, protectedNames, xorKey, localClassNames, obfConfig)

                tmpPath = absPath + ".obf.tmp"
                try:
                    with open(tmpPath, "w", encoding="utf-8") as f:
                        f.write(source)
                    result = subprocess.run(
                        [python311, "-c",
                         f"import py_compile; py_compile.compile({tmpPath!r}, cfile={pycAbsPath!r}, dfile={relPath!r}, doraise=True, optimize={optimizeLevel})"],
                        capture_output=True,
                        text=True,
                    )
                finally:
                    if os.path.exists(tmpPath):
                        os.remove(tmpPath)
                log(f"  compile: {relPath} (obfuscated)")
            else:
                result = subprocess.run(
                    [python311, "-c",
                     f"import py_compile; py_compile.compile({absPath!r}, cfile={pycAbsPath!r}, dfile={relPath!r}, doraise=True, optimize={optimizeLevel})"],
                    capture_output=True,
                    text=True,
                )
                log(f"  compile: {relPath}")

            if result.returncode != 0:
                print(f"{RED}Compilation failed:{RESET}")
                print(f"{RED}{result.stderr.strip()}{RESET}")
                return False, manifest
            if not shouldObfuscate:
                manifest[relPath] = {"mtime": stat.st_mtime, "size": stat.st_size, "optimizeLevel": optimizeLevel}
            compiled += 1
            if bar:
                bar.advance()
    saveManifest(manifestPath, manifest)
    log(f"compile: {compiled} compiled, {cached} from cache")
    return True, manifest

def pycCachePath(sourceDir: str, cacheDir: str, pyAbsPath: str) -> str:
    relPath = os.path.relpath(pyAbsPath, sourceDir).replace(os.sep, "/")
    pycRelPath = relPath[:-3] + ".pyc"
    return os.path.join(cacheDir, pycRelPath.replace("/", os.sep))

def checkAst(sourceDir: str, verbose: bool, log) -> bool:
    for root, dirs, files in os.walk(sourceDir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            if not file.endswith(".py"):
                continue
            absPath = os.path.join(root, file)
            relPath = os.path.relpath(absPath, sourceDir).replace(os.sep, "/")
            log(f"  ast check: {relPath}")
            try:
                with open(absPath, "r", encoding="utf-8") as f:
                    ast.parse(f.read(), filename=relPath)
            except SyntaxError as e:
                print(f"{RED}Failed to complete build:{RESET}")
                print(f"{RED}{e}{RESET}")
                return False
    return True

def runBuild(noAssets: bool = False, noFolder: bool = False, verbose: bool = False, checkAstFlag: bool = False, compileLevel: int | None = None, resetCache: bool = False, encryptMethod: str | None = None, encryptPassword: str | None = None, noInfo: bool = False, staticVersion: str | None = None, staticVersionInName: bool = False, staticClient: str | None = None, staticClientName: str | None = None, obfuscation: list[str] | None = None):
    def fail(msg: str) -> None:
        print(f"{RED}error: {msg}{RESET}")

    if resetCache and compileLevel is None:
        fail("--reset requires --compile")
        return

    obfuscateAll = obfuscation is not None and len(obfuscation) == 0
    obfuscateFiles: frozenset[str] = frozenset(obfuscation) if obfuscation else frozenset()

    pyzipperModule = None
    if encryptMethod is not None:
        ok, pyzipperModule, _ = resolveEncryption(encryptMethod, encryptPassword)
        if not ok:
            return

    cwd = os.getcwd()
    refmapResult = findRefmap(cwd)
    if not refmapResult:
        fail("refmap.yml not found in current directory")
        return
    refmapPath, refmap = refmapResult

    builderRelPath = refmap.get("elyxbuilder")
    if not builderRelPath:
        fail(f"{os.path.basename(refmapPath)} missing key: elyxbuilder")
        return
    builderDir = os.path.join(cwd, builderRelPath)
    if not os.path.isdir(builderDir):
        fail(f"builder directory not found: {builderDir}")
        return

    def failTracked(msg: str) -> None:
        print(f"{RED}error: {msg}{RESET}")
        incrementFailedBuildStats(builderDir)
    fail = failTracked

    configPath = os.path.join(builderDir, "config.yml")
    if not os.path.exists(configPath):
        fail(f"config.yml not found in {builderDir}")
        return
    config = loadYaml(configPath)

    elyxConfigPath = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(elyxConfigPath, "r", encoding="utf-8") as f:
        elyxConfig = json.load(f)
    compilePythonVer = elyxConfig.get("compilePythonVer", "3.11")

    excludedAssets: set[str] = set()
    if noAssets:
        rawAssets = config.get("optionalAssets")
        if isinstance(rawAssets, list):
            excludedAssets = set(rawAssets)

    obfConfig: dict = loadObfuscationConfig(config, configPath)
    rawIgnoreAll = config.get("ignoreAll")
    ignoreAll: list[str] = rawIgnoreAll if isinstance(rawIgnoreAll, list) else []
    zipFormat = config.get("zipFormat")

    if not zipFormat:
        fail("config.yml missing key: zipFormat")
        return
    buildNameUncompiled = config.get("buildNameUncompiled")
    if not buildNameUncompiled:
        fail("config.yml missing key: buildNameUncompiled")
        return

    if compileLevel is not None:
        buildNameTemplate = config.get("buildNameCompiled")
        if not buildNameTemplate:
            fail("config.yml missing key: buildNameCompiled")
            return
    else:
        buildNameTemplate = buildNameUncompiled

    metaRelPath = refmap.get("metainfo")
    if not metaRelPath:
        fail(f"{os.path.basename(refmapPath)} missing key: metainfo")
        return
    metaPath = os.path.join(cwd, metaRelPath)
    if not os.path.exists(metaPath):
        fail(f"metainfo not found: {metaPath}")
        return
    meta = loadMetainfo(metaPath)

    try:
        buildName = resolveBuildName(buildNameTemplate, meta)
    except KeyError as e:
        fail(str(e))
        return

    suffix = ""
    if staticVersionInName and staticVersion:
        suffix += f"-{staticVersion}"
    if staticClientName is not None:
        suffix += f"-{staticClientName}"
    archiveName = f"{buildName}{suffix}.{zipFormat}"

    buildsDir = os.path.join(cwd, "builds")
    os.makedirs(buildsDir, exist_ok=True)
    archivePath = os.path.join(buildsDir, archiveName)

    pluginDir = os.path.dirname(builderDir)
    arcBase = os.path.dirname(os.path.normpath(pluginDir))
    sourceRelPath = config.get("source")

    # pre-scan ignore paths for work estimation
    rawIgnorePre = config.get("compilationIgnore") or []
    ignoreAbsPathsPre: set[str] = {os.path.normpath(os.path.join(cwd, p)) for p in rawIgnorePre}
    sourceDirPre = os.path.join(cwd, sourceRelPath) if sourceRelPath else None
    total = countBuildWork(sourceDirPre, pluginDir, ignoreAbsPathsPre, compileLevel, obfuscation, checkAstFlag)

    bar = ProgressBar(total)
    bar.start()

    def log(msg: str) -> None:
        if verbose:
            bar.log(msg)

    def status(msg: str) -> None:
        if not verbose:
            bar.log(msg)

    # setup done
    bar.advance()
    status("Loading config")

    if checkAstFlag:
        if not sourceRelPath:
            bar.stop()
            fail("config.yml missing key: source (required for --ast)")
            return
        sourceDir = os.path.join(cwd, sourceRelPath)
        log(f"ast: scanning {sourceDir}")
        status("AST check")
        if not checkAst(sourceDir, verbose, log):
            bar.stop()
            incrementFailedBuildStats(builderDir)
            return
        bar.advance()

    obfuscatedSources: dict[str, bytes] = {}
    if obfuscation is not None and compileLevel is None:
        if not sourceRelPath:
            bar.stop()
            fail("config.yml missing key: source (required for --obfuscation)")
            return
        sourceDir = os.path.join(cwd, sourceRelPath)
        rawIgnore = config.get("compilationIgnore") or []
        ignoreAbsPaths = {os.path.normpath(os.path.join(cwd, p)) for p in rawIgnore}

        # obfuscationIgnore decouples obfuscation from compilationIgnore
        rawObfIgnore = config.get("obfuscationIgnore")
        if rawObfIgnore is not None:
            obfIgnoreAbsPaths = {os.path.normpath(os.path.join(cwd, p)) for p in rawObfIgnore}
        else:
            obfIgnoreAbsPaths = ignoreAbsPaths

        from elyb.cmds.obfuscate import collectProtectedNames, collectLocalClassNames, applyObfuscationPipelineWithMapping
        import random
        protectedNames = collectProtectedNames(sourceDir)
        localClassNames = collectLocalClassNames(sourceDir)
        log(f"obfuscation: collected {len(protectedNames)} protected name(s)")
        obfuscationMapping: dict[str, dict] = {}

        status("Obfuscating source")
        for root, dirs, files in os.walk(sourceDir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if not file.endswith(".py"):
                    continue
                absPath = os.path.join(root, file)
                normalizedAbs = os.path.normpath(absPath)
                if normalizedAbs in obfIgnoreAbsPaths:
                    continue
                relPath = os.path.relpath(absPath, sourceDir)
                relPathUnix = relPath.replace(os.sep, "/")
                if obfuscateFiles and relPathUnix not in obfuscateFiles:
                    continue
                with open(absPath, "r", encoding="utf-8") as f:
                    source = f.read()
                xorKey = random.randint(1, 254)
                obfuscated, fileMapping = applyObfuscationPipelineWithMapping(source, protectedNames, xorKey, localClassNames, obfConfig)
                arcKey = os.path.relpath(absPath, arcBase).replace(os.sep, "/")
                obfuscatedSources[arcKey] = obfuscated.encode("utf-8")
                obfuscationMapping[relPathUnix] = fileMapping
                log(f"  obfuscated: {relPathUnix}")
                bar.advance()

        if obfConfig.get("saveMapping", True):
            mappingPath = os.path.join(buildsDir, "latest_mapping.json")
            with open(mappingPath, "w", encoding="utf-8") as f:
                json.dump(obfuscationMapping, f, indent=2, ensure_ascii=False)
            log(f"mapping saved: {mappingPath}")

    if compileLevel is not None:
        if not sourceRelPath:
            bar.stop()
            fail("config.yml missing key: source (required for --compile)")
            return
        sourceDir = os.path.join(cwd, sourceRelPath)
        cacheDir = os.path.join(cwd, ".elyx", "cache", "python311")

        if resetCache and os.path.exists(cacheDir):
            import shutil
            shutil.rmtree(cacheDir)
            log("compile: cache cleared")

        rawIgnore = config.get("compilationIgnore") or []
        ignoreAbsPaths = {os.path.normpath(os.path.join(cwd, p)) for p in rawIgnore}
        log(f"compile: scanning {sourceDir}, ignoring {len(ignoreAbsPaths)} file(s)")

        # obfuscationIgnore decouples obfuscation from compilationIgnore
        rawObfIgnore = config.get("obfuscationIgnore")
        if rawObfIgnore is not None:
            obfIgnoreAbsPaths = {os.path.normpath(os.path.join(cwd, p)) for p in rawObfIgnore}
            log(f"compile: obfuscation ignore: {len(obfIgnoreAbsPaths)} file(s)")
        else:
            obfIgnoreAbsPaths = None  # fall back to compilationIgnore

        obfuscatedSources: dict[str, bytes] = {}
        obfuscationMapping: dict[str, dict] = {}

        protectedNames: frozenset[str] = frozenset()
        localClassNames: frozenset[str] = frozenset()
        if obfuscation is not None:
            from elyb.cmds.obfuscate import collectProtectedNames, collectLocalClassNames
            protectedNames = collectProtectedNames(sourceDir)
            localClassNames = collectLocalClassNames(sourceDir)
            log(f"obfuscation: collected {len(protectedNames)} protected name(s)")

        obfuscationMapping: dict[str, dict] = {}

        status("Compiling to bytecode")
        ok, _ = compileSourceFiles(sourceDir, cacheDir, ignoreAbsPaths, log, bar, obfuscateAll, obfuscateFiles, protectedNames, localClassNames, obfConfig, compileLevel, obfIgnoreAbsPaths=obfIgnoreAbsPaths, obfuscatedSources=obfuscatedSources, obfuscationMapping=obfuscationMapping, arcBase=arcBase)
        if not ok:
            bar.stop()
            incrementFailedBuildStats(builderDir)
            return

        if obfuscation is not None and obfuscationMapping and obfConfig.get("saveMapping", True):
            mappingPath = os.path.join(buildsDir, "latest_mapping.json")
            with open(mappingPath, "w", encoding="utf-8") as f:
                json.dump(obfuscationMapping, f, indent=2, ensure_ascii=False)
            log(f"mapping saved: {mappingPath}")

    statsPath = os.path.join(builderDir, "stats.yml")
    buildNum = loadStats(statsPath)["builds"] + 1
    metaAbsPath = os.path.normpath(metaPath)

    # strip @ELYBNoObf — always
    cleanedSources: dict[str, bytes] = {}
    if sourceRelPath:
        sourceDir = os.path.join(cwd, sourceRelPath)
        rawIgnoreClean = config.get("compilationIgnore") or []
        ignoreAbsClean = {os.path.normpath(os.path.join(cwd, p)) for p in rawIgnoreClean}
        from elyb.cmds.obfuscate import stripNoObfDecorator
        for root, dirs, files in os.walk(sourceDir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if not file.endswith(".py"):
                    continue
                absPath = os.path.join(root, file)
                arcName = os.path.relpath(absPath, arcBase).replace(os.sep, "/")
                if arcName in obfuscatedSources:
                    continue
                if compileLevel is not None and os.path.normpath(absPath) not in ignoreAbsClean:
                    continue
                with open(absPath, "r", encoding="utf-8") as f:
                    source = f.read()
                cleaned = stripNoObfDecorator(source)
                if cleaned == source:
                    continue
                cleanedSources[arcName] = cleaned.encode("utf-8")
                log(f"  cleanup: {os.path.relpath(absPath, sourceDir).replace(os.sep, '/')}")

    status("Packing archive")
    bar.advance()
    fileCount = 0
    skippedCount = 0

    with openArchive(archivePath, encryptMethod, encryptPassword, pyzipperModule) as zf:
        refmapArcName = os.path.relpath(refmapPath, cwd).replace(os.sep, "/")
        zf.write(refmapPath, refmapArcName)
        log(f"  + {refmapArcName}")
        fileCount += 1
        bar.advance()

        for root, dirs, files in os.walk(pluginDir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            if noFolder and os.path.normpath(root) == os.path.normpath(builderDir):
                dirs.clear()
                log(f"  - {os.path.relpath(root, arcBase).replace(os.sep, '/')}/ (--no-folder)")
                continue

            relDir = os.path.relpath(root, arcBase).replace(os.sep, "/")
            dirInfo = zipfile.ZipInfo(relDir + "/")
            zf.writestr(dirInfo, "")
            log(f"  d {relDir}/")

            for file in files:
                absPath = os.path.join(root, file)
                arcName = relDir + "/" + file
                if any(fnmatch.fnmatch(arcName, pattern) for pattern in ignoreAll):
                    log(f"  - {arcName} (ignoreAll)")
                    skippedCount += 1
                    continue
                if excludedAssets and arcName in excludedAssets:
                    log(f"  - {arcName} (excluded)")
                    skippedCount += 1
                    continue
                if compileLevel is not None and file.endswith(".py"):
                    normalizedAbs = os.path.normpath(absPath)
                    if normalizedAbs in ignoreAbsPaths:
                        # ignored from compilation — check if obfuscated version exists
                        if arcName in obfuscatedSources:
                            zf.writestr(arcName, obfuscatedSources[arcName])
                            log(f"  + {arcName} (obfuscated, source)")
                        else:
                            zf.write(absPath, arcName)
                            log(f"  + {arcName} (not compiled)")
                        fileCount += 1
                        bar.advance()
                        continue
                    pycPath = pycCachePath(sourceDir, cacheDir, absPath)
                    pycArcName = relDir + "/" + file[:-3] + ".pyc"
                    zf.write(pycPath, pycArcName)
                    log(f"  + {pycArcName} (compiled from {file})")
                    fileCount += 1
                    bar.advance()
                    continue
                if not noInfo and os.path.normpath(absPath) == metaAbsPath:
                    patchedMeta = buildMetaInfo(absPath, compileLevel is not None, buildNum, compilePythonVer, staticVersion, staticClient)
                    zf.writestr(arcName, patchedMeta.encode("utf-8"))
                    log(f"  + {arcName} (patched)")
                elif arcName in obfuscatedSources:
                    zf.writestr(arcName, obfuscatedSources[arcName])
                    log(f"  + {arcName} (obfuscated)")
                elif arcName in cleanedSources:
                    zf.writestr(arcName, cleanedSources[arcName])
                    log(f"  + {arcName} (cleaned)")
                else:
                    zf.write(absPath, arcName)
                    log(f"  + {arcName}")
                fileCount += 1
                bar.advance()

    if verbose:
        log(f"packed {fileCount} file(s), skipped {skippedCount} file(s)")

    bar.stop()
    incrementBuildStats(builderDir, compileLevel is not None)
    relArchivePath = os.path.join("builds", archiveName)
    print(f"{GREEN}Successful build at {relArchivePath}!{RESET}")
