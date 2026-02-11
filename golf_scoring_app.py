import streamlit as st
import pandas as pd
import sqlite3
import json
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.set_page_config(layout="wide", page_title="Golf Rumble Scoring", initial_sidebar_state="collapsed")

hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ────────────────────────────────────────────────
# Database setup – now with courses table
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
        pars TEXT,          -- JSON list of 18 pars
        stroke_indices TEXT -- JSON list of 18 stroke indices
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

# ────────────────────────────────────────────────
# Tabs – added Manage Courses
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Course Setup", "Manage Courses", "Manage Players", "Competition Setup",
    "Enter Scores", "Individual Leaderboard", "Team Leaderboard", "Player Details"
])

# ────────────────────────────────────────────────
# Tab 1: Course Setup (load from saved or edit new)
# ────────────────────────────────────────────────
with tab1:
    st.header("Course Setup")

    course_names = load_all_course_names()

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_course = st.selectbox("Load saved course", ["New Course"] + course_names)
    with col2:
        if selected_course != "New Course" and st.button("Delete this course"):
            delete_course(selected_course)
            st.success(f"Deleted {selected_course}")
            st.rerun()

    default_course = pd.DataFrame({
        'Hole': range(1, 19),
        'Par': [4] * 18,
        'Stroke Index': list(range(1, 19))
    })

    if selected_course == "New Course":
        current_df = st.session_state.get('course', default_course.copy())
    else:
        loaded = load_course(selected_course)
        if loaded is not None:
            current_df = loaded
        else:
            current_df = default_course.copy()

    st.caption("Arrow keys to move • Enter to go down")

    gb = GridOptionsBuilder.from_dataframe(current_df)
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
        current_df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        height=680,
        fit_columns_on_grid_load=True,
        key="course_grid"
    )

    col_save, col_name = st.columns([3, 2])
    with col_save:
        if st.button("💾 Save Course", use_container_width=True):
            updated = pd.DataFrame(response['data'])
            st.session_state.course = updated
            st.success("Course saved (temporary – name it below to keep permanently)")

    with col_name:
        course_name = st.text_input("Course Name (to save permanently)", value=selected_course if selected_course != "New Course" else "")
        if st.button("Save as Named Course") and course_name.strip():
            save_course(course_name.strip(), updated['Par'].tolist(), updated['Stroke Index'].tolist())
            st.success(f"Saved as '{course_name}'")
            st.rerun()

# ────────────────────────────────────────────────
# Tab 2: Manage Courses
# ────────────────────────────────────────────────
with tab2:
    st.header("Manage Saved Courses")

    courses = load_all_course_names()
    if not courses:
        st.info("No saved courses yet")
    else:
        st.subheader("Saved Courses")
        for c in courses:
            col_name, col_del = st.columns([4, 1])
            col_name.write(c)
            if col_del.button("Delete", key=f"del_course_{c}"):
                delete_course(c)
                st.success(f"Deleted {c}")
                st.rerun()

