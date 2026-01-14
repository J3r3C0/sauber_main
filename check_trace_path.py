from pathlib import Path
import os

print(f"CWD: {os.getcwd()}")
print(f"Trace file (abs): {Path('logs/decision_trace.jsonl').absolute()}")
