import argparse
import logging
import os
from pathlib import Path

from outreach.export import export_workbook
from outreach.personalize import personalize_file


def main() -> None:
    parser = argparse.ArgumentParser(prog="outreach")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("personalize", help="добавить персонализацию к CSV с компаниями")
    run.add_argument("source", type=Path, help="CSV с колонками company, website, email")
    run.add_argument("-o", "--output", type=Path, required=True)
    run.add_argument("--workers", type=int, default=int(os.getenv("WORKERS", "4")))
    run.add_argument("--limit", type=int, help="обработать только первые N строк")

    export = commands.add_parser("export", help="собрать xlsx для импорта в Google Таблицы")
    export.add_argument("-o", "--output", type=Path, default=Path("deliverables.xlsx"))
    export.add_argument("--base", type=Path, default=Path("data/base_personalized.csv"))
    export.add_argument("--sequence", type=Path, default=Path("data/sequence.csv"))
    export.add_argument("--polza", type=Path, default=Path("data/polza_personalized.csv"))

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.command == "personalize":
        personalize_file(args.source, args.output, workers=args.workers, limit=args.limit)
    else:
        export_workbook(
            {
                "База": args.base,
                "Цепочка писем": args.sequence,
                "Задача 4": args.polza,
            },
            args.output,
        )
