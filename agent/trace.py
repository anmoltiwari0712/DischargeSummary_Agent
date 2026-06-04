

""" 
Observability layer — records every step the agent takes. 
""" 
 
import json 
import os 
from datetime import datetime 
 
 
class AgentTrace: 
   def __init__(self, patient_id: str): 
       self.patient_id = patient_id 
       self.started_at = datetime.now().isoformat() 
       self.steps = [] 
       self.warnings = [] 
       self.final_status = None 
 
   def log_step(self, step_number: int, thought: str, action: str = None, 
                action_args: dict = None, result: str = None): 
       step = { 
           "step": step_number, 
           "timestamp": datetime.now().isoformat(), 
           "thought": thought, 
       } 
       if action: 
           step["action"] = action 
           step["action_args"] = action_args or {} 
       if result is not None: 
           step["result"] = result[:500] + "...[truncated]" if len(result) > 500 else result 
 
       self.steps.append(step) 
 
       print(f"\n[Step {step_number}]") 
       if thought: 
           print(f"  Thought : {thought[:150]}") 
       if action: 
           print(f"  Action  : {action}({json.dumps(action_args or {})[:100]})") 
       if result: 
           print(f"  Result  : {result[:150]}") 
 
   def log_warning(self, warning: str): 
       self.warnings.append(warning) 
       print(f"  WARNING : {warning}") 
 
   def finalize(self, status: str): 
       self.final_status = status 
       self.completed_at = datetime.now().isoformat() 
 
       trace_data = { 
           "patient_id": self.patient_id, 
           "started_at": self.started_at, 
           "completed_at": self.completed_at, 
           "final_status": status, 
           "total_steps": len(self.steps), 
           "warnings": self.warnings, 
           "steps": self.steps, 
       } 
 
       out_path = os.path.join("output", "traces", f"{self.patient_id}_trace.json") 
       os.makedirs(os.path.dirname(out_path), exist_ok=True) 
       with open(out_path, "w", encoding="utf-8") as f: 
           json.dump(trace_data, f, indent=2, ensure_ascii=False) 
 
       print(f"\n{'='*60}") 
       print(f"Status     : {status}") 
       print(f"Total steps: {len(self.steps)}") 
       print(f"Trace saved: {out_path}") 
       print(f"{'='*60}") 
 
       return trace_data 
 



 