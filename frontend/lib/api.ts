import type {AdaptiveRecommendation,HomeSummary,PerformanceEvaluation,PersonalBaseline,ReportSummary,Scenario,Task,TaskBenchmark} from './types';
const BASE=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
export async function api<T=unknown>(path:string, options?:RequestInit):Promise<T>{const r=await fetch(`${BASE}${path}`,{...options,headers:{'Content-Type':'application/json',...(options?.headers||{})},cache:'no-store'});if(!r.ok)throw new Error(await r.text());return r.json()}
export const getHome=()=>Promise.all([api<HomeSummary>('/operators/OP-001/summary'),api<Task[]>('/tasks/today'),api<unknown[]>('/machines'),api<AdaptiveRecommendation>('/recommendations/current')]);
export const getEvaluation=(sessionId='WS-DEMO')=>api<PerformanceEvaluation>(`/performance/evaluate/${sessionId}`);
export const getTasks=()=>api<Task[]>('/tasks/today');
export const getScenarios=()=>api<Scenario[]>('/training/scenarios');
export const getReports=()=>api<ReportSummary>('/reports/summary');
export const getBenchmarks=()=>api<TaskBenchmark[]>('/benchmarks');
export const getPersonalBaseline=(operatorId='OP-001',scenarioId='SCN-PROX-01')=>api<PersonalBaseline>(`/performance/${operatorId}/personal-baseline?scenario_id=${scenarioId}`);
export const getBenchmarkComparison=(operatorId='OP-001')=>api(`/performance/${operatorId}/benchmark-comparison`);
export const startWork=(task_id='T-001',machine_id='M-320')=>api<{session_id:string}>('/work/sessions',{method:'POST',body:JSON.stringify({operator_id:'OP-001',machine_id,task_id})}).then((s)=>api<{session_id:string}>(`/work/sessions/${s.session_id}/start`,{method:'POST'}));
export const finishWork=(id:string)=>api(`/work/sessions/${id}/complete`,{method:'POST'});
export const analyze=(session_id:string,text:string)=>api<import('./types').ReflectionResponse>('/reflections',{method:'POST',body:JSON.stringify({session_id,text})});
export const completeTraining=(scenario_id:string)=>api(`/training/runs/TRAIN-${Date.now()}/complete`,{method:'POST',body:JSON.stringify({scenario_id,operator_id:'OP-001',score:86,hazard_response_sec:1.9,efficiency_score:88,safety_score:94})});
export {BASE};
