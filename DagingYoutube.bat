@echo off
setlocal EnableDelayedExpansion
title Daging YouTube
cd /d "%~dp0"

echo.
echo  ==========================================
echo    DAGING YOUTUBE - Pembahasan Lengkap
echo  ==========================================
echo.
set "URL="
set /p "URL=  Paste URL YouTube (Enter kosong = buka agent saja): "

echo.
echo  Pilih agent:  1 = Claude Code   2 = Antigravity
set "AGENT=1"
set /p "AGENT=  Pilihan [1]: "

set "PERINTAH=Baca file .claude/skills/daging/SKILL.md lalu ikuti seluruh alurnya sampai PDF selesai. Input ($ARGUMENTS): !URL!"

if "!AGENT!"=="2" goto antigravity

:claude
if "!URL!"=="" (claude) else (claude "/daging !URL!")
goto selesai

:antigravity
if "!URL!"=="" (agy) else (agy --mode accept-edits -i "!PERINTAH!")
goto selesai


:selesai
endlocal
