from pathlib import Path
import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import vonpp_functions

POSITIONS = ["QB", "WR", "RB", "TE", "K", "DST"]
PROJECTIONS_COL = "FPTS" 

@st.cache_data
def load_fantasypros():
    all_df = []
    for pos in POSITIONS:
        df = (
            pd.read_csv(
                Path(__file__).parent / f"staticdata/FantasyPros_Fantasy_Football_Projections_{pos}.csv",
                usecols=["Player", "Team", "FPTS"],
                skiprows=[1]
            )
            .assign(Position=pos, Available=True)
            .sort_values("FPTS", ascending=False)
            .assign(Rank=lambda df_: df_["FPTS"].rank(ascending=False))
        )
        all_df.append(df)
    return (
        pd.concat(all_df)
        .dropna(subset=["Player"])
        .sort_values(["Rank", "FPTS"], ascending=[True, False])
        .reset_index(drop=True)
        [["Available", "Player", "Team", "Position", "Rank", "FPTS"]]
    )


if 'df' not in st.session_state:
    st.session_state.df = load_fantasypros()
if 'df_modified' not in st.session_state:
    st.session_state.df_modified = load_fantasypros().copy()
    
    
def visualize():
    df = st.session_state.df_modified[
        st.session_state.df_modified["Available"]
    ].copy()
    df["Delta"] = df.groupby("Position")[PROJECTIONS_COL].transform(
        lambda vals: -1 * np.diff(vals, append=vals.values[-1])
    )
    
    selector_legend = alt.selection_point(fields=["Position"], bind="legend")
    chart = (
        alt.Chart(
            df, 
            height=400, width=400
        )
        .mark_line(point=True)
        .encode(
            x=alt.X("Rank:Q").scale(
                domain=(
                    df["Rank"].min() - 1, 
                    df["Rank"].max() + 1
                )
            ),
            y=alt.Y(f"{PROJECTIONS_COL}:Q").scale(
                domain=(
                    df[PROJECTIONS_COL].min() - 1, 
                    df[PROJECTIONS_COL].max() + 1
                )
            ),
            color=alt.Color("Position:N"),
            tooltip=["Player", "Rank", PROJECTIONS_COL, "Delta"],
            opacity=alt.condition(selector_legend, alt.value(1), alt.value(0.2))
        )
        .add_params(selector_legend)
        .configure_point(size=50)
        .interactive()
    )

    altair_chart = st.altair_chart(chart, theme=None, use_container_width=True)

    
def apply_changes():
    change_info = st.session_state.changes["edited_rows"]
    for idx, change_dict in change_info.items():
        for change_col, change_val in change_dict.items():
            st.session_state.df_modified.loc[idx, change_col] = change_val
            
def reset_changes():
    df = st.session_state.df_modified
    df["Available"] = True
    
def summarize_positions():
    df = st.session_state.df_modified[
        st.session_state.df_modified["Available"]
    ].copy()
    
    sliders = [None] * len(POSITIONS)
    for i, pos in enumerate(POSITIONS):
        position_df = df[df["Position"]==pos].drop(columns=["Position", "Available"])

        with st.expander(pos):
            sliders[i] = st.slider(
                "Show N players", min_value=1, max_value=25, 
                value=12, step=1, format="%i",
                key=f"Slider{pos}"
            )
            st.dataframe(position_df.head(sliders[i]), use_container_width=True)

def suggest_picks():
    with st.expander("Draft Suggestions"):
        n_teams = st.number_input("Number of teams", format="%i", step=1, value=10)
        draft_strategy = st.radio("Lookahead style", ["Fixed", "Snake"])
        look_ahead_selection = st.number_input(
            "Lookahead interval (only used if lookahead style is fixed)", format="%i", 
            step=1, value=10
        )
        superflex = st.toggle("Activate superflex", value=False)
        run_suggestions = st.button("Run draft suggestions")

        if run_suggestions:
            if draft_strategy == "Snake":
                look_ahead = "simulate"
            else:
                look_ahead = int(look_ahead_selection)
            df = st.session_state.df_modified[
                st.session_state.df_modified["Available"]
            ].copy()
            suggestions = vonpp_functions.run_ranker(
                df, n_teams=n_teams, look_ahead_strategy=look_ahead,
                superflex=superflex
            ).drop(columns=["Available"])
            st.dataframe(suggestions, use_container_width=True)

st.data_editor(
    st.session_state.df_modified, 
    disabled=["Value", "Team", "Player", PROJECTIONS_COL, "Rank", "Position"],
    hide_index=True,
    on_change=apply_changes,
    key="changes",
    use_container_width=True,
)
reset_selections = st.button("Reset selections", on_click=reset_changes)

visualize()

summarize_positions()

suggest_picks()
