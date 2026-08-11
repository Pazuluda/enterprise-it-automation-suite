# Frontend EITAS

Ce répertoire contient le frontend React/Vite de Enterprise IT Automation Suite.

## Rôle

Le frontend fournit notamment le portail EITAS, l’Explorateur Active Directory et les interfaces intégrées aux fonctions d’administration.

L’authentification humaine utilise EITAS Identity via OIDC/PKCE. Les appels API du portail utilisent un Bearer token ; `X-API-Key` reste réservé aux workers techniques concernés.

## Structure

- `src/` : sources React ;
- `public/` : ressources publiques ;
- `dist/` : artefact local produit par le build Vite ;
- `package.json` : scripts et dépendances frontend.

## Développement

Utiliser les scripts déclarés dans `package.json` depuis ce répertoire.

Le serveur Vite de développement ne fait pas partie du runtime Production EITAS et le port 5173 ne doit pas être ouvert comme solution de dépannage en production.

## Build et runtime Production

Le build Vite produit `frontend/dist`.

Dans le runtime actuellement validé, le navigateur accède à Nginx en HTTPS, Nginx relaie vers FastAPI et FastAPI sert l’application depuis `api/static/app` ainsi que les ressources sous `/static/`.

`frontend/dist` n’est donc pas directement la racine web Nginx de production.

Aucun mécanisme générique versionné de synchronisation automatique `frontend/dist` vers `api/static/app` ne doit être supposé. Suivre la procédure de déploiement validée.

## Validation

Avant intégration d’un changement frontend, utiliser les contrôles adaptés au lot concerné, notamment lint/tests/build lorsqu’ils sont applicables, puis vérifier le résultat dans le portail déployé.

Une modification frontend ne doit jamais modifier implicitement le mode global de l’agent ni ouvrir un chemin Production.

## Documentation

- [Architecture frontend](../docs/architecture/frontend.md)
- [Architecture générale](../docs/architecture/overview.md)
- [EITAS Identity](../docs/architecture/identity.md)
- [Configuration](../docs/operations/configuration.md)
- [Déploiement](../docs/operations/deployment.md)
- [Dépannage](../docs/operations/troubleshooting.md)

Le README racine du projet reste le point d’entrée principal pour la présentation générale de EITAS.
