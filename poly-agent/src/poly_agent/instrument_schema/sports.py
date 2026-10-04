"""Sports instrument schema parser — identifies market types from metadata fields.

Per Polymarket Exchange docs: "Always match on `market_sport_type` alone."
Updated for v0.0.93 (MLB inning-total markets) and full inventory.
"""


class SportsSchemaParser:
    """Parses sports instrument metadata to identify market type, sport, and structure."""

    # Full market_sport_type inventory from Polymarket Exchange docs
    MARKET_TYPES = {
        # Baseball
        "baseball_team_full_game_winner": ("MLB", "Team", "Full Game", "Moneyline"),
        "baseball_team_full_game_spread": ("MLB", "Team", "Full Game", "Spread"),
        "baseball_team_full_game_total": ("MLB", "Team", "Full Game", "Total"),
        "baseball_team_inning1_winner": ("MLB", "Team", "Inning 1", "Winner"),
        "baseball_team_inning2_winner": ("MLB", "Team", "Inning 2", "Winner"),
        "baseball_team_inning3_winner": ("MLB", "Team", "Inning 3", "Winner"),
        "baseball_team_inning4_winner": ("MLB", "Team", "Inning 4", "Winner"),
        "baseball_team_inning5_winner": ("MLB", "Team", "Inning 5", "Winner"),
        "baseball_team_inning6_winner": ("MLB", "Team", "Inning 6", "Winner"),
        "baseball_team_inning7_winner": ("MLB", "Team", "Inning 7", "Winner"),
        "baseball_team_inning8_winner": ("MLB", "Team", "Inning 8", "Winner"),
        "baseball_team_inning9_winner": ("MLB", "Team", "Inning 9", "Winner"),
        # MLB inning-totals (v0.0.93, Sep 29) — Over/Under at 0.5 and 1.5 per inning
        "baseball_team_inning1_total": ("MLB", "Team", "Inning 1", "Total"),
        "baseball_team_inning2_total": ("MLB", "Team", "Inning 2", "Total"),
        "baseball_team_inning3_total": ("MLB", "Team", "Inning 3", "Total"),
        "baseball_team_inning4_total": ("MLB", "Team", "Inning 4", "Total"),
        "baseball_team_inning5_total": ("MLB", "Team", "Inning 5", "Total"),
        "baseball_team_inning6_total": ("MLB", "Team", "Inning 6", "Total"),
        "baseball_team_inning7_total": ("MLB", "Team", "Inning 7", "Total"),
        "baseball_team_inning8_total": ("MLB", "Team", "Inning 8", "Total"),
        "baseball_team_inning9_total": ("MLB", "Team", "Inning 9", "Total"),
        # Baseball player props (v0.0.76)
        "baseball_player_home_runs": ("MLB", "Player", "Full Game", "HR Prop"),
        "baseball_player_strikeouts": ("MLB", "Player", "Full Game", "SO Prop"),
        "baseball_player_rbis": ("MLB", "Player", "Full Game", "RBI Prop"),
        "baseball_player_stolen_bases": ("MLB", "Player", "Full Game", "SB Prop"),
        "baseball_team_total_runs": ("MLB", "Team", "Full Game", "Runs Total"),

        # Basketball (NBA, WNBA, CBB, WCBB)
        "basketball_team_full_game_winner": ("NBA/WNBA/CBB", "Team", "Full Game", "Moneyline"),
        "basketball_team_full_game_spread": ("NBA/WNBA/CBB", "Team", "Full Game", "Spread"),
        "basketball_team_full_game_total": ("NBA/WNBA/CBB", "Team", "Full Game", "Total"),
        "basketball_team_first_half_winner": ("NBA/WNBA/CBB", "Team", "First Half", "Prop"),
        "basketball_team_first_half_spread": ("NBA/WNBA/CBB", "Team", "First Half", "Spread"),
        "basketball_team_first_half_total": ("NBA/WNBA/CBB", "Team", "First Half", "Total"),
        "basketball_team_second_half_winner": ("NBA/WNBA/CBB", "Team", "Second Half", "Prop"),
        "basketball_team_second_half_spread": ("NBA/WNBA/CBB", "Team", "Second Half", "Spread"),
        "basketball_team_second_half_total": ("NBA/WNBA/CBB", "Team", "Second Half", "Total"),
        # NBA quarter markets (v0.0.37)
        "basketball_team_first_quarter_spread": ("NBA/WNBA/CBB", "Team", "1st Quarter", "Spread"),
        "basketball_team_second_quarter_spread": ("NBA/WNBA/CBB", "Team", "2nd Quarter", "Spread"),
        "basketball_team_third_quarter_spread": ("NBA/WNBA/CBB", "Team", "3rd Quarter", "Spread"),
        "basketball_team_fourth_quarter_spread": ("NBA/WNBA/CBB", "Team", "4th Quarter", "Spread"),
        "basketball_team_first_quarter_total": ("NBA/WNBA/CBB", "Team", "1st Quarter", "Total"),
        "basketball_team_second_quarter_total": ("NBA/WNBA/CBB", "Team", "2nd Quarter", "Total"),
        "basketball_team_third_quarter_total": ("NBA/WNBA/CBB", "Team", "3rd Quarter", "Total"),
        "basketball_team_fourth_quarter_total": ("NBA/WNBA/CBB", "Team", "4th Quarter", "Total"),
        "basketball_game_overtime": ("NBA/WNBA/CBB", "Game", "Full Game", "OT Prop"),
        # NBA player props (v0.0.36)
        "basketball_player_points": ("NBA/WNBA/CBB", "Player", "Full Game", "Points Prop"),
        "basketball_player_assists": ("NBA/WNBA/CBB", "Player", "Full Game", "Ast Prop"),
        "basketball_player_rebounds": ("NBA/WNBA/CBB", "Player", "Full Game", "Reb Prop"),
        "basketball_player_threes": ("NBA/WNBA/CBB", "Player", "Full Game", "3PT Made Prop"),
        "basketball_player_steals": ("NBA/WNBA/CBB", "Player", "Full Game", "Stl Prop"),
        "basketball_player_blocks": ("NBA/WNBA/CBB", "Player", "Full Game", "Blk Prop"),
        "basketball_player_double_double": ("NBA/WNBA/CBB", "Player", "Full Game", "DD Prop"),
        "basketball_player_triple_double": ("NBA/WNBA/CBB", "Player", "Full Game", "TD Prop"),

        # Football (NFL, CFB) — 71 types total (v0.0.86 + v0.0.93 additions)
        "football_team_full_game_winner": ("NFL/CFB", "Team", "Full Game", "Moneyline"),
        "football_team_full_game_spread": ("NFL/CFB", "Team", "Full Game", "Spread"),
        "football_team_full_game_total": ("NFL/CFB", "Team", "Full Game", "Total"),
        "football_team_first_half_winner": ("NFL/CFB", "Team", "First Half", "Prop"),
        "football_team_first_half_spread": ("NFL/CFB", "Team", "First Half", "Spread"),
        "football_team_first_half_total": ("NFL/CFB", "Team", "First Half", "Total"),
        "football_team_second_half_winner": ("NFL/CFB", "Team", "Second Half", "Prop"),
        "football_team_second_half_spread": ("NFL/CFB", "Team", "Second Half", "Spread"),
        "football_team_second_half_total": ("NFL/CFB", "Team", "Second Half", "Total"),
        # Player props (v0.0.86)
        "football_player_touchdowns": ("NFL/CFB", "Player", "Full Game", "TD Prop"),
        "football_player_passing_attempts": ("NFL/CFB", "Player", "Full Game", "PA Prop"),
        "football_player_passing_completions": ("NFL/CFB", "Player", "Full Game", "PC Prop"),
        "football_player_rushing_attempts": ("NFL/CFB", "Player", "Full Game", "RA Prop"),
        "football_player_longest_rush": ("NFL/CFB", "Player", "Full Game", "Long Rush Prop"),
        "football_player_longest_reception": ("NFL/CFB", "Player", "Full Game", "Long Rec Prop"),
        "football_player_field_goals_made": ("NFL/CFB", "Player", "Full Game", "FG Made Prop"),
        "football_player_50_plus_yard_field_goals_made": ("NFL/CFB", "Player", "Full Game", "50+ FG Prop"),
        "football_player_fantasy_points_ppr": ("NFL/CFB", "Player", "Full Game", "PPR Prop"),
        "football_player_scrimmage_yards": ("NFL/CFB", "Player", "Full Game", "Scrimmage Yds Prop"),
        # First TD for team (v0.0.86)
        "football_player_team_first_touchdown": ("NFL/CFB", "Player", "Full Game", "1st TD Prop"),
        # Selected-team totals (v0.0.86)
        "football_team_total_offensive_yards": ("NFL/CFB", "Team", "Full Game", "Off Yds Total"),
        "football_team_total_first_downs": ("NFL/CFB", "Team", "Full Game", "1st Down Total"),
        "football_team_total_defensive_special_teams_touchdowns": ("NFL/CFB", "Team", "Full Game", "Def/Special TD Total"),
        # Game outcomes (v0.0.86)
        "football_game_double_result": ("NFL/CFB", "Game", "Full Game", "Double Result"),
        "football_game_last_score": ("NFL/CFB", "Game", "Full Game", "Last Score Prop"),
        "football_game_last_touchdown": ("NFL/CFB", "Game", "Full Game", "Last TD Prop"),
        "football_game_race_to_points": ("NFL/CFB", "Game", "Full Game", "Race to X Points"),
        "football_game_highest_scoring_quarter": ("NFL/CFB", "Game", "Full Game", "Highest Scoring Qtr"),
        "football_game_possession_winner": ("NFL/CFB", "Game", "Full Game", "Possession Winner"),
        "football_game_tie": ("NFL/CFB", "Game", "Full Game", "Tie Prop"),
        "football_game_safety": ("NFL/CFB", "Game", "Full Game", "Safety Prop"),
        "football_game_onside_kick_attempt": ("NFL/CFB", "Game", "Full Game", "Onside Kick Prop"),
        # Combined game totals (v0.0.86)
        "football_game_total_pass_yards": ("NFL/CFB", "Game", "Full Game", "Pass Yds Total"),
        "football_game_total_pass_touchdowns": ("NFL/CFB", "Game", "Full Game", "Pass TD Total"),
        "football_game_total_defensive_interceptions": ("NFL/CFB", "Game", "Full Game", "Def INT Total"),
        "football_game_total_fourth_down_conversions": ("NFL/CFB", "Game", "Full Game", "4th Down Conv Total"),
        "football_game_total_two_point_conversions": ("NFL/CFB", "Game", "Full Game", "2PT Conv Yes/No"),

        # Soccer (v0.0.58 + v0.0.65)
        "soccer_team_full_time_winner": ("Soccer", "Team", "Full Time", "Winner"),
        "soccer_team_full_game_spread": ("Soccer", "Team", "Full Game", "Spread"),
        "soccer_team_full_game_total": ("Soccer", "Team", "Full Game", "Total"),
        "soccer_team_first_half_winner": ("Soccer", "Team", "First Half", "Winner"),
        "soccer_team_first_half_spread": ("Soccer", "Team", "First Half", "Spread"),
        "soccer_team_first_half_total": ("Soccer", "Team", "First Half", "Total"),
        "soccer_game_btts": ("Soccer", "Game", "Full Game", "BTTS"),
        "soccer_game_first_team_to_score": ("Soccer", "Game", "Full Game", "1st Team Score"),
        "soccer_game_exact_score": ("Soccer", "Game", "Full Game", "Exact Score"),
        "soccer_game_total_corners": ("Soccer", "Game", "Full Game", "Corners Total"),
        "soccer_player_goals": ("Soccer", "Player", "Full Game", "Goals Prop"),
        "soccer_player_assists": ("Soccer", "Player", "Full Game", "Assists Prop"),
        # Soccer half BTTS/FTTS (v0.0.58)
        "soccer_game_first_half_btts": ("Soccer", "Game", "First Half", "BTTS"),
        "soccer_game_first_half_first_team_to_score": ("Soccer", "Game", "First Half", "1st Team Score"),
        "soccer_game_second_half_btts": ("Soccer", "Game", "Second Half", "BTTS"),
        "soccer_game_second_half_first_team_to_score": ("Soccer", "Game", "Second Half", "1st Team Score"),
        # Soccer extra-time (v0.0.57) — World Cup knockouts only
        "soccer_game_goes_to_extra_time": ("Soccer", "Game", "Extra Time", "Goes to ET"),
        "soccer_team_extra_time_spread": ("Soccer", "Team", "Extra Time", "ET Spread"),
        "soccer_game_extra_time_total": ("Soccer", "Game", "Extra Time", "ET Total"),
        "soccer_game_extra_time_btts": ("Soccer", "Game", "Extra Time", "ET BTTS"),
        "soccer_game_extra_time_first_team_to_score": ("Soccer", "Game", "Extra Time", "1st Team Score ET"),
        # Soccer To Advance (v0.0.65) — single two-sided instrument
        "soccer_game_to_advance": ("Soccer", "Game", "Knockout Tie", "To Advance"),

        # Tennis (v0.0.49 + v0.0.58)
        "tennis_match_winner": ("Tennis", "Player", "Match", "Moneyline"),
        "tennis_match_games_spread": ("Tennis", "Player", "Match", "Games Spread"),
        "tennis_match_total_games": ("Tennis", "Player", "Match", "Total Games"),
        "tennis_match_exact_score": ("Tennis", "Player", "Match", "Exact Score"),
        "tennis_set_1_winner": ("Tennis", "Player", "Set 1", "Winner"),
        "tennis_set_2_winner": ("Tennis", "Player", "Set 2", "Winner"),
        "tennis_set_3_winner": ("Tennis", "Player", "Set 3", "Winner"),

        # Cricket (v0.0.56)
        "cricket_match_winner": ("Cricket", "Team", "Match", "Moneyline"),

        # UFC/Boxing/Darts/Pickleball/Lacrosse/Table Tennis
        "ufc_fight_winner": ("UFC", "Fighter", "Fight", "Moneyline"),
        "ufc_method_of_victory": ("UFC", "Fighter", "Fight", "Method of Victory"),
        "ufc_go_the_distance": ("UFC", "Fight", "Fight", "Go Distance"),
        "ufc_round_of_victory": ("UFC", "Fight", "Fight", "Round of Victory"),
        "ufc_round_of_finish": ("UFC", "Fight", "Fight", "Round of Finish"),
        "ufc_method_of_finish": ("UFC", "Fight", "Fight", "Method of Finish"),
        "boxing_match_winner": ("Boxing", "Fighter", "Fight", "Moneyline"),
        "darts_match_winner": ("Darts", "Player", "Match", "Moneyline"),
        "pickleball_match_winner": ("Pickleball", "Team", "Match", "Moneyline"),
        "lacrosse_team_full_game_winner": ("Lacrosse", "Team", "Full Game", "Winner"),
        "table_tennis_match_winner": ("Table Tennis", "Player", "Match", "Moneyline"),
        "table_tennis_set_1_winner": ("Table Tennis", "Player", "Set 1", "Winner"),
        "table_tennis_set_2_winner": ("Table Tennis", "Player", "Set 2", "Winner"),
        "table_tennis_set_3_winner": ("Table Tennis", "Player", "Set 3", "Winner"),
        "table_tennis_set_4_winner": ("Table Tennis", "Player", "Set 4", "Winner"),

        # Esports (v0.0.86)
        "esports_match_winner": ("Esports", "Team", "Match", "Moneyline"),
        "esports_map_winner_1": ("Esports", "Team", "Map 1", "Winner"),
        "esports_map_winner_2": ("Esports", "Team", "Map 2", "Winner"),
        "esports_map_winner_3": ("Esports", "Team", "Map 3", "Winner"),
        "esports_map_winner_4": ("Esports", "Team", "Map 4", "Winner"),
        "esports_game_winner_1": ("Esports", "Team", "Game 1", "Winner"),
        "esports_game_winner_2": ("Esports", "Team", "Game 2", "Winner"),
        "esports_game_winner_3": ("Esports", "Team", "Game 3", "Winner"),

        # Hockey (v0.0.42)
        "hockey_team_full_game_winner": ("NHL", "Team", "Full Game", "Moneyline"),
        "hockey_team_full_game_spread": ("NHL", "Team", "Full Game", "Spread"),
        "hockey_team_full_game_total": ("NHL", "Team", "Full Game", "Total"),
        "hockey_game_overtime": ("NHL", "Game", "Full Game", "Goes to OT"),
        "hockey_game_double_overtime": ("NHL", "Game", "Full Game", "Goes to 2OT"),
        "hockey_player_goals": ("NHL", "Player", "Full Game", "Goals Prop"),
        "hockey_player_assists": ("NHL", "Player", "Full Game", "Assists Prop"),
        "hockey_player_points": ("NHL", "Player", "Full Game", "Points Prop"),

        # Generic values (v0.0.86) — for instruments with no sport-specific value
        "moneyline": ("Generic", "Team/Player/Fighter", "Full Game", "Moneyline"),
        "spreads": ("Generic", "Team/Player/Fighter", "Full Game", "Spread"),
        "totals": ("Generic", "Team/Player/Fighter", "Full Game", "Total"),
        "drawable_outcome": ("Generic", "Team/Player/Fighter", "Full Game", "Drawable Outcome"),
    }

    @classmethod
    def parse(cls, instrument: dict) -> Optional[dict]:
        """Parse a sports instrument and return structured market info."""
        metadata = instrument.get("metadata", {})
        market_type = metadata.get("market_sport_type")

        if not market_type or market_type not in cls.MARKET_TYPES:
            return None

        sport, scope, period, type_desc = cls.MARKET_TYPES[market_type]
        outcome_strike = metadata.get("outcome_strike", "0.0")
        long_participant_id = metadata.get("long_participant_id", "")
        home_team_name = metadata.get("home_team_name", "")
        away_team_name = metadata.get("away_team_name", "")
        tournament_name = metadata.get("tournament_name", "")

        return {
            "sport": sport,
            "scope": scope,
            "period": period,
            "type": type_desc,
            "market_type_enum": market_type,
            "outcome_strike": outcome_strike,
            "long_participant_id": long_participant_id,
            "home_team_name": home_team_name,
            "away_team_name": away_team_name,
            "tournament_name": tournament_name,
            "event_start_time": metadata.get("event_start_time"),
            "symbol": instrument.get("symbol", ""),
        }

    @classmethod
    def is_interesting(cls, parsed: dict) -> bool:
        """Determine if a sports market is worth trading (high liquidity, clear edge)."""
        # Focus on moneylines and spreads (most liquid)
        return parsed["type"] in ("Moneyline", "Spread")
