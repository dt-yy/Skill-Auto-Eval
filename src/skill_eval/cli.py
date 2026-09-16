"""Unified skill evaluation CLI."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class ToolResult:
    name: str
    command: list[str]
    returncode: int
    report: str | None = None
    error: str | None = None


def _run(command: list[str], *, cwd: Path | None = None) -> ToolResult:
    name = Path(command[0]).name
    try:
        proc = subprocess.run(command, cwd=cwd, check=False)
    except OSError as exc:
        return ToolResult(name, command, 127, error=str(exc))
    return ToolResult(name, command, proc.returncode)


def _require_path(value: str, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    return path


def run_evaluation(args: argparse.Namespace) -> int:
    skill = _require_path(args.skill, "skill path")
    results: list[ToolResult] = []
    if args.suite in ("all", "effectiveness"):
        if not args.eval:
            raise ValueError("--eval is required for effectiveness evaluation")
        eval_path = _require_path(args.eval, "eval.yaml")
        command = [args.skill_up, "run", str(eval_path)]
        if args.output:
            command += ["--output-dir", str(Path(args.output).resolve() / "skill-up")]
        results.append(_run(command, cwd=eval_path.parent.parent))
    if args.suite in ("all", "security"):
        command = [args.skillspector, "scan", str(skill), "--format", args.format]
        if args.no_llm:
            command.append("--no-llm")
        if args.fail_on_findings:
            command.append("--fail-on-findings")
        if args.output:
            report = Path(args.output).resolve() / f"security.{args.format}"
            report.parent.mkdir(parents=True, exist_ok=True)
            command += ["--output", str(report)]
        results.append(_run(command, cwd=skill))
    payload = {"skill": str(skill), "results": [asdict(item) for item in results]}
    print(json.dumps(payload, indent=2))
    return 0 if all(item.returncode == 0 for item in results) else 1


def install(args: argparse.Namespace) -> int:
    # Official release installers: skill-up's release script and Skillspector's
    # published PyPI package. No source checkout or editable install is used.
    if args.tool in ("all", "skill-up"):
        script = Path(__file__).resolve().parents[2] / "scripts" / "install_skill_up.ps1"
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Version", args.skill_up_version]
        result = _run(command)
        if result.returncode:
            return result.returncode
    if args.tool in ("all", "skillspector"):
        package = "skillspector" if args.skillspector_version == "latest" else f"skillspector=={args.skillspector_version}"
        command = [sys.executable, "-m", "pip", "install", "--upgrade", package]
        result = _run(command)
        if result.returncode:
            return result.returncode
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="skill-eval")
    sub = root.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run availability/effectiveness and/or security evaluation")
    run.add_argument("--skill", required=True)
    run.add_argument("--eval", help="skill-up eval.yaml for availability/effectiveness")
    run.add_argument("--suite", choices=("all", "effectiveness", "security"), default="all")
    run.add_argument("--skill-up", default=os.environ.get("SKILL_UP_BIN", "skill-up"))
    run.add_argument("--skillspector", default=os.environ.get("SKILLSPECTOR_BIN", "skillspector"))
    run.add_argument("--output")
    run.add_argument("--format", choices=("terminal", "json", "markdown", "sarif"), default="json")
    run.add_argument("--no-llm", action="store_true", default=True)
    run.add_argument("--fail-on-findings", action="store_true", default=True)
    run.set_defaults(func=run_evaluation)
    ins = sub.add_parser("install", help="install or update tools from released packages")
    ins.add_argument("--tool", choices=("all", "skill-up", "skillspector"), default="all")
    ins.add_argument("--skill-up-version", default=os.environ.get("SKILL_UP_VERSION", "latest"))
    ins.add_argument("--skillspector-version", default=os.environ.get("SKILLSPECTOR_VERSION", "latest"))
    ins.set_defaults(func=install)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return parser().parse_args(argv).func(parser().parse_args(argv)) if False else _dispatch(argv)
    except (ValueError, OSError) as exc:
        print(f"skill-eval: error: {exc}", file=sys.stderr)
        return 2


def _dispatch(argv: Sequence[str] | None) -> int:
    args = parser().parse_args(argv)
    if args.command == "install" and args.skillspector_version == "latest":
        args.skillspector_version = "0"
        # pip's --upgrade without a version selects the latest published release.
        args.skillspector_version = "latest"
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())


