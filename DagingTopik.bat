@echo off
setlocal EnableDelayedExpansion
title Daging Topik
cd /d "%~dp0"

echo.
echo  ==========================================
echo    DAGING TOPIK - Riset Mendalam
echo  ==========================================
echo.
echo  Contoh: sejarah ekonomi Jepang pasca Perang Dunia II
echo          sistem moneter Indonesia, fokus era reformasi
echo.
set "TOPIK="
set /p "TOPIK=  Topik (Enter kosong = buka agent saja): "
if not "!TOPIK!"=="" set "TOPIK=!TOPIK:"='!"

echo.
echo  Pilih agent:  1 = Claude Code   2 = Antigravity
set "AGENT=1"
set /p "AGENT=  Pilihan [1]: "

set "PERINTAH=Baca file .claude/skills/riset/SKILL.md lalu ikuti seluruh alurnya sampai PDF selesai. Input ($ARGUMENTS): !TOPIK!"

if "!AGENT!"=="2" goto antigravity

:claude
if "!TOPIK!"=="" (claude) else (claude "/riset !TOPIK!")
goto selesai

:antigravity
if "!TOPIK!"=="" (agy) else (agy --mode accept-edits -i "!PERINTAH!")
goto selesai


:selesai
endlocal
