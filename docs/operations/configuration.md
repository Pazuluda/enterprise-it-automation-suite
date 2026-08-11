# Configuration

Ce document décrit les surfaces de configuration actuellement utilisées par EITAS.

Il distingue volontairement :

- les secrets Linux ;
- les données runtime ;
- la configuration du portail et de l’API ;
- la configuration des workers Windows ;
- la configuration EITAS Identity.

Aucune valeur secrète réelle ne doit être ajoutée à cette documentation ou au dépôt Git.

## Principes

La configuration EITAS suit actuellement trois règles principales :

1. le code reste sous `/opt/enterprise-it-automation-suite` ;
2. les données runtime restent sous `/var/lib/eitas` ;
3. les secrets et paramètres sensibles Linux restent hors du dépôt.

Cette séparation doit être conservée lors des futurs déploiements.

## Configuration sensible de l’API

Le service `eitas-api.service` charge :

```text
/etc/eitas-api.env
```

Ce fichier est actuellement :

- possédé par `root:root` ;
- protégé en mode `0600` ;
- chargé par systemd via `EnvironmentFile`.

Il ne doit jamais être commité.

## Variables API actuellement observées

L’environnement réellement installé expose actuellement les noms de variables suivants :

```text
EITAS_API_KEY
EITAS_DATA_DIR
EITAS_OIDC_ALLOWED_AZP
EITAS_OIDC_AUDIENCE
EITAS_OIDC_CA_CERT
EITAS_OIDC_ISSUER
EITAS_OIDC_JWKS_URL
```

La valeur de ces variables est volontairement exclue de la documentation.

## EITAS_DATA_DIR

`EITAS_DATA_DIR` définit le répertoire runtime utilisé par l’API.

Le déploiement actuel utilise :

```text
/var/lib/eitas
```

Le backend exige un chemin absolu lorsqu’une valeur est fournie.

Les principaux fichiers métier permanents observés comprennent notamment :

```text
requests.json
templates.json
audit.jsonl
agent-config.json
agent-status.json
worker-status.json
worker-events.jsonl
ad-admin-jobs.json
ad-check-jobs.json
ad-lookup-jobs.json
ad-explorer-jobs.json
ad-snapshot.json
ad-domain-catalog.json
```

Les chaînes de sécurité spécialisées C8/C9 maintiennent également leurs propres registres et fichiers de verrouillage dans ce répertoire.

Ces fichiers appartiennent au runtime et ne doivent pas être remplacés par des copies provenant du dépôt sans procédure explicite.

## Clé technique des workers

`EITAS_API_KEY` reste utilisée comme authentification technique pour les workers Windows compatibles avec ce mécanisme.

Elle ne doit pas être présentée comme le mécanisme principal d’authentification des utilisateurs humains.

Le portail humain et les routes humaines utilisent la chaîne OIDC/Bearer décrite dans la documentation de sécurité.

## Configuration OIDC humaine

Les variables OIDC actuellement présentes sont :

```text
EITAS_OIDC_ISSUER
EITAS_OIDC_JWKS_URL
EITAS_OIDC_CA_CERT
EITAS_OIDC_ALLOWED_AZP
EITAS_OIDC_AUDIENCE
```

Elles servent à l’intégration entre l’API et EITAS Identity.

La configuration réellement validée doit rester cohérente avec :

- l’issuer Keycloak ;
- l’URL JWKS ;
- le certificat CA de confiance ;
- les clients autorisés ;
- l’audience attendue lorsqu’elle est utilisée.

Les valeurs exactes dépendent de l’environnement et ne doivent pas être copiées depuis un exemple non validé.

## Configuration du centre de mise à jour Identity

L’environnement installé contient également des variables dédiées au mécanisme spécialisé EITAS Identity Update :

```text
EITAS_IDENTITY_UPDATE_OIDC_ALLOWED_AZP
EITAS_IDENTITY_UPDATE_OIDC_AUDIENCE
EITAS_IDENTITY_UPDATE_OIDC_CA_CERT
EITAS_IDENTITY_UPDATE_OIDC_ISSUER
EITAS_IDENTITY_UPDATE_OIDC_JWKS_URL
EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS
EITAS_IDENTITY_UPDATE_SOURCE_CHECK_REQUEST_FILE
EITAS_IDENTITY_UPDATE_STATUS_FILE
```

Ces variables appartiennent au sous-système Identity Update et ne doivent pas être confondues avec les variables OIDC générales du portail.

Le détail de ce mécanisme reste maintenu sous `eitas-identity/`.

## Limite actuelle de `.env.example`

Le fichier racine :

```text
.env.example
```

ne contient actuellement que :

```text
EITAS_API_KEY
```

Il ne représente donc plus à lui seul l’ensemble de la configuration réellement requise par le runtime moderne EITAS.

Il doit être considéré comme incomplet tant qu’un exemple de configuration non secrète actualisé n’a pas été produit et validé.

## Mode global

Le système possède un mode global dont les valeurs utilisées par les workers historiques sont notamment :

```text
Simulation
Production
```

L’état de référence pour une installation ou une maintenance non explicitement autorisée doit rester :

```text
Simulation
```

Le mode Production ne doit jamais être activé implicitement par une opération de configuration.

Certaines chaînes spécialisées utilisent des tickets et autorisations supplémentaires même lorsque le mode global reste Simulation.

