import streamlit as st
import pandas as pd
import sqlite3
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

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

# ────────────────────────────────────────────────
# Database setup (SQLite for persistent player profiles)
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
conn.commit()

def save_player(name, handicap):
    cursor.execute('''
        INSERT OR REPLACE INTO players (name, handicap)
        VALUES (?, ?)
    ''', (name, handicap))
    conn.commit()

def delete_players(names):
    if not names:
        return
    placeholders = ','.join('?' for _ in names)
    cursor.execute(f'DELETE FROM players WHERE name IN ({placeholders})', names)
    conn.commit()

def load_players():
    cursor.execute('SELECT * FROM players ORDER BY name')
    return pd.DataFrame(cursor.fetchall(), columns=['Name', 'Handicap'])

# ────────────────────────────────────────────────
# Stableford functions (unchanged)
# ────────────────────────────────────────────────
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

def strokes_on_hole(handicap, stroke_index):
    full_strokes = handicap // 18
    remainder = handicap % 18
    if stroke_index <= remainder:
        return full_strokes + 1
    return full_strokes

# ────────────────────────────────────────────────
# Tabs
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Course Setup", "Manage Players", "Assign to Competition",
    "Enter Scores", "Individual Leaderboard", "Team Leaderboard", "Player Details"
])

# ────────────────────────────────────────────────
# Course Setup – with AgGrid for fast keyboard navigation
# ────────────────────────────────────────────────
with tab1:
    st.header("Course Setup")

    default_course = pd.DataFrame({
        'Hole': range(1, 19),
        'Par': [4] * 18,
        'Stroke Index': list(range(1, 19))
    })

    if 'course' not in st.session_state:
        st.session_state.course = default_course.copy()

    course_df = st.session_state.course.copy()

    st.subheader("Edit pars and stroke indices")
    st.caption("Use arrow keys to move, Enter to confirm and move down")

    # AgGrid configuration
    gb = GridOptionsBuilder.from_dataframe(course_df)
    gb.configure_default_column(editable=True, minWidth=90)
    gb.configure_column("Hole", editable=False, width=80)
    gb.configure_column("Par", type="number", width=100)
    gb.configure_column("Stroke Index", type="number", width=120)

    gb.configure_grid_options(
        enterNavigatesVerticallyAfterEdit=True,  # Enter moves down
        suppressRowClickSelection=True,
        domLayout='autoHeight',
        rowHeight=40
    )

    grid_options = gb.build()

    response = AgGrid(
        course_df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        height=680,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        key="course_aggrid"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Course Setup", use_container_width=True):
            updated_df = pd.DataFrame(response['data'])
            st.session_state.course = updated_df
            st.success("Course saved!")
            st.rerun()

    with col2:
        if st.button("Reset to Default Course", use_container_width=True):
            st.session_state.course = default_course.copy()
            st.success("Course reset to defaults.")
            st.rerun()

# ────────────────────────────────────────────────
# Manage Players (your previous version – insert here)
# ────────────────────────────────────────────────
with tab2:
    st.header("Manage Player Profiles")

    players_df = load_players()

    if players_df.empty:
        st.info("No players in database yet. Add one below.")
    else:
        st.subheader("Edit or Delete Players")

        edit_df = players_df.copy()
        edit_df['Delete?'] = False

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
                for _, row in edited_df.iterrows():
                    if not row['Delete?']:
                        save_player(row['Name'], int(row['Handicap']))
                st.success("Changes saved!")
                st.rerun()

        with col2:
            selected_for_delete = edited_df[edited_df['Delete?'] == True]['Name'].tolist()
            if st.button("🗑️ Delete Selected", type="primary"):
                if selected_for_delete:
                    delete_players(selected_for_delete)
                    st.success(f"Deleted {len(selected_for_delete)} player(s)")
                    st.rerun()
                else:
                    st.warning("No players selected")

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

# ────────────────────────────────────────────────
# Assign to Competition (your previous version – insert here)
# ────────────────────────────────────────────────
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
                    'Team': team,
                    'scores': [0] * 18
                })
            st.success(f"Added {len(selected_players)} players")
            st.rerun()

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
                'Team': new_team,
                'scores': [0] * 18
            })
            st.success(f"Added and saved {new_name_comp}")
            st.rerun()
        else:
            st.error("Enter a name")

    if st.session_state.golfers:
        st.subheader("Current Competition Golfers")
        st.table(pd.DataFrame(st.session_state.golfers).drop(columns=['scores']))

# ────────────────────────────────────────────────
# Enter Scores – with AgGrid for fast keyboard navigation
# ────────────────────────────────────────────────
with tab4:
    st.header("Enter Scores – Fast Entry")

    if 'golfers' not in st.session_state or not st.session_state.golfers:
        st.info("Assign players to the competition first.")
    else:
        teams = {}
        for golfer in st.session_state.golfers:
            team = golfer['Team']
            if team not in teams:
                teams[team] = []
            teams[team].append(golfer)

        # Status
        status_data = []
        for team_name, members in teams.items():
            row = {'Team': team_name}
            for m in members:
                scores = m.get('scores', [0]*18)
                row[m['Name']] = "✅" if all(s > 0 for s in scores) else "⏳"
            status_data.append(row)

        if status_data:
            st.subheader("Entry Status")
            st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)

        for team_name, members in teams.items():
            if len(members) != 4:
                st.warning(f"Team {team_name}: needs exactly 4 players for group entry.")
                continue

            st.subheader(f"Team {team_name}")

            player_names = [m['Name'] for m in members]

            data = {'Hole': list(range(1, 19))}
            for name in player_names:
                golfer = next(g for g in members if g['Name'] == name)
                data[name] = golfer.get('scores', [0]*18)

            df = pd.DataFrame(data)

            # AgGrid config
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_default_column(editable=True, minWidth=100)
            gb.configure_column("Hole", editable=False, width=80)
            for name in player_names:
                gb.configure_column(name, type="number", width=110)

            gb.configure_grid_options(
                enterNavigatesVerticallyAfterEdit=True,
                suppressRowClickSelection=True,
                domLayout='autoHeight',
                rowHeight=40
            )

            grid_options = gb.build()

            response = AgGrid(
                df,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.AS_INPUT,
                update_mode=GridUpdateMode.VALUE_CHANGED,
                height=680,
                fit_columns_on_grid_load=True,
                key=f"scores_aggrid_{team_name}"
            )

            if st.button(f"💾 Save Scores for {team_name}", use_container_width=True):
                updated_df = pd.DataFrame(response['data'])
                for name in player_names:
                    scores_list = updated_df[name].tolist()
                    for golfer in members:
                        if golfer['Name'] == name:
                            golfer['scores'] = scores_list
                            break
                st.success(f"Scores saved for {team_name}")
                st.rerun()

            st.markdown("---")

# ────────────────────────────────────────────────
# Leaderboards and Player Details (keep your previous code here)
# ────────────────────────────────────────────────
# Insert your compute_results() function, Calculate Results button,
# and tab5, tab6, tab7 code from earlier versions here

# Example placeholder:
with tab5:
    st.header("Individual Leaderboard")
    st.info("Your leaderboard code here...")

# ... rest of tabs ...

# Reset competition
if st.button("Reset Competition Data (Keeps Player DB)"):
    for key in ['golfers', 'ind_df', 'team_df', 'player_details']:
        st.session_state.pop(key, None)
    st.rerun()
