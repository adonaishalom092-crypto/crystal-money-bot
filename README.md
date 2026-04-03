# Crystal Money Bot - Render Deployment

## Variables d'environnement
- `TELEGRAM_TOKEN` : Ton token Telegram Bot

## Déploiement Render

1. Crée un **Background Worker**
2. Build Command : `pip install -r requirements.txt`
3. Start Command : `python main.py`
4. Ajoute la variable d'environnement `TELEGRAM_TOKEN` sur Render
5. Déploie et vérifie les logs → tu devrais voir `Bot en ligne...`
