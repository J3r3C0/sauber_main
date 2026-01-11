import re
from typing import Dict, Any


SECTION_PATTERN = re.compile(
    r"""(?ms)
    ^A\)\s*(?P<A_title>.+?)$\s*(?P<A_body>.+?)
    ^B\)\s*(?P<B_title>.+?)$\s*(?P<B_body>.+?)
    ^C\)\s*(?P<C_title>.+?)$\s*(?P<C_body>.+?)
    ^D\)\s*(?P<D_title>.+?)$\s*(?P<D_body>.+)$
    """.strip(),
    re.MULTILINE,
)


def parse_selfloop_markdown(text: str) -> Dict[str, str]:
    """Parse eine Self-Loop-Antwort im A/B/C/D-Format.

    Erwartet ein Format der Art:

    A) Standortanalyse
    - ...

    B) Nächster sinnvoller Schritt
    - ...

    C) Umsetzung
    - ...

    D) Vorschlag für nächsten Loop
    - ...

    Falls das Muster nicht vollständig erkannt wird, wird so robust wie möglich
    extrahiert und fehlende Sections als leere Strings zurückgegeben.
    """
    if not text:
        return {"A": "", "B": "", "C": "", "D": ""}

    match = SECTION_PATTERN.search(text)
    if not match:
        # Fallback: naive Splits
        sections = {"A": "", "B": "", "C": "", "D": ""}
        current_key = None
        buffer = []
        for line in text.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("A)"):
                if current_key:
                    sections[current_key] = "\n".join(buffer).strip()
                current_key = "A"
                buffer = []
            elif line_stripped.startswith("B)"):
                if current_key:
                    sections[current_key] = "\n".join(buffer).strip()
                current_key = "B"
                buffer = []
            elif line_stripped.startswith("C)"):
                if current_key:
                    sections[current_key] = "\n".join(buffer).strip()
                current_key = "C"
                buffer = []
            elif line_stripped.startswith("D)"):
                if current_key:
                    sections[current_key] = "\n".join(buffer).strip()
                current_key = "D"
                buffer = []
            else:
                buffer.append(line)

        if current_key:
            sections[current_key] = "\n".join(buffer).strip()

        return sections

    groups = match.groupdict()
    return {
        "A": (groups.get("A_body") or "").strip(),
        "B": (groups.get("B_body") or "").strip(),
        "C": (groups.get("C_body") or "").strip(),
        "D": (groups.get("D_body") or "").strip(),
    }


def build_next_loop_state(prev_state: Dict[str, Any], parsed: Dict[str, str]) -> Dict[str, Any]:
    """Baue den nächsten Loop-State aus dem vorherigen State und der aktuellen Antwort.

    - iteration: +1
    - history_summary: wird um eine knappe Notiz aus A/C erweitert
    - open_questions: heuristisch aus D extrahiert (Bullet-Points oder Fragenzeichen-Zeilen)
    - constraints: werden unverändert übernommen
    """
    prev_state = prev_state or {}
    parsed = parsed or {}

    prev_iteration = int(prev_state.get("iteration", 1))
    prev_history = prev_state.get("history_summary", "") or ""
    constraints = prev_state.get("constraints", []) or []

    # History erweitern (sehr kompakt halten)
    snippet = parsed.get("C") or parsed.get("B") or ""
    snippet = snippet.strip().replace("\n", " ")
    if len(snippet) > 280:
        snippet = snippet[:277] + "..."

    new_history_entry = f"[Iter {prev_iteration}] {snippet}" if snippet else f"[Iter {prev_iteration}] (kein Fortschrittstext gefunden)"

    if prev_history:
        history_summary = prev_history + "\n" + new_history_entry
    else:
        history_summary = new_history_entry

    # Offene Fragen aus D heuristisch extrahieren
    open_questions: list[str] = []
    section_d = parsed.get("D", "")
    for line in section_d.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith("-"):
            open_questions.append(line_stripped.lstrip("- ").strip())
        elif "?" in line_stripped:
            open_questions.append(line_stripped.strip())

    next_state: Dict[str, Any] = {
        "iteration": prev_iteration + 1,
        "history_summary": history_summary,
        "constraints": constraints,
        "open_questions": open_questions,
    }
    return next_state
