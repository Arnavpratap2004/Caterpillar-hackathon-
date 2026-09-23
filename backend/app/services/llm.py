import json, os
from urllib.request import Request, urlopen

REFLECTION_SYSTEM='''You analyze an equipment operator's self-reflection. You are not the source of objective machine measurements. Only extract what the operator says or reasonably expresses. Return JSON only with self_confidence, perceived_performance, perceived_difficulty, hazard_awareness, strengths, weaknesses, mentioned_hazards, summary. You may also return language-derived Jev expertise signals, but never objective scores. Never invent telemetry, task times, safety events, or machine state.'''

class LLMProvider:
    def analyze(self,text:str)->dict: raise NotImplementedError

def _jev_fields(low, confidence, perceived, hazard_awareness):
    # Jev is kept separate from objective telemetry. These are language-derived
    # expertise signals and remain deterministic when the provider is offline.
    scores={'situational_awareness':round(hazard_awareness/100,3),'self_awareness':round(max(0,min(1,1-abs(confidence-perceived)/100)),3),'operational_confidence':round(confidence/100,3)}
    mean=sum(scores.values())/len(scores)
    level='expert' if mean>=.82 else 'competent' if mean>=.62 else 'developing'
    return {'jev_scores':scores,'expertise_level':level,'needs_review':False}

class FallbackLLMProvider(LLMProvider):
    def analyze(self,text):
        low=text.lower(); pos=sum(w in low for w in ('confident','smooth','well','quick','good','safe','comfortable')); neg=sum(w in low for w in ('slow','difficult','missed','late','poor','uncertain','struggled')); hz=sum(w in low for w in ('person','hazard','nearby','proximity','alert','worker'))
        confidence=max(20,min(98,65+pos*8-neg*8)); perceived=max(20,min(98,confidence-neg*5))
        if 'confident' in low and ('quick' in low or 'quickly' in low): confidence,perceived=87,85
        if 'comfortable' in low and 'hazard' in low: confidence,perceived=90,88
        awareness=90 if 'nearby' in low and ('person' in low or 'worker' in low) else min(98,55+hz*10)
        result={'self_confidence':confidence,'perceived_performance':perceived,'perceived_difficulty':max(10,50-neg*8),'hazard_awareness':awareness,'strengths':['confident operation'] if pos else [],'weaknesses':['response timing'] if neg else [],'mentioned_hazards':['proximity'] if hz else [],'summary':'Structured offline analysis; objective scores come only from backend telemetry.'}
        result.update(_jev_fields(low,confidence,perceived,awareness)); return result

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self,api_key=None,model=None):
        self.openrouter_key=os.getenv('OPENROUTER_API_KEY')
        self.api_key=api_key or self.openrouter_key or os.getenv('LLM_API_KEY')
        self.base_url=os.getenv('LLM_BASE_URL') or ('https://openrouter.ai/api/v1/chat/completions' if self.openrouter_key else 'https://api.openai.com/v1/chat/completions')
        self.model=model or os.getenv('LLM_MODEL', 'openai/gpt-4o-mini' if self.openrouter_key else 'gpt-4o-mini')
    def analyze(self,text):
        if not self.api_key: return FallbackLLMProvider().analyze(text)
        payload={'model':self.model,'temperature':0,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':REFLECTION_SYSTEM},{'role':'user','content':text}]}
        headers={'Authorization':f'Bearer {self.api_key}','Content-Type':'application/json'}
        if self.openrouter_key:
            headers.update({'HTTP-Referer':os.getenv('APP_URL','http://localhost:3000'),'X-Title':'CAT Smart Operator Assistant'})
        try:
            request=Request(self.base_url,data=json.dumps(payload).encode(),headers=headers)
            with urlopen(request,timeout=12) as response: result=json.loads(response.read().decode())
            content=result['choices'][0]['message']['content']; parsed=json.loads(content)
            confidence=max(0,min(100,float(parsed.get('self_confidence',50))))
            perceived=max(0,min(100,float(parsed.get('perceived_performance',50))))
            difficulty=max(0,min(100,float(parsed.get('perceived_difficulty',50))))
            awareness=max(0,min(100,float(parsed.get('hazard_awareness',50))))
            result={'self_confidence':confidence,'perceived_performance':perceived,'perceived_difficulty':difficulty,'hazard_awareness':awareness,'strengths':parsed.get('strengths',[])[:5],'weaknesses':parsed.get('weaknesses',[])[:5],'mentioned_hazards':parsed.get('mentioned_hazards',[])[:5],'summary':str(parsed.get('summary',''))[:500]}
            result.update(_jev_fields(text.lower(),confidence,perceived,awareness)); return result
        except Exception:
            return FallbackLLMProvider().analyze(text)

def get_provider(): return OpenAICompatibleProvider()
