#!/usr/bin/env python3
"""Collect repository architecture facts for architecture diagram generation.

Cross-platform (Windows / macOS / Linux) using only the Python standard library.
Auto-discovers single-module and multi-module source/config layouts across
Java/Kotlin, Python, TypeScript/JavaScript, and Go, and redacts inline secrets.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Iterable

CODE_EXTENSIONS = {".java", ".kt", ".kts", ".py", ".ts", ".tsx", ".js", ".jsx", ".go"}
CONFIG_EXTENSIONS = {".yml", ".yaml", ".properties", ".toml", ".json", ".ini", ".conf"}
BUILD_FILES = {
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
    "go.mod",
    "Cargo.toml",
}
SKIP_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "out",
    "target",
    "node_modules",
    "vendor",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    ".nuxt",
    "coverage",
}
TEST_DIR_NAMES = {"test", "tests", "__tests__", "testdata", "fixtures"}
TEST_FILE_RE = re.compile(
    r"(?:^test_.*|.*_test\.(?:py|go)|.*\.(?:test|spec)\.[jt]sx?|.*Test(?:s)?\.(?:java|kt))$",
    re.IGNORECASE,
)
SENSITIVE_FILE_RE = re.compile(
    r"(?:^\.env(?:\..+)?$|.*(?:secret|credential|keystore|id_rsa|id_ed25519).*|\.(?:pem|key|p12|pfx)$)",
    re.IGNORECASE,
)
ARCH_DIR_KEYWORDS = {
    "interfaces",
    "application",
    "domain",
    "infrastructure",
    "controller",
    "controllers",
    "router",
    "routers",
    "api",
    "service",
    "services",
    "engine",
    "engines",
    "pipeline",
    "pipelines",
    "provider",
    "facade",
    "adapter",
    "adapters",
    "consumer",
    "job",
    "jobs",
    "scheduler",
    "graph",
    "agent",
    "agents",
}

PATTERNS: dict[str, re.Pattern[str]] = {
    "HTTP / RPC Entrypoints": re.compile(
        r"@(?:RestController|RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|"
        r"GrpcService|DubboService)\b|"
        r"class\s+\w*(?:Controller|Resource|Endpoint)\b|"
        r"@(?:app|router|bp)\.(?:get|post|put|delete|patch|websocket|route)\b|"
        r"\b(?:FastAPI|APIRouter)\s*\(|"
        r"@(?:Controller|Get|Post|Put|Delete|Patch)\s*\(|"
        r"\b(?:router|app)\.(?:GET|POST|PUT|DELETE|PATCH|Handle|HandleFunc)\s*\(|"
        r"\bRegister\w+Server\s*\("
    ),
    "MQ / Stream / Async Consumers": re.compile(
        r"@(?:KafkaListener|RabbitListener|RocketMQMessageListener|JmsListener|SqsListener|"
        r"EventPattern|MessagePattern)\b|"
        r"class\s+\w*(?:Consumer|Listener)\b|"
        r"@(?:celery\.task|shared_task)\b|"
        r"\b(?:KafkaConsumer|AIOKafkaConsumer|kafka\.NewReader|sarama\.NewConsumer)\b"
    ),
    "Scheduled Jobs & Workflow Graphs": re.compile(
        r"@(?:XxlJob|Scheduled|SchedulerLock)\b|"
        r"class\s+\w*(?:Job|JobHandler|TaskScheduler)\b|"
        r"\b(?:APScheduler|BackgroundScheduler|AsyncIOScheduler|cron\.New|StateGraph|CompiledGraph)\b"
    ),
    "Core Services / Engines / Pipelines": re.compile(
        r"\b(?:class|interface|type)\s+\w*(?:ApplicationService|DomainService|ServiceImpl|"
        r"Engine|Pipeline|Orchestrator|Processor|UseCase|Planner)\b"
    ),
    "Outbound RPC / HTTP / Model Clients": re.compile(
        r"@FeignClient\b|"
        r"\b(?:OkHttpClient|RestTemplate|WebClient|HttpClient|ManagedChannelBuilder|"
        r"httpx\.(?:Async)?Client|aiohttp\.ClientSession|requests\.(?:Session|get|post)|"
        r"OpenAI|AsyncOpenAI|ChatOpenAI|tritonclient)\b"
    ),
    "Persistence & Cache Adapters": re.compile(
        r"\b(?:MongoTemplate|RedisTemplate|StringRedisTemplate|JdbcTemplate|NamedParameterJdbcTemplate|"
        r"EntityManager|SqlSession|PrismaClient|createEngine|create_engine|AsyncSession|"
        r"motor\.motor_asyncio|pymongo\.MongoClient|redis\.Redis|gorm\.DB)\b|"
        r"\b(?:interface|class)\s+\w*(?:Repository|Mapper|Dao)\b"
    ),
}

CONFIG_KEY_RE = re.compile(
    r"\b(?:url|uri|host|port|topic|queue|bootstrap[-_.]?servers?|redis|mongodb|mysql|postgres|"
    r"kafka|rabbitmq|rocketmq|nacos|consul|etcd|feign|grpc|triton|milvus|elasticsearch|opensearch)\b\s*[:=]",
    re.IGNORECASE,
)
URL_CRED_RE = re.compile(r"(://[^/\s:@]+:)([^@\s]+)(@)")
SECRET_KV_RE = re.compile(
    r"((?:password|passwd|pwd|secret|token|api[-_.]?key|access[-_.]?key|private[-_.]?key|ak|sk)"
    r"\s*[:=]\s*[\"']?)([^\"'\s,#]+)",
    re.IGNORECASE,
)
MAX_FILE_BYTES = 1_000_000


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def redact_line(line: str) -> str:
    line = URL_CRED_RE.sub(r"\1[REDACTED]\3", line)
    line = SECRET_KV_RE.sub(r"\1[REDACTED]", line)
    return line


def iter_files(
    search_root: Path,
    extensions: set[str] | None = None,
    include_tests: bool = False,
) -> Iterable[Path]:
    if not search_root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(search_root):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in SKIP_DIRS
            and not name.startswith(".git")
            and (include_tests or name.lower() not in TEST_DIR_NAMES)
        )
        base = Path(dirpath)
        for filename in sorted(filenames):
            path = base / filename
            if not include_tests and TEST_FILE_RE.match(filename):
                continue
            if extensions is not None and path.suffix.lower() not in extensions:
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, OSError):
            continue
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def print_section(title: str) -> None:
    print()
    print(f"## {title}")


def print_top_level_and_modules(root: Path) -> None:
    print_section("Top-Level Structure")
    interesting = re.compile(
        r"^(?:README|AGENTS|CLAUDE|Makefile|Dockerfile|docker-compose|build|settings|pom|package|pyproject|go\.mod|Cargo)",
        re.IGNORECASE,
    )
    for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name in SKIP_DIRS:
            continue
        if child.is_dir():
            print(f"- {child.name}/")
        elif interesting.search(child.name):
            print(f"- {child.name}")

    print_section("Detected Build Modules")
    modules: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        matched = sorted(f for f in filenames if f in BUILD_FILES)
        if matched:
            rel_dir = rel(Path(dirpath), root)
            modules.append(f"- {rel_dir} ({', '.join(matched)})")
            if len(modules) >= 60:
                modules.append("- ... truncated after 60 modules")
                break
    if modules:
        for item in modules:
            print(item)
    else:
        print("- none found")


def print_arch_directories(root: Path, search_root: Path, include_tests: bool) -> None:
    print_section("Architecture & Package Directories")
    if not search_root.exists():
        print(f"- skipped: {rel(search_root, root)} does not exist")
        return
    matched_dirs: list[str] = []
    for dirpath, dirnames, _ in os.walk(search_root):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in SKIP_DIRS and (include_tests or d.lower() not in TEST_DIR_NAMES)
        )
        current = Path(dirpath)
        if current == root:
            continue
        normalized = rel(current, root)
        parts = [p.lower() for p in normalized.split("/")]
        if parts[-1] in ARCH_DIR_KEYWORDS or (
            len(parts) >= 2 and parts[-2] in {"interfaces", "application", "domain", "infrastructure"}
        ):
            matched_dirs.append(normalized)
            if len(matched_dirs) >= 120:
                break
    if not matched_dirs:
        print("- none found")
        return
    for item in matched_dirs[:120]:
        print(f"- {item}")
    if len(matched_dirs) >= 120:
        print("- ... truncated after 120 directories")


def scan_pattern(
    root: Path,
    search_root: Path,
    title: str,
    pattern: re.Pattern[str],
    include_tests: bool,
    max_items: int,
) -> None:
    print_section(title)
    if not search_root.exists():
        print(f"- skipped: {rel(search_root, root)} does not exist")
        return
    hits = 0
    for path in iter_files(search_root, CODE_EXTENSIONS, include_tests=include_tests):
        text = read_text(path)
        for index, raw_line in enumerate(text.splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith(("//", "#", "/*", "*")):
                continue
            if pattern.search(stripped):
                hits += 1
                if hits <= max_items:
                    snippet = redact_line(stripped)
                    if len(snippet) > 160:
                        snippet = snippet[:157] + "..."
                    print(f"- {rel(path, root)}:{index}: {snippet}")
    if hits == 0:
        print("- none found")
    elif hits > max_items:
        print(f"- ... truncated ({hits - max_items} more matches omitted; pass --max-items to expand)")


def print_config(root: Path, config_root: Path, include_tests: bool, max_items: int) -> None:
    print_section("Config & External Endpoints (Redacted)")
    if not config_root.exists():
        print(f"- skipped: {rel(config_root, root)} does not exist")
        return
    hits = 0
    skipped_sensitive: list[str] = []
    lock_or_meta_files = {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "tsconfig.json",
        "jsconfig.json",
        "openai.yaml",
    }

    for dirpath, dirnames, filenames in os.walk(config_root):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in SKIP_DIRS and (include_tests or d.lower() not in TEST_DIR_NAMES)
        )
        base = Path(dirpath)
        for filename in sorted(filenames):
            path = base / filename
            if SENSITIVE_FILE_RE.match(filename):
                skipped_sensitive.append(rel(path, root))
                continue
            if filename in lock_or_meta_files or path.suffix.lower() not in CONFIG_EXTENSIONS:
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            text = read_text(path)
            for index, raw_line in enumerate(text.splitlines(), start=1):
                stripped = raw_line.strip()
                if not stripped or stripped.startswith(("#", "//", "<!--")):
                    continue
                if CONFIG_KEY_RE.search(stripped):
                    hits += 1
                    if hits <= max_items:
                        safe_line = redact_line(stripped)
                        if len(safe_line) > 160:
                            safe_line = safe_line[:157] + "..."
                        print(f"- {rel(path, root)}:{index}: {safe_line}")

    if hits == 0:
        print("- none found")
    elif hits > max_items:
        print(f"- ... truncated ({hits - max_items} more config lines omitted)")
    if skipped_sensitive:
        preview = ", ".join(skipped_sensitive[:10])
        suffix = "..." if len(skipped_sensitive) > 10 else ""
        print(f"- skipped sensitive files (not read): {preview}{suffix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect architecture facts from a repository.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument(
        "--source-root",
        default=None,
        help="Optional source directory relative to --root. Defaults to scanning the whole repository.",
    )
    parser.add_argument(
        "--java-root",
        default=None,
        help="Legacy alias for --source-root (optional).",
    )
    parser.add_argument(
        "--resources-root",
        default=None,
        help="Optional config/resources directory relative to --root. Defaults to scanning the whole repository.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test directories and test files in pattern scans.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=60,
        help="Maximum matches printed per section (default: 60).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    explicit_src = args.source_root or args.java_root
    source_root = (root / explicit_src).resolve() if explicit_src else root
    config_root = (root / args.resources_root).resolve() if args.resources_root else root

    print("# Architecture Scan Facts")
    print()
    print(f"Generated from: {root}")

    print_top_level_and_modules(root)
    print_arch_directories(root, source_root, include_tests=args.include_tests)
    for title, pattern in PATTERNS.items():
        scan_pattern(
            root,
            source_root,
            title,
            pattern,
            include_tests=args.include_tests,
            max_items=args.max_items,
        )
    print_config(root, config_root, include_tests=args.include_tests, max_items=args.max_items)


if __name__ == "__main__":
    main()
