from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
import mysql.connector
import csv
import io

app = Flask(__name__)
app.secret_key = 'secret'

def query(sql):
    conn = mysql.connector.connect(host='127.0.0.1', user='nba_user', password='nba_password', database='nba_db')
    cur = conn.cursor(dictionary=True)
    cur.execute(sql)
    res = cur.fetchall() if sql.strip()[0] == 'S' else conn.commit()
    cur.close()
    conn.close()
    return res

@app.route('/')
def index():
    return render_template('index.html', c={
        'teams': query("SELECT COUNT(*) c FROM teams")[0]['c'],
        'players': query("SELECT COUNT(*) c FROM players")[0]['c'],
        'games': query("SELECT COUNT(*) c FROM games")[0]['c'],
        'stats': query("SELECT COUNT(*) c FROM player_stats")[0]['c']
    })

@app.route('/teams')
def teams_list():
    return render_template('teams.html', t=query("SELECT * FROM teams ORDER BY team_name"))

@app.route('/players')
def players_list():
    return render_template('players.html', p=query("SELECT p.*, t.team_name, t.abbreviation t_abbr FROM players p LEFT JOIN teams t ON p.team_id = t.team_id ORDER BY player_name"))

@app.route('/players/search')
def players_search():
    k = request.args.get('q', '')
    return render_template('players.html', p=query(f"SELECT p.*, t.team_name, t.abbreviation t_abbr FROM players p LEFT JOIN teams t ON p.team_id = t.team_id WHERE player_name LIKE '%{k}%'") if k else [], k=k)

@app.route('/players/<int:id>')
def players_detail(id):
    r = query(f"""
        SELECT p.*, t.team_name, t.abbreviation t_abbr
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE player_id = {id}
    """)
    if not r:
        return redirect(url_for('players_list'))
    avg = query(f"""
        SELECT ROUND(AVG(points),1) ppg, ROUND(AVG(rebounds),1) rpg,
        ROUND(AVG(assists),1) apg, ROUND(AVG(steals),1) spg,
        ROUND(AVG(blocks),1) bpg, COUNT(*) gp
        FROM player_stats WHERE player_id={id}
    """)[0]
    return render_template('player_detail.html', x=r[0], avg=avg)

@app.route('/players/add', methods=['GET', 'POST'])
def players_add():
    if request.method == 'POST':
        f = request.form
        id = (query("SELECT MAX(player_id) m FROM players")[0]['m'] or 0) + 1
        b = f"'{f['b']}'" if f['b'] else 'NULL'
        query(f"INSERT INTO players VALUES ({id}, '{f['n']}', {f['t'] or 'NULL'}, '{f['pos']}', '{f['h']}', {f['w'] or 'NULL'}, {b})")
        flash('ok')
        return redirect(url_for('players_list'))
    return render_template('player_form.html', t=query("SELECT * FROM teams ORDER BY team_name"))

@app.route('/players/<int:id>/edit', methods=['GET', 'POST'])
def players_edit(id):
    if request.method == 'POST':
        f = request.form
        query(f"UPDATE players SET player_name='{f['n']}', team_id={f['t'] or 'NULL'}, position='{f['pos']}', height='{f['h']}', weight={f['w'] or 'NULL'} WHERE player_id={id}")
        flash('ok')
        return redirect(url_for('players_detail', id=id))
    r = query(f"SELECT p.*, t.team_name FROM players p LEFT JOIN teams t ON p.team_id = t.team_id WHERE player_id = {id}")
    return render_template('player_form.html', x=r[0], t=query("SELECT * FROM teams ORDER BY team_name"))

@app.route('/players/<int:id>/delete', methods=['POST'])
def players_delete(id):
    query(f"DELETE FROM players WHERE player_id={id}")
    flash('ok')
    return redirect(url_for('players_list'))

@app.route('/games')
def games_list():
    return render_template('games.html', g=query("""
        SELECT g.*, h.abbreviation h_abbr, a.abbreviation a_abbr
        FROM games g
        LEFT JOIN teams h ON g.home_team_id=h.team_id
        LEFT JOIN teams a ON g.away_team_id=a.team_id
        WHERE g.game_id IN (SELECT DISTINCT game_id FROM player_stats)
        ORDER BY game_date DESC
        LIMIT 100
    """))

