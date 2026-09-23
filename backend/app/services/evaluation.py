"""Pure three-layer evaluation helpers. The API composes these with domain data."""

def adjust_benchmark_for_context(benchmark, environment=None, machine_state=None):
    """Apply explainable, task-agnostic context factors without using reflection text."""
    environment = environment or {}
    machine_state = machine_state or {}
    factor = 0.0
    contributors = []
    temperature = float(environment.get('ambient_temp_c', environment.get('temperature', 30)) or 30)
    if temperature >= 34:
        factor += 0.05
        contributors.append('high temperature')
    elif temperature >= 30:
        factor += 0.02
    humidity = float(environment.get('humidity_pct', environment.get('humidity', 0)) or 0)
    if humidity >= 80:
        factor += 0.02
        contributors.append('high humidity')
    ground = f"{environment.get('ground_condition', '')} {environment.get('soil_type', '')}".lower()
    if 'hard' in ground or 'rock' in ground:
        factor += 0.08
        contributors.append('challenging ground')
    elif 'wet' in ground or 'mud' in ground:
        factor += 0.04
        contributors.append('challenging ground')
    load = float(environment.get('payload_pct', environment.get('hydraulic_load_pct', environment.get('load_pct', 0))) or 0)
    if load >= 65:
        factor += 0.035
        contributors.append('high workload')
    visibility = str(environment.get('visibility', 'good')).lower()
    if visibility in ('poor', 'reduced', 'low', 'fog', 'night'):
        factor += 0.06
        contributors.append('reduced visibility')
    if str(machine_state.get('status', 'operational')).lower() not in ('operational', 'normal', ''):
        factor += 0.08
        contributors.append('machine condition')
    factor = min(0.25, round(factor, 3))
    minimum = float(benchmark.get('expected_duration_min', benchmark.get('min', 0)))
    maximum = float(benchmark.get('expected_duration_max', benchmark.get('max', 0)))
    return {'adjusted_min': round(minimum * (1 + factor), 1), 'adjusted_max': round(maximum * (1 + factor), 1), 'context_factor': factor, 'contributing_factors': contributors or ['normal conditions']}

def calibration_signal(objective, confidence):
    objective=float(objective); confidence=float(confidence); signed=round(confidence-objective,1); gap=round(abs(signed),1)
    if signed>=20:
        return {'code':'OVERCONFIDENCE_RISK','label':'Overconfidence risk','message':f'You rated this task {confidence:.0f}/100, while objective evidence scored {objective:.0f}/100.','confidence':confidence,'objective':objective,'gap':gap}
    if signed<=-20:
        return {'code':'UNDERCONFIDENCE','label':'Underconfidence','message':f'You rated this task {confidence:.0f}/100, while objective evidence scored {objective:.0f}/100.','confidence':confidence,'objective':objective,'gap':gap}
    return {'code':'CALIBRATED','label':'Calibrated self-assessment','message':f'Your self-rating ({confidence:.0f}/100) is aligned with objective evidence ({objective:.0f}/100).','confidence':confidence,'objective':objective,'gap':gap}

def calculate_benchmark_deviation(current_hours, adjusted_min, adjusted_max):
    midpoint=(float(adjusted_min)+float(adjusted_max))/2
    return round((float(current_hours)-midpoint)/midpoint*100,1) if midpoint else 0.0

def calculate_personal_deviation(current_hours, personal_hours):
    return round((float(current_hours)-float(personal_hours))/float(personal_hours)*100,1) if personal_hours else 0.0

def classify_duration(current_hours, adjusted_min, adjusted_max):
    current=float(current_hours); upper=float(adjusted_max)
    if float(adjusted_min)<=current<=upper:return 'WITHIN_EXPECTATION'
    if current<=upper*1.05:return 'SLIGHTLY_ABOVE_EXPECTATION'
    if current<=upper*1.4:return 'SIGNIFICANTLY_ABOVE_EXPECTATION'
    return 'SEVERE_DEVIATION'
