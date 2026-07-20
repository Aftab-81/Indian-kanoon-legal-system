@echo off
title MCP Server - Indian Kanoon
color 0A

echo.
echo  ====================================================
echo    Indian Kanoon MCP Server
echo    This exposes tools that AI models can call.
echo  ====================================================
echo.

cd /d "%~dp0mcp_server"
python server.py

