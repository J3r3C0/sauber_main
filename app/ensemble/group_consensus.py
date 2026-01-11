
def consensus_check(gpt_decision: str, prophet_entry: float, threshold: float = 0.002):
    try:
        # Extrahiere Entry aus GPT-Text (vereinfachter Parser)
        entry_line = [line for line in gpt_decision.splitlines() if "entry" in line.lower()]
        if entry_line:
            gpt_value = float(''.join([c for c in entry_line[0] if c.isdigit() or c == '.' or c == ',']).replace(",", "."))
            diff = abs(gpt_value - prophet_entry)
            if diff <= threshold:
                return True, diff
            else:
                return False, diff
        return False, None
    except:
        return False, None
