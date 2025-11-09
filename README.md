# Discord bot

Proof of concept of a discord bot that gets song from a playlist and posts it to a specific channel

## How to run

```bash
cp .env.example .env
```

1. Get your own discord bot token from discord developer portal and add it to the .env file
2. Go to spotify for developers dashboard, create and insert the app clientID/secret to .env

### Docker

```bash
sudo docker compose up
```

### Local

```bash
pip install -r -requirements.txt
```

```bash
python main.py
```