@app.route('/stats')
def stats_list():
    s = request.args.get('sort', 'points')
    o = request.args.get('order', 'DESC')
    valid = ['points', 'rebounds', 'assists', 'steals', 'blocks']
    if s not in valid:
        s = 'points'
    if o not in ['ASC', 'DESC']:
        o = 'DESC'
    pts = query("""
        SELECT ps.points, p.player_name, p.player_id
        FROM player_stats ps JOIN players p ON ps.player_id=p.player_id
        ORDER BY ps.points DESC LIMIT 5
    """)
    reb = query("""
        SELECT ps.rebounds, p.player_name, p.player_id
        FROM player_stats ps JOIN players p ON ps.player_id=p.player_id
        ORDER BY ps.rebounds DESC LIMIT 5
    """)
    ast = query("""
        SELECT ps.assists, p.player_name, p.player_id
        FROM player_stats ps JOIN players p ON ps.player_id=p.player_id
        ORDER BY ps.assists DESC LIMIT 5
    """)
    return render_template('stats.html', d=query(f"SELECT ps.*, p.player_name, t.abbreviation t_abbr, g.game_date FROM player_stats ps JOIN players p ON ps.player_id=p.player_id LEFT JOIN teams t ON p.team_id=t.team_id JOIN games g ON ps.game_id=g.game_id ORDER BY {s} {o} LIMIT 50"), s=s, o=o, pts=pts, reb=reb, ast=ast)

@app.route('/teams/<int:id>')
def teams_detail(id):
    t = query(f"SELECT * FROM teams WHERE team_id = {id}")
    if not t:
        return redirect(url_for('teams_list'))
    players = query(f"SELECT * FROM players WHERE team_id = {id} ORDER BY player_name")
    wins = query(f"""
        SELECT COUNT(*) c FROM games
        WHERE season='2025-26' AND ((home_team_id={id} AND home_score>away_score)
        OR (away_team_id={id} AND away_score>home_score))
    """)[0]['c']
    losses = query(f"""
        SELECT COUNT(*) c FROM games
        WHERE season='2025-26' AND ((home_team_id={id} AND home_score<away_score)
        OR (away_team_id={id} AND away_score<home_score))
    """)[0]['c']
    return render_template('team_detail.html', t=t[0], players=players, wins=wins, losses=losses)

@app.route('/games/<id>')
def games_detail(id):
    g = query(f"""
        SELECT g.*, h.team_name h_name, h.abbreviation h_abbr,
        a.team_name a_name, a.abbreviation a_abbr
        FROM games g
        LEFT JOIN teams h ON g.home_team_id=h.team_id
        LEFT JOIN teams a ON g.away_team_id=a.team_id
        WHERE game_id='{id}'
    """)
    if not g:
        return redirect(url_for('games_list'))
    stats = query(f"""
        SELECT ps.*, p.player_name, t.abbreviation t_abbr
        FROM player_stats ps
        JOIN players p ON ps.player_id=p.player_id
        LEFT JOIN teams t ON ps.team_id=t.team_id
        WHERE ps.game_id='{id}'
        ORDER BY ps.team_id, ps.points DESC
    """)
    return render_template('game_detail.html', g=g[0], stats=stats)

@app.route('/players/filter')
def players_filter():
    tid = request.args.get('team', '')
    pos = request.args.get('pos', '')
    sql = """
        SELECT p.*, t.team_name, t.abbreviation t_abbr
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE 1=1
    """
    if tid:
        sql += f" AND p.team_id = {tid}"
    if pos:
        sql += f" AND p.position LIKE '%{pos}%'"
    sql += " ORDER BY player_name"
    return render_template('players_filter.html', p=query(sql), teams=query("SELECT * FROM teams ORDER BY team_name"), tid=tid, pos=pos)

@app.route('/compare')
def compare():
    ids = [i for i in request.args.getlist('id') if i]
    players = []
    for pid in ids[:2]:
        p = query(f"""
            SELECT p.*, t.team_name
            FROM players p
            LEFT JOIN teams t ON p.team_id=t.team_id
            WHERE player_id={pid}
        """)
        if p:
            avg = query(f"""
                SELECT ROUND(AVG(points),1) ppg, ROUND(AVG(rebounds),1) rpg,
                ROUND(AVG(assists),1) apg, ROUND(AVG(steals),1) spg,
                ROUND(AVG(blocks),1) bpg, COUNT(*) gp
                FROM player_stats WHERE player_id={pid}
            """)[0]
            players.append({**p[0], **avg})
    all_players = query("SELECT player_id, player_name FROM players ORDER BY player_name")
    return render_template('compare.html', players=players, all_players=all_players, ids=ids)

