from pathlib import Path
import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

POSITIONS = ["QB", "WR", "RB", "TE"]
PROJECTIONS_COL = "FantasyPts"

def parse_code(val):
    match_pattern = r"([A-Z]*)([0-9]*)"
    matched = re.match(match_pattern, val)
    parsed = {"Position": matched.group(1), "Rank": int(matched.group(2))}
    return pd.Series(parsed)

@st.cache_data
def load_data():
    df = (
        pd.read_csv("staticdata/2023fantasypointsprojections.csv")
        .rename(columns={"Rank": "OverallRank"})
        .assign(Available=True)
    )
    parsed_codes = df["Code"].apply(parse_code)
    df = (
        df.merge(parsed_codes, left_index=True, right_index=True)
        .drop(columns=["Code", "OverallRank"])
        [lambda df_: df_["Position"].isin(POSITIONS)]
    )
    return df[["Available", "Name", "Team", "Position", "Rank", "FantasyPts"]]


if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'df_modified' not in st.session_state:
    st.session_state.df_modified = load_data().copy()
    
    
def visualize():
    df = st.session_state.df_modified[
        st.session_state.df_modified["Available"]
    ].copy()
    df["VONP"] = df.groupby("Position")[PROJECTIONS_COL].transform(
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
            tooltip=["Name", "Rank", PROJECTIONS_COL, "VONP"],
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
    df["VONP"] = df.groupby("Position")[PROJECTIONS_COL].transform(
        lambda vals: -1 * np.diff(vals, append=vals.values[-1])
    )
    
    sliders = [None] * 4
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
    df = st.session_state.df_modified[
        st.session_state.df_modified["Available"]
    ].copy()



st.data_editor(
    st.session_state.df_modified, 
    disabled=["Value", "Team", "Name", PROJECTIONS_COL, "Rank", "Position"],
    hide_index=True,
    on_change=apply_changes,
    key="changes",
    use_container_width=True,
)
reset_selections = st.button("Reset selections", on_click=reset_changes)

visualize()

summarize_positions()
