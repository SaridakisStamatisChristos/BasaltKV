from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from . import Database, __version__, verify_database


def _decode(text: str, mode: str) -> bytes:
    if mode == "text":
        return text.encode("utf-8")
    if mode == "hex":
        return bytes.fromhex(text)
    if mode == "base64":
        return base64.b64decode(text, validate=True)
    raise ValueError(mode)


def _encode(data: bytes, mode: str) -> str:
    if mode == "text":
        return data.decode("utf-8")
    if mode == "hex":
        return data.hex()
    if mode == "base64":
        return base64.b64encode(data).decode("ascii")
    raise ValueError(mode)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="basaltkv", description="Crash-consistent embedded transactional key-value store")
    p.add_argument("--version", action="version", version=f"basaltkv {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize a database")
    init.add_argument("path")

    info = sub.add_parser("info", help="show database statistics")
    info.add_argument("path")

    for name in ("get", "delete"):
        sp = sub.add_parser(name)
        sp.add_argument("path")
        sp.add_argument("key")
        sp.add_argument("--key-encoding", choices=("text", "hex", "base64"), default="text")
        if name == "get":
            sp.add_argument("--output", choices=("text", "hex", "base64"), default="hex")

    put = sub.add_parser("put")
    put.add_argument("path")
    put.add_argument("key")
    put.add_argument("value")
    put.add_argument("--key-encoding", choices=("text", "hex", "base64"), default="text")
    put.add_argument("--value-encoding", choices=("text", "hex", "base64"), default="text")

    scan = sub.add_parser("scan")
    scan.add_argument("path")
    scan.add_argument("--prefix")
    scan.add_argument("--prefix-encoding", choices=("text", "hex", "base64"), default="text")
    scan.add_argument("--output", choices=("text", "hex", "base64"), default="hex")

    verify = sub.add_parser("verify")
    verify.add_argument("path")

    compact = sub.add_parser("compact")
    compact.add_argument("path")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            with Database.open(args.path):
                pass
            print(f"initialized {args.path}")
            return 0
        if args.command == "verify":
            report = verify_database(args.path)
            print(json.dumps(report.__dict__, indent=2))
            return 0 if report.ok else 2
        if args.command == "info":
            with Database.open(args.path, create=False, read_only=True) as db:
                print(json.dumps(db.stats(), indent=2))
            return 0
        if args.command == "compact":
            with Database.open(args.path, create=False) as db:
                count = db.compact()
                print(json.dumps({"compaction_count": count}))
            return 0
        if args.command == "get":
            key = _decode(args.key, args.key_encoding)
            with Database.open(args.path, create=False, read_only=True) as db:
                value = db.get(key)
            if value is None:
                return 1
            print(_encode(value, args.output))
            return 0
        if args.command == "put":
            key = _decode(args.key, args.key_encoding)
            value = _decode(args.value, args.value_encoding)
            with Database.open(args.path, create=False) as db:
                seq = db.put(key, value)
            print(json.dumps({"sequence": seq}))
            return 0
        if args.command == "delete":
            key = _decode(args.key, args.key_encoding)
            with Database.open(args.path, create=False) as db:
                seq = db.delete(key)
            print(json.dumps({"sequence": seq}))
            return 0
        if args.command == "scan":
            prefix = None if args.prefix is None else _decode(args.prefix, args.prefix_encoding)
            with Database.open(args.path, create=False, read_only=True) as db:
                for key, value in db.scan(prefix):
                    print(f"{_encode(key, args.output)}\t{_encode(value, args.output)}")
            return 0
        raise AssertionError(args.command)
    except Exception as exc:
        print(f"basaltkv: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
