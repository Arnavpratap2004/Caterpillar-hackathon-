"""Deterministic safety hazard onset/resolution rules for telemetry playback."""


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
    previous_distance = float(previous_event.get('proximity_distance_m', 99) or 99)
    if distance < 8 and previous_distance >= 8:
        alerts.append({'type': 'PROXIMITY', 'severity': 'HIGH', 'status': 'OPEN', 'acknowledged': False, 'resolution': 'Person entered the proximity zone.'})
    elif distance < 8 and distance <= previous_distance:
        alerts.append({'type': 'PROXIMITY', 'severity': 'CRITICAL', 'status': 'ESCALATED', 'acknowledged': False, 'resolution': 'Hazard persists while separation is not recovering.'})
    elif distance >= 8 and previous_distance < 8:
        alerts.append({'type': 'PROXIMITY', 'severity': 'LOW', 'status': 'RESOLVED', 'acknowledged': True, 'resolution': 'Operator response increased separation.'})

    tilt = float(current_event.get('tilt_deg', 0) or 0)
    previous_tilt = float(previous_event.get('tilt_deg', 0) or 0)
    if tilt >= 6 and previous_tilt < 6:
        alerts.append({'type': 'TILT', 'severity': 'HIGH', 'status': 'OPEN', 'acknowledged': False, 'resolution': 'Stabilize the machine on level ground.'})
    elif tilt < 4 and previous_tilt >= 6:
        alerts.append({'type': 'TILT', 'severity': 'LOW', 'status': 'RESOLVED', 'acknowledged': True, 'resolution': 'Machine attitude returned to a safe range.'})

    visibility = str(current_event.get('visibility', 'Good')).lower()
    previous_visibility = str(previous_event.get('visibility', 'Good')).lower()
    poor = {'poor', 'reduced', 'low', 'fog', 'night'}
    if visibility in poor and previous_visibility not in poor:
        alerts.append({'type': 'WEATHER', 'severity': 'MEDIUM', 'status': 'OPEN', 'acknowledged': False, 'resolution': 'Reduce speed and confirm visibility before continuing.'})
    elif visibility not in poor and previous_visibility in poor:
        alerts.append({'type': 'WEATHER', 'severity': 'LOW', 'status': 'RESOLVED', 'acknowledged': True, 'resolution': 'Visibility returned to normal.'})
    return alerts
