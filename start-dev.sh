#!/bin/bash

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "tmux is not installed. Please install it first."
    exit 1
fi

# Create a new tmux session named 'sms-bot'
tmux new-session -d -s sms-bot

# Split the window horizontally
tmux split-window -h

# In the left pane, start the FastAPI server
tmux send-keys -t sms-bot:0.0 'uvicorn main:app --reload --port 3030' C-m

# In the right pane, start ngrok
tmux send-keys -t sms-bot:0.1 'ngrok http 3030' C-m

# Attach to the session
tmux attach-session -t sms-bot