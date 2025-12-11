from ..core.state import State


def _get_full_text(state: State) -> str:
    pages = state.get("pages", [])
    return "\n\n".join(pages)


def _get_first_pages(state: State, n: int = 3) -> str:
    pages = state.get("pages", [])
    return "\n\n".join(pages[:n])

