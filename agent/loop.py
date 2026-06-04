""" 

Core agent loop — the LLM drives all decisions. 

""" 

  

import json 

import os 

from dotenv import load_dotenv 

from groq import Groq 

  

from agent.tools import TOOL_SCHEMAS, execute_tool 

from agent.prompts import SYSTEM_PROMPT 

from agent.trace import AgentTrace 

  

load_dotenv() 

  

MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", 25)) 

GROQ_MODEL = "llama-3.3-70b-versatile" 

MAX_MESSAGES_IN_CONTEXT = 12  # trim old messages to stay under token limit 

  

  

def trim_messages(messages: list) -> list: 

    """ 

    Keeps the system prompt + user message + last N messages. 

    Prevents context window from growing too large. 

    """ 

    if len(messages) <= MAX_MESSAGES_IN_CONTEXT: 

        return messages 

  

    # Always keep system prompt (index 0) and user message (index 1) 

    fixed = messages[:2] 

    recent = messages[-(MAX_MESSAGES_IN_CONTEXT - 2):] 

  

    # Make sure we don't start with a tool result — that confuses the LLM 

    while recent and recent[0].get("role") == "tool": 

        recent = recent[1:] 

  

    return fixed + recent 

  

  

def run_agent(pdf_path: str, patient_id: str = "patient_001") -> dict: 

    client = Groq(api_key=os.getenv("GROQ_API_KEY")) 

    trace = AgentTrace(patient_id) 

  

    print(f"\n{'='*60}") 

    print(f"Starting discharge summary agent") 

    print(f"Patient    : {patient_id}") 

    print(f"PDF        : {pdf_path}") 

    print(f"Max steps  : {MAX_STEPS}") 

    print(f"Model      : {GROQ_MODEL}") 

    print(f"{'='*60}") 

  

    messages = [ 

        {"role": "system", "content": SYSTEM_PROMPT}, 

        { 

            "role": "user", 

            "content": ( 

                f"Generate a complete discharge summary for patient '{patient_id}'. " 

                f"The records are at: {pdf_path}\n\n" 

                f"Follow your workflow: read the document, extract each clinical section, " 

                f"check drug interactions for actual drugs found, flag conflicts and missing fields, " 

                f"then finalize the summary.\n\n" 

                f"Never invent facts. Never use placeholder values like 'drug1' or 'diagnosis1'. " 

                f"Only use real values found in the document." 

            ), 

        }, 

    ] 

  

    step = 0 

    summary_result = None 

  

    while step < MAX_STEPS: 

        step += 1 

  

        # Trim messages to stay under token limit 

        messages = trim_messages(messages) 

  

        # ── Call the LLM ── 

        try: 

            response = client.chat.completions.create( 

                model=GROQ_MODEL, 

                messages=messages, 

                tools=TOOL_SCHEMAS, 

                tool_choice="auto", 

                temperature=0.1, 

                max_tokens=2048, 

            ) 

        except Exception as e: 

            trace.log_warning(f"LLM call failed on step {step}: {e}") 

            # If token limit hit, trim more aggressively and retry 

            if "413" in str(e) or "rate_limit" in str(e): 

                messages = messages[:2] + messages[-4:] 

                try: 

                    response = client.chat.completions.create( 

                        model=GROQ_MODEL, 

                        messages=messages, 

                        tools=TOOL_SCHEMAS, 

                        tool_choice="auto", 

                        temperature=0.1, 

                        max_tokens=2048, 

                    ) 

                except Exception as e2: 

                    trace.log_warning(f"Retry failed: {e2}. Stopping.") 

                    break 

            else: 

                trace.log_warning(f"Retry failed. Stopping.") 

                break 

  

        choice = response.choices[0] 

        message = choice.message 

        finish_reason = choice.finish_reason 

  

        # ── Agent finished naturally ── 

        if finish_reason == "stop" and not message.tool_calls: 

            trace.log_step(step, thought=message.content or "Agent done.") 

            break 

  

        # ── Agent wants to call tools ── 

        if message.tool_calls: 

            thought = message.content or "Calling tool..." 

  

            messages.append({ 

                "role": "assistant", 

                "content": message.content, 

                "tool_calls": [ 

                    { 

                        "id": tc.id, 

                        "type": "function", 

                        "function": { 

                            "name": tc.function.name, 

                            "arguments": tc.function.arguments 

                        }, 

                    } 

                    for tc in message.tool_calls 

                ], 

            }) 

  

            for tool_call in message.tool_calls: 

                tool_name = tool_call.function.name 

                try: 

                    tool_args = json.loads(tool_call.function.arguments) 

                except json.JSONDecodeError: 

                    tool_args = {} 

  

                trace.log_step( 

                    step, 

                    thought=thought, 

                    action=tool_name, 

                    action_args=tool_args, 

                ) 

  

                tool_result = execute_tool(tool_name, tool_args) 

  

                # Truncate large tool results before adding to context 

                # This is the key fix — raw PDF content is too large to keep in full 

                if tool_name == "read_document": 

                    context_result = tool_result[:3000] 

                elif tool_name in ["get_raw_pages", "get_section"]: 

                    context_result = tool_result[:1500] 

                else: 

                    context_result = tool_result[:800] 

  

                if trace.steps: 

                    trace.steps[-1]["result"] = ( 

                        tool_result[:500] + "...[truncated]" 

                        if len(tool_result) > 500 

                        else tool_result 

                    ) 

  

                print(f"  Result  : {tool_result[:200]}") 

  

                if tool_name == "finalize_summary": 

                    summary_result = tool_result 

  

                messages.append({ 

                    "role": "tool", 

                    "tool_call_id": tool_call.id, 

                    "content": context_result, 

                }) 

  

                step += 1 

                if step >= MAX_STEPS: 

                    trace.log_warning( 

                        f"Hit step limit ({MAX_STEPS}). Summary may be incomplete." 

                    ) 

                    break 

  

            if step >= MAX_STEPS: 

                break 

        else: 

            trace.log_step(step, thought=message.content or "No action.") 

            break 

  

    # ── Finalize ── 

    if summary_result: 

        status = "COMPLETED" 

    elif step >= MAX_STEPS: 

        status = "HIT_STEP_LIMIT — summary may be incomplete" 

    else: 

        status = "STOPPED_EARLY — check trace for details" 

  

    return trace.finalize(status) 