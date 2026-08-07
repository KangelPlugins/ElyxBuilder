import argparse
import shlex
import sys

from elyb.cmds.version import runVersion
from elyb.cmds.new import runNew, runInteractive
from elyb.cmds.build import runBuild
from elyb.cmds.cached import runCached
from elyb.cmds.ignore import runAddIgnore, runDelIgnore
from elyb.cmds.stats import runStatBuilds, runStatLines, runStatSize, runStatFiles
from elyb.cmds.watch import runWatch
from elyb.cmds.script import runScript

def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="elyb")
    parser.add_argument("-v", "--version", action="store_true", help="show version")
    subparsers = parser.add_subparsers(dest="command")
    newParser = subparsers.add_parser("new", help="create new plugin from template")
    newParser.add_argument("-g", "--gen", action="store_true", dest="gen", help="fast generation (non-interactive)")
    newParser.add_argument("-n", "--name", dest="pluginname", help="plugin name (required with --gen)")
    newParser.add_argument("-a", "--author", dest="author", help="author id (required with --gen)")
    newParser.add_argument("-zf", "--zipformat", default="eaf", help="zip format (default: eaf, only with --gen)")
    buildParser = subparsers.add_parser("build", help="build plugin into archive")
    buildParser.add_argument("--no-assets", action="store_true", dest="noAssets", help="exclude optionalAssets from archive")
    buildParser.add_argument("-nf", "--no-folder", action="store_true", dest="noFolder", help="exclude elyxbuilder directory from archive")
    buildParser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="print build log")
    buildParser.add_argument("-r", "--reset", action="store_true", dest="reset", help="clear compilation cache before build (requires --compile)")
    buildParser.add_argument("-p", "--password", nargs=2, metavar=("METHOD", "PASSWORD"), dest="encrypt", help="encrypt archive (e.g. -p aes-256 mypassword)")
    buildParser.add_argument("-ni", "--no-info", action="store_true", dest="noInfo", help="skip appending elyxbuilder info block to meta.yml")
    buildParser.add_argument("-sv", "--static-version", nargs="+", metavar=("VERSION", "APPEND"), dest="staticVersion", default=None, help="set static_ver in build info; optional APPEND=true appends version to archive name")
    buildParser.add_argument("-sc", "--static-client", nargs="+", metavar=("PACKAGE", "NAME"), dest="staticClient", default=None, help="set client in build info; optional NAME appended to archive name")
    buildModeGroup = buildParser.add_mutually_exclusive_group()
    buildModeGroup.add_argument("-a", "--ast", action="store_true", dest="checkAst", help="check .py files in source via AST before build")
    buildModeGroup.add_argument("-c", "--compile", nargs="?", type=int, choices=[0, 1, 2], const=1, default=None, dest="compile", metavar="LEVEL", help="compile .py files to .pyc (optimization level 0-2, default 1)")
    buildParser.add_argument("-o", "--obfuscation", nargs="*", metavar="FILE", dest="obfuscation", default=None, help="obfuscate source before compilation; optional file paths relative to source")
    subparsers.add_parser("cached", help="show which source files have changed since last compilation")
    watchParser = subparsers.add_parser("watch", help="poll for changes and rebuild automatically")
    watchParser.add_argument("interval", type=int, metavar="TIME", help="polling interval in seconds")
    watchParser.add_argument("-a", "--args", dest="buildArgs", default="", metavar="ARGS", help="arguments to pass to elyb build")
    statsParser = subparsers.add_parser("stats", help="project statistics")
    statsSubparsers = statsParser.add_subparsers(dest="statsCommand")
    statsSubparsers.add_parser("builds", help="show build counts")
    linesParser = statsSubparsers.add_parser("lines", help="count lines of code")
    linesParser.add_argument("-a", "--all", action="store_true", dest="allMode", help="count all non-binary files in plugin root")
    linesParser.add_argument("-add", "--additional", nargs="+", dest="additionalDirs", metavar="DIR", default=[], help="additional directories to include (relative to cwd, only with --all)")
    sizeParser = statsSubparsers.add_parser("size", help="count file sizes")
    sizeParser.add_argument("-a", "--all", action="store_true", dest="allMode", help="count all non-binary files in plugin root")
    sizeParser.add_argument("-add", "--additional", nargs="+", dest="additionalDirs", metavar="DIR", default=[], help="additional directories to include (relative to cwd, only with --all)")
    filesParser = statsSubparsers.add_parser("files", help="count files by extension")
    filesParser.add_argument("-a", "--all", action="store_true", dest="allMode", help="include refmap.yml and additional directories")
    filesParser.add_argument("-add", "--additional", nargs="+", dest="additionalDirs", metavar="DIR", default=[], help="additional directories to include (relative to cwd, only with --all)")
    scriptParser = subparsers.add_parser("script", help="run .edsl script")
    scriptParser.add_argument("name", help="script name (without .edsl)")
    scriptParser.add_argument("args", nargs="*", help="arguments passed to script")
    addIgnoreParser = subparsers.add_parser("add-ignore", help="add path to an ignore list in config.yml")
    addIgnoreParser.add_argument("path", help="path to add (Unix-style)")
    addIgnoreGroup = addIgnoreParser.add_mutually_exclusive_group(required=True)
    addIgnoreGroup.add_argument("-a", "--all", action="store_const", const="all", dest="target", help="add to ignoreAll (excluded from every build)")
    addIgnoreGroup.add_argument("-na", "--no-assets", action="store_const", const="no_assets", dest="target", help="add to optionalAssets (excluded with --no-assets)")
    addIgnoreGroup.add_argument("-c", "--compile", action="store_const", const="compile", dest="target", help="add to compilationIgnore (excluded from compilation)")
    delIgnoreParser = subparsers.add_parser("del-ignore", help="remove path from an ignore list by index")
    delIgnoreParser.add_argument("index", help="index to remove")
    delIgnoreGroup = delIgnoreParser.add_mutually_exclusive_group(required=True)
    delIgnoreGroup.add_argument("-a", "--all", action="store_const", const="all", dest="target", help="remove from ignoreAll")
    delIgnoreGroup.add_argument("-na", "--no-assets", action="store_const", const="no_assets", dest="target", help="remove from optionalAssets")
    delIgnoreGroup.add_argument("-c", "--compile", action="store_const", const="compile", dest="target", help="remove from compilationIgnore")
    return parser

def main():
    parser = buildParser()
    args = parser.parse_args()
    if args.version:
        runVersion()
        return
    if args.command == "new":
        if args.gen:
            if not args.pluginname or not args.author:
                print("error: pluginname and author are required with --gen")
                sys.exit(1)
            runNew(args.pluginname, args.author, args.zipformat)
        else:
            runInteractive()
        return
    if args.command == "build":
        encryptMethod, encryptPassword = (args.encrypt[0], args.encrypt[1]) if args.encrypt else (None, None)
        if args.staticVersion is not None:
            if len(args.staticVersion) > 2:
                print("error: --static-version accepts at most 2 arguments: VERSION and optional APPEND")
                sys.exit(1)
            staticVersion = args.staticVersion[0]
            staticVersionInName = args.staticVersion[1].lower() == "true" if len(args.staticVersion) == 2 else False
        else:
            staticVersion = None
            staticVersionInName = False
        if args.staticClient is not None:
            if len(args.staticClient) > 2:
                print("error: --static-client accepts at most 2 arguments: PACKAGE and optional NAME")
                sys.exit(1)
            staticClientPackage = args.staticClient[0]
            staticClientName = args.staticClient[1] if len(args.staticClient) == 2 else None
        else:
            staticClientPackage = None
            staticClientName = None
        runBuild(args.noAssets, args.noFolder, args.verbose, args.checkAst, args.compile, args.reset, encryptMethod, encryptPassword, args.noInfo, staticVersion, staticVersionInName, staticClientPackage, staticClientName, args.obfuscation)
        return
    if args.command == "cached":
        runCached()
        return
    if args.command == "watch":
        try:
            buildArgs = shlex.split(args.buildArgs) if args.buildArgs.strip() else []
        except ValueError as e:
            print(f"error: invalid build args: {e}")
            sys.exit(1)
        runWatch(args.interval, buildArgs)
        return
    if args.command == "stats":
        if args.statsCommand in ("builds", "lines", "size", "files"):
            import os
            import yaml
            cwd = os.getcwd()
            refmapPath = os.path.join(cwd, "refmap.yml")
            if not os.path.exists(refmapPath):
                print("error: refmap.yml not found in current directory")
                sys.exit(1)
            with open(refmapPath, "r", encoding="utf-8") as f:
                refmap = yaml.safe_load(f)
            builderRelPath = refmap.get("elyxbuilder")
            if not builderRelPath:
                print("error: refmap.yml missing key: elyxbuilder")
                sys.exit(1)
            builderDir = os.path.join(cwd, builderRelPath)
            if args.statsCommand == "builds":
                runStatBuilds(builderDir)
            elif args.statsCommand == "files":
                metaRelPath = refmap.get("metainfo")
                if not metaRelPath:
                    print("error: refmap.yml missing key: metainfo")
                    sys.exit(1)
                metaPath = os.path.join(cwd, metaRelPath)
                if not os.path.exists(metaPath):
                    print(f"error: meta.yml not found: {metaPath}")
                    sys.exit(1)
                with open(metaPath, "r", encoding="utf-8") as f:
                    meta = yaml.safe_load(f)
                pluginName = meta.get("name", "unknown")
                pluginDir = os.path.dirname(builderDir)
                runStatFiles(pluginDir, pluginName, cwd, refmapPath, args.allMode, args.additionalDirs, builderDir)
            else:
                metaRelPath = refmap.get("metainfo")
                if not metaRelPath:
                    print("error: refmap.yml missing key: metainfo")
                    sys.exit(1)
                metaPath = os.path.join(cwd, metaRelPath)
                if not os.path.exists(metaPath):
                    print(f"error: meta.yml not found: {metaPath}")
                    sys.exit(1)
                with open(metaPath, "r", encoding="utf-8") as f:
                    meta = yaml.safe_load(f)
                pluginName = meta.get("name", "unknown")
                pluginDir = os.path.dirname(builderDir)
                configPath = os.path.join(builderDir, "config.yml")
                if not os.path.exists(configPath):
                    print(f"error: config.yml not found in {builderDir}")
                    sys.exit(1)
                with open(configPath, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                sourceRelPath = config.get("source")
                if not sourceRelPath:
                    print("error: config.yml missing key: source")
                    sys.exit(1)
                if args.statsCommand == "lines":
                    runStatLines(
                        pluginDir, sourceRelPath, pluginName, cwd, refmapPath,
                        args.allMode, args.additionalDirs, builderDir,
                    )
                else:
                    runStatSize(
                        pluginDir, sourceRelPath, pluginName, cwd, refmapPath,
                        args.allMode, args.additionalDirs, builderDir,
                    )
        else:
            parser.parse_args(["stats", "--help"])
        return
    if args.command == "script":
        runScript(args.name, args.args)
        return
    if args.command == "add-ignore":
        runAddIgnore(args.path, args.target)
        return
    if args.command == "del-ignore":
        runDelIgnore(args.index, args.target)
        return
    parser.print_help()
    sys.exit(1)
