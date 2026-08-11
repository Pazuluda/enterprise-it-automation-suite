# Architecture générale EITAS

Ce document décrit l’architecture actuellement déployée et vérifiée de **Enterprise IT Automation Suite (EITAS)**. Il constitue la référence d’architecture générale ; les objectifs futurs et anciens plans de migration sont documentés séparément.

## Vue d’ensemble

EITAS sépare le portail utilisateur, l’API, l’identité, les données runtime, les workers Windows et Active Directory.

```text
Utilisateur
    |
    | HTTPS :62443
    v
  Nginx
    |
    +---- Portail React
    |
    +---- API FastAPI :8000 (loopback)
    |        |
    |        +---- OIDC Bearer + RBAC pour les humains
    |        +---- X-API-Key pour les workers Windows
    |
    +---- Keycloak / EITAS Identity :8180 (loopback)
             |
             +---- management :9000 (loopback)

API EITAS
    |
    +---- données runtime : /var/lib/eitas
    |
    v
Workers PowerShell Windows Server
    |
    v
Microsoft Active Directory
```

## Composants principaux

| Composant | Technologie ou rôle | État actuel |
|---|---|---|
| Portail | React 19 | Déployé |
| Build frontend | Vite 8 | Utilisé pour le développement et la construction des assets |
| Reverse proxy | Nginx | Exposé en HTTPS sur le port 62443 |
| API | Python / FastAPI | Active sur 127.0.0.1:8000 |
| Identité | Keycloak / EITAS Identity | Instance principale active |
| Workers | PowerShell sur Windows Server | Actifs selon leurs tâches dédiées |
| Annuaire | Microsoft Active Directory | Cible des opérations contrôlées |
| Données runtime | /var/lib/eitas | Séparées du code source |

## Exposition réseau

### Interface publique

Nginx constitue la frontière HTTP/HTTPS publique d’EITAS.

L’instance observée écoute sur le port HTTPS `62443`. Le portail est servi derrière ce reverse proxy et les services internes ne doivent pas être exposés directement aux utilisateurs.

### API

FastAPI écoute sur :

- `127.0.0.1:8000` ;
- aucune écoute publique directe de l’API n’a été observée lors de l’audit documentaire.

Nginx relaie les requêtes nécessaires vers cette API loopback.

### Identité

L’instance d’identité principale observée utilise :

- HTTP interne : `127.0.0.1:8180` ;
- management : `127.0.0.1:9000` ;
- exposition publique via Nginx sous `/auth/`.

Une route Nginx `/identity-test/` existe vers `127.0.0.1:8280`, mais le service `eitas-identity-test.service` était **inactif** lors de l’audit. Cette route ne doit donc pas être présentée comme une instance de test actuellement active.

## Frontend

Le portail utilise React. Vite est utilisé comme outil de développement et de build.

L’exposition de Vite comme serveur de développement n’appartient pas à l’architecture de production. Aucun listener `5173` n’a été observé pendant l’audit.

Les assets frontend de production sont servis derrière Nginx.

## API EITAS

L’API est une application FastAPI exécutée par `eitas-api.service`.

État vérifié :

- utilisateur système : `eitas` ;
- groupe : `eitas` ;
- écoute applicative : `127.0.0.1:8000` ;
- runtime accessible en écriture : `/var/lib/eitas`.

Le service applique actuellement plusieurs protections systemd :

- `UMask=0027` ;
- `NoNewPrivileges=yes` ;
- `PrivateTmp=yes` ;
- `ProtectHome=yes` ;
- `ProtectSystem=strict` ;
- `ReadWritePaths=/var/lib/eitas`.

## Authentification et autorisation

### Utilisateurs humains

Les accès humains utilisent OIDC avec des jetons Bearer validés côté API.

La validation actuelle comprend notamment :

- signature JWT RS256 ;
- issuer OIDC ;
- JWKS ;
- client autorisé ;
- contrôles temporels des jetons ;
- rôles applicatifs contrôlés côté backend.

Le portail ne constitue pas une frontière d’autorisation : l’API réévalue les droits.

### Workers Windows

Les workers Windows utilisent actuellement une authentification dédiée par `X-API-Key`.

Les routes worker peuvent être séparées des routes humaines et certaines frontières refusent explicitement l’authentification OIDC lorsqu’une identité worker est requise.

Le remplacement généralisé de cette authentification par mTLS n’est **pas** documenté comme implémenté aujourd’hui.

## Workers Windows et Active Directory

Les opérations nécessitant Windows Server ou les cmdlets Active Directory sont déportées vers des workers PowerShell.

Cette séparation permet notamment :

- de conserver FastAPI sur Debian sans dépendance aux cmdlets AD ;
- de limiter les opérations Windows à des handlers dédiés ;
- de maintenir des chemins Simulation et Production contrôlés ;
- de renvoyer le résultat d’exécution vers l’API ;
- d’isoler les opérations Active Directory sensibles des dispatchers génériques lorsqu’une frontière dédiée est nécessaire.

## Code, runtime et configuration

Les emplacements actuellement vérifiés sont :

| Usage | Emplacement | Permissions observées |
|---|---|---|
| Code source | `/opt/enterprise-it-automation-suite` | `root:root`, 0775 lors de l’audit |
| Données runtime EITAS | `/var/lib/eitas` | `eitas:eitas`, 0750 |
| Configuration sensible API | `/etc/eitas-api.env` | `root:root`, 0600 |

Les secrets et données runtime ne doivent pas être stockés dans le dépôt Git.

## EITAS Identity

EITAS Identity repose sur Keycloak et fournit l’identité OIDC utilisée par le portail et l’API.

La documentation spécifique au composant reste maintenue sous `eitas-identity/` pendant la présente refonte documentaire.

L’instance principale était active pendant l’audit. L’instance parallèle `eitas-identity-test.service` était arrêtée.

## Éléments non présentés comme implémentés

L’ancien document d’architecture Forteresse contient plusieurs objectifs de sécurité à long terme. L’audit actuel n’a pas identifié d’implémentation applicative généralisée des fonctions suivantes dans le périmètre vérifié :

- mTLS par worker ;
- ABAC complet ;
- élévation JIT généralisée ;
- règle des quatre yeux généralisée ;
- WebAuthn ou FIDO2 comme mécanisme applicatif EITAS propre ;
- stockage applicatif PostgreSQL via psycopg, SQLAlchemy ou asyncpg.

Ces éléments peuvent rester des objectifs ou exister dans des composants externes spécialisés, mais ils ne doivent pas être décrits comme capacités EITAS déployées sans nouvelle validation.

## Principe documentaire

Ce document décrit l’état réellement observé. Les changements futurs d’architecture doivent mettre à jour cette référence après validation de leur déploiement.
