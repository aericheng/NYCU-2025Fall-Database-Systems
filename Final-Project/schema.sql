CREATE DATABASE IF NOT EXISTS nba_db;
USE nba_db;

CREATE TABLE IF NOT EXISTS teams (
    team_id INT PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10),
    city VARCHAR(50),
    conference VARCHAR(10),
    division VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS players (
    player_id INT PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    team_id INT,
    position VARCHAR(20),
    height VARCHAR(10),
    weight INT,
    birth_date DATE,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS games (
    game_id VARCHAR(20) PRIMARY KEY,
    game_date DATE NOT NULL,
    home_team_id INT,
    away_team_id INT,
    home_score INT,
    away_score INT,
    season VARCHAR(10),
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS player_stats (
    stat_id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT NOT NULL,
    game_id VARCHAR(20) NOT NULL,
    team_id INT,
    points INT DEFAULT 0,
    rebounds INT DEFAULT 0,
    assists INT DEFAULT 0,
    steals INT DEFAULT 0,
    blocks INT DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE SET NULL
);
