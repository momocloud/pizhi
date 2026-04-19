from __future__ import annotations

import argparse
from collections.abc import Sequence

from pizhi import __version__
from pizhi.commands.brainstorm_cmd import run_brainstorm
from pizhi.commands.compile_cmd import run_compile
from pizhi.commands.continue_cmd import run_continue
from pizhi.commands.init_cmd import run_init
from pizhi.commands.outline_cmd import run_outline_expand
from pizhi.commands.provider_cmd import run_provider_configure
from pizhi.commands.review_cmd import run_review
from pizhi.commands.status_cmd import run_status
from pizhi.commands.write_cmd import run_write


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pizhi")
    parser.add_argument("--version", action="store_true", help="show the CLI version")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="initialize a Pizhi project")
    init_parser.add_argument("--project-name", required=True, help="novel title")
    init_parser.add_argument("--genre", default="", help="genre or style")
    init_parser.add_argument("--total-chapters", type=int, default=0, help="planned chapter count")
    init_parser.add_argument("--per-volume", type=int, default=20, help="chapters per volume")
    init_parser.add_argument("--pov", default="", help="point of view and narrative style")
    init_parser.set_defaults(handler=run_init)

    brainstorm_parser = subparsers.add_parser("brainstorm", help="prepare or apply brainstorm packets")
    brainstorm_parser.add_argument("--response-file", help="structured brainstorm response file")
    brainstorm_parser.add_argument("--execute", action="store_true", help="call the configured provider")
    brainstorm_parser.set_defaults(handler=run_brainstorm)

    outline_parser = subparsers.add_parser("outline", help="prepare or apply outline expansion packets")
    outline_subparsers = outline_parser.add_subparsers(dest="outline_command")

    outline_expand_parser = outline_subparsers.add_parser("expand", help="expand chapter outlines")
    outline_expand_parser.add_argument("--chapters", required=True, help="chapter range such as 1-3")
    outline_expand_parser.add_argument("--direction", help="extra steering note")
    outline_expand_parser.add_argument("--response-file", help="structured outline response file")
    outline_expand_parser.add_argument("--execute", action="store_true", help="call the configured provider")
    outline_expand_parser.set_defaults(handler=run_outline_expand)

    provider_parser = subparsers.add_parser("provider", help="configure provider settings")
    provider_subparsers = provider_parser.add_subparsers(dest="provider_command")

    provider_configure_parser = provider_subparsers.add_parser("configure", help="create or update provider config")
    provider_configure_parser.add_argument("--provider", required=True, help="provider identifier")
    provider_configure_parser.add_argument("--model", required=True, help="provider model name")
    provider_configure_parser.add_argument("--base-url", required=True, help="provider base URL")
    provider_configure_parser.add_argument("--api-key-env", required=True, help="environment variable name for the API key")
    provider_configure_parser.set_defaults(handler=run_provider_configure)

    compile_parser = subparsers.add_parser("compile", help="compile drafted chapters into manuscript volumes")
    compile_parser.set_defaults(handler=run_compile)

    continue_parser = subparsers.add_parser("continue", help="continue outlining and writing chapters")
    continue_parser.add_argument("--count", required=True, type=int, help="number of chapters to continue")
    continue_parser.add_argument("--direction", help="extra steering note")
    continue_parser.add_argument("--outline-response-file", help="outline response file")
    continue_parser.add_argument("--chapter-responses-dir", help="directory containing chapter response files")
    continue_parser.set_defaults(handler=run_continue)

    review_parser = subparsers.add_parser("review", help="run structural consistency review")
    review_parser.add_argument("--chapter", type=int, help="review a single chapter number")
    review_parser.add_argument("--full", action="store_true", help="review all known chapters")
    review_parser.set_defaults(handler=run_review)

    status_parser = subparsers.add_parser("status", help="show project status")
    status_parser.set_defaults(handler=run_status)

    write_parser = subparsers.add_parser("write", help="prepare or apply chapter writing packets")
    write_parser.add_argument("--chapter", required=True, type=int, help="chapter number")
    write_parser.add_argument("--response-file", help="chapter response file")
    write_parser.add_argument("--execute", action="store_true", help="call the configured provider")
    write_parser.set_defaults(handler=run_write)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))
