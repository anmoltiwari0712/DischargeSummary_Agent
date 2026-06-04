""" 

SQLite storage for discharge summary feedback scores. 

Stores clinician ratings across 5 dimensions for RL loop. 

""" 

 

import sqlite3 

import json 

import os 

from datetime import datetime 

 

DB_PATH = os.path.join("feedback", "feedback.db") 

 

 

def init_db(): 

    """Creates the feedback database and tables if they don't exist.""" 

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) 

    conn = sqlite3.connect(DB_PATH) 

    cursor = conn.cursor() 

    cursor.execute(""" 

        CREATE TABLE IF NOT EXISTS feedback ( 

            id INTEGER PRIMARY KEY AUTOINCREMENT, 

            patient_id TEXT NOT NULL, 

            timestamp TEXT NOT NULL, 

            summary_json TEXT NOT NULL, 

            completeness INTEGER NOT NULL, 

            accuracy INTEGER NOT NULL, 

            flag_quality INTEGER NOT NULL, 

            no_fabrication INTEGER NOT NULL, 

            coherence INTEGER NOT NULL, 

            composite_score REAL NOT NULL, 

            corrections TEXT, 

            notes TEXT 

        ) 

    """) 

    conn.commit() 

    conn.close() 

 

 

def save_feedback( 

    patient_id: str, 

    summary: dict, 

    completeness: int, 

    accuracy: int, 

    flag_quality: int, 

    no_fabrication: int, 

    coherence: int, 

    corrections: str = "", 

    notes: str = "" 

) -> int: 

    """ 

    Saves a feedback record. Returns the new record ID. 

    Composite score is weighted average of 5 dimensions. 

    """ 

    # Weighted scoring — no_fabrication and accuracy weighted higher 

    composite = ( 

        completeness * 0.2 + 

        accuracy * 0.25 + 

        flag_quality * 0.2 + 

        no_fabrication * 0.25 + 

        coherence * 0.1 

    ) 

 

    init_db() 

    conn = sqlite3.connect(DB_PATH) 

    cursor = conn.cursor() 

    cursor.execute(""" 

        INSERT INTO feedback ( 

            patient_id, timestamp, summary_json, 

            completeness, accuracy, flag_quality, 

            no_fabrication, coherence, composite_score, 

            corrections, notes 

        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 

    """, ( 

        patient_id, 

        datetime.now().isoformat(), 

        json.dumps(summary), 

        completeness, 

        accuracy, 

        flag_quality, 

        no_fabrication, 

        coherence, 

        round(composite, 2), 

        corrections, 

        notes 

    )) 

    record_id = cursor.lastrowid 

    conn.commit() 

    conn.close() 

    return record_id 

 

 

def get_all_feedback() -> list: 

    """Returns all feedback records sorted by composite score descending.""" 

    init_db() 

    conn = sqlite3.connect(DB_PATH) 

    cursor = conn.cursor() 

    cursor.execute(""" 

        SELECT id, patient_id, timestamp, composite_score, 

               completeness, accuracy, flag_quality, 

               no_fabrication, coherence, corrections, notes 

        FROM feedback 

        ORDER BY composite_score DESC 

    """) 

    rows = cursor.fetchall() 

    conn.close() 

    return rows 

 

 

def get_top_summaries(limit: int = 3) -> list: 

    """ 

    Returns the top N summaries by composite score. 

    Used by retriever to build few-shot examples. 

    """ 

    init_db() 

    conn = sqlite3.connect(DB_PATH) 

    cursor = conn.cursor() 

    cursor.execute(""" 

        SELECT patient_id, summary_json, composite_score, 

               corrections, notes 

        FROM feedback 

        ORDER BY composite_score DESC 

        LIMIT ? 

    """, (limit,)) 

    rows = cursor.fetchall() 

    conn.close() 

    return rows 

 

 

def get_score_trend() -> list: 

    """Returns composite scores over time to track improvement.""" 

    init_db() 

    conn = sqlite3.connect(DB_PATH) 

    cursor = conn.cursor() 

    cursor.execute(""" 

        SELECT timestamp, composite_score, patient_id 

        FROM feedback 

        ORDER BY timestamp ASC 

    """) 

    rows = cursor.fetchall() 

    conn.close() 

    return rows 

 

 