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
    archetypes=['NORMAL','FAST_BUT_RISKY','SLOW_BUT_SAFE','BLIND_SPOT','INCONSISTENT']
    for i in range(1,21): operators.append({'operator_id':f'OP-{i:03d}','name':'Raghav Sharma' if i==1 else f'Operator {i}','experience_years':7 if i==1 else r.randint(1,12),'level':'Proficient','site':'Site A' if i%2 else 'Site B','profile':('BLIND_SPOT' if i==1 else 'FAST_BUT_RISKY' if i==2 else archetypes[i%5])})
    write('operators.csv',operators[0].keys(),operators)
    machines=[{'machine_id':f'M-{i}','model':m,'machine_type':typ,'domain':domain,'status':'Operational','engine_hours':r.randint(1400,6200)} for i,(m,typ,domain) in enumerate([('CAT 320 Excavator','Excavator','EXCAVATION_LOAD'),('CAT 323 Excavator','Excavator','EXCAVATION_LOAD'),('CAT 950 Wheel Loader','Wheel Loader','EXCAVATION_LOAD'),('Backhoe Loader','Backhoe Loader','EXCAVATION_LOAD'),('CAT 777 Off-Highway Truck','Haul Truck','HAUL_TRANSPORT'),('Articulated Hauler','Hauler','HAUL_TRANSPORT'),('CAT 777 Haul Truck','Haul Truck','HAUL_TRANSPORT'),('CAT 950 Loader','Wheel Loader','EXCAVATION_LOAD')],1)]
    write('machines.csv',machines[0].keys(),machines)
    domains=[{'domain':'EXCAVATION_LOAD','name':'Excavation / Loading','phases':'ACQUIRE|LIFT|SWING|DUMP|RETURN','primary_metrics':'cycle_time|control_precision|idle_time|hazard_response|safety_behavior'},{'domain':'HAUL_TRANSPORT','name':'Haul / Transport','phases':'LOAD|TRAVEL_LOADED|QUEUE_SPOT|DUMP|TRAVEL_EMPTY|RETURN','primary_metrics':'cycle_time|queue_time|reaction_latency|stop_response|efficiency'}]
    write('machine_domains.csv',domains[0].keys(),domains)
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
    task_headers=['task_id','operator_id','machine_id','domain','task_type','site','scheduled_start','scheduled_end','status','baseline_duration_min','weather','operator_skill','machine_age_hours','demo_seed','job_options_json']
    tasks=[]
    for i in range(150):
        mach='M-1' if i==1 else ['M-1','M-3','M-5'][i%3]; task_id='T002-today' if i==1 else f'T-{i+1:03d}'; task_name='Excavation — Trench Digging' if i==1 else ['Excavation — Trench Digging','Material Loading','Haul Cycle'][i%3]; task_site='Site A — Rain Trench' if i==1 else ('Site A' if i%2 else 'Site B'); scheduled_end='10:45' if i==1 else '09:00'; tasks.append(dict(zip(task_headers,[task_id,'OP-001' if i==1 else f'OP-{i%20+1:03d}',mach,'HAUL_TRANSPORT' if mach=='M-5' else 'EXCAVATION_LOAD',task_name,task_site,'10:00' if i==1 else '08:00',scheduled_end,'Upcoming' if i==1 else ('Completed' if i%4 else 'Upcoming'),45 if mach=='M-1' else 60,'rainy' if i==1 else 'clear','intermediate',2140 if i==1 else r.randint(1200,6000),170923 if i==1 else '', '{"duration_min":45,"weather":"rainy","skill":"intermediate"}' if i==1 else '{}'])))
    write('tasks.csv',task_headers,tasks)
    synthetic_tasks=list(tasks)
    for i in range(len(synthetic_tasks),3000):
        machine=['M-1','M-3','M-5'][i%3]
        task_name=['Excavation — Trench Digging','Material Loading','Haul Cycle'][i%3]
        synthetic_tasks.append(dict(zip(task_headers,[f'SYN-T-{i+1:04d}',f'OP-{i%20+1:03d}',machine,'HAUL_TRANSPORT' if machine=='M-5' else 'EXCAVATION_LOAD',task_name,'Site A' if i%2 else 'Site B','08:00','09:00','Completed' if i%4 else 'Upcoming',45 if machine=='M-1' else 60,'clear','intermediate',1200+(i*37)%4800,'','{}'])))
    write('synthetic_tasks.csv',task_headers,synthetic_tasks)
    # compact but correlated records suitable for importing
    runs=[]
    for i in range(200):
        operator=f'OP-{i%20+1:03d}'; profile='BLIND_SPOT' if operator=='OP-001' else 'FAST_BUT_RISKY' if operator=='OP-002' else ['NORMAL','SLOW_BUT_SAFE','INCONSISTENT'][i%3]; skill=82 if operator=='OP-001' else 58 if operator=='OP-002' else 60+r.random()*35; confidence=90 if operator in ('OP-001','OP-002') else round(55+skill*.35+r.random()*12,1); runs.append({'run_id':f'TR-{i+1:04d}','operator_id':operator,'scenario_id':f'SCN-{i%30+1:02d}','score':round(skill,1),'hazard_response_sec':round(1.7+(100-skill)/35+r.random()*.4,2),'efficiency_score':round(skill,1),'safety_score':round(min(99,skill+10),1),'self_confidence':confidence,'operator_profile':profile})
    write('training_runs.csv',runs[0].keys(),runs)
    baselines=[{'baseline_id':i+1,'operator_id':'OP-001' if i<4 else f'OP-{i%20+1:03d}','scenario_id':'SCN-01','metric_name':m,'metric_value':v,'sample_count':5,'updated_at':'2026-09-23T08:00:00'} for i,(m,v) in enumerate([('hazard_response',2.0),('cycle_time',140),('efficiency',88),('safety',94)]*8)]
    write('operator_baselines.csv',baselines[0].keys(),baselines)
    personal=[{'operator_id':f'OP-{i:03d}','scenario_id':'SCN-01','average_task_time_hours':7.2 if i==1 else round(7.2+r.random()*2,1),'average_cycle_time_sec':140 if i==1 else round(140+r.random()*30,1),'average_hazard_response_sec':2.0 if i==1 else round(2+r.random(),2),'average_efficiency':88 if i==1 else round(70+r.random()*20,1),'average_safety':94 if i==1 else round(78+r.random()*18,1),'average_control_precision':87 if i==1 else round(72+r.random()*20,1),'consistency_score':92 if i==1 else round(65+r.random()*25,1),'sample_count':5} for i in range(1,21)]
    write('personal_operator_baselines.csv',personal[0].keys(),personal)
    work=[]; hazards=[]; reflections=[]; cycles=[]; sensors=[]
    phases=['ACQUIRE','LIFT','SWING','DUMP','RETURN']
    for i in range(150):
        sid=f'WS-{i+1:03d}'; operator=f'OP-{i%20+1:03d}'; eff=round((61 if operator=='OP-001' else 42 if operator=='OP-002' else 62+r.random()*30),1); saf=round((72 if operator=='OP-001' else 58 if operator=='OP-002' else min(98,72+r.random()*24)),1); hours=10.1 if operator=='OP-001' and i==0 else 24.0 if operator=='OP-002' and i==1 else round(7.2+r.random()*3,1)
        work.append({'session_id':sid,'operator_id':operator,'machine_id':['M-1','M-3','M-5'][i%3],'task_id':f'T-{i+1:03d}','actual_time_min':round(hours*60,1),'actual_time_hours':hours,'overall_score':round(eff*.55+saf*.45,1),'safety_score':saf,'efficiency_score':eff,'operator_profile':'BLIND_SPOT' if operator=='OP-001' else 'FAST_BUT_RISKY' if operator=='OP-002' else ('SLOW_BUT_SAFE' if operator=='OP-003' else 'NORMAL'),'status':'Completed'})
        response=round(1.7+(100-eff)/35+r.random()*.6,2); hazards.append({'hazard_id':f'HZ-{i+1:03d}','session_id':sid,'hazard_type':'proximity','severity':'high','response_duration_sec':response,'acknowledged':1,'escalated':int(response>3),'resolved':1})
        reflections.append({'reflection_id':f'RF-{i+1:03d}','session_id':sid,'operator_id':f'OP-{i%20+1:03d}','text':'The task went well and I felt confident. I noticed the person nearby.','self_confidence':round(62+r.random()*30,1),'perceived_performance':round(65+r.random()*28,1),'hazard_awareness':round(70+r.random()*25,1)})
        for j in range(150):
            phase=phases[j%5]; ambient=round(32+math.sin(j/10)+r.random()*2,1); load=round(45+(25 if phase in ('LIFT','SWING') else 0)+r.random()*8,1)
            sensors.append({'event_id':i*150+j+1,'session_id':sid,'timestamp':'2026-09-23T08:00:00','ambient_temp_c':ambient,'humidity_pct':58,'wind_speed_kmh':12,'fuel_level_pct':round(62-j*.02,1),'fuel_rate_lph':round(18+load*.06,1),'engine_temp_c':round(76+(ambient-30)*.5+load*.04,1),'hydraulic_load_pct':load,'payload_pct':65 if phase in ('LIFT','SWING') else 20,'seatbelt_fastened':0 if operator=='OP-002' and j in (20,21) else 1,'proximity_distance_m':12 if j%30<25 else 6,'proximity_limit_m':8,'proximity_closing_speed_mps':0,'visibility':'Good','soil_type':'Rocky' if operator=='OP-001' else 'Medium (Sandy)','ground_condition':'Hard' if operator=='OP-001' else 'Dry','tilt_deg':round(2+r.random()*2,1),'idle_seconds':3 if phase=='RETURN' and j%17==0 else 0,'fuel_per_cycle_l':round((18+load*.06)/5*(1.35 if operator=='OP-002' else 1),2),'unusual_pattern':operator=='OP-002' and j%47==0,'cycle_phase':phase})
        for j,phase in enumerate(phases): cycles.append({'cycle_id':i*5+j+1,'session_id':sid,'cycle_number':j+1,'phase':phase,'duration_sec':round(25+r.random()*12,1)})
    write('work_sessions.csv',work[0].keys(),work); write('hazard_events.csv',hazards[0].keys(),hazards); write('reflections.csv',reflections[0].keys(),reflections); write('sensor_events.csv',sensors[0].keys(),sensors); synthetic_telemetry=[]
    for i in range(2000):
        event=dict(sensors[i % len(sensors)])
        event['event_id']=i+1
        event['unusual_pattern']=bool(event.get('unusual_pattern') or i%20==0)
        synthetic_telemetry.append(event)
    write('synthetic_telemetry.csv',sensors[0].keys(),synthetic_telemetry); write('machine_cycles.csv',cycles[0].keys(),cycles)
    print(f'Generated {len(operators)} operators, {len(machines)} machines, {len(tasks)} tasks, {len(synthetic_tasks)} synthetic tasks, {len(scenarios)} scenarios, {len(runs)} correlated training runs and {len(sensors)} sensor events ({len(synthetic_telemetry)} exported synthetic telemetry rows) in {OUT}')
if __name__=='__main__': main()
