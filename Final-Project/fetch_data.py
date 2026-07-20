from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import leaguegamefinder, playergamelog, commonplayerinfo
import mysql.connector
from datetime import datetime
from tqdm import tqdm
import time

def try_api(func):
    try:
        return func()
    except:
        return None

print("=== NBA Data Fetcher (200 players) ===")
PLAYER_LIMIT = 200

conn = mysql.connector.connect(host='127.0.0.1', user='nba_user', password='nba_password', database='nba_db')
cur = conn.cursor()

print("Cleaning old data...")
cur.execute("SET FOREIGN_KEY_CHECKS = 0")
cur.execute("TRUNCATE TABLE player_stats")
cur.execute("TRUNCATE TABLE games")
cur.execute("TRUNCATE TABLE players")
cur.execute("TRUNCATE TABLE teams")
cur.execute("SET FOREIGN_KEY_CHECKS = 1")
conn.commit()

team_info = {
    'ATL': ('East', 'Southeast'), 'BOS': ('East', 'Atlantic'), 'BKN': ('East', 'Atlantic'),
    'CHA': ('East', 'Southeast'), 'CHI': ('East', 'Central'), 'CLE': ('East', 'Central'),
    'DAL': ('West', 'Southwest'), 'DEN': ('West', 'Northwest'), 'DET': ('East', 'Central'),
    'GSW': ('West', 'Pacific'), 'HOU': ('West', 'Southwest'), 'IND': ('East', 'Central'),
    'LAC': ('West', 'Pacific'), 'LAL': ('West', 'Pacific'), 'MEM': ('West', 'Southwest'),
    'MIA': ('East', 'Southeast'), 'MIL': ('East', 'Central'), 'MIN': ('West', 'Northwest'),
    'NOP': ('West', 'Southwest'), 'NYK': ('East', 'Atlantic'), 'OKC': ('West', 'Northwest'),
    'ORL': ('East', 'Southeast'), 'PHI': ('East', 'Atlantic'), 'PHX': ('West', 'Pacific'),
    'POR': ('West', 'Northwest'), 'SAC': ('West', 'Pacific'), 'SAS': ('West', 'Southwest'),
    'TOR': ('East', 'Atlantic'), 'UTA': ('West', 'Northwest'), 'WAS': ('East', 'Southeast')
}

print("Fetching teams...")
for t in tqdm(teams.get_teams(), desc="Teams"):
    conf, div = team_info.get(t['abbreviation'], ('', ''))
    cur.execute(f"""
        INSERT INTO teams(team_id, team_name, abbreviation, city, conference, division)
        VALUES({t['id']}, '{t['full_name']}', '{t['abbreviation']}', '{t['city']}', '{conf}', '{div}')
        ON DUPLICATE KEY UPDATE
            team_name=VALUES(team_name),
            conference=VALUES(conference),
            division=VALUES(division)
    """)
conn.commit()

cur.execute("SELECT team_id, abbreviation FROM teams")
team_map = {r[1]: r[0] for r in cur.fetchall()}

print("\nFetching players...")
all_players = players.get_active_players()[:PLAYER_LIMIT]
for p in tqdm(all_players, desc="Players"):
    result = try_api(lambda pid=p['id']: commonplayerinfo.CommonPlayerInfo(player_id=pid, timeout=10).get_data_frames()[0])
    if result is not None and len(result):
        r = result.iloc[0]
        tid = team_map.get(r.get('TEAM_ABBREVIATION','')) or 'NULL'
        pos = r.get('POSITION','').replace("'", "''")
        h = r.get('HEIGHT','')
        w = int(r['WEIGHT']) if r.get('WEIGHT') else 'NULL'
        bd = f"'{datetime.strptime(str(r.get('BIRTHDATE',''))[:10], '%Y-%m-%d').date()}'" if r.get('BIRTHDATE') else 'NULL'
        name = p['full_name'].replace("'", "''")
        cur.execute(f"""
            INSERT INTO players VALUES({p['id']}, '{name}', {tid}, '{pos}', '{h}', {w}, {bd})
            ON DUPLICATE KEY UPDATE player_name=VALUES(player_name)
        """)
    time.sleep(0.2)
conn.commit()

print("\nFetching games...")
df = leaguegamefinder.LeagueGameFinder(season_nullable='2025-26', league_id_nullable='00').get_data_frames()[0]
g = {}
for _, r in df.iterrows():
    gid = r['GAME_ID']
    if gid not in g:
        g[gid] = {'date': r['GAME_DATE'], 'tid': r['TEAM_ID'], 'pts': r['PTS'], 'm': r['MATCHUP']}
    else:
        if '@' in r['MATCHUP']:
            g[gid]['a_id'], g[gid]['a_s'], g[gid]['h_id'], g[gid]['h_s'] = r['TEAM_ID'], r['PTS'], g[gid]['tid'], g[gid]['pts']
        else:
            g[gid]['h_id'], g[gid]['h_s'], g[gid]['a_id'], g[gid]['a_s'] = r['TEAM_ID'], r['PTS'], g[gid]['tid'], g[gid]['pts']

for gid, x in tqdm(list(g.items()), desc="Games"):
    if 'h_id' in x and gid.startswith('002'):
        try:
            d = datetime.strptime(x['date'], '%Y-%m-%d').date()
            cur.execute(f"""
                INSERT INTO games VALUES('{gid}', '{d}', {x['h_id']}, {x['a_id']}, {x['h_s']}, {x['a_s']}, '2025-26')
                ON DUPLICATE KEY UPDATE home_score=VALUES(home_score)
            """)
        except: pass
conn.commit()

print("\nFetching player stats...")
cur.execute(f"SELECT player_id FROM players LIMIT {PLAYER_LIMIT}")
pids = [r[0] for r in cur.fetchall()]
cur.execute("SELECT game_id FROM games")
gids = set(str(r[0]) for r in cur.fetchall())
print(f"Found {len(gids)} games, {len(pids)} players")

stats_count = 0
failed_players = []
for pid in tqdm(pids, desc="Stats"):
    df = try_api(lambda p=pid: playergamelog.PlayerGameLog(player_id=p, season='2025-26', timeout=10).get_data_frames()[0])
    if df is not None and len(df) > 0:
        for _, r in df.iterrows():
            if str(r['Game_ID']) in gids:
                try:
                    matchup = r.get('MATCHUP', '')
                    team_abbr = matchup.split(' ')[0] if matchup else ''
                    tid = team_map.get(team_abbr, 'NULL')
                    cur.execute(f"""
                        INSERT INTO player_stats(player_id, game_id, team_id, points, rebounds, assists, steals, blocks)
                        VALUES({pid}, '{str(r['Game_ID'])}', {tid}, {r.get('PTS',0)}, {r.get('REB',0)}, {r.get('AST',0)}, {r.get('STL',0)}, {r.get('BLK',0)})
                        ON DUPLICATE KEY UPDATE points=VALUES(points), team_id=VALUES(team_id)
                    """)
                    stats_count += 1
                except: pass
    else:
        failed_players.append(pid)
    time.sleep(0.2)
conn.commit()
print(f"Inserted {stats_count} player stats")

if failed_players:
    print(f"Warning: {len(failed_players)} players failed: {failed_players[:5]}...")

cur.close()
conn.close()
print("\nDone!")
