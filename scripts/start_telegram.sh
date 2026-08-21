#!/usr/bin/env bash
set -e

echo "🚀 Starting SwaraSetu Backend & Telegram Tunnel..."

# 1. Start FastAPI Backend in background
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

# 3. Start LocalTunnel with fixed subdomain
echo "🌐 Starting LocalTunnel (swarasetu-live.loca.lt)..."
npx -y localtunnel --port 8000 --subdomain swarasetu-live &
TUNNEL_PID=$!

sleep 2

# 4. Register Telegram Webhook
python3 -c "
import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv('.env')
load_dotenv('backend/.env')

token = os.getenv('TELEGRAM_BOT_TOKEN')
secret = os.getenv('TELEGRAM_WEBHOOK_SECRET', 'swarasetu_tg_sec_98f12a3d4c')
webhook_url = 'https://swarasetu-live.loca.lt/channels/telegram'

if token:
    try:
        set_url = f'https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}&secret_token={secret}&drop_pending_updates=True'
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