# ────────────────────────────────────────────────
# Tab 3: Manage Players (unchanged from your last working version)
# ────────────────────────────────────────────────
with tab3:
    st.header("Manage Players")

    df_players = load_players()

    if df_players.empty:
        st.info("No players yet")
    else:
        st.subheader("Edit or Delete")
        edit_df = df_players.copy()
        edit_df['Delete'] = False

        edited = st.data_editor(
            edit_df,
            column_config={
                "Name": st.column_config.TextColumn(required=True),
                "Handicap": st.column_config.NumberColumn(min_value=0, max_value=54, required=True),
                "Delete": st.column_config.CheckboxColumn("Delete?", default=False)
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button("Save Changes"):
            for _, row in edited.iterrows():
                if not row['Delete']:
                    save_player(row['Name'], int(row['Handicap']))
            st.success("Saved")
            st.rerun()

        to_del = edited[edited['Delete']]['Name'].tolist()
        if st.button("Delete Selected") and to_del:
            delete_players(to_del)
            st.success(f"Deleted {len(to_del)} players")
            st.rerun()

    st.subheader("Add New")
    new_name = st.text_input("Name", key="player_name")
    new_hc = st.number_input("Handicap", 0, 54, 0, key="player_hc")
    if st.button("Add"):
        if new_name.strip():
            save_player(new_name.strip(), new_hc)
            st.success("Added")
            st.rerun()

# ────────────────────────────────────────────────
# Tab 4: Competition Setup (unchanged)
# ────────────────────────────────────────────────
with tab4:
    st.header("Competition Setup")

    if 'golfers' not in st.session_state:
        st.session_state.golfers = []

    players_db = load_players()

    st.subheader("Add Players")
    selected = st.multiselect("From database", players_db['Name'].tolist())
    team_input = st.text_input("Team name")
    if st.button("Add selected"):
        for name in selected:
            hc = players_db[players_db['Name'] == name]['Handicap'].values[0]
            st.session_state.golfers.append({
                'Name': name,
                'Handicap': hc,
                'Team': team_input,
                'scores': [0]*18
            })
        st.success("Added")
        st.rerun()

    if st.session_state.golfers:
        df_comp = pd.DataFrame(st.session_state.golfers)

        st.subheader("Current Players")

        edited_comp = st.data_editor(
            df_comp,
            column_config={
                "Name": st.column_config.TextColumn("Name", disabled=True),
                "Handicap": st.column_config.NumberColumn("Handicap", min_value=0, max_value=54),
                "Team": st.column_config.TextColumn("Team"),
            },
            hide_index=True,
            use_container_width=True,
            key="comp_editor"
        )

        if st.button("Save Team / Handicap Changes"):
            with st.popover("Confirm changes"):
                st.write("Are you sure?")
                col1, col2 = st.columns(2)
                if col1.button("Yes – Save"):
                    st.session_state.golfers = edited_comp.to_dict('records')
                    st.success("Changes saved")
                    st.rerun()
                if col2.button("Cancel"):
                    st.rerun()

        remove_names = st.multiselect("Remove players", df_comp['Name'].tolist(), key="remove_select")
        if st.button("Remove selected players"):
            st.session_state.golfers = [g for g in st.session_state.golfers if g['Name'] not in remove_names]
            st.success(f"Removed {len(remove_names)} player(s)")
            st.rerun()

# ────────────────────────────────────────────────
# Tab 5: Enter Scores with AgGrid
# ────────────────────────────────────────────────
with tab5:
    st.header("Enter Scores")

    if not st.session_state.get('golfers'):
        st.info("No players in competition")
    else:
        teams = {}
        for g in st.session_state.golfers:
            teams.setdefault(g['Team'], []).append(g)

        status_rows = []
        for t, ms in teams.items():
            r = {'Team': t}
            for m in ms:
                s = m.get('scores', [0]*18)
                r[m['Name']] = "✅" if all(x > 0 for x in s) else "⏳"
            status_rows.append(r)

        if status_rows:
            st.subheader("Entry Status")
            st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)

        for team, members in teams.items():
            if len(members) != 4:
                st.warning(f"Team {team} has {len(members)} players (expected 4)")
                continue

            st.subheader(f"Team {team}")

            names = [m['Name'] for m in members]
            data = {'Hole': list(range(1, 19))}
            for n in names:
                g = next(x for x in members if x['Name'] == n)
                data[n] = g.get('scores', [0]*18)

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
                key=f"scores_{team}"
            )

            if st.button(f"Save scores for {team}"):
                updated = pd.DataFrame(resp['data'])
                for n in names:
                    scores = updated[n].tolist()
                    for g in members:
                        if g['Name'] == n:
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
        st.warning("No course loaded")
        return None, None, {}

    course = st.session_state.course
    ind = []
    det = {}

    for g in st.session_state.golfers:
        if 'scores' not in g or not g['scores']:
            continue

        pts = []
        for h in range(18):
            gross = g['scores'][h]
            if gross <= 0:
                pts.append(0)
                continue
            par = course.iloc[h]['Par']
            si = course.iloc[h]['Stroke Index']
            strk = strokes_on_hole(g['Handicap'], si)
            pts.append(stableford_points(gross, par, strk))

        tot = sum(pts)
        b9 = sum(pts[9:18])
        b6 = sum(pts[12:18])
        b3 = sum(pts[15:18])
        b1 = pts[17]

        ind.append({
            'Name': g['Name'],
            'Team': g['Team'],
            'Total Points': tot,
            'Back 9': b9,
            'Back 6': b6,
            'Back 3': b3,
            'Back 1': b1
        })

        det[g['Name']] = {
            'Points per Hole': pts,
            'Breakdowns': {'Total': tot, 'Back 9': b9, 'Back 6': b6, 'Back 3': b3, 'Back 1': b1},
            'course': course.to_dict('records')  # for scorecard
        }

    if not ind:
        return None, None, {}

    ind_df = pd.DataFrame(ind).sort_values(
        ['Total Points', 'Back 9', 'Back 6', 'Back 3', 'Back 1'],
        ascending=[False]*5
    )

    # Team Irish Rumble
    team_dict = {}
    for g in st.session_state.golfers:
        if 'scores' not in g:
            continue
        t = g['Team']
        team_dict.setdefault(t, []).append({
            'points': [stableford_points(g['scores'][h], course.iloc[h]['Par'], strokes_on_hole(g['Handicap'], course.iloc[h]['Stroke Index']))
                       for h in range(18)],
            'name': g['Name']
        })

    team_res = []
    for t, players in team_dict.items():
        if len(players) < 4:
            continue

        tpts = []
        for h in range(18):
            hole_scores = sorted([p['points'][h] for p in players], reverse=True)
            if h < 6:
                tpts.append(hole_scores[0])
            elif h < 12:
                tpts.append(sum(hole_scores[:2]))
            elif h == 17:  # hole 18
                tpts.append(sum(hole_scores[:4]))  # all 4
            else:
                tpts.append(sum(hole_scores[:3]))

        tot = sum(tpts)
        team_res.append({
            'Team': t,
            'Players': ", ".join([p['name'] for p in players]),
            'Total Points': tot,
            'Back 9': sum(tpts[9:18]),
            'Back 6': sum(tpts[12:18]),
            'Back 3': sum(tpts[15:18]),
            'Back 1': tpts[17]
        })

    team_df = pd.DataFrame(team_res).sort_values(
        ['Total Points', 'Back 9', 'Back 6', 'Back 3', 'Back 1'],
        ascending=[False]*5
    ) if team_res else None

    return ind_df, team_df, det

