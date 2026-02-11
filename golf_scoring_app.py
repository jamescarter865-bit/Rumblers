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
    if net_score > par + 1:  # Net double bogey or worse
        return 0
    elif net_score == par + 1:  # Net bogey
        return 1
    elif net_score == par:  # Net par
        return 2
    elif net_score == par - 1:  # Net birdie
        return 3
    elif net_score == par - 2:  # Net eagle
        return 4
    else:  # Better (albatross, etc.)
        return 5 + (par - net_score - 2)  # General formula

# Function to calculate strokes received on a hole
def strokes_on_hole(handicap, stroke_index):
    # Full handicap strokes: extra strokes per hole based on SI
    full_strokes = handicap // 18
    remainder = handicap % 18
    if stroke_index <= remainder:
        return full_strokes + 1
    return full_strokes

# App layout with tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Course Setup", "Manage Players", "Assign to Competition", "Enter Scores", "Individual Leaderboard", "Team Leaderboard", "Player Details"])

with tab1:
    st.header("Course Setup")
    if 'course' not in st.session_state:
        st.session_state.course = pd.DataFrame({
            'Hole': range(1, 19),
            'Par': [4] * 18,  # Default pars
            'Stroke Index': list(range(1, 19))  # Default SIs (edit as needed)
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
                    if not row['Delete?']:  # Only save non-deleted
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
                    'Team': team,
                    'scores': [0] * 18  # Initialize scores
                })
            st.success(f"Added {len(selected_players)} players to competition")
            st.rerun()

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

with tab4:
    st.header("Enter Scores")

    if 'golfers' not in st.session_state or not st.session_state.golfers:
        st.info("Assign players to the competition first in the Assign tab.")
    else:
        # Group golfers by team
        teams = {}
        for golfer in st.session_state.golfers:
            team = golfer['Team']
            if team not in teams:
                teams[team] = []
            teams[team].append(golfer)

        # Status table
        status_data = []
        for team_name, members in teams.items():
            team_status = {'Team': team_name}
            for member in members:
                scores_entered = all(s > 0 for s in member['scores'])
                status = "Entered" if scores_entered else "Outstanding"
                team_status[member['Name']] = status
            status_data.append(team_status)

        if status_data:
            st.subheader("Score Entry Status")
            st.table(pd.DataFrame(status_data))

        # Score entry per team
        for team_name, members in teams.items():
            if len(members) != 4:
                st.warning(f"Team {team_name} does not have exactly 4 players. Skipping group entry.")
                continue

            st.subheader(f"Scores for Team {team_name}")

            # Create DF with holes as rows, players as columns
            player_names = [m['Name'] for m in members]
            score_data = {
                'Hole': range(1, 19)
            }
            for i, member in enumerate(members):
                score_data[player_names[i]] = member['scores']

            scores_df = pd.DataFrame(score_data)

            # Editable table - Enter moves down (built-in to data_editor)
            edited_scores = st.data_editor(
                scores_df,
                num_rows="fixed",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Hole": st.column_config.NumberColumn(disabled=True),
                    **{name: st.column_config.NumberColumn(name, min_value=0, step=1) for name in player_names}
                },
                key=f"scores_editor_{team_name}"
            )

            # Save back to session
            for i, name in enumerate(player_names):
                for golfer in members:
                    if golfer['Name'] == name:
                        golfer['scores'] = edited_scores[name].tolist()
                        break

# Compute results function (same as before)
def compute_results():
    course_df = st.session_state.course
    individual_results = []
    player_details = {}
    for golfer in st.session_state.golfers:
        if 'scores' not in golfer:
            continue
        points = []
        for hole in range(18):
            gross = golfer['scores'][hole]
            if gross == 0:
                pts = 0
            else:
                par = course_df.iloc[hole]['Par']
                si = course_df.iloc[hole]['Stroke Index']
                strokes = strokes_on_hole(golfer['Handicap'], si)
                pts = stableford_points(gross, par, strokes)
            points.append(pts)
        
        total = sum(points)
        front9 = sum(points[0:9])
        back9 = sum(points[9:18])
        back6 = sum(points[12:18])
        back3 = sum(points[15:18])
        back1 = points[17] if len(points) > 17 else 0
        
        individual_results.append({
            'Name': golfer['Name'],
            'Team': golfer['Team'],
            'Total Points': total,
            'Front 9': front9,
            'Back 9': back9,
            'Back 6': back6,
            'Back 3': back3,
            'Back 1': back1
        })
        
        # Store details for separate sheet
        player_details[golfer['Name']] = {
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
    
    # Sort individual leaderboard with tiebreakers
    if individual_results:
        ind_df = pd.DataFrame(individual_results).sort_values(
            ['Total Points', 'Back 9', 'Back 6', 'Back 3', 'Back 1'],
            ascending=[False, False, False, False, False]
        )
    else:
        ind_df = None
    
    # Compute team Irish Rumble (with all 4 on 18th)
    teams = {}
    for golfer in st.session_state.golfers:
        if 'scores' not in golfer:
            continue
        team_name = golfer['Team']
        if team_name not in teams:
            teams[team_name] = []
        # Compute per-hole Stableford points for this golfer
        golfer_points = []
        for hole in range(18):
            gross = golfer['scores'][hole]
            if gross == 0:
                pts = 0
            else:
                par = course_df.iloc[hole]['Par']
                si = course_df.iloc[hole]['Stroke Index']
                strokes = strokes_on_hole(golfer['Handicap'], si)
                pts = stableford_points(gross, par, strokes)
            golfer_points.append(pts)
        teams[team_name].append(golfer_points)
    
    team_results = []
    for team_name, members_points in teams.items():
        if len(members_points) < 4:
            st.warning(f"Team {team_name} has fewer than 4 players—skipping.")
            continue
        team_points = []
        for hole in range(18):
            hole_points = sorted([mp[hole] for mp in members_points], reverse=True)
            if hole < 6:  # Holes 1-6: best 1
                team_points.append(hole_points[0])
            elif hole < 12:  # 7-12: best 2
                team_points.append(sum(hole_points[:2]))
            elif hole < 17:  # 13-17: best 3
                team_points.append(sum(hole_points[:3]))
            else:  # Hole 18: all 4
                team_points.append(sum(hole_points[:4]))
        
        total = sum(team_points)
        front9 = sum(team_points[0:9])
        back9 = sum(team_points[9:18])
        back6 = sum(team_points[12:18])
        back3 = sum(team_points[15:18])
        back1 = team_points[17]
        
        team_results.append({
            'Team': team_name,
            'Total Points': total,
            'Front 9': front9,
            'Back 9': back9,
            'Back 6': back6,
            'Back 3': back3,
            'Back 1': back1
        })
    
    # Sort team leaderboard with tiebreakers
    if team_results:
        team_df = pd.DataFrame(team_results).sort_values(
            ['Total Points', 'Back 9', 'Back 6', 'Back 3', 'Back 1'],
            ascending=[False, False, False, False, False]
        )
    else:
        team_df = None
    
    return ind_df, team_df, player_details

# Button to calculate
if st.button("Calculate Results"):
    st.session_state.ind_df, st.session_state.team_df, st.session_state.player_details = compute_results()

with tab5:
    st.header("Individual Stableford Leaderboard")
    if 'ind_df' in st.session_state and st.session_state.ind_df is not None:
        st.table(st.session_state.ind_df)
    else:
        st.info("Enter scores and click 'Calculate Results' to see the leaderboard.")

with tab6:
    st.header("Team Irish Rumble Leaderboard")
    if 'team_df' in st.session_state and st.session_state.team_df is not None:
        st.table(st.session_state.team_df)
    else:
        st.info("Enter scores and click 'Calculate Results' to see the leaderboard.")

with tab7:
    st.header("Player Details (Stableford Points)")
    if 'player_details' in st.session_state and st.session_state.player_details:
        selected_player = st.selectbox("Select Player", list(st.session_state.player_details.keys()))
        if selected_player:
            details = st.session_state.player_details[selected_player]
            # Per-hole points
            st.subheader("Points per Hole")
            hole_df = pd.DataFrame({
                'Hole': range(1, 19),
                'Stableford Points': details['Points per Hole']
            })
            st.table(hole_df)
            
            # Breakdowns
            st.subheader("Breakdowns")
            breakdown_df = pd.DataFrame.from_dict(details['Breakdowns'], orient='index', columns=['Points'])
            st.table(breakdown_df)
    else:
        st.info("Enter scores and click 'Calculate Results' to see details.")

# Optional: Reset competition (but keep DB)
if st.button("Reset Competition Data (Keeps Player DB)"):
    if 'golfers' in st.session_state:
        del st.session_state.golfers
    if 'ind_df' in st.session_state:
        del st.session_state.ind_df
    if 'team_df' in st.session_state:
        del st.session_state.team_df
    if 'player_details' in st.session_state:
        del st.session_state.player_details
    st.experimental_rerun()
