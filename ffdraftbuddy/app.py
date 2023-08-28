import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

POSITIONS = ["QB", "WR", "RB", "TE"]

@st.cache_data()
def load_data():
    df = (
        pd.read_csv("staticdata/2023footballsheet.csv")
        .assign(Available=True)
        .sort_values(["Rank", "Pts/week"], ascending=[True, False])
        .reset_index(drop=True)
    )

    return df[["Available", "Name", "Position", "Team", "Value", "Pts/week", "Rank"]]


if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'df_modified' not in st.session_state:
    st.session_state.df_modified = load_data().copy()
    
    
def visualize():
    df = st.session_state.df_modified[
        st.session_state.df_modified["Available"]
    ].copy()
    df["VONP"] = df.groupby("Position")["Pts/week"].transform(
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
            y=alt.Y("Pts/week:Q").scale(
                domain=(
                    df["Pts/week"].min() - 1, 
                    df["Pts/week"].max() + 1
                )
            ),
            color=alt.Color("Position:N"),
            tooltip=["Name", "Rank", "Pts/week", "VONP"],
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
    
def suggest_picks():
    df = st.session_state.df_modified[
        st.session_state.df_modified["Available"]
    ].copy()
    df["VONP"] = df.groupby("Position")["Pts/week"].transform(
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


st.data_editor(
    st.session_state.df_modified, 
    disabled=["Value", "Team", "Name", "Pts/week", "Rank", "Position"],
    hide_index=True,
    on_change=apply_changes,
    key="changes",
    use_container_width=True,
)
reset_selections = st.button("Reset selections", on_click=reset_changes)

visualize()

suggest_picks()
