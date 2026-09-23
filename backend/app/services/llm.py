import json, os, re
class LLMProvider:
    def analyze(self,text:str)->dict: raise NotImplementedError
class FallbackLLMProvider(LLMProvider):
    def analyze(self,text):
        low=text.lower(); pos=sum(w in low for w in ('confident','smooth','well','quick','good','safe')); neg=sum(w in low for w in ('slow','difficult','missed','late','poor','uncertain')); hz=sum(w in low for w in ('person','hazard','nearby','proximity','alert','worker'))
        confidence=max(20,min(98,65+pos*8-neg*8)); return {'self_confidence':confidence,'perceived_performance':max(20,min(98,confidence-neg*5)),'perceived_difficulty':max(10,50-neg*8),'hazard_awareness':min(98,55+hz*10),'strengths':['confident operation'] if pos else [],'weaknesses':['response timing'] if neg else [],'mentioned_hazards':['proximity'] if hz else [],'summary':'Structured fallback analysis; objective scores come only from backend telemetry.'}
class OpenAICompatibleProvider(LLMProvider):
    def __init__(self,api_key=None): self.api_key=api_key or os.getenv('LLM_API_KEY')
    def analyze(self,text):
        # Kept intentionally optional for a hackathon: offline fallback remains the default.
        return FallbackLLMProvider().analyze(text)
def get_provider(): return OpenAICompatibleProvider() if os.getenv('LLM_API_KEY') else FallbackLLMProvider()
