import streamlit as st
import pandas as pd
import sqlite3
import json

# Mobile-friendly settings
st.set_page_config(
    layout="wide",
    page_title="Golf Rumble Scoring",
    initial_sidebar_state="collapsed"
)

hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ────────────────────────────────────────────────
# Database setup
# ────────────────────────────────────────────────
DB_FILE = 'golf_db.db'
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        name TEXT PRIMARY KEY,
        handicap INTEGER
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        name TEXT PRIMARY KEY,
        pars TEXT,
        stroke_indices TEXT
    )
''')
conn.commit()

def save_player(name, handicap):
    cursor.execute('INSERT OR REPLACE INTO players (name, handicap) VALUES (?, ?)', (name, handicap))
    conn.commit()

def delete_players(names):
    if not names: return
    placeholders = ','.join('?' for _ in names)
    cursor.execute(f'DELETE FROM players WHERE name IN ({placeholders})', names)
    conn.commit()

def load_players():
    cursor.execute('SELECT * FROM players ORDER BY name')
    return pd.DataFrame(cursor.fetchall(), columns=['Name', 'Handicap'])

def save_course(name, pars_list, si_list):
    cursor.execute('''
        INSERT OR REPLACE INTO courses (name, pars, stroke_indices)
        VALUES (?, ?, ?)
    ''', (name, json.dumps(pars_list), json.dumps(si_list)))
    conn.commit()

def load_course(name):
    cursor.execute('SELECT pars, stroke_indices FROM courses WHERE name = ?', (name,))
    row = cursor.fetchone()
    if row:
        return pd.DataFrame({
            'Hole': range(1, 19),
            'Par': json.loads(row[0]),
            'Stroke Index': json.loads(row[1])
        })
    return None

def load_all_course_names():
    cursor.execute('SELECT name FROM courses ORDER BY name')
    return [row[0] for row in cursor.fetchall()]

def delete_course(name):
    cursor.execute('DELETE FROM courses WHERE name = ?', (name,))
    conn.commit()

# ────────────────────────────────────────────────
# Scoring functions
# ────────────────────────────────────────────────
def stableford_points(gross_score, par, strokes_received):
    if gross_score <= 0:
        return 0
    net_score = gross_score - strokes_received
    if net_score > par + 1: return 0
    elif net_score == par + 1: return 1
    elif net_score == par: return 2
    elif net_score == par - 1: return 3
    elif net_score == par - 2: return 4
    else: return 5 + (par - net_score - 2)

def strokes_on_hole(handicap, stroke_index):
    full = handicap // 18
    rem = handicap % 18
    return full + 1 if stroke_index <= rem else full

#
