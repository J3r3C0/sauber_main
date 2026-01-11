
def compute_crv(entry, sl, tp):
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk == 0: return 0
    return round(reward / risk, 2)
