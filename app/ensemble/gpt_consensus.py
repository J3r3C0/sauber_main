
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gpt_consensus_evaluator(symbol: str, prophet: dict, xgb_signal: str, lgbm_entry: float, lgbm_sl: float, lgbm_tp: float):
    prompt = f"""
Symbol: {symbol}

📈 Prophet Prognose:
- Trend: {prophet.get("trend")}
- Entry: {prophet.get("entry")}
- SL: {prophet.get("sl")}
- TP: {prophet.get("tp")}

🤖 XGBoost-Signal: {xgb_signal}

📊 LightGBM Prognose:
- Entry: {lgbm_entry}
- SL: {lgbm_sl}
- TP: {lgbm_tp}

Bitte bewerte diese drei unabhängigen Analysen:
1. Stimmen sie im Trend überein?
2. Gibt es widersprüchliche Werte?
3. Wie hoch ist die Wahrscheinlichkeit, dass ein Trade erfolgreich ist?
4. Soll eine Order ausgelöst werden?
Bitte antworte in strukturierter Form mit kurzer Begründung.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Du bist ein objektiver Entscheidungsanalyst, der drei Analysen logisch abgleicht."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()
