"""Reproducible CSV generator for the Smart Operator Companion demo."""
from pathlib import Path
import csv, random, math

SEED=42
OUT=Path(__file__).resolve().parents[2]/'data'

def write(name, headers, records):
    OUT.mkdir(exist_ok=True)
    with open(OUT/name,'w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=headers); w.writeheader(); w.writerows(records)

def main():
    r=random.Random(SEED)
    operators=[]
    archetypes=['experienced_safe','blind_spot','new_cautious','efficient_idle','hazard_aware']
    for i in range(1,21): operators.append({'operator_id':f'OP-{i:03d}','name':'Raghav Sharma' if i==1 else f'Operator {i}','experience_years':7 if i==1 else r.randint(1,12),'level':'Proficient','site':'Site A' if i%2 else 'Site B','archetype':archetypes[i%5]})
    write('operators.csv',operators[0].keys(),operators)
    machines=[{'machine_id':f'M-{i}','model':m,'machine_type':typ,'domain':domain,'status':'Operational','engine_hours':r.randint(1400,6200)} for i,(m,typ,domain) in enumerate([('CAT 320 Excavator','Excavator','EXCAVATION_LOAD'),('CAT 323 Excavator','Excavator','EXCAVATION_LOAD'),('CAT 950 Wheel Loader','Wheel Loader','EXCAVATION_LOAD'),('Backhoe Loader','Backhoe Loader','EXCAVATION_LOAD'),('CAT 777 Off-Highway Truck','Haul Truck','HAUL_TRANSPORT'),('Articulated Hauler','Hauler','HAUL_TRANSPORT'),('CAT 777 Haul Truck','Haul Truck','HAUL_TRANSPORT'),('CAT 950 Loader','Wheel Loader','EXCAVATION_LOAD')],1)]
    write('machines.csv',machines[0].keys(),machines)
    scenarios=[]
    skills=['hazard_response','cycle_efficiency','control_precision','situational_awareness','load_handling']
    for i in range(30): scenarios.append({'scenario_id':f'SCN-{i+1:02d}','name':['Proximity Hazard Response','Efficient Excavation','High-Load Operation','Night Operation Awareness','Bucket Control'][i%5],'domain':'EXCAVATION_LOAD' if i%2 else 'HAUL_TRANSPORT','machine_type':'CAT 320 Excavator' if i%2 else 'CAT 777 Off-Highway Truck','difficulty':['Beginner','Intermediate','Advanced'][i%3],'duration_min':12+i%14,'target_skill':skills[i%len(skills)],'hazard_type':'proximity' if i%3==0 else 'none'})
    write('training_scenarios.csv',scenarios[0].keys(),scenarios)
    benchmarks=[]
    for s in scenarios:
        if 'Haul' in s['name'] or s['domain']=='HAUL_TRANSPORT': values=('Haul Cycle',5,7,160,210,95,82,2.5)
        elif 'Load' in s['name'] or 'Loading' in s['name']: values=('Material Loading',4,6,90,125,94,78,2.8)
        else: values=('Excavation — Trench Digging',6,8,135,160,95,80,2.5)
        benchmarks.append({'scenario_id':s['scenario_id'],'task_type':values[0],'machine_type':s['machine_type'],'domain':s['domain'],'expected_duration_min':values[1],'expected_duration_max':values[2],'expected_cycle_time_min_sec':values[3],'expected_cycle_time_max_sec':values[4],'minimum_safety_score':values[5],'minimum_efficiency_score':values[6],'maximum_hazard_response_sec':values[7]})
    write('task_benchmarks.csv',benchmarks[0].keys(),benchmarks)
    task_headers=['task_id','operator_id','machine_id','domain','task_type','site','scheduled_start','scheduled_end','status','baseline_duration_min']
    tasks=[]
    for i in range(150):
        mach=['M-1','M-3','M-5'][i%3]; tasks.append(dict(zip(task_headers,[f'T-{i+1:03d}',f'OP-{i%20+1:03d}',mach,'HAUL_TRANSPORT' if mach=='M-5' else 'EXCAVATION_LOAD',['Excavation — Trench Digging','Material Loading','Haul Cycle'][i%3],'Site A' if i%2 else 'Site B','08:00','09:00','Completed' if i%4 else 'Upcoming',45 if mach=='M-1' else 60])))
    write('tasks.csv',task_headers,tasks)
    # compact but correlated records suitable for importing
    runs=[]
    for i in range(200):
        operator=f'OP-{i%20+1:03d}'; skill=82 if operator=='OP-001' else 58 if operator=='OP-002' else 60+r.random()*35; confidence=90 if operator=='OP-002' else round(55+skill*.35+r.random()*12,1); runs.append({'run_id':f'TR-{i+1:04d}','operator_id':operator,'scenario_id':f'SCN-{i%30+1:02d}','score':round(skill,1),'hazard_response_sec':round(1.7+(100-skill)/35+r.random()*.4,2),'efficiency_score':round(skill,1),'safety_score':round(min(99,skill+10),1),'self_confidence':confidence})
    write('training_runs.csv',runs[0].keys(),runs)
    baselines=[{'baseline_id':i+1,'operator_id':'OP-001' if i<4 else f'OP-{i%20+1:03d}','scenario_id':'SCN-01','metric_name':m,'metric_value':v,'sample_count':5,'updated_at':'2026-09-23T08:00:00'} for i,(m,v) in enumerate([('hazard_response',2.0),('cycle_time',140),('efficiency',88),('safety',94)]*8)]
    write('operator_baselines.csv',baselines[0].keys(),baselines)
    work=[]; hazards=[]; reflections=[]; cycles=[]; sensors=[]
    phases=['ACQUIRE','LIFT','SWING','DUMP','RETURN']
    for i in range(150):
        sid=f'WS-{i+1:03d}'; operator=f'OP-{i%20+1:03d}'; eff=round((61 if operator=='OP-001' else 42 if operator=='OP-002' else 62+r.random()*30),1); saf=round((72 if operator=='OP-001' else 58 if operator=='OP-002' else min(98,72+r.random()*24)),1); hours=10.1 if operator=='OP-001' and i==0 else 24.0 if operator=='OP-002' and i==1 else round(7.2+r.random()*3,1)
        work.append({'session_id':sid,'operator_id':operator,'machine_id':['M-1','M-3','M-5'][i%3],'task_id':f'T-{i+1:03d}','actual_time_min':round(hours*60,1),'actual_time_hours':hours,'overall_score':round(eff*.55+saf*.45,1),'safety_score':saf,'efficiency_score':eff,'operator_profile':'blind_spot' if operator=='OP-002' else 'demo' if operator=='OP-001' else 'normal','status':'Completed'})
        response=round(1.7+(100-eff)/35+r.random()*.6,2); hazards.append({'hazard_id':f'HZ-{i+1:03d}','session_id':sid,'hazard_type':'proximity','severity':'high','response_duration_sec':response,'acknowledged':1,'escalated':int(response>3),'resolved':1})
        reflections.append({'reflection_id':f'RF-{i+1:03d}','session_id':sid,'operator_id':f'OP-{i%20+1:03d}','text':'The task went well and I felt confident. I noticed the person nearby.','self_confidence':round(62+r.random()*30,1),'perceived_performance':round(65+r.random()*28,1),'hazard_awareness':round(70+r.random()*25,1)})
        for j in range(150):
            phase=phases[j%5]; ambient=round(32+math.sin(j/10)+r.random()*2,1); load=round(45+(25 if phase in ('LIFT','SWING') else 0)+r.random()*8,1)
            sensors.append({'event_id':i*150+j+1,'session_id':sid,'timestamp':'2026-09-23T08:00:00','ambient_temp_c':ambient,'humidity_pct':58,'wind_speed_kmh':12,'fuel_level_pct':round(62-j*.02,1),'fuel_rate_lph':round(18+load*.06,1),'engine_temp_c':round(76+(ambient-30)*.5+load*.04,1),'hydraulic_load_pct':load,'payload_pct':65 if phase in ('LIFT','SWING') else 20,'seatbelt_fastened':1,'proximity_distance_m':12 if j%30<25 else 6,'cycle_phase':phase})
        for j,phase in enumerate(phases): cycles.append({'cycle_id':i*5+j+1,'session_id':sid,'cycle_number':j+1,'phase':phase,'duration_sec':round(25+r.random()*12,1)})
    write('work_sessions.csv',work[0].keys(),work); write('hazard_events.csv',hazards[0].keys(),hazards); write('reflections.csv',reflections[0].keys(),reflections); write('sensor_events.csv',sensors[0].keys(),sensors); write('machine_cycles.csv',cycles[0].keys(),cycles)
    print(f'Generated {len(operators)} operators, {len(machines)} machines, {len(tasks)} tasks, {len(scenarios)} scenarios, {len(runs)} correlated training runs and {len(sensors)} sensor events in {OUT}')
if __name__=='__main__': main()
