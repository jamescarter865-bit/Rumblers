import streamlit as st
import pandas as pd
import sqlite3
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

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

# ────────────────────────────────────────────────
# Scoring functions
# ────────────────────────────────────────────────
def stableford_points(gross_score, par, strokes_received):
    net_score = gross_score - strokes_received
    if net_score > par + 1: return 0
    elif net_score == par + 1: return 1
    elif net_score == par: return 2
    elif net_score == par - 1: return 3
    elif net_score == par - 2: return 4
    else: return 5 + (par - net_score - 2)

def strokes_on_hole(handicap, stroke_index):
    full_strokes = handicap // 18
    remainder = handicap % 18
    return full_strokes + 1 if stroke_index <= remainder else full_strokes

# ────────────────────────────────────────────────
# Tabs
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Course Setup", "Manage Players", "Assign to Competition",
    "Enter Scores", "Individual Leaderboard", "Team Leaderboard", "Player Details"
])

# ────────────────────────────────────────────────
# Tab 1: Course Setup with AgGrid
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
    st.caption("Arrow keys to move • Enter to confirm and go down")

    gb = GridOptionsBuilder.from_dataframe(course_df)
    gb.configure_default_column(editable=True, minWidth=90)
    gb.configure_column("Hole", editable=False, width=80)
    gb.configure_column("Par", type="number", width=100)
    gb.configure_column("Stroke Index", type="number", width=120)
    gb.configure_grid_options(
        enterNavigatesVerticallyAfterEdit=True,
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
        key="course_aggrid"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Course Setup", use_container_width=True):
            st.session_state.course = pd.DataFrame(response['data'])
            st.success("Course saved!")
            st.rerun()

    with col2:
        if st.button("Reset to Default", use_container_width=True):
            st.session_state.course = default_course.copy()
            st.success("Reset to defaults.")
            st.rerun()

# ────────────────────────────────────────────────
# Tab 2: Manage Players
# ────────────────────────────────────────────────
with tab2:
    st.header("Manage Player Profiles")

    players_df = load_players()

    if players_df.empty:
        st.info("No players yet. Add below.")
    else:
        st.subheader("Edit / Delete")
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
                st.success("Saved!")
                st.rerun()

        with col2:
            to_delete = edited_df[edited_df['Delete?']]['Name'].tolist()
            if st.button("🗑️ Delete Selected", type="primary"):
                if to_delete:
                    delete_players(to_delete)
                    st.success(f"Deleted {len(to_delete)} players")
                    st.rerun()
                else:
                    st.warning("None selected")

    st.subheader("Add New Player")
    new_name = st.text_input("Name", key="new_name")
    new_hc = st.number_input("Handicap", 0, 54, 0, key="new_hc")
    if st.button("Add Player"):
        if new_name.strip():
            save_player(new_name.strip(), new_hc)
            st.success(f"Added {new_name}")
            st.rerun()
        else:
            st.error("Enter name")

# ────────────────────────────────────────────────
# Tab 3: Assign to Competition
# ────────────────────────────────────────────────
with tab3:
    st.header("Assign Players to Competition")
    if 'golfers' not in st.session_state:
        st.session_state.golfers = []

    players_df = load_players()
    if not players_df.empty:
        selected = st.multiselect("Select from database", players_df['Name'].tolist())
        team_name = st.text_input("Team Name")
        if st.button("Add Selected"):
            for name in selected:
                hc = players_df[players_df['Name'] == name]['Handicap'].values[0]
                st.session_state.golfers.append({
                    'Name': name, 'Handicap': hc, 'Team': team_name, 'scores': [0]*18
                })
            st.success(f"Added {len(selected)} players")
            st.rerun()

    st.subheader("Add New")
    nn = st.text_input("New Name", key="nn_comp")
    nh = st.number_input("Handicap", 0, 54, 0, key="nh_comp")
    nt = st.text_input("Team")
    if st.button("Add & Save"):
        if nn.strip():
            save_player(nn.strip(), nh)
            st.session_state.golfers.append({
                'Name': nn.strip(), 'Handicap': nh, 'Team': nt, 'scores': [0]*18
            })
            st.success(f"Added {nn}")
            st.rerun()

    if st.session_state.golfers:
        st.subheader("Current Players")
        st.table(pd.DataFrame(st.session_state.golfers).drop(columns=['scores']))

# ────────────────────────────────────────────────
# Tab 4: Enter Scores with AgGrid
# ────────────────────────────────────────────────
with tab4:
    st.header("Enter Scores – Fast Entry")

    if not st.session_state.get('golfers'):
        st.info("Assign players first.")
    else:
        teams = {}
        for g in st.session_state.golfers:
            teams.setdefault(g['Team'], []).append(g)

        # Status
        status_rows = []
        for team, members in teams.items():
            row = {'Team': team}
            for m in members:
                s = m.get('scores', [0]*18)
                row[m['Name']] = "✅" if all(x > 0 for x in s) else "⏳"
            status_rows.append(row)

        if status_rows:
            st.subheader("Status")
            st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)

        for team, members in teams.items():
            if len(members) != 4:
                st.warning(f"Team {team} needs 4 players.")
                continue

            st.subheader(f"Team {team}")

            names = [m['Name'] for m in members]
            data = {'Hole': list(range(1, 19))}
            for name in names:
                g = next(x for x in members if x['Name'] == name)
                data[name] = g.get('scores', [0]*18)

            df = pd.DataFrame(data)

            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_default_column(editable=True, minWidth=100)
            gb.configure_column("Hole", editable=False, width=80)
            for n in names:
                gb.configure_column(n, type="number", width=110)

            gb.configure_grid_options(
                enterNavigatesVerticallyAfterEdit=True,
                suppressRowClickSelection=True,
                domLayout='autoHeight',
                rowHeight=40
            )
            grid_options = gb.build()

            resp = AgGrid(
                df,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.AS_INPUT,
                update_mode=GridUpdateMode.VALUE_CHANGED,
                height=680,
                fit_columns_on_grid_load=True,
                key=f"aggrid_scores_{team}"
            )

            if st.button(f"Save Scores – {team}", use_container_width=True):
                updated = pd.DataFrame(resp['data'])
                for name in names:
                    scores = updated[name].tolist()
                    for g in members:
                        if g['Name'] == name:
                            g['scores'] = scores
                            break
                st.success(f"Saved {team}")
                st.rerun()

            st.markdown("---")

