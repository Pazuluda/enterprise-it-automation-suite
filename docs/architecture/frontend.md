# Frontend EITAS

Ce document décrit l’architecture actuelle du portail frontend de **Enterprise IT Automation Suite (EITAS)**.

Il complète [l’architecture générale](overview.md), [l’architecture de sécurité](security.md) et [l’architecture backend](backend-api.md).

## Technologies

Le frontend actuel repose sur :

- React 19 ;
- Vite 8 pour le développement et la construction des assets ;
- `keycloak-js` pour l’intégration OIDC côté navigateur ;
- CSS applicatif organisé par domaines fonctionnels.

Vite n’est pas le serveur frontend de production : les assets construits sont servis derrière Nginx.

## Point d’entrée

Le point d’entrée React est `frontend/src/main.jsx`.

L’audit du code montre que ce fichier :

- crée la racine React avec `createRoot` ;
- initialise l’authentification avant ou autour du démarrage applicatif via `initializeAuthentication` ;
- charge ensuite l’application principale.

Le composant applicatif principal est `frontend/src/App.jsx`.

## Authentification OIDC

La logique d’authentification navigateur est centralisée dans :

- `frontend/src/auth/keycloak.js`.

Cette couche utilise `keycloak-js` et prend notamment en charge :

- l’initialisation de la session ;
- la connexion ;
- la déconnexion ;
- l’accès au jeton courant ;
- le renouvellement du jeton ;
- la réaction à l’expiration du jeton ;
- la réauthentification lorsque nécessaire ;
- l’extraction des informations d’identité et de rôles utiles au portail.

Le jeton obtenu côté navigateur est utilisé pour les appels API nécessitant une identité humaine.

## RBAC côté interface

Le frontend possède également une couche dédiée :

- `frontend/src/auth/rbac.js`.

Elle permet au portail d’adapter l’affichage et la disponibilité des fonctions selon les rôles de l’utilisateur.

Cette logique améliore l’expérience utilisateur mais ne constitue jamais la frontière d’autorisation finale.

L’API FastAPI réévalue les rôles et autorisations sur les routes protégées, conformément à [l’architecture de sécurité](security.md).

## Appels API

Le frontend effectue actuellement ses appels HTTP applicatifs avec `fetch`.

Les appels passent par l’exposition Nginx du portail et de l’API plutôt que par une connexion navigateur directe vers le listener FastAPI `127.0.0.1:8000`.

Pour les routes humaines protégées, les requêtes peuvent inclure le jeton Bearer OIDC obtenu depuis la couche Keycloak.

Le frontend ne possède ni ne doit posséder la clé `X-API-Key` réservée aux workers Windows.

## Organisation des composants

L’audit de `frontend/src/components/` montre des composants dédiés à plusieurs domaines fonctionnels, notamment :

- cycle de vie et nouvelles demandes ;
- offboarding ;
- audit ;
- paramètres ;
- timeline des demandes ;
- résultats des agents ;
- formulaires et aides de saisie ;
- panneaux et éléments d’interface réutilisables.

Une part importante de l’interface applicative reste actuellement concentrée dans `App.jsx`.

La documentation ne présente donc pas le frontend comme une architecture entièrement découpée en pages ou modules indépendants tant que cette refactorisation n’est pas effectivement réalisée.

## Navigation

L’audit DOC-17 n’a pas identifié de signal `BrowserRouter`, `Routes` ou `Route` dans le périmètre frontend vérifié.

La documentation ne suppose donc pas l’utilisation de React Router comme mécanisme de navigation actuel.

Si une bibliothèque de routage est introduite ultérieurement, ce document devra être mis à jour après validation.

## Styles

Les styles frontend sont répartis entre les fichiers généraux `App.css`, `index.css` et plusieurs feuilles spécialisées sous `frontend/src/styles/`.

Les domaines visibles comprennent notamment :

- base ;
- layout ;
- sidebar ;
- formulaires ;
- vue générale ;
- demandes ;
- cycle de vie ;
- Active Directory ;
- agents ;
- administration ;
- utilitaires ;
- responsive ;
- statut workers ;
- authentification.

Cette organisation permet de limiter la concentration de toute la présentation dans une feuille CSS unique.

## Production

En production :

- le navigateur accède au portail via Nginx en HTTPS ;
- les assets React construits sont servis derrière Nginx ;
- le serveur de développement Vite n’appartient pas au chemin de production ;
- aucun listener `5173` n’a été observé lors de l’audit d’architecture.

L’exposition publique observée utilise le port HTTPS `62443`.

## Relation avec EITAS Identity

Le frontend initialise son authentification avec Keycloak / EITAS Identity via `keycloak-js`.

Cette intégration couvre la session navigateur et les jetons utilisés pour l’API.

Les fonctions propres à EITAS Identity, comme l’administration de l’IAM, le thème ou son centre de mise à jour, sont documentées séparément.

## Relation avec le backend

Le frontend présente les données et déclenche les actions disponibles pour l’utilisateur, tandis que le backend reste responsable :

- de la validation de l’identité ;
- de l’autorisation réelle ;
- de la logique métier ;
- des workflows ;
- des jobs ;
- des interactions avec les workers ;
- de l’audit ;
- des barrières précédant les opérations sensibles.

Une action masquée ou désactivée dans le frontend ne remplace jamais un refus backend.

## Limites et évolution

L’architecture frontend actuelle fonctionne, mais certains éléments pourront être restructurés lors de la phase finale de finition du projet.

Toute évolution significative devra préserver :

- l’intégration OIDC ;
- les contrôles RBAC côté interface sans affaiblir ceux du backend ;
- la séparation entre frontend humain et authentification worker ;
- l’absence de secrets techniques dans le bundle navigateur ;
- la construction reproductible des assets ;
- l’exposition de production derrière Nginx.

La documentation devra être mise à jour après toute modification de la navigation, de l’authentification, du découpage des composants ou du pipeline de build.
