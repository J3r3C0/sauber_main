
import os

def log_decision(symbol, decision_text, result):
    log_path = "insight_matrix.json"
    import json
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if symbol not in data:
        data[symbol] = []
    data[symbol].append({
        "decision": decision_text,
        "result": result
    })

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