# ────────────────────────────────────────────────
# Calculation function
# ────────────────────────────────────────────────
def compute_results():
    if 'course' not in st.session_state:
        st.warning("No course loaded.")
        return None, None, {}

    course = st.session_state.course
    ind_results = []
    details = {}

    for golfer in st.session_state.golfers:
        if 'scores' not in golfer or not golfer['scores']:
            continue

        points = []
        for h in range(18):
            gross = golfer['scores'][h]
            if gross <= 0:
                pts = 0
            else:
                par = course.iloc[h]['Par']
                si = course.iloc[h]['Stroke Index']
                strokes = strokes_on_hole(golfer['Handicap'], si)
                pts = stableford_points(gross, par, strokes)
            points.append(pts)

        total = sum(points)
        front9 = sum(points[0:9])
        back9 = sum(points[9:18])
        back6 = sum(points[12:18])
        back3 = sum(points[15:18])
        back1 = points[17]

        ind_results.append({
            'Name': golfer['Name'],
            'Team': golfer['Team'],
            'Total Points': total,
            'Front 9': front9,
            'Back 9': back9,
            'Back 6': back6,
            'Back 3': back3,
            'Back 1': back1
        })

        details[golfer['Name']] = {
            'Points per Hole': points,
            'Breakdowns': {
                'Total': total,
                'Front 9': front9,
                'Back 9': back9,
                'Back 6': back6,
                'Back 3': back3,
                'Last Hole': back1
            }
        }

    if not ind_results:
        return None, None, {}

    ind_df = pd.DataFrame(ind_results).sort_values(
        ['Total Points', 'Back 9', 'Back 6', 'Back 3', 'Back 1'],
        ascending=[False] * 5
    )

    # Team Irish Rumble
    teams_dict = {}
    for g in st.session_state.golfers:
        if 'scores' not in g:
            continue
        t = g['Team']
        teams_dict.setdefault(t, []).append(
            [stableford_points(g['scores'][h], course.iloc[h]['Par'], strokes_on_hole(g['Handicap'], course.iloc[h]['Stroke Index']))
             for h in range(18)]
        )

    team_results = []
    for team, players_points in teams_dict.items():
        if len(players_points) < 4:
            continue

        team_pts = []
        for h in range(18):
            hole_scores = sorted([p[h] for p in players_points], reverse=True)
            if h < 6:
                team_pts.append(hole_scores[0])
            elif h < 12:
                team_pts.append(sum(hole_scores[:2]))
            elif h < 17:
                team_pts.append(sum(hole_scores[:3]))
            else:
                team_pts.append(sum(hole_scores[:4]))

        total = sum(team_pts)
        team_results.append({
            'Team': team,
            'Total Points': total,
            'Front 9': sum(team_pts[0:9]),
            'Back 9': sum(team_pts[9:18]),
            'Back 6': sum(team_pts[12:18]),
            'Back 3': sum(team_pts[15:18]),
            'Back 1': team_pts[17]
        })

    team_df = pd.DataFrame(team_results).sort_values(
        ['Total Points', 'Back 9', 'Back 6', 'Back 3', 'Back 1'],
        ascending=[False] * 5
    ) if team_results else None

    return ind_df, team_df, details

