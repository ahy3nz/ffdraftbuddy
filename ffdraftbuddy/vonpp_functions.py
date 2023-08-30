from pathlib import Path
import re

import numpy as np
import pandas as pd


POSITIONS = ["QB", "WR", "RB", "TE", "K", "DST"]
PROJECTION_COL = "FantasyPts"


class PlayerRanker:
    def __init__(self, df, n_teams=10, log=True, look_ahead_strategy="simulate", blur=1, superflex=False):
        self.draft_ranking = [] # Store our ranking
        self.n_teams = n_teams

        # For each position, create a queue of players
        # where the better players are at the top of the queue
        self.position_queue = dict()
        for pos in POSITIONS:
            self.position_queue[pos] = list(
                df[df["Position"]==pos]
                .to_dict(orient="index")
                .values()
            )
        
        self.log = log
        self.look_ahead_strategy = look_ahead_strategy
        self.blur = blur
        self.superflex = superflex
        if self.superflex:
            self.reduced_positions = ["TE"]
        else:
            self.reduced_positions = ["QB", "TE"]
        
                
    def compute_vonpp(self, df, size=100):
        """ Iteratively select players based on VONPP

        This means, one-by-one, we try drafting players using the VONPP strategy
        and modify the pool of available players as we draft.

        Understanding that fantasy projections and picking a representative player is not perfect,
        we include a `blur` to say we identify the next possible player by taking our lookahead +/- 1,
        so we look at 3 players to derive the next possible player
        """
        # If some players have been picked, we have to re-derive rankings
        # so we have a continuous range
        df["Rerank"] = df.groupby("Position")[PROJECTION_COL].rank(ascending=False)
        for pick in range(1, size):
            # Find the best player available at each position
            players_by_position = df.groupby("Position")
            # Given the pick number, deduece the round and draft position
            round_number = 1 + ((pick - 1) // self.n_teams)
            is_odd_round = (round_number % 2 == 1)
            draft_position = (pick % self.n_teams)
            if draft_position == 0:
                draft_position = self.n_teams
            
            # Derive the "look ahead" (how we identify the next possible player)
            if self.look_ahead_strategy == "simulate":
                # If we simulate, then our look ahead is  based on the draft position
                # and where we end up next in a snake draft
                look_ahead = (2 * (self.n_teams - draft_position)) + 1
            elif isinstance(self.look_ahead_strategy, int):
                # For simplicity, can also hard-sepcify a look ahead integer
                look_ahead = self.look_ahead_strategy
            else:
                raise ValueError(f"Lookahead strategy {self.look_ahead_strategy} invalid")
            
            # Our player pool is a compilation of best availble players
            # and associated VONPPs
            player_pool = []
            for pos in POSITIONS:
                best_player_available = players_by_position.get_group(pos).head(1).iloc[0]
                if best_player_available is not None:
                    # Modify our lookahead based on the position
                    if pos in self.reduced_positions:
                        count_forward = max(round(look_ahead/2), 1)
                    else:
                        count_forward = look_ahead
                    
                    # Determine our next possible player
                    # By looking at the players around a certain rank

                    avg_next_player = (
                        df[
                            (df["Position"] == pos) &
                            (
                                (df["Rerank"] >= best_player_available["Rerank"] + count_forward - self.blur) &
                                (df["Rerank"] <= best_player_available["Rerank"] + count_forward + self.blur)
                            )
                        ]
                        [PROJECTION_COL]
                        .mean()
                    )

                    # Compute VONPP by looking at best available player and 
                    # next possible player
                    vonpp = best_player_available[PROJECTION_COL] - avg_next_player
                    player_pool.append( (best_player_available, vonpp, count_forward) )
                    if self.log:
                        print(f"Candidate position: {pos}")
                        print(f"Best player available: {best_player_available}")
                        print(f"VONPP: {vonpp}")
                        print(f"Count forward: {count_forward}")
                
            # From the player pool, find the player with the highest VONPP
            person_to_draft = max(
                player_pool,
                key=lambda combos: combos[1]
            )
            # Add to our draft list
            to_draft = {**person_to_draft[0], "VONPP": person_to_draft[1], "LookAhead": person_to_draft[2]}
            self.draft_ranking.append(to_draft)
            df = df.drop(index=[person_to_draft[0].name])

def run_ranker(df, n_teams=10, log=False, look_ahead_strategy="simulate", blur=1, superflex=False):
    # Ranking strategy by simulating a snake draft
    ranker = PlayerRanker(
        df, 
        n_teams=n_teams, 
        log=False, 
        look_ahead_strategy=look_ahead_strategy, 
        blur=blur,
        superflex=superflex,
    )
    ranker.compute_vonpp(df, size=30)
    simulated_ranking = pd.DataFrame(ranker.draft_ranking).drop(columns=["Rerank"])
    return simulated_ranking

