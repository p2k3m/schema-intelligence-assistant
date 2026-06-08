"""Local command-line runner for the Schema Intelligence Assistant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.agent import SchemaIntelligenceAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Schema Intelligence Assistant locally.")
    parser.add_argument("--demo", action="store_true", help="Run a sample schema analysis and config generation.")
    parser.add_argument("--question", help="Ask a masking documentation or schema intelligence question.")
    parser.add_argument("--schema", help="Path to schema JSON for analysis/config generation.")
    args = parser.parse_args()

    agent = SchemaIntelligenceAgent()

    if args.demo:
        schema_path = Path("masking-generator/tests/10_column_schema.json")
        schema = json.loads(schema_path.read_text())
        print(agent.chat("Analyse this schema for PII", schema=schema))
        print(agent.chat("Generate a masking configuration for these results", schema=schema))
        return

    schema = json.loads(Path(args.schema).read_text()) if args.schema else None
    question = args.question or "What does DATE_SHIFT do and what parameters does it accept?"
    print(agent.chat(question, schema=schema))


if __name__ == "__main__":
    main()

