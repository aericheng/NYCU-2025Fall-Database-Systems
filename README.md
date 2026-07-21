# Introduction to Database Systems — NYCU, Fall 2025

國立陽明交通大學「資料庫系統概論」課程期末專題

## Course Info ｜ 課程資訊

- **Institution:** National Yang Ming Chiao Tung University (NYCU 國立陽明交通大學)
- **Semester:** Fall 2025（114學年度第1學期）
- **Course:** Introduction to Database Systems 資料庫系統概論（undergraduate course, 資訊工程學系）
- **Instructor:** 王邦任 Dennis Wang
- **Field:** Database Systems

## Overview

This repository collects the final project for the NYCU Introduction to
Database Systems course: an NBA statistics web application built with Flask
and a MySQL-backed relational schema. The system ingests official NBA
data via `nba_api` (teams, players, games, and per-player performance stats)
and exposes a web UI for CRUD operations plus advanced queries such as
player-to-player comparison, statistical leaderboards, team standings, and
head-to-head matchup history. This was a team project; the commit history
below has been preserved from the original team repository.
本專題為修課團隊之期末專案，一個以 Flask 網頁框架與資料庫建置的 NBA 數據管理系統。

## Contents ｜ 內容

| Folder | Topic | Summary |
|--------|-------|---------|
| [Final-Project](Final-Project/) | NBA Database System（NBA 數據管理系統） | Flask + MySQL web application for managing NBA teams, players, games, and stats, with CRUD, player comparison, leaderboards, and head-to-head query features. |

## Notes

`Final-Project/` keeps its own original README with full schema design,
motivation, and setup instructions — please refer to it before running any
code. After the database and data-import steps described there are done,
start the web app itself with `python main.py` (Flask dev server). Commit
history has been preserved from the original team repository; this was a
team-authored final project.
