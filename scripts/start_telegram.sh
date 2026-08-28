#!/usr/bin/env bash
set -e

MODE="${1:-poll}"

if [ "$MODE" == "--webhook" ] || [ "$MODE" == "webhook" ] || [ "$MODE" == "--tunnel" ]; then
    echo "🚀 Starting SwaraSetu Backend & Telegram Webhook Tunnel..."

    BE_PID=""
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Existing backend detected on http://localhost:8000 (reusing)"
    else
        echo "⏳ Starting FastAPI Backend on port 8000..."
        PYTHONPATH=backend python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
        BE_PID=$!
        until curl -s http://localhost:8000/health > /dev/null 2>&1; do
            sleep 0.5
        done
        echo "✅ Backend running on http://localhost:8000"
    fi

    cleanup() {
        echo ""
        echo "🛑 Shutting down Telegram Tunnel & Services..."
        if [ -n "$BE_PID" ]; then
            kill "$BE_PID" 2>/dev/null || true
        fi
        if [ -n "$TUNNEL_PID" ]; then
            kill "$TUNNEL_PID" 2>/dev/null || true
        fi
        pkill -P $$ 2>/dev/null || true
        rm -f "$LT_LOG" 2>/dev/null || true
        exit 0
    }
    trap cleanup SIGINT SIGTERM

    echo "🌐 Starting LocalTunnel..."
    LT_LOG=$(mktemp)
    npx -y localtunnel --port 8000 --subdomain swarasetu-live > "$LT_LOG" 2>&1 &
    TUNNEL_PID=$!

    TUNNEL_URL=""
    for i in {1..30}; do
        if grep -q "your url is:" "$LT_LOG"; then
            TUNNEL_URL=$(grep "your url is:" "$LT_LOG" | awk '{print $NF}' | tr -d '\r\n')
            break
        fi
        sleep 0.5
    done

    if [ -z "$TUNNEL_URL" ]; then
        TUNNEL_URL="https://swarasetu-live.loca.lt"
    fi

    echo "🌐 LocalTunnel URL: $TUNNEL_URL"

    python3 -c "
import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv('.env')
load_dotenv('backend/.env')

token = os.getenv('TELEGRAM_BOT_TOKEN')
secret = os.getenv('TELEGRAM_WEBHOOK_SECRET')
base_url = '${TUNNEL_URL}'
webhook_url = f'{base_url}/channels/telegram'

if token:
    try:
        secret_param = f'&secret_token={secret}' if secret else ''
        set_url = f'https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}{secret_param}&drop_pending_updates=True'
        req = urllib.request.urlopen(set_url)
        res = json.loads(req.read())
        if res.get('ok'):
            print('✅ Telegram Webhook registered: ' + webhook_url)
        else:
            print('⚠️ Webhook response:', res)
    except Exception as e:
        print('⚠️ Failed to register webhook:', e)
else:
    print('⚠️ TELEGRAM_BOT_TOKEN not found in .env')
"

    echo "🤖 Telegram Bot is LIVE (Webhook mode)! (Press Ctrl+C to stop)"
    while true; do
        sleep 1
    done
else
    # Default: Robust Long-Polling Mode (No tunnels, zero timeouts, 100% uptime)
    echo "🚀 Starting SwaraSetu Telegram Bot in Long-Polling Mode..."
    export PYTHONPATH=backend
    python3 backend/scripts/run_telegram_poller.py
fi
