import sys

from research_paper_review_agent import run_cli, run_gui


def main(argv=None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if "--cli" in args:
        filtered = [arg for arg in args if arg != "--cli"]
        run_cli(filtered)
    else:
        filtered = [arg for arg in args if arg != "--gui"]
        run_gui(filtered)


if __name__ == "__main__":
    main()
