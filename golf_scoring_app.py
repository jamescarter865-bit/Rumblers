import streamlit as st
import pandas as pd

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

# Now the rest of your original code...
# Function to calculate Stableford points for a hole
def stableford_points(gross_score, par, strokes_received):
    ...
import streamlit as st
import pandas as pd

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

# App layout
st.title("Golf Competition Scoring App")

# Step 1: Input Course Details (18 holes assumed)
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

# Step 2: Input Golfers
st.header("Add Golfers")
if 'golfers' not in st.session_state:
    st.session_state.golfers = []

golfer_name = st.text_input("Golfer Name")
handicap = st.number_input("Handicap", min_value=0, max_value=54, value=0)
team = st.text_input("Team Name (e.g., Team A)")

if st.button("Add Golfer"):
    st.session_state.golfers.append({
        'Name': golfer_name,
        'Handicap': handicap,
        'Team': team
    })
    st.success(f"Added {golfer_name}")

# Display golfers
if st.session_state.golfers:
    golfers_df = pd.DataFrame(st.session_state.golfers)
    st.table(golfers_df)

# Step 3: Input Scores (one golfer at a time)
st.header("Enter Scores")
selected_golfer = st.selectbox("Select Golfer", [g['Name'] for g in st.session_state.golfers])
if selected_golfer:
    golfer = next(g for g in st.session_state.golfers if g['Name'] == selected_golfer)
    if 'scores' not in golfer:
        golfer['scores'] = [0] * 18  # Default gross scores

    scores = st.data_editor(
        pd.DataFrame({
            'Hole': range(1, 19),
            'Gross Score': golfer['scores']
        }),
        num_rows="fixed",
        hide_index=True,
        column_config={"Hole": st.column_config.NumberColumn(disabled=True)}
    )
    golfer['scores'] = scores['Gross Score'].tolist()

# Step 4: Compute and Display Results (once all data is in)
if st.button("Calculate Results"):
    # Compute individual Stableford
    individual_results = []
    for golfer in st.session_state.golfers:
        if 'scores' not in golfer:
            continue
        points = []
        for hole in range(18):
            gross = golfer['scores'][hole]
            if gross == 0:
                points.append(0)
                continue
            par = course_df.iloc[hole]['Par']
            si = course_df.iloc[hole]['Stroke Index']
            strokes = strokes_on_hole(golfer['Handicap'], si)
            pts = stableford_points(gross, par, strokes)
            points.append(pts)
        
        total = sum(points)
        back9 = sum(points[9:18])
        back6 = sum(points[12:18])
        back3 = sum(points[15:18])
        back1 = points[17]
        
        individual_results.append({
            'Name': golfer['Name'],
            'Team': golfer['Team'],
            'Total Points': total,
            'Back 9': back9,
            'Back 6': back6,
            'Back 3': back3,
            'Back 1': back1
        })
    
    if individual_results:
        ind_df = pd.DataFrame(individual_results).sort_values('Total Points', ascending=False)
        st.header("Individual Stableford Leaderboard")
        st.table(ind_df)
    
    # Compute team Irish Rumble
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
                golfer_points.append(0)
                continue
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
            else:  # 13-18: best 3
                team_points.append(sum(hole_points[:3]))
        
        total = sum(team_points)
        back9 = sum(team_points[9:18])
        back6 = sum(team_points[12:18])
        back3 = sum(team_points[15:18])
        back1 = team_points[17]
        
        team_results.append({
            'Team': team_name,
            'Total Points': total,
            'Back 9': back9,
            'Back 6': back6,
            'Back 3': back3,
            'Back 1': back1
        })
    
    if team_results:
        team_df = pd.DataFrame(team_results).sort_values('Total Points', ascending=False)
        st.header("Team Irish Rumble Leaderboard")
        st.table(team_df)

# Optional: Reset app
if st.button("Reset All Data"):
    st.session_state.clear()
    st.experimental_rerun()
