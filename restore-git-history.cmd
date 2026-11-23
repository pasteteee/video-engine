@echo off
REM Restores the git history (7 commits) into this folder. Needs Git for Windows.
cd /d "%~dp0"
if exist .git (echo .git already exists, nothing to do & exit /b 0)
git init -q
git fetch -q face-engine-history.bundle master
git reset -q FETCH_HEAD
git log --oneline
