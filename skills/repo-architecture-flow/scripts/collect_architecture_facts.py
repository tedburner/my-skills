#!/usr/bin/env python3
"""Collect repository architecture facts for architecture diagram generation.

The script intentionally emits evidence, not a final architecture model.
It is cross-platform and uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Iterable


CODE_EXTENSIONS = {".java", ".kt", ".kts", ".py", ".ts", ".tsx", ".js", ".jsx", ".go"}
CONFIG_EXTENSIONS = {".yml", ".yaml", ".properties", ".toml", ".json", ".xml"}
SKIP_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    ".vscode",
    "build",
    "dist",
    "out",
    "target",
    "node_modules",
    "__pycache__",
}


PATTERNS = {
    "HTTP API Entrypoints": re.compile(
        r"@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)|class\s+\w*Controller\b"
    ),
    "MQ Consumers": re.compile(r"@KafkaListener|class\s+\w*Consumer\b|@RabbitListener|@JmsListener"),
    "Scheduled Jobs": re.compile(r"@XxlJob|class\s+\w*Job\b|@Scheduled\b"),
    "Outbound RPC Clients": re.compile(r"@FeignClient|OkHttpClient|RestTemplate|WebClient|HttpClient"),
    "Persistence Adapters": re.compile(
        r"extends\s+AbstractBaseMapper|MongoTemplate|Repository\b|Mapper\b|JdbcTemplate|EntityManager|RedisTemplate"
    ),
}

CONFIG_PATTERN = re.compile(
    r"\b(url|uri|host|port|topic|bootstrap[-_.]?(server|servers)?|redis|mongodb|mysql|kafka|feign|http)\b\s*[:=]",
    re.IGNORECASE,
)


def iter_files(root: Path, extensions: set[str] | None = None) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        base = Path(dirpath)
        for filename in filenames:
            path = base / filename
            if extensions is None or path.suffix.lower() in extensions:
                yield path


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def print_section(title: str) -> None:
    print()
    print(f"## {title}")


def scan_pattern(root: Path, search_root: Path, title: str, pattern: re.Pattern[str]) -> None:
    print_section(title)
    if not search_root.exists():
        print(f"- skipped: {rel(search_root, root)} does not exist")
        return
    found = False
    for path in iter_files(search_root, CODE_EXTENSIONS):
        text = read_text(path)
        for index, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                print(f"- {rel(path, root)}:{index}: {line.strip()}")
                found = True
    if not found:
        print("- none found")


def print_top_level(root: Path) -> None:
    print_section("Top-Level Files")
    interesting = re.compile(r"^(README|AGENTS|CLAUDE|build|settings|pom|package|gradle)", re.IGNORECASE)
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if child.is_dir() or interesting.search(child.name):
            print(f"- {child.name}")


def print_package_dirs(root: Path, java_root: Path) -> None:
    print_section("Java Package Directories")
    if not java_root.exists():
        print(f"- skipped: {rel(java_root, root)} does not exist")
        return
    count = 0
    for path in sorted(p for p in java_root.rglob("*") if p.is_dir()):
        normalized = rel(path, root)
        if any(part in normalized.split("/") for part in ("interfaces", "application", "domain", "infrastructure")):
            print(f"- {normalized}")
            count += 1
            if count >= 160:
                print("- truncated after 160 directories")
                break


def print_config(root: Path, resources_root: Path) -> None:
    print_section("Config And External Endpoints")
    if not resources_root.exists():
        print(f"- skipped: {rel(resources_root, root)} does not exist")
        return
    found = False
    for path in iter_files(resources_root, CONFIG_EXTENSIONS):
        text = read_text(path)
        for index, line in enumerate(text.splitlines(), start=1):
            if CONFIG_PATTERN.search(line):
                print(f"- {rel(path, root)}:{index}: {line.strip()}")
                found = True
    if not found:
        print("- none found")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect architecture facts from a repository.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--java-root", default="app/src/main/java", help="Java source root relative to --root.")
    parser.add_argument(
        "--resources-root",
        default="app/src/main/resources",
        help="Resource/config root relative to --root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    java_root = (root / args.java_root).resolve()
    resources_root = (root / args.resources_root).resolve()

    print("# Architecture Scan Facts")
    print()
    print(f"Generated from: {root}")

    print_top_level(root)
    print_package_dirs(root, java_root)
    for title, pattern in PATTERNS.items():
        scan_pattern(root, java_root, title, pattern)
    print_config(root, resources_root)


if __name__ == "__main__":
    main()
