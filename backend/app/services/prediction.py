def predict_task_time(baseline_time, operator_factor=1, environment_factor=1, machine_factor=1):
    factors=[max(.85,min(1.2,operator_factor)),max(.9,min(1.2,environment_factor)),max(.9,min(1.15,machine_factor))]
    value=baseline_time
    for factor in factors:value*=factor
    return {'predicted_time':round(value,1),'confidence':round(max(55,95-abs(value-baseline_time)*1.5),0),'top_contributing_factors':['operator efficiency','environment','machine state']}
