#!/usr/bin/env bash
# Runs SwaraSetu Telegram Bot in a detached tmux session so it survives terminal closing.

SESSION_NAME="swarasetu_telegram"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️ Telegram bot is already running in tmux session '$SESSION_NAME'."
    echo "👉 Attach with: tmux attach -t $SESSION_NAME"
    echo "👉 Kill with:   tmux kill-session -t $SESSION_NAME"
    exit 0
fi

echo "🚀 Launching Telegram bot inside detached tmux session: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME" "cd $(pwd) && PYTHONPATH=backend python3 backend/scripts/run_telegram_poller.py"
echo "✅ Bot is now running 24/7 in the background!"
echo "👉 To view live logs:  tmux attach -t $SESSION_NAME"
echo "👉 To stop the bot:   tmux kill-session -t $SESSION_NAME"
