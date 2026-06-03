@echo off
chcp 65001 >nul
title VR Phobia — Mock (no EEG)
cd /d "%~dp0"
set PHOBIAS_MOCK=1
set ELECTRON_RUN_AS_NODE=
call "%~dp0run-experiment.bat" --mock
