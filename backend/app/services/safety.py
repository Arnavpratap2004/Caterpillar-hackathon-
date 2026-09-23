"""Deterministic safety hazard onset/resolution rules for telemetry playback."""

BASE_PROXIMITY_LIMIT_M = 8.0
CONDITION_ADJUSTED_PROXIMITY_LIMIT_M = 10.0
TILT_LIMIT_DEG = 6.0
WET_TILT_LIMIT_DEG = 5.0


def working_condition_limits(event):
    event = event or {}
    weather = str(event.get('weather', 'clear')).lower()
    visibility = str(event.get('visibility', 'good')).lower()
    ground = str(event.get('ground_condition', '')).lower()
    wet = weather in ('rain', 'rainy', 'wet', 'storm') or visibility in ('poor', 'reduced', 'low', 'fog') or any(x in ground for x in ('wet', 'mud'))
    return (CONDITION_ADJUSTED_PROXIMITY_LIMIT_M if wet else BASE_PROXIMITY_LIMIT_M, WET_TILT_LIMIT_DEG if wet else TILT_LIMIT_DEG)


def evaluate_safety(previous_event, current_event):
    previous_event = previous_event or {}
    current_event = current_event or {}
    alerts = []
    moving = str(current_event.get('cycle_phase', '')).upper() not in ('IDLE', 'PARKED', '')

    belt = bool(current_event.get('seatbelt_fastened', True))
    previous_belt = bool(previous_event.get('seatbelt_fastened', True))
    if moving and not belt and previous_belt:
        alerts.append({'type': 'SEATBELT', 'severity': 'HIGH', 'status': 'OPEN', 'acknowledged': False, 'resolution': 'Seatbelt required while the machine is moving.'})

    distance = float(current_event.get('proximity_distance_m', 99) or 99)
    had_previous = bool(previous_event)
    previous_distance = float(previous_event.get('proximity_distance_m', distance) or distance)
    proximity_limit, tilt_limit = working_condition_limits(current_event)
    previous_limit, _ = working_condition_limits(previous_event)
    closing_speed = max(0.0, previous_distance - distance)
    if distance < proximity_limit and (not had_previous or previous_distance >= previous_limit):
        alerts.append({'type': 'PROXIMITY', 'severity': 'HIGH', 'status': 'OPEN', 'acknowledged': False, 'resolution': f'Person entered the {proximity_limit:.0f}m condition-adjusted proximity zone.'})
    elif distance < proximity_limit and distance <= previous_distance:
        alerts.append({'type': 'PROXIMITY', 'severity': 'CRITICAL', 'status': 'ESCALATED', 'acknowledged': False, 'resolution': 'Hazard persists while separation is not recovering.'})
    elif distance >= proximity_limit and previous_distance < previous_limit:
        alerts.append({'type': 'PROXIMITY', 'severity': 'LOW', 'status': 'RESOLVED', 'acknowledged': True, 'resolution': 'Operator response increased separation.'})
    elif distance >= proximity_limit and previous_distance >= previous_limit and closing_speed >= 2:
        alerts.append({'type': 'PROXIMITY_APPROACHING', 'severity': 'MEDIUM', 'status': 'PREDICTED', 'acknowledged': False, 'resolution': 'Person is closing quickly; slow or stop before the proximity limit is crossed.'})

    tilt = float(current_event.get('tilt_deg', 0) or 0)
    previous_tilt = float(previous_event.get('tilt_deg', tilt) or tilt)
    if tilt >= tilt_limit and (not had_previous or previous_tilt < tilt_limit):
        alerts.append({'type': 'TILT', 'severity': 'HIGH', 'status': 'OPEN', 'acknowledged': False, 'resolution': f'Stabilize the machine below {tilt_limit:.0f} degrees under current conditions.'})
    elif tilt < max(3.0, tilt_limit - 2) and previous_tilt >= tilt_limit:
        alerts.append({'type': 'TILT', 'severity': 'LOW', 'status': 'RESOLVED', 'acknowledged': True, 'resolution': 'Machine attitude returned to a safe range.'})

    visibility = str(current_event.get('visibility', 'Good')).lower()
    previous_visibility = str(previous_event.get('visibility', 'Good')).lower()
    poor = {'poor', 'reduced', 'low', 'fog', 'night'}
    if visibility in poor and previous_visibility not in poor:
        alerts.append({'type': 'WEATHER', 'severity': 'MEDIUM', 'status': 'OPEN', 'acknowledged': False, 'resolution': 'Reduce speed and confirm visibility before continuing.'})
    elif visibility not in poor and previous_visibility in poor:
        alerts.append({'type': 'WEATHER', 'severity': 'LOW', 'status': 'RESOLVED', 'acknowledged': True, 'resolution': 'Visibility returned to normal.'})
    return alerts
