""" 

Retrieves top-scoring past summaries to use as few-shot examples. 

This is the RL loop — better summaries get used as examples for future runs. 

""" 

 

import json 

from feedback.store import get_top_summaries, get_score_trend 

 

 

def get_few_shot_examples(limit: int = 2) -> str: 

    """ 

    Returns the top N summaries formatted as few-shot examples. 

    Injected into the system prompt to guide future runs. 

    """ 

    top_summaries = get_top_summaries(limit=limit) 

 

    if not top_summaries: 

        return "" 

 

    examples = [] 

    for patient_id, summary_json, score, corrections, notes in top_summaries: 

        try: 

            summary = json.loads(summary_json) 

        except Exception: 

            continue 

 

        example = f""" 

EXAMPLE SUMMARY (Score: {score:.2f}/5.00): 

Patient: {patient_id} 

Primary Diagnosis: {summary.get('diagnoses', {}).get('primary', {}).get('name', 'N/A')} 

Medications: {len(summary.get('discharge_medications', []))} items 

Flags: {summary.get('total_flags', 0)} clinician flags 

""" 

        if corrections: 

            example += f"Known corrections from clinician: {corrections}\n" 

        if notes: 

            example += f"Notes: {notes}\n" 

 

        examples.append(example) 

 

    if not examples: 

        return "" 

 

    return ( 

        "\n\n=== FEW-SHOT EXAMPLES FROM PREVIOUS HIGH-SCORING RUNS ===\n" 

        + "\n---\n".join(examples) 

        + "\n=== END EXAMPLES ===\n" 

        + "Use these as reference for quality — aim to match or exceed these scores.\n" 

    ) 

 

 

def get_improvement_context() -> str: 

    """ 

    Returns a summary of score trends and common corrections. 

    Injected into the prompt to guide improvement areas. 

    """ 

    trend = get_score_trend() 

    if not trend: 

        return "" 

 

    scores = [row[1] for row in trend] 

    if len(scores) < 2: 

        return "" 

 

    avg = sum(scores) / len(scores) 

    best = max(scores) 

    latest = scores[-1] 

    improvement = latest - scores[0] 

 

    context = f""" 

=== IMPROVEMENT CONTEXT === 

Runs completed: {len(scores)} 

Average score: {avg:.2f}/5.00 

Best score: {best:.2f}/5.00 

Latest score: {latest:.2f}/5.00 

Overall improvement: {'+' if improvement >= 0 else ''}{improvement:.2f} points 

=========================== 

""" 

    return context 

 

 

def print_feedback_report(): 

    """Prints a human-readable feedback report to the terminal.""" 

    trend = get_score_trend() 

 

    if not trend: 

        print("No feedback recorded yet. Run collector.py after generating a summary.") 

        return 

 

    print("\n" + "=" * 60) 

    print("FEEDBACK REPORT") 

    print("=" * 60) 

 

    scores = [row[1] for row in trend] 

    print(f"Total runs scored : {len(scores)}") 

    print(f"Average score     : {sum(scores)/len(scores):.2f}/5.00") 

    print(f"Best score        : {max(scores):.2f}/5.00") 

    print(f"Latest score      : {scores[-1]:.2f}/5.00") 

 

    print("\nScore history:") 

    for i, (ts, score, pid) in enumerate(trend): 

        bar = "█" * int(score * 4) 

        date = ts[:10] 

        print(f"  Run {i+1} ({date}) [{pid}]: {score:.2f} {bar}") 

 

    if len(scores) > 1: 

        improvement = scores[-1] - scores[0] 

        print(f"\nImprovement from run 1 to latest: {'+' if improvement >= 0 else ''}{improvement:.2f} points") 

 

    top = get_top_summaries(limit=1) 

    if top: 

        print(f"\nBest summary: patient={top[0][0]}, score={top[0][2]:.2f}") 

        if top[0][3]: 

            print(f"Clinician corrections: {top[0][3]}") 

 

    print("=" * 60) 

 

 

if __name__ == "__main__": 

    print_feedback_report() 

 

 