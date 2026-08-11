# Backend et API EITAS

Ce document décrit l’organisation actuelle du backend Python et de l’API FastAPI de **Enterprise IT Automation Suite (EITAS)**.

Il complète [l’architecture générale](overview.md) et [l’architecture de sécurité](security.md).

## Rôle du backend

Le backend constitue la frontière applicative centrale entre :

- le portail React ;
- la couche d’identité OIDC ;
- les données runtime EITAS ;
- les workers Windows ;
- les workflows d’administration et d’automatisation ;
- les mécanismes d’audit et de validation.

Il porte la logique d’autorisation backend et ne délègue pas la décision de sécurité au frontend.

## Point d’entrée FastAPI

L’application FastAPI est actuellement définie dans `api/main.py`.

L’audit du code a identifié :

- l’instanciation principale de `FastAPI` ;
- le montage des fichiers statiques sous `/static` ;
- aucun signal `include_router` dans l’entrypoint audité.

La documentation ne présente donc pas actuellement le backend comme une architecture reposant sur des `APIRouter` séparés tant qu’une telle organisation n’est pas effectivement introduite.

## Organisation du code

Le backend est organisé autour de plusieurs niveaux.

### Core

`api/app/core/` contient les fonctions transverses principales :

- `config.py` : configuration applicative ;
- `security.py` : authentification et autorisation principales ;
- `identity_update_security.py` : sécurité spécialisée du centre de mise à jour Identity ;
- `storage.py` : primitives et chemins de stockage applicatif.

### Modèles

`api/app/models.py` centralise les modèles applicatifs utilisés par l’API et les services.

### Services

`api/app/services/` contient la logique métier et les mécanismes spécialisés.

Les familles actuellement visibles comprennent notamment :

- cycle de vie des collaborateurs ;
- demandes et actions associées ;
- templates ;
- audit ;
- statut et runtime des workers ;
- mode des agents ;
- Explorateur Active Directory ;
- jobs AD ;
- snapshots Active Directory ;
- administration Active Directory ;
- attributs LDAP ;
- HAB Seniority Index ;
- ACL et délégation ;
- Corbeille Active Directory ;
- restauration d’objets supprimés ;
- activation contrôlée de la Corbeille ;
- centre de mise à jour EITAS Identity.

## Découpage des opérations sensibles

Certaines fonctionnalités sensibles disposent d’un découpage beaucoup plus strict qu’un simple appel métier.

La restauration d’objets supprimés, par exemple, possède des services distincts pour plusieurs étapes telles que :

- préflight ;
- autorisation humaine ;
- autorisation technique ;
- persistance de l’autorisation ;
- consommation d’autorisation ;
- challenge et ticket ;
- consommation du ticket ;
- préexécution ;
- contrôle runtime ;
- transport d’exécution ;
- enveloppe Windows WhatIf ;
- enveloppe Windows d’exécution ;
- contrôle après autorisation.

La même philosophie apparaît dans les flux d’activation de la Corbeille et d’ACL/délégation.

Cette séparation permet de limiter les responsabilités de chaque composant et de placer des barrières explicites avant les écritures sensibles.

## Authentification

### Utilisateurs humains

Les utilisateurs humains appellent les routes protégées avec un jeton Bearer OIDC.

La validation est réalisée dans le backend et comprend notamment les contrôles JWT/OIDC documentés dans [l’architecture de sécurité](security.md).

### Workers Windows

Les workers utilisent actuellement `X-API-Key`.

Le backend possède des mécanismes permettant :

- d’accepter une identité OIDC pour les routes humaines ;
- d’accepter une API key pour les routes techniques compatibles ;
- d’exiger explicitement une identité worker sur certaines frontières ;
- de refuser un Bearer OIDC lorsqu’une route est réservée aux workers.

## Autorisation

Le contrôle des rôles est réalisé côté backend.

`api/app/core/security.py` fournit notamment des dépendances d’autorisation basées sur les rôles et des variantes adaptées aux routes pouvant accepter un worker authentifié par API key.

Les flux les plus sensibles ajoutent leurs propres vérifications de contexte, d’identité, de fraîcheur, de ticket ou de confirmation.

## Données runtime

Les données runtime actuelles sont séparées du dépôt et résident sous :

- `/var/lib/eitas`.

Le service FastAPI dispose de l’écriture sur ce périmètre via sa configuration systemd.

La configuration sensible API reste séparée dans `/etc/eitas-api.env`.

L’audit architectural n’a pas identifié de couche applicative généralisée basée sur `psycopg`, `SQLAlchemy` ou `asyncpg`. La documentation ne présente donc pas PostgreSQL comme le stockage principal du backend EITAS actuel.

Cette remarque concerne le backend EITAS lui-même et non les bases utilisées par des composants externes tels que Keycloak / EITAS Identity.

## Interaction avec le frontend

Le frontend consomme l’API derrière Nginx.

L’API constitue la source d’autorité pour :

- les demandes ;
- les workflows ;
- les données Active Directory exposées au portail ;
- les jobs ;
- les contrôles de sécurité ;
- les résultats workers ;
- l’audit ;
- les opérations administratives.

Le frontend peut masquer ou désactiver des actions selon les rôles, mais cette logique ne remplace jamais les contrôles backend.

## Interaction avec les workers

Le backend prépare, persiste ou expose les jobs destinés aux workers Windows selon la fonctionnalité.

Les workers récupèrent les opérations autorisées, exécutent le traitement Windows ou Active Directory correspondant, puis renvoient le résultat vers l’API.

Pour les opérations les plus sensibles, l’enveloppe envoyée au worker peut être spécialisée et liée à des tickets, autorisations ou données validées en amont.

## Service système

L’API de production est exécutée par `eitas-api.service` sous le compte système `eitas:eitas`.

Le service observé lance `/usr/local/libexec/eitas-api-loopback` et expose FastAPI uniquement sur `127.0.0.1:8000`.

Les détails de durcissement systemd sont maintenus dans [l’architecture de sécurité](security.md).

## Principes de maintenance

Lorsqu’une évolution modifie la structure du backend, cette documentation doit être mise à jour après validation réelle.

En particulier, doivent être documentés explicitement :

- l’introduction éventuelle de routers FastAPI modulaires ;
- un changement de stockage persistant ;
- une nouvelle frontière d’authentification ;
- une modification du modèle d’autorisation ;
- une nouvelle catégorie de worker ;
- toute nouvelle chaîne d’autorisation pour une écriture sensible.
