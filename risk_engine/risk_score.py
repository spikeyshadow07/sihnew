"""Transparent ranking heuristic; this score is not a crash probability."""
def calculate_near_miss_risk_score(min_ttc, pet, max_drac, delta_v_kmh, min_distance_m, participant_classes):
    ttc = 0 if min_ttc is None else 50*max(0, 1-min_ttc/3.5)
    braking = 0 if max_drac is None else min(20, max_drac/6.5*20)
    speed = min(15, max(0, delta_v_kmh or 0)/60*15)
    proximity = 0 if min_distance_m is None else min(15, max(0, 5-min_distance_m)*3)
    multiplier = 1.1 if any(c in ("pedestrian", "bicycle", "cyclist") for c in participant_classes) else 1.
    score = round(min(100, (ttc+braking+speed+proximity)*multiplier), 1)
    level = "critical" if score >= 85 else "high" if score >= 65 else "medium" if score >= 40 else "low"
    return {"risk_score": score, "risk_level": level,
            "breakdown": {"ttc": ttc, "braking": braking, "relative_speed": speed, "proximity": proximity}}