# ────────────────────────────────────────────────
# Leaderboards
# ────────────────────────────────────────────────
with tab6:
    st.header("Individual Leaderboard")
    if st.button("Calculate / Refresh Results", type="primary"):
        st.session_state.ind_df, st.session_state.team_df, st.session_state.details = compute_results()
        st.success("Results updated")
    if 'ind_df' in st.session_state and st.session_state.ind_df is not None:
        st.dataframe(st.session_state.ind_df, use_container_width=True, hide_index=True)
    else:
        st.info("Enter scores and calculate")

with tab7:
    st.header("Team Leaderboard (Irish Rumble)")
    if 'team_df' in st.session_state and st.session_state.team_df is not None:
        st.dataframe(st.session_state.team_df, use_container_width=True, hide_index=True)
    else:
        st.info("Calculate results above")

with tab8:
    st.header("Player Details")
    if 'details' in st.session_state and st.session_state.details:
        player = st.selectbox("Select player", list(st.session_state.details.keys()))
        if player:
            d = st.session_state.details[player]

            st.subheader("Full Scorecard")

            course_data = d.get('course', [])
            if not course_data:
                st.warning("No course data available")
            else:
                scorecard = []
                gross_total = 0
                net_total = 0
                points_total = 0

                for h in range(18):
                    gross = st.session_state.golfers[[g['Name'] for g in st.session_state.golfers].index(player)]['scores'][h] if player in [g['Name'] for g in st.session_state.golfers] else 0
                    par = course_data[h]['Par']
                    si = course_data[h]['Stroke Index']
                    strokes = strokes_on_hole(st.session_state.golfers[[g['Name'] for g in st.session_state.golfers].index(player)]['Handicap'], si) if player in [g['Name'] for g in st.session_state.golfers] else 0
                    net = gross - strokes
                    points = d['Points per Hole'][h]

                    scorecard.append({
                        'Hole': h+1,
                        'Par': par,
                        'Stroke Index': si,
                        'Gross': gross,
                        'Strokes': strokes,
                        'Net': net,
                        'Stableford': points
                    })

                    gross_total += gross
                    net_total += net
                    points_total += points

                df_score = pd.DataFrame(scorecard)

                # Totals row
                totals = pd.DataFrame([{
                    'Hole': 'TOTAL',
                    'Par': df_score['Par'].sum(),
                    'Stroke Index': '-',
                    'Gross': gross_total,
                    'Strokes': '-',
                    'Net': net_total,
                    'Stableford': points_total
                }])

                full_scorecard = pd.concat([df_score, totals], ignore_index=True)
                st.dataframe(full_scorecard, use_container_width=True, hide_index=True)

            st.subheader("Points Breakdown")
            st.dataframe(pd.Series(d['Breakdowns']).to_frame('Points'))
    else:
        st.info("Calculate results first")

# Reset
if st.button("Reset Competition (keeps DB)"):
    for k in ['golfers', 'ind_df', 'team_df', 'details', 'course']:
        st.session_state.pop(k, None)
    st.rerun()
