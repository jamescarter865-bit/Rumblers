import streamlit as st
import pandas as pd
import sqlite3
import json
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
# Database setup – players + courses
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
# Tabs – reordered per request
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Manage Players", "Manage Courses", "Competition Setup",
    "Enter Scores", "Individual Leaderboard", "Team Leaderboard", "Player Details"
])

# ────────────────────────────────────────────────
# Tab 1: Manage Players
# ────────────────────────────────────────────────
with tab1:
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
            width="stretch"
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
    new_name = st.text_input("Name")
    new_hc = st.number_input("Handicap", 0, 54, 0)
    if st.button("Add"):
        if new_name.strip():
            save_player(new_name.strip(), new_hc)
            st.success("Added")
            st.rerun()

# ────────────────────────────────────────────────
# Tab 2: Manage Courses – create, edit, delete
# ────────────────────────────────────────────────
with tab2:
    st.header("Manage Courses")

    courses = load_all_course_names()
    if not courses:
        st.info("No saved courses yet – create one below")
    else:
        st.subheader("Saved Courses")
        for c in courses:
            col1, col2 = st.columns([4, 1])
            col1.write(c)
            if col2.button("Delete", key=f"del_{c}"):
                delete_course(c)
                st.success(f"Deleted {c}")
                st.rerun()

    st.subheader("Create or Edit Course")

    selected_edit_course = st.selectbox("Edit existing course", ["New Course"] + courses, key="edit_course_select")

    if selected_edit_course != "New Course":
        loaded = load_course(selected_edit_course)
        if loaded is not None:
            pars = loaded['Par'].tolist()
            sis = loaded['Stroke Index'].tolist()
        else:
            pars = [4] * 18
            sis = list(range(1, 19))
    else:
        pars = [4] * 18
        sis = list(range(1, 19))

    course_name = st.text_input("Course Name", value=selected_edit_course if selected_edit_course != "New Course" else "")

    st.subheader("Enter Pars and Stroke Indices")

    pars_new = []
    sis_new = []

    col_par, col_si = st.columns(2)
    with col_par:
        st.subheader("Par")
        for h in range(1, 19):
            p = st.number_input(f"Hole {h} Par", min_value=3, max_value=5, value=pars[h-1], key=f"par_{h}_{selected_edit_course}")
            pars_new.append(p)

    with col_si:
        st.subheader("Stroke Index")
        for h in range(1, 19):
            s = st.number_input(f"Hole {h} SI", min_value=1, max_value=18, value=sis[h-1], key=f"si_{h}_{selected_edit_course}")
            sis_new.append(s)

    if st.button("Save Course"):
        if not course_name.strip():
            st.error("Enter a course name")
        else:
            if course_name in courses:
                with st.popover("Confirm overwrite"):
                    st.write(f"Overwrite '{course_name}'?")
                    if st.button("Yes"):
                        save_course(course_name.strip(), pars_new, sis_new)
                        st.success(f"Course '{course_name}' overwritten")
                        st.rerun()
            else:
                save_course(course_name.strip(), pars_new, sis_new)
                st.success(f"Course '{course_name}' saved")
                st.rerun()

# ────────────────────────────────────────────────
# Tab 3: Competition Setup – select course
# ────────────────────────────────────────────────
with tab3:
    st.header("Competition Setup")

    courses = load_all_course_names()
    if not courses:
        st.warning("No courses saved. Create one in Manage Courses tab")
    else:
        selected_course = st.selectbox("Select Course for Competition", courses)
        if st.button("Load Selected Course"):
            loaded = load_course(selected_course)
            if loaded is not None:
                st.session_state.course = loaded
                st.success(f"Course '{selected_course}' loaded")

    if 'course' not in st.session_state:
        st.info("Load a course to continue")

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
            width="stretch",
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
# Tab 4: Enter Scores
# ────────────────────────────────────────────────
with tab4:
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
            st.dataframe(pd.DataFrame(status_rows), width="stretch", hide_index=True)

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
# Tab 5: Individual Leaderboard
# ────────────────────────────────────────────────
with tab5:
    st.header("Individual Leaderboard")
    if st.button("Calculate / Refresh Results", type="primary"):
        st.session_state.ind_df, st.session_state.team_df, st.session_state.details = compute_results()
        st.success("Results updated")
    if 'ind_df' in st.session_state and st.session_state.ind_df is not None:
        st.dataframe(st.session_state.ind_df, width="stretch", hide_index=True)
    else:
        st.info("Enter scores and calculate")

# ────────────────────────────────────────────────
# Tab 6: Team Leaderboard
# ────────────────────────────────────────────────
with tab6:
    st.header("Team Leaderboard (Irish Rumble)")
    if 'team_df' in st.session_state and st.session_state.team_df is not None:
        st.dataframe(st.session_state.team_df, width="stretch", hide_index=True)
    else:
        st.info("Calculate results above")

# ────────────────────────────────────────────────
# Tab 7: Player Details
# ────────────────────────────────────────────────
with tab7:
    st.header("Player Details & Full Scorecard")

    if 'details' in st.session_state and st.session_state.details:
        player = st.selectbox("Select player", list(st.session_state.details.keys()))

        if player:
            d = st.session_state.details[player]

            # Full Scorecard
            st.subheader("Full Scorecard")

            course_data = d.get('course', [])
            gross_scores = d.get('gross_scores', [0]*18)
            handicap = d.get('handicap', 0)

            if not course_data:
                st.warning("No course data available")
            else:
                scorecard = []
                gross_total = net_total = points_total = 0

                for h in range(18):
                    gross = gross_scores[h]
                    par = course_data[h]['Par']
                    si = course_data[h]['Stroke Index']
                    strokes = strokes_on_hole(handicap, si)
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

                totals_row = pd.DataFrame([{
                    'Hole': 'TOTAL',
                    'Par': df_score['Par'].sum(),
                    'Stroke Index': '—',
                    'Gross': gross_total,
                    'Strokes': '—',
                    'Net': net_total,
                    'Stableford': points_total
                }])

                full_scorecard = pd.concat([df_score, totals_row], ignore_index=True)
                st.dataframe(full_scorecard, width="stretch", hide_index=True)

            # Breakdowns
            st.subheader("Points Breakdown")
            st.dataframe(pd.Series(d['Breakdowns']).to_frame('Points'), width="stretch")
    else:
        st.info("Calculate results first")

# Reset
if st.button("Reset Competition (keeps database)"):
    for k in ['golfers', 'ind_df', 'team_df', 'details', 'course', 'course_temp', 'selected_course']:
        st.session_state.pop(k, None)
    st.rerun()