# ────────────────────────────────────────────────
# Tab 5: Individual Leaderboard
# ────────────────────────────────────────────────
with tab5:
    st.header("Individual Stableford Leaderboard")

    if st.button("Calculate / Refresh Results", type="primary", use_container_width=True):
        st.session_state.ind_df, st.session_state.team_df, st.session_state.player_details = compute_results()
        st.success("Results calculated!")

    if 'ind_df' in st.session_state and st.session_state.ind_df is not None:
        st.dataframe(st.session_state.ind_df, use_container_width=True, hide_index=True)
    else:
        st.info("Click 'Calculate / Refresh Results' after entering scores.")

# ────────────────────────────────────────────────
# Tab 6: Team Leaderboard
# ────────────────────────────────────────────────
with tab6:
    st.header("Team Irish Rumble Leaderboard")

    if 'team_df' in st.session_state and st.session_state.team_df is not None:
        st.dataframe(st.session_state.team_df, use_container_width=True, hide_index=True)
    else:
        st.info("Calculate results above.")

# ────────────────────────────────────────────────
# Tab 7: Player Details
# ────────────────────────────────────────────────
with tab7:
    st.header("Player Details")

    if 'player_details' in st.session_state and st.session_state.player_details:
        player = st.selectbox("Select Player", list(st.session_state.player_details.keys()))

        if player:
            d = st.session_state.player_details[player]

            st.subheader("Points per Hole")
            hole_df = pd.DataFrame({
                'Hole': range(1, 19),
                'Points': d['Points per Hole']
            })
            st.dataframe(hole_df, use_container_width=True, hide_index=True)

            st.subheader("Breakdowns")
            breakdown = pd.Series(d['Breakdowns']).to_frame('Points')
            st.dataframe(breakdown, use_container_width=True)
    else:
        st.info("Calculate results first.")

# ────────────────────────────────────────────────
# Reset
# ────────────────────────────────────────────────
if st.button("Reset Competition (keeps players DB)"):
    for k in ['golfers', 'ind_df', 'team_df', 'player_details']:
        st.session_state.pop(k, None)
    st.rerun()
