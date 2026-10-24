import re


_LATIN_RUN = re.compile(
    r"[.,،(\[{'\"]*[A-Za-z0-9][A-Za-z0-9 \t+&.,()\[\]{}'/-]*"
)
_FIRST_STRONG_ISOLATE = "\u2068"
_POP_DIRECTIONAL_ISOLATE = "\u2069"


def isolate_latin_runs(text: str) -> str:
    def isolate(match: re.Match[str]) -> str:
        run = match.group()
        content = run.rstrip(" \t")
        trailing_space = run[len(content) :]
        return (
            f"{_FIRST_STRONG_ISOLATE}{content}"
            f"{_POP_DIRECTIONAL_ISOLATE}{trailing_space}"
        )

    return _LATIN_RUN.sub(isolate, text)
