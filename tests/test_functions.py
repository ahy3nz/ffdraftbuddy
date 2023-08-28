from pathlib import Path

import pandas as pd
import pytest

TEST_DIR = Path(__file__).parent


@pytest.fixture
def ffdata():
    df = pd.read_csv(TEST_DIR.parent / "ffdraftbuddy/staticdata/2023footballsheet.csv")
    return df


def test_data(ffdata):
    cols_needed = ["Name", "Position", "Team", "Value", "Pts/week", "Rank"]
    all_cols_present = [c in ffdata.columns for c in cols_needed]
    assert all(all_cols_present)


def test_positions(ffdata):
    positions_needed = {"QB", "RB", "WR", "TE"}
    positions_present = ffdata["Position"].unique()
    intersection = positions_needed.intersection(positions_present)

    assert len(intersection) == 4
