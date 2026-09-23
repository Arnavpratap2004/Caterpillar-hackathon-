"""Pure, reusable scoring primitives shared by both machine domains."""
def calculate_performance(metrics):
    return round(max(0,min(100,float(metrics.get('safety',80))*.2+float(metrics.get('efficiency',70))*.25+float(metrics.get('hazard_response',70))*.2+float(metrics.get('control_precision',75))*.2+float(metrics.get('consistency',75))*.15)),1)
def calculate_deviation(current, baseline):
    return {k:round((float(v)-float(baseline[k]))/float(baseline[k])*100,1) for k,v in current.items() if k in baseline and baseline[k]}
def calculate_calibration_gap(objective, confidence): return round(abs(objective-confidence),1)
def classify_operator_state(performance, confidence):
    if performance>=70 and confidence>=70:return 'CALIBRATED'
    if performance>=70:return 'UNDERCONFIDENT'
    if confidence<70:return 'AWARE_DEVELOPING'
    return 'BLIND_SPOT'
def calculate_proficiency(m):
    score=float(m.get('performance',70))*.3+float(m.get('safety',80))*.2+float(m.get('efficiency',70))*.15+float(m.get('hazard_response',70))*.15+float(m.get('consistency',75))*.1+(100-float(m.get('calibration_gap',20)))*.1
    return round(score,1)
