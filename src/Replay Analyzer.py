from pprint import pprint
import json
import os
from pathlib import Path
import sc2reader
from tkinter import *
from tkinter import ttk
import mpyq
import sqlite3
from tqdm import tqdm

REPLAY_PATH = r'C:\Users\jchur\Documents\StarCraft II\Accounts\65253659\1-S2-1-1656173\Replays\Multiplayer'
USER = ['acheron', 'Koolboi']

con = sqlite3.connect('sc2reader.db')
p = Path(REPLAY_PATH)
replay_paths = [x for x in p.iterdir() if x.is_file()]


def determine_players_races(replay):
    archive = mpyq.MPQArchive(replay.filename)
    jsondata = archive.read_file("replay.gamemetadata.json").decode("utf-8")
    obj = json.loads(jsondata)
    p1_mmr = obj['Players'][0]['MMR'] if 'MMR' in obj['Players'][0].keys() else None
    p2_mmr = obj['Players'][1]['MMR'] if 'MMR' in obj['Players'][1].keys() else None
    players = str(replay.players).split(' ')
    player_1 = players[3]
    p1_race = players[4][1:-2]
    player_2 = players[8]
    p2_race = players[9][1:-2]
    if player_2 in USER: # swap players if p2 is in USER
        player_1, player_2 = player_2, player_1
        p1_race, p2_race = p2_race, p1_race
        p1_mmr, p2_mmr = p2_mmr, p1_mmr
    diff = p2_mmr-p1_mmr
    
    return [player_1, p1_race, player_2, p2_race, p1_mmr, p2_mmr, diff]

def parse_replay(replay):
    player_info = determine_players_races(replay)
    out = {
        'map_name': replay.map_name,
        'winner': str(replay.winner).split(' ')[5] if replay.winner else None,
        'date': str(replay.date),
        'player_1': player_info[0],
        'p1_race': player_info[1],
        'player_2': player_info[2],
        'p2_race': player_info[3],
        'p1_mmr': player_info[4],
        'p2_mmr': player_info[5],
        'length': replay.game_length.total_seconds(),
        'region': replay.region,
        'mmr_diff': player_info[6]
    }
    if out['winner'] in USER:
        out['win_or_lose'] = 1
    else:
        out['win_or_lose'] = 0
    return out

def create_table(cur: sqlite3.Cursor):
    cur.execute("CREATE TABLE IF NOT EXISTS replays(map_name, \
        winner, date, player_1, p1_race, player_2, p2_race, p1_mmr, p2_mmr, length, region, mmr_diff, win_or_lose, UNIQUE (map_name, date, length))")
    con.commit()

def insert_data(data: dict, cur: sqlite3.Cursor):
    cur.execute("INSERT OR IGNORE INTO "
                "replays (map_name, winner, date, player_1, p1_race, player_2, p2_race, p1_mmr, p2_mmr, length, region, mmr_diff, win_or_lose) "
                "VALUES (:map_name, :winner, :date, :player_1, :p1_race, :player_2, :p2_race, :p1_mmr, :p2_mmr, :length, :region, :mmr_diff, :win_or_lose)", data)

def add_replays():
    errors = []
    cur = con.cursor()
    create_table(cur)
    sc2 = sc2reader.factories.SC2Factory() # factory class to load replays
    for replay_path in tqdm(replay_paths, desc='LOADING...'):
        try:
            replay = sc2.load_replay(str(replay_path))
            if not replay.is_ladder or len(replay.teams) != 2 or len(replay.players) != 2: # ignore non ladder, non 2-player, and games with observors.
                continue
            insert_data(parse_replay(replay), cur)
        except Exception as error:
            err = f'{error=}' + f'{replay_path=}'
            errors.append(err)
    # pprint(cur.execute('SELECT * FROM replays').fetchall())
    con.commit()
    cur.close()
    pprint(errors)

def make_audit():
    pass

def get_data(query):
    cur = con.cursor()

def build_query(audit: dict):
    query = ""
    if audit['query_type'] == 'AVG':
        query += "SELECT AVG(" + audit['AVG'] + ') FROM replays WHERE '
    elif audit['query_type'] == 'SEARCH':
        query += 'SELECT * FROM replays WHERE '
    else:
        pass
    if audit['query_type'] == 'SEARCH':
        keys = list(audit.keys()).pop(0)
    elif audit['query_type'] == 'AVG':
        keys = list(audit.keys()).pop(0)
        keys.pop(0)
    keys_length = len(keys)
    keys_used = 0
    #my mmr
    if 'mmr_max' in keys: # if mmr max and min are in keys
        if 'mmr_min' in keys:
            query += f'p1_mmr BETWEEN {audit["mmr_min"]} AND {audit["mmr_max"]}'
            keys_used += 2
            if keys_used != keys_length:
                query += ' AND '
    if 'mmr_max' in keys and 'mmr_min' not in keys: #if mmr max is in keys but not mmr min
        query += f'p1_mmr<{audit["mmr_max"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '
    if 'mmr_min' in keys and 'mmr_max' not in keys: #if mmr min is in keys but not mmr max
        query += f'p1_mmr>{audit["mmr_min"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '

    #opponent mmr
    if 'opp_mmr_max' in keys: # if mmr max and min are in keys
        if 'opp_mmr_min' in keys:
            query += f'p2_mmr BETWEEN {audit["opp_mmr_min"]} AND {audit["opp_mmr_max"]} '
            keys_used += 2
            if keys_used != keys_length:
                query += ' AND '
    if 'opp_mmr_max' in keys and 'opp_mmr_min' not in keys: #if mmr max is in keys but not mmr min
        query += f'p2_mmr<{audit["opp_mmr_max"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '
    if 'opp_mmr_min' in keys and 'opp_mmr_max' not in keys: #if mmr min is in keys but not mmr max
        query += f'p2_mmr>{audit["opp_mmr_min"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '

    #mmr difference
    if 'mmr_diff' in keys:
        query += f'mmr_diff<{audit["mmr_diff"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '

    # races
    if 'race' in keys:
        query += f'p1_race={audit["race"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '
    if 'opp_race' in keys:
        query += f'p2_race={audit["opp_race"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '

    # server
    if 'region' in keys:
        query += f'region={audit["region"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '

    # time
    if 'length' in keys:
        query += f'length={audit["length"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '

    # map
    if 'map' in keys:
        query += f'map={audit["map"]}'
        keys_used += 1
        if keys_used != keys_length:
            query += ' AND '


    return query











if __name__ == '__main__':
    add_replays()