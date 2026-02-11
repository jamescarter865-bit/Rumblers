import streamlit as st
import pandas as pd
import sqlite3

# Mobile-friendly settings - MUST come right after import, before any st.title etc.
st.set_page_config(
    layout="wide",
    page_title="Golf Rumble Scoring",
    initial_sidebar_state="collapsed"
)

# Hide extra Streamlit stuff for cleaner mobile look
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Database setup (SQLite for persistent player profiles)
DB_FILE = 'golf_db.db'
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# Create players table if not exists
cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        name TEXT PRIMARY KEY,
        handicap INTEGER
    )
''')
conn.commit()

# Function to add or update player in DB
def save_player(name, handicap):
    cursor.execute('''
        INSERT OR REPLACE INTO players (name, handicap)
        VALUES (?, ?)
    ''', (name, handicap))
    conn.commit()

# Function to delete players by name
def delete_players(names):
    if not names:
        return
    placeholders = ','.join('?' for _ in names)
    cursor.execute(f'DELETE FROM players WHERE name IN ({placeholders})', names)
    conn.commit()

# Function to load all players from DB
def load_players():
    cursor.execute('SELECT * FROM players ORDER BY name')
    return pd.DataFrame(cursor.fetchall(), columns=['Name', 'Handicap'])

# Function to calculate Stableford points for a hole
def stableford_points(gross_score, par, strokes_received):
    net_score = gross_score - strokes_received
    if net_score > par + 1:
        return 0
    elif net_score == par + 1:
        return 1
    elif net_score == par:
        return 2
    elif net_score == par - 1:
        return 3
    elif net_score == par - 2:
        return 4
    else:
        return 5 + (par - net_score - 2)

# Function to calculate strokes received on a hole
def strokes_on_hole(handicap, stroke_index):
    full_strokes = handicap // 18
    remainder = handicap % 18
    if stroke_index <= remainder:
        return full_strokes + 1
    return full_strokes

# App layout with tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Course Setup", 
    "Manage Players", 
    "Assign to Competition", 
    "Enter Scores", 
    "Individual Leaderboard", 
    "Team Leaderboard", 
    "Player Details"
])

with tab1:
    st.header("Course Setup")
    if 'course' not in st.session_state:
        st.session_state.course = pd.DataFrame({
            'Hole': range(1, 19),
            'Par': [4] * 18,
            'Stroke Index': list(range(1, 19))
        })

    course_df = st.data_editor(
        st.session_state.course,
        num_rows="fixed",
        hide_index=True,
        column_config={
            "Hole": st.column_config.NumberColumn(disabled=True),
            "Par": st.column_config.NumberColumn(min_value=3, max_value=5),
            "Stroke Index": st.column_config.NumberColumn(min_value=1, max_value=18)
        }
    )
    st.session_state.course = course_df

with tab2:
    st.header("Manage Player Profiles")

    players_df = load_players()

    if players_df.empty:
        st.info("No players in database yet. Add one below.")
    else:
        st.subheader("Edit or Delete Players")

        # Add selection column for deletion
        edit_df = players_df.copy()
        edit_df['Delete?'] = False  # checkbox column

        # Editable data editor
        edited_df = st.data_editor(
            edit_df,
            num_rows="fixed",
            hide_index=True,
            column_config={
                "Name": st.column_config.TextColumn("Name", required=True),
                "Handicap": st.column_config.NumberColumn("Handicap", min_value=0, max_value=54, required=True),
                "Delete?": st.column_config.CheckboxColumn("Delete?", default=False)
            },
            key="player_editor",
            use_container_width=True
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save All Edits"):
                # Process updates (including name changes)
                for _, row in edited_df.iterrows():
                    original_name = players_df[players_df['Name'] == row['Name']]['Name']
                    # If name changed or new, but since name is PK we treat as update
                    save_player(row['Name'], int(row['Handicap']))
                st.success("Changes saved!")
                st.rerun()  # Refresh table

        with col2:
            selected_for_delete = edited_df[edited_df['Delete?'] == True]['Name'].tolist()
            if st.button("🗑️ Delete Selected", type="primary"):
                if selected_for_delete:
                    delete_players(selected_for_delete)
                    st.success(f"Deleted {len(selected_for_delete)} player(s)")
                    st.rerun()
                else:
                    st.warning("No players selected for deletion")

    # Add new player section (below the table)
    st.subheader("Add New Player")
    new_name = st.text_input("New Player Name", key="new_name")
    new_handicap = st.number_input("New Handicap", min_value=0, max_value=54, value=0, key="new_hc")
    
    if st.button("Add New Player"):
        if new_name.strip():
            save_player(new_name.strip(), new_handicap)
            st.success(f"Added {new_name}")
            st.rerun()
        else:
            st.error("Please enter a name")

with tab3:
    st.header("Assign Players to Competition")
    if 'golfers' not in st.session_state:
        st.session_state.golfers = []

    players_df = load_players()
    if not players_df.empty:
        selected_players = st.multiselect("Select Players from Database", players_df['Name'].tolist())
        team = st.text_input("Team Name (e.g., Team A)")

        if st.button("Add Selected to Competition"):
            for name in selected_players:
                hc = players_df[players_df['Name'] == name]['Handicap'].values[0]
                st.session_state.golfers.append({
                    'Name': name,
                    'Handicap': hc,
                    'Team': team
                })
            st.success(f"Added {len(selected_players)} players to competition")
    else:
        st.info("Add players in the Manage Players tab first.")

    # Option to add new player directly here
    st.subheader("Or Add New Player")
    new_name_comp = st.text_input("New Player Name", key="new_name_comp")
    new_hc_comp = st.number_input("New Handicap", min_value=0, max_value=54, value=0, key="new_hc_comp")
    new_team = st.text_input("New Team Name")
    if st.button("Add New and Save to DB"):
        if new_name_comp.strip():
            save_player(new_name_comp.strip(), new_hc_comp)
            st.session_state.golfers.append({
                'Name': new_name_comp.strip(),
                'Handicap': new_hc_comp,
                'Team': new_team
            })
            st.success(f"Added and saved {new_name_comp}")
            st.rerun()
        else:
            st.error("Enter a name")

    if st.session_state.golfers:
        st.subheader("Current Competition Golfers")
        st.table(pd.DataFrame(st.session_state.golfers))

# ────────────────────────────────────────────────
# The rest of your app (Enter Scores, Leaderboards, etc.) remains unchanged
# Paste your existing code for tabs 4–7 + compute_results() + Calculate button here
# ────────────────────────────────────────────────

# Example placeholder (replace with your full code from previous version)
with tab4:
    st.header("Enter Scores")
    st.info("Your score entry code goes here...")

# ... rest of tabs ...

if st.button("Reset Competition Data (Keeps Player DB)"):
    keys_to_reset = ['golfers', 'ind_df', 'team_df', 'player_details']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