## Configuration Windows

Les workers sont installés actuellement sous :

```text
C:\EnterpriseIT\agent-windows
```

Leur configuration locale attend un fichier :

```text
C:\EnterpriseIT\agent-windows\config.json
```

Ce fichier est une configuration runtime locale et ne doit pas être commité avec des secrets.

## Exemple Windows du dépôt

Le dépôt fournit :

```text
agent-windows/config.example.json
```

L’exemple contient actuellement les propriétés suivantes :

```text
ApiBaseUrl
ApiKey
Mode
PollIntervalSeconds
```

Le worker Employee Lifecycle sait également exploiter des paramètres complémentaires lorsqu’ils existent, notamment un nom d’agent, un nom de tâche et le périmètre OU EITAS.

La configuration réellement installée sur Windows doit toujours être considérée comme la source de vérité avant toute modification.

## Limite actuelle de `config.example.json`

Le `config.example.json` présent dans le dépôt référence encore historiquement :

```text
http://10.10.10.11:8000
```

Cette adresse ne correspond plus à l’exposition Linux durcie actuelle, puisque FastAPI écoute désormais uniquement sur `127.0.0.1:8000`.

Cet exemple ne doit donc **pas être copié tel quel** sur une nouvelle installation.

Sa correction sera traitée séparément après validation du chemin réseau réellement utilisé par les workers Windows installés.

## Polling Windows

Les workers spécialisés possèdent leurs propres paramètres de polling.

Les valeurs par défaut actuellement présentes dans le code sont :

| Worker | Polling par défaut | Heartbeat par défaut |
|---|---:|---:|
| AD Admin | 1 seconde | 60 secondes |
| AD Check | 5 secondes | 60 secondes |
| AD Lookup | 250 ms | 60 secondes |

AD Lookup possède également par défaut :

- snapshot AD toutes les `5` secondes ;
- catalogue domaine toutes les `15` secondes.

Ces valeurs sont des valeurs de code par défaut et ne constituent pas une obligation de configuration pour tous les environnements futurs.

## Employee Lifecycle

Le worker Employee Lifecycle fonctionne avec une tâche planifiée Windows et peut ajuster sa fréquence à partir de la configuration distante.

La plage acceptée par le code actuel est :

```text
1 à 1440 minutes
```

Le nom de tâche par défaut du script est :

```text
EITAS Employee Lifecycle Agent
```

La configuration réellement installée de cette tâche sera documentée après audit Windows dédié.

## Restauration contrôlée C9.5

Le worker AD Admin possède une capacité explicitement opt-in :

```text
-EnableDeletedObjectRestoreExecution
```

Sans ce switch, le polling de la restauration réelle des objets supprimés reste désactivé.

Ce paramètre ne doit jamais être ajouté comme simple réglage permanent sans respecter toute la chaîne d’autorisation C9.5.

## Configuration Nginx

La configuration Production observée est chargée notamment depuis :

```text
/etc/nginx/sites-enabled/eitas.conf
/etc/nginx/conf.d/eitas-rate-limits.conf
```

Nginx expose le service principal sur :

```text
https://<hôte-eitas>:62443
```

et relaie :

- le trafic applicatif vers FastAPI loopback ;
- `/auth/` vers Keycloak Production loopback.

Les routes Identity de test, préproduction ou candidate présentes dans Nginx ne prouvent pas que les services correspondants sont actifs.

## TLS

Les chemins TLS actuellement utilisés sont :

```text
/etc/eitas/pki/certs/eitas-server.crt
/etc/eitas/pki/private/eitas-server.key
```

La clé privée ne doit jamais être placée dans le dépôt.

## Keycloak

Le service Production charge sa configuration sensible depuis :

```text
/etc/keycloak/keycloak.env
```

et fonctionne sous le compte :

```text
keycloak:keycloak
```

La configuration complète Keycloak, les thèmes et les mécanismes spécifiques EITAS Identity restent documentés sous `eitas-identity/`.

## Configuration et Git

Ne doivent pas être commitées :

- les clés API réelles ;
- les secrets OIDC ;
- les mots de passe ;
- les secrets Keycloak ;
- les clés privées TLS ;
- les configurations Windows contenant des secrets ;
- les données runtime de `/var/lib/eitas`.

Les fichiers exemple du dépôt doivent contenir uniquement des valeurs fictives ou neutres.

## Vérifications après modification

Après une modification de configuration, la validation doit rester proportionnée au composant concerné.

Elle peut comprendre notamment :

- validation syntaxique ;
- contrôle des permissions ;
- vérification du listener attendu ;
- vérification du service systemd ;
- test HTTPS via Nginx ;
- contrôle du mode Simulation ;
- contrôle du heartbeat worker ;
- validation fonctionnelle ciblée.

Un changement de configuration ne doit pas être considéré comme valide uniquement parce qu’un fichier a été écrit avec succès.

## Documentation associée

- [Installation et prérequis](installation.md)
- [Vue architecture](../architecture/overview.md)
- [Architecture de sécurité](../architecture/security.md)
- [Agent Windows](../architecture/windows-agent.md)
- [EITAS Identity](../architecture/identity.md)

## Règle de maintenance

Cette page doit être mise à jour après tout changement validé concernant les variables d’environnement, les chemins runtime, le mode global, les paramètres workers, les fichiers de configuration Nginx, TLS ou Identity.
