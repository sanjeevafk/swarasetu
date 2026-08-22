#!/usr/bin/env bash
set -e

echo "🚀 Starting SwaraSetu Backend & Telegram Tunnel..."

# 1. Clear any stale process on port 8000 & start FastAPI Backend in background
fuser -k 8000/tcp 2>/dev/null || true
PYTHONPATH=backend python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BE_PID=$!

# Trap signals to cleanup background processes on Ctrl+C
cleanup() {
    echo ""
    echo "🛑 Shutting down SwaraSetu Backend & Tunnel..."
    kill $BE_PID 2>/dev/null || true
    kill $TUNNEL_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 2. Wait for backend to be healthy
echo "⏳ Waiting for backend to start..."
until curl -s http://localhost:8000/health > /dev/null; do
    sleep 0.5
done
echo "✅ Backend running on http://localhost:8000"

# 3. Start LocalTunnel and capture assigned public URL
echo "🌐 Starting LocalTunnel..."
LT_LOG=$(mktemp)
npx -y localtunnel --port 8000 --subdomain swarasetu-live > "$LT_LOG" 2>&1 &
TUNNEL_PID=$!

# Wait for localtunnel URL
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

# 4. Register Telegram Webhook with actual tunnel URL
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

echo "🤖 Telegram Bot is LIVE! (Press Ctrl+C to stop)"
wait $BE_PID $TUNNEL_PID
