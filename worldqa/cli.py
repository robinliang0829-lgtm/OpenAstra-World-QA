"""Portable command-line interface. Inputs are never modified."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from . import __version__
from .report import render_html, render_markdown


def _pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def _read_json(path):
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8-sig"),
                       object_pairs_hook=_pairs_without_duplicates,
                       parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: JSON root must be an object")
    return raw, value


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def write_bundle(output, report, manifest_bytes, config_bytes=None):
    """Create a new directory exclusively; never reuse an evidence directory."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError(f"Output already exists; choose a new directory: {output}")
    files = {
        "report.json": _json_bytes(report),
        "report.md": render_markdown(report).encode("utf-8"),
        "report.html": render_html(report).encode("utf-8"),
        "manifest.input.json": manifest_bytes,
        "config.effective.json": _json_bytes(report["config"]),
    }
    if config_bytes is not None:
        files["config.input.json"] = config_bytes
    # mkdir without exist_ok rejects a concurrently created directory/symlink.
    output.mkdir(parents=True, exist_ok=False)
    written = []
    try:
        for filename, data in files.items():
            target = output / filename
            with target.open("xb") as stream:
                stream.write(data)
            written.append(target)
    except OSError:
        # Remove only this call's own writes; don't recursively remove anything.
        for target in written:
            target.unlink(missing_ok=True)
        try:
            output.rmdir()
        except OSError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="worldqa", description="OpenAstra 世界质检：只读检查与可复现证据包")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    inspect = subcommands.add_parser("inspect", help="Inspect one scene manifest")
    inspect.add_argument("scene", type=Path)
    inspect.add_argument("--config", type=Path)
    inspect.add_argument("--output", type=Path, required=True,
                         help="New directory; existing directories are refused")
    args = parser.parse_args(argv)
    try:
        manifest_bytes, scene = _read_json(args.scene)
        config_bytes, config = (None, None)
        if args.config is not None:
            config_bytes, config = _read_json(args.config)
        from .engine import inspect_scene
        report = inspect_scene(scene, config)
        report["provenance"] = {
            "tool": "OpenAstra-World-QA",
            "tool_version": __version__,
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "config_input_sha256": (hashlib.sha256(config_bytes).hexdigest()
                                    if config_bytes is not None else None),
            "effective_config_sha256": hashlib.sha256(
                _json_bytes(report["config"])).hexdigest(),
        }
        report["limitations"] = [
            "PASS applies only to declared checks and supplied evidence; it is not release approval.",
            "Synthetic fixtures do not establish real-island quality.",
            "Engine-exported geometry does not establish camera, GPU or gameplay acceptance.",
            "Route traces establish ordered sample coverage only, not collision clearance or physical traversability.",
            "Default thresholds are demonstration values pending island-owner calibration.",
        ]
        status = report["summary"]["status"]
        codes = {"pass": 0, "fail": 1, "blocked": 3}
        if status not in codes:
            raise ValueError(f"Unexpected engine summary status: {status!r}")
        write_bundle(args.output, report, manifest_bytes, config_bytes)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"worldqa: invalid input/output: {exc}", file=sys.stderr)
        return 2
    print(f"{status.upper()} | scene={report['scene_id']} | "
          f"evidence={report['evidence_kind']} | report={args.output / 'report.html'}")
    return codes[status]
