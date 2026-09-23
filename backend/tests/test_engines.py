import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from app.main import compare_to_baseline, calculate_calibration_gap, classify_operator_state, calibration_signal, predict_task_time, calculate_proficiency, adjust_benchmark_for_context, evaluate_task_performance, evaluate_safety, working_condition_limits, live_operator_guidance, calculate_benchmark_deviation, calculate_personal_deviation, recommendation

def test_deviation():
    x=compare_to_baseline({'hazard_response':2.92},{'hazard_response':2.0})
    assert x['deviation_percent']['hazard_response']==46.0

def test_blind_spot():
    assert calculate_calibration_gap(58,87)==29
    assert classify_operator_state(58,87)=='BLIND_SPOT'

def test_prediction():
    assert predict_task_time(40,1.08,1.06,1)['predicted_time']==45.8

def test_proficiency():
    assert calculate_proficiency({'performance':78,'safety':85,'efficiency':68,'hazard_response':70,'calibration_gap':29})['level'] in ('Developing','Proficient')

def test_three_layer_evaluation_and_context():
    benchmark={'expected_duration_min':6,'expected_duration_max':8,'expected_cycle_time_min_sec':135,'expected_cycle_time_max_sec':160,'minimum_safety_score':95,'minimum_efficiency_score':80,'maximum_hazard_response_sec':2.5}
    baseline={'average_task_time_hours':7.2,'average_cycle_time_sec':140,'average_hazard_response_sec':2.0,'average_efficiency':88,'average_safety':94,'average_control_precision':87,'consistency_score':92}
    context={'environment':{'ambient_temp_c':34,'soil_type':'Medium (Sandy)','payload_pct':68},'machine_state':{'status':'Operational'}}
    evaluation=evaluate_task_performance({}, {'task_time_hours':10.1,'cycle_time_sec':165,'safety':72,'efficiency':61,'hazard_response_sec':2.9,'hazard_response_score':54,'control_precision':65}, benchmark, baseline, context)
    assert evaluation['personal_deviation_pct']==40.3
    assert evaluation['status']=='SIGNIFICANTLY_ABOVE_EXPECTATION'
    assert evaluation['context_adjusted_benchmark']['context_factor']>.1

def test_severe_deviation():
    benchmark={'expected_duration_min':6,'expected_duration_max':8,'expected_cycle_time_min_sec':135,'expected_cycle_time_max_sec':160,'minimum_safety_score':95,'minimum_efficiency_score':80,'maximum_hazard_response_sec':2.5}
    baseline={'average_task_time_hours':7.3}
    result=evaluate_task_performance({}, {'task_time_hours':24,'cycle_time_sec':200,'safety':96,'efficiency':82,'hazard_response_sec':2.0}, benchmark, baseline, {})
    assert result['status']=='SEVERE_DEVIATION'

def test_safety_transition_and_escalation():
    triggered=evaluate_safety({'proximity_distance_m':12},{'proximity_distance_m':5,'cycle_phase':'SWING','seatbelt_fastened':True})
    escalated=evaluate_safety({'proximity_distance_m':5},{'proximity_distance_m':4,'cycle_phase':'SWING','seatbelt_fastened':True})
    resolved=evaluate_safety({'proximity_distance_m':5},{'proximity_distance_m':12,'cycle_phase':'SWING','seatbelt_fastened':True})
    assert triggered[0]['status']=='OPEN'
    assert escalated[0]['status']=='ESCALATED'
    assert resolved[0]['status']=='RESOLVED'

def test_deviation_helpers():
    assert calculate_benchmark_deviation(10.1,7,9)>25
    assert calculate_personal_deviation(10.1,7.2)==40.3

def test_adaptive_recommendation():
    assert recommendation('OP-001',state='BLIND_SPOT')['recommended_scenario']=='Proximity Hazard Response'

def test_benchmark_status_within_context_range():
    benchmark={'expected_duration_min':6,'expected_duration_max':8}
    result=evaluate_task_performance({}, {'task_time_hours':7.5}, benchmark, {'average_task_time_hours':7}, {})
    assert result['status']=='WITHIN_EXPECTATION'

def test_benchmark_status_significant_deviation():
    benchmark={'expected_duration_min':6,'expected_duration_max':8}
    result=evaluate_task_performance({}, {'task_time_hours':10.5}, benchmark, {'average_task_time_hours':7}, {'environment':{'ambient_temp_c':34,'ground_condition':'Hard','payload_pct':68}})
    assert result['status']=='SIGNIFICANTLY_ABOVE_EXPECTATION'

def test_personal_deviation_small_and_large():
    assert calculate_personal_deviation(7.1,7)==1.4
    assert calculate_personal_deviation(10,7)==42.9

def test_calibration_states():
    assert classify_operator_state(85,55)=='UNDERCONFIDENT'
    assert classify_operator_state(58,87)=='BLIND_SPOT'

def test_calibration_signal_surfaces_overconfidence():
    signal=calibration_signal(58,87)
    assert signal['code']=='OVERCONFIDENCE_RISK'
    assert signal['gap']==29

def test_working_conditions_adjust_hazard_margin_and_predict_approach():
    current={'proximity_distance_m':10,'weather':'rainy','visibility':'Good','ground_condition':'Wet','cycle_phase':'SWING'}
    alerts=evaluate_safety({'proximity_distance_m':12,'weather':'rainy','visibility':'Good','ground_condition':'Wet'},current)
    assert working_condition_limits(current)[0]==10
    assert alerts[0]['type']=='PROXIMITY_APPROACHING'
    assert live_operator_guidance(current,alerts)['source']=='rate-of-change'
