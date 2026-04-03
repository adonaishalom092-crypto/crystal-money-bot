# Crystal Money Bot - Render Deployment

## Variables d'environnement
- `8489287711:AAE11z079C4RrbpJHr1Rq5Iatx1ZHuYd7DM` : Ton token Telegram Bot

## Déploiement Render

1. Crée un **Background Worker**
2. Build Command : `pip install -r requirements.txt`
3. Start Command : `python main.py`
4. Ajoute la variable d'environnement `TELEGRAM_TOKEN` sur Render
5. Déploie et vérifie les logs → tu devrais voir `Bot en ligne...`
