# Enterprise IT Automation Suite

Suite d'automatisation IT pour les entreprises.

Le but du projet est de gérer les arrivées, modifications et départs utilisateurs via une API centrale et un agent Windows Server.

## Etat actuel

Version lab fonctionnelle en simulation.

Fonctionnalités déjà présentes :

- API FastAPI
- Documentation Swagger locale
- Création de demande onboarding
- Validation admin obligatoire
- Agent Windows Server PowerShell
- Statuts de workflow
- Audit logs
- Sécurisation par clé API X-API-Key

## Workflow

request_created
-> waiting_approval
-> request_approved
-> pending
-> request_claimed
-> processing
-> request_completed

## Architecture

Admin / Technicien
-> API FastAPI sur Debian
-> Agent PowerShell Windows Server
-> Simulation AD / futur Active Directory

## Sécurité

Les routes sensibles sont protégées par une clé API.

Exemple :

curl http://127.0.0.1:8000/api/agent/pending -H "X-API-Key: $EITAS_API_KEY"

## Ne jamais pousser sur GitHub

- /etc/eitas-api.env
- agent-windows/config.json
- api/data/requests.json
- api/data/audit.jsonl
- vraies clés API
- mots de passe
- données client réelles

## Prochaines étapes

- Refactoriser le code en plusieurs fichiers
- Ajouter une interface web
- Ajouter les templates modifiables depuis l'API
- Ajouter le mode réel Active Directory
- Ajouter l'offboarding