@app.route('/leaders')
def leaders():
    cat = request.args.get('cat', 'points')
    valid = ['points', 'rebounds', 'assists', 'steals', 'blocks']
    if cat not in valid:
        cat = 'points'
    leaders = query(f"""
        SELECT p.player_id, p.player_name, t.abbreviation t_abbr,
        ROUND(AVG(ps.{cat}),1) avg_val, COUNT(*) gp
        FROM player_stats ps
        JOIN players p ON ps.player_id=p.player_id
        LEFT JOIN teams t ON p.team_id=t.team_id
        GROUP BY p.player_id
        ORDER BY avg_val DESC LIMIT 20
    """)
    return render_template('leaders.html', leaders=leaders, cat=cat)

@app.route('/players/<int:id>/chart')
def players_chart(id):
    p = query(f"SELECT * FROM players WHERE player_id={id}")
    if not p:
        return redirect(url_for('players_list'))
    stats = query(f"""
        SELECT ps.points, ps.rebounds, ps.assists, g.game_date
        FROM player_stats ps
        JOIN games g ON ps.game_id=g.game_id
        WHERE ps.player_id={id}
        ORDER BY g.game_date
    """)
    return render_template('player_chart.html', p=p[0], stats=stats)

@app.route('/export/players')
def export_players():
    data = query("""
        SELECT p.player_id, p.player_name, t.team_name, p.position, p.height, p.weight
        FROM players p
        LEFT JOIN teams t ON p.team_id=t.team_id
        ORDER BY player_name
    """)
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(['ID', 'Name', 'Team', 'Position', 'Height', 'Weight'])
    for r in data:
        w.writerow([r['player_id'], r['player_name'], r['team_name'] or '', r['position'] or '', r['height'] or '', r['weight'] or ''])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=players.csv'})

@app.route('/export/stats')
def export_stats():
    data = query("""
        SELECT p.player_name, g.game_date, ps.points, ps.rebounds,
        ps.assists, ps.steals, ps.blocks
        FROM player_stats ps
        JOIN players p ON ps.player_id=p.player_id
        JOIN games g ON ps.game_id=g.game_id
        ORDER BY g.game_date DESC, ps.points DESC
    """)
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(['Player', 'Date', 'PTS', 'REB', 'AST', 'STL', 'BLK'])
    for r in data:
        w.writerow([r['player_name'], r['game_date'], r['points'], r['rebounds'], r['assists'], r['steals'], r['blocks']])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=stats.csv'})

@app.route('/standings')
def standings():
    teams = query("""
        SELECT t.team_id, t.team_name, t.abbreviation, t.conference,
        (SELECT COUNT(*) FROM games WHERE season='2025-26' AND ((home_team_id=t.team_id AND home_score>away_score) OR (away_team_id=t.team_id AND away_score>home_score))) as wins,
        (SELECT COUNT(*) FROM games WHERE season='2025-26' AND ((home_team_id=t.team_id AND home_score<away_score) OR (away_team_id=t.team_id AND away_score<home_score))) as losses
        FROM teams t
        ORDER BY wins DESC
    """)
    for t in teams:
        total = t['wins'] + t['losses']
        t['pct'] = round(t['wins'] / total, 3) if total > 0 else 0
    return render_template('standings.html', teams=teams)

@app.route('/headtohead')
def headtohead():
    t1 = request.args.get('t1', '')
    t2 = request.args.get('t2', '')
    games = []
    if t1 and t2:
        games = query(f"""
            SELECT g.*, h.abbreviation h_abbr, a.abbreviation a_abbr
            FROM games g
            LEFT JOIN teams h ON g.home_team_id=h.team_id
            LEFT JOIN teams a ON g.away_team_id=a.team_id
            WHERE (g.home_team_id={t1} AND g.away_team_id={t2})
            OR (g.home_team_id={t2} AND g.away_team_id={t1})
            ORDER BY g.game_date DESC
        """)
    all_teams = query("SELECT team_id, team_name, abbreviation FROM teams ORDER BY team_name")
    return render_template('headtohead.html', games=games, teams=all_teams, t1=t1, t2=t2)


@app.route('/api/players')
def api_players():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    players = query(f"""
        SELECT player_id, player_name
        FROM players
        WHERE player_name LIKE '%{q}%'
        LIMIT 10
    """)
    return jsonify(players)

if __name__ == '__main__':
    app.run(debug=True)
