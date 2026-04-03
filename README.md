# Crystal Money Bot

Bot Telegram “Crystal Money” pour gagner des FCFA quotidiens et gérer les références.

Ce projet est conçu pour être déployé sur **Render Web Service gratuit** avec **polling**.

---

## 🔹 Fonctionnalités

- `/start` : Commence à utiliser le bot et vérifie l’abonnement au canal.  
- `/bonus` : Réclame un bonus quotidien de 25 FCFA.  
- `/solde` : Affiche le solde actuel.  
- `/refer` : Fournit ton lien de parrainage pour inviter des amis.  

---

## 🔹 Prérequis

- Python 3.10 ou supérieur  
- aiogram  
- aiohttp  
- SQLite (inclus dans Python standard)

---

## 🔹 Variables d’environnement

| Nom | Valeur |
|-----|--------|
| TELEGRAM_TOKEN | Ton token Telegram Bot (ex: 123456789:ABCdefGhIjklMNOpqrsTUVwxyZ) |

> ⚠️ Ne mets jamais ton token directement dans le code si tu publies le projet sur GitHub.

---

## 🔹 Déploiement sur Render (Web Service gratuit)

1. Crée un **Web Service** sur Render.  
2. Connecte ton dépôt GitHub contenant le projet.  
3. Configure les commandes :  
   - **Build Command** :  
     ```bash
     pip install -r requirements.txt
     ```  
   - **Start Command** :  
     ```bash
     python main.py
     ```  
4. Ajoute la variable d’environnement `TELEGRAM_TOKEN` avec ton token Telegram.  
5. Déploie le service.  
6. Vérifie les logs → tu devrais voir :
