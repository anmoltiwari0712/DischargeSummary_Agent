""" 

CLI tool for clinicians to score a generated discharge summary. 

Scores across 5 dimensions — stored for the RL feedback loop. 

""" 

 

import json 

import os 

from feedback.store import save_feedback, get_score_trend 

 

SUMMARY_PATH = os.path.join("output", "summaries", "patient_001_summary.json") 

 

 

def score_input(prompt: str, min_val: int = 1, max_val: int = 5) -> int: 

    """Gets a validated integer score from the user.""" 

    while True: 

        try: 

            val = int(input(prompt)) 

            if min_val <= val <= max_val: 

                return val 

            print(f"  Please enter a number between {min_val} and {max_val}.") 

        except ValueError: 

            print("  Invalid input. Please enter a number.") 

 

 

def collect_feedback(patient_id: str = "patient_001", summary_path: str = SUMMARY_PATH): 

    """ 

    Interactive CLI for scoring a discharge summary. 

    Walks the clinician through 5 scoring dimensions. 

    """ 

    if not os.path.exists(summary_path): 

        print(f"ERROR: Summary not found at {summary_path}") 

        print("Run main.py first to generate a summary.") 

        return 

 

    with open(summary_path, "r", encoding="utf-8") as f: 

        summary = json.load(f) 

 

    print("\n" + "=" * 60) 

    print("DISCHARGE SUMMARY FEEDBACK COLLECTOR") 

    print("=" * 60) 

    print(f"Patient ID : {patient_id}") 

    print(f"Summary    : {summary_path}") 

    print("\nPlease review the summary at the path above before scoring.") 

    print("\nScoring Guide: 1 = Very Poor  |  3 = Acceptable  |  5 = Excellent") 

    print("=" * 60) 

 

    print("\n1. COMPLETENESS — Did every required field get filled or explicitly flagged?") 

    print("   (Diagnoses, medications, history, procedures, follow-up, pending results)") 

    completeness = score_input("   Score (1-5): ") 

 

    print("\n2. ACCURACY — Do the values match what is actually in the source document?") 

    print("   (Check diagnoses, lab values, medication names and doses)") 

    accuracy = score_input("   Score (1-5): ") 

 

    print("\n3. FLAG QUALITY — Were conflicts and missing fields correctly identified?") 

    print("   (Were real problems flagged? Were any false flags raised?)") 

    flag_quality = score_input("   Score (1-5): ") 

 

    print("\n4. NO FABRICATION — Did the agent invent anything not in the source document?") 

    print("   (5 = nothing invented, 1 = significant fabrication found)") 

    no_fabrication = score_input("   Score (1-5): ") 

 

    print("\n5. COHERENCE — Is the summary readable and clinically logical?") 

    print("   (Would a clinician find this useful as a starting draft?)") 

    coherence = score_input("   Score (1-5): ") 

 

    composite = ( 

        completeness * 0.2 + 

        accuracy * 0.25 + 

        flag_quality * 0.2 + 

        no_fabrication * 0.25 + 

        coherence * 0.1 

    ) 

 

    print(f"\n{'=' * 60}") 

    print(f"Composite score: {composite:.2f} / 5.00") 

    print(f"{'=' * 60}") 

 

    print("\nOptional: Add corrections or notes (press Enter to skip)") 

    corrections = input("Corrections (what was wrong): ").strip() 

    notes = input("General notes: ").strip() 

 

    record_id = save_feedback( 

        patient_id=patient_id, 

        summary=summary, 

        completeness=completeness, 

        accuracy=accuracy, 

        flag_quality=flag_quality, 

        no_fabrication=no_fabrication, 

        coherence=coherence, 

        corrections=corrections, 

        notes=notes, 

    ) 

 

    print(f"\nFeedback saved (record #{record_id})") 

 

    # Show score trend 

    trend = get_score_trend() 

    if len(trend) > 1: 

        scores = [row[1] for row in trend] 

        print(f"\nScore trend across {len(scores)} runs:") 

        for i, (ts, score, pid) in enumerate(trend): 

            bar = "█" * int(score * 4) 

            print(f"  Run {i+1}: {score:.2f} {bar}") 

        improvement = scores[-1] - scores[0] 

        if improvement > 0: 

            print(f"\n  Overall improvement: +{improvement:.2f} points") 

        elif improvement < 0: 

            print(f"\n  Overall change: {improvement:.2f} points") 

        else: 

            print("\n  Score stable across runs.") 

 

    print("\nDone. This feedback will be used to improve future summaries.") 

 

 

if __name__ == "__main__": 

    collect_feedback() 

 

 