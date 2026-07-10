"""
Test Parser Registry.

Run:

python -m scripts.test_registry
"""

from pathlib import Path

from src.parsers.registry import ParserRegistry


def main():

    registry = ParserRegistry()

    print("=" * 70)
    print("PARSER REGISTRY TEST")
    print("=" * 70)

    print("\nRegistered Parsers")

    for parser in registry.available_parsers():

        print(parser)

    print("\nSupported Extensions")

    for ext in registry.supported_extensions:

        print(ext)

    files = [

        Path("employee.pdf"),

        Path("guide.md"),

        Path("leave_policy.xlsx"),

        Path("engineering.json"),

    ]

    print("\nParser Lookup")

    for file in files:

        parser = registry.get_parser(file)

        print(

            f"{file.name:25}",

            "->",

            parser.__class__.__name__,

        )


if __name__ == "__main__":
    main()