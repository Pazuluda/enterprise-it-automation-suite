# EITAS Identity

Ce document décrit la place actuelle de **Keycloak / EITAS Identity** dans l’architecture de Enterprise IT Automation Suite.

Il complète [l’architecture générale](overview.md), [l’architecture de sécurité](security.md), [le backend](backend-api.md) et [le frontend](frontend.md).

## Rôle

La couche d’identité fournit l’authentification OIDC utilisée par les utilisateurs humains du portail EITAS.

Elle est responsable de la session d’identité et de l’émission des jetons utilisés ensuite par le frontend et validés par l’API.

Elle ne remplace pas les contrôles RBAC applicatifs du backend : FastAPI vérifie de nouveau l’identité et les rôles sur les routes protégées.

## Base technologique

EITAS Identity est construit autour de Keycloak.

Le projet `eitas-identity/` suit une stratégie downstream :

- conserver les mécanismes IAM éprouvés de Keycloak ;
- limiter les modifications du cœur amont ;
- privilégier thèmes, configuration, extensions et automatisation ;
- maintenir une identité visuelle et une expérience EITAS propres ;
- conserver une stratégie de mise à jour et de rollback contrôlée.

La base amont documentée dans le projet Identity est Keycloak `26.7.0`.

## Instance principale actuellement utilisée

Lors de l’audit d’architecture, le service principal `keycloak.service` était :

- actif ;
- en cours d’exécution.

L’exposition interne observée est :

- HTTP : `127.0.0.1:8180` ;
- management : `127.0.0.1:9000`.

Nginx expose l’identité principale sous `/auth/` sur l’interface HTTPS EITAS.

Cette instance constitue actuellement le fournisseur OIDC utilisé par le portail et l’API.

## Instance parallèle EITAS Identity

Le dépôt contient également la documentation et les artefacts d’une instance parallèle EITAS Identity destinée au développement et à la validation.

La configuration documentée prévoit notamment :

- service : `eitas-identity-test.service` ;
- HTTP interne : `127.0.0.1:8280` ;
- management : `127.0.0.1:9100` ;
- exposition Nginx sous `/identity-test/`.

### État observé

Lors de l’audit d’architecture :

- la route Nginx `/identity-test/` existait ;
- `eitas-identity-test.service` était **inactif** ;
- aucun listener `8280` ou `9100` actif n’a été observé.

La documentation actuelle ne présente donc pas cette instance parallèle comme un service en cours d’exécution permanent.

Son historique de déploiement et de validation reste utile, mais doit être distingué de l’état runtime présent.

## Intégration frontend

Le frontend utilise `keycloak-js` dans `frontend/src/auth/keycloak.js`.

Cette couche gère notamment :

- l’initialisation de l’authentification ;
- la connexion ;
- la déconnexion ;
- l’accès au jeton ;
- le renouvellement du jeton ;
- la réaction à l’expiration ;
- les informations d’identité et de rôles utiles à l’interface.

Les jetons humains sont transmis à l’API sous forme de Bearer OIDC lorsque la route l’exige.

## Validation backend

L’API valide indépendamment les jetons OIDC.

Les contrôles actuellement documentés comprennent notamment :

- signature `RS256` ;
- issuer attendu ;
- JWKS ;
- client autorisé ;
- contraintes temporelles ;
- sujet OIDC ;
- rôles applicatifs.

Une session valide dans le navigateur ne suffit donc pas à contourner l’autorisation backend.

## Séparation avec les workers

La couche Identity concerne les utilisateurs humains.

Les workers Windows utilisent actuellement une identité technique distincte par `X-API-Key`.

Un token OIDC utilisateur ne doit pas être utilisé comme remplacement de l’identité worker.

Cette séparation est détaillée dans [l’architecture de sécurité](security.md) et [la documentation des agents Windows](windows-agent.md).

## Capacités IAM

Keycloak peut fournir de nombreuses fonctions IAM, notamment les sessions, groupes, rôles, MFA et mécanismes WebAuthn selon sa configuration.

Toutefois, une capacité disponible dans Keycloak ne doit pas être présentée automatiquement comme une capacité intégrée ou obligatoire dans tous les workflows EITAS.

La documentation doit distinguer :

1. les capacités natives disponibles dans la plateforme Identity ;
2. les capacités réellement configurées ;
3. les capacités effectivement consommées et validées par EITAS.

## Documentation interne EITAS Identity

Le composant conserve sa documentation spécialisée sous `eitas-identity/docs/`.

Les documents actuels comprennent :

- `architecture.md` ;
- `deployment-state.md` ;
- `IDENTITY_UPDATE_CENTER.md` ;
- `NOTICE.md` ;
- `test-instance.md` ;
- `theme-packaging.md` ;
- `ui-downstream-architecture.md` ;
- `validation-realm.md`.

Ces documents détaillent le développement downstream, les instances de validation, le packaging du thème, le centre de mise à jour et les contraintes propres au composant.

Ils ne doivent pas être confondus avec la présente documentation d’architecture globale, qui décrit l’intégration Identity dans EITAS.

## Centre de mise à jour

EITAS Identity possède une documentation dédiée au centre de mise à jour.

Une mise à jour Identity doit rester une opération contrôlée : la présence d’un mécanisme ou d’un bouton d’administration ne doit pas transformer une mise à niveau IAM en mise à jour Production aveugle.

Les procédures de vérification, sauvegarde, compatibilité et rollback restent nécessaires avant toute bascule.

## Séparation downstream / amont

La stratégie downstream vise à conserver une base Keycloak identifiable et maintenable tout en ajoutant les éléments propres à EITAS.

Cette séparation facilite :

- le suivi des versions amont ;
- l’analyse des différences ;
- la reconstruction ;
- les mises à jour ;
- le rollback ;
- la conservation des obligations de licence et de notice.

## État documentaire

Certains documents internes historiques emploient encore des termes comme `prévu` ou décrivent une instance parallèle qui a été validée à une étape antérieure.

La source de vérité runtime lors du dernier audit est la suivante :

- `keycloak.service` : actif ;
- `8180` et `9000` : listeners loopback actifs ;
- `eitas-identity-test.service` : inactif ;
- `8280` et `9100` : non observés en écoute ;
- route Nginx `/identity-test/` : présente.

Ces informations devront être réévaluées après tout nouveau déploiement Identity.

## Maintenance

Ce document doit être mis à jour après validation de tout changement portant sur :

- le fournisseur OIDC principal ;
- les ports internes ;
- l’exposition Nginx ;
- la version de base Keycloak ;
- le mécanisme d’intégration frontend ;
- la validation backend des jetons ;
- l’activation de l’instance parallèle ;
- la stratégie de mise à jour ou de rollback.
