# Installation et prérequis

Ce document décrit la base installation actuellement observée pour EITAS.

Il ne constitue pas encore un installateur automatisé universel. Le dépôt ne contient actuellement aucun mécanisme unique capable de reconstruire intégralement une instance EITAS depuis une machine vierge.

Les procédures décrites ici doivent donc être lues comme la référence de la topologie validée et des prérequis nécessaires avant configuration et déploiement.

## Topologie validée

Le déploiement actuel sépare :

- le serveur Linux EITAS ;
- le serveur Windows chargé des workers Active Directory ;
- Active Directory ;
- EITAS Identity basé sur Keycloak ;
- PostgreSQL utilisé par Keycloak.

Le portail utilisateur est exposé uniquement derrière Nginx en HTTPS.

## Chemins principaux Linux

Le dépôt principal est actuellement installé dans :

```text
/opt/enterprise-it-automation-suite
```

Les composants principaux sont organisés sous :

```text
api/
frontend/
agent-windows/
eitas-identity/
docs/
```

Les données runtime ne doivent pas être écrites dans le dépôt Git.

Elles sont stockées sous :

```text
/var/lib/eitas
```

La configuration sensible de API est séparée dans :

```text
/etc/eitas-api.env
```

## Compte de service API

Le service FastAPI fonctionne sous le compte système :

```text
eitas:eitas
```

Le répertoire runtime `/var/lib/eitas` est actuellement possédé par ce compte et protégé en mode `0750`.

Le fichier `/etc/eitas-api.env` est actuellement possédé par `root:root` et protégé en mode `0600`.

Cette séparation entre code, données runtime et secrets doit être conservée.

## Python et API

Le runtime validé utilise actuellement Python `3.13.5`.

Le dépôt contient :

```text
api/requirements.txt
```

avec les dépendances principales :

- FastAPI ;
- Uvicorn ;
- Pydantic ;
- PyJWT avec support cryptographique ;
- cryptography.

Le service installé utilise un environnement virtuel local sous :

```text
/opt/enterprise-it-automation-suite/api/.venv
```

La présence de cet environnement et des dépendances installées est donc une précondition du service API actuel.

## Service systemd API

Le service installé est :

```text
eitas-api.service
```

Son unité principale est située dans :

```text
/etc/systemd/system/eitas-api.service
```

Un drop-in de durcissement réseau actif est situé dans :

```text
/etc/systemd/system/eitas-api.service.d/40-loopback-only.conf
```

Ce drop-in remplace la commande historique de lancement et utilise :

```text
/usr/local/libexec/eitas-api-loopback
```

Le launcher démarre Uvicorn uniquement sur :

```text
127.0.0.1:8000
```

Le port `8000` ne doit pas être exposé directement aux utilisateurs ou au réseau public EITAS.

## Frontend

Le frontend utilise React et Vite.

Le runtime observé utilise actuellement :

- Node.js `22.23.1` ;
- npm `10.9.8` ;
- React `19.2.7` ;
- Vite `8.1.1`.

Ces versions décrivent le runtime validé actuel. Elles ne doivent pas être interprétées automatiquement comme des bornes minimales de compatibilité pour toutes les futures versions EITAS.

Les dépendances frontend sont décrites dans :

```text
frontend/package.json
frontend/package-lock.json
```

Le build Vite est produit dans :

```text
frontend/dist
```

La copie effectivement servie par FastAPI se trouve dans :

```text
api/static/app
```

Lors du dernier audit, ces deux arbres contenaient exactement le même ensemble de fichiers et le même contenu.

Le dépôt ne contient cependant pas encore de script générique tracké automatisant cette synchronisation. La procédure de déploiement doit donc traiter cette étape explicitement.

## Nginx

Nginx constitue la frontière HTTP publique actuelle.

Le portail validé est exposé en HTTPS sur :

```text
62443
```

Le firewall Linux observé autorise depuis le réseau EITAS :

- SSH sur `22` ;
- HTTPS EITAS sur `62443`.

Les listeners internes FastAPI et Keycloak ne doivent pas être ajoutés aux règles exposition utilisateur.

## TLS

Le serveur Nginx utilise actuellement :

```text
/etc/eitas/pki/certs/eitas-server.crt
/etc/eitas/pki/private/eitas-server.key
```

Le certificat est actuellement lisible en mode `0644`.

La clé privée est protégée en mode `0600` et appartient à `root:root`.

Une installation nouvelle doit disposer de son propre certificat et de sa propre clé privée. Aucun secret TLS ne doit être ajouté au dépôt Git.

## EITAS Identity

EITAS Identity repose actuellement sur Keycloak.

Le service Production installé est :

```text
keycloak.service
```

Il fonctionne sous :

```text
keycloak:keycloak
```

et utilise PostgreSQL comme dépendance de service.

Le runtime Production Keycloak écoute actuellement uniquement sur des ports internes loopback avant exposition par Nginx sous `/auth/`.

Les environnements Identity de test, préproduction ou candidate doivent rester distincts du service Production et ne doivent pas être supposés actifs uniquement parce que des routes Nginx existent.

## Windows et Active Directory

Les workers Active Directory sont exécutés sur Windows Server et utilisent Windows PowerShell 5.1 dans environnement actuellement validé.

Le code source des workers se trouve sous :

```text
agent-windows/
```

Le répertoire installé actuellement utilisé sur Windows est :

```text
C:\EnterpriseIT\agent-windows
```

La configuration Windows déployée ne doit jamais être remplacée aveuglément par `config.example.json`, qui reste un exemple de dépôt et non une preuve de configuration runtime.

La configuration exacte des workers et tâches planifiées est documentée séparément après validation de environnement Windows installé.

## Mode de sécurité initial

Une nouvelle installation doit commencer en mode Simulation tant que les prérequis Active Directory, les workers et les contrôles de sécurité ne sont pas validés.

Le passage en Production ne fait pas partie de installation de base et ne doit jamais être implicite.

Certaines capacités spécialisées, notamment les chaînes récentes de sécurité AD, utilisent en plus leurs propres autorisations étroites indépendantes du mode global.

## Documentation associée

Pour comprendre architecture actuelle :

- [Vue architecture](../architecture/overview.md) ;
- [Backend et API](../architecture/backend-api.md) ;
- [Frontend](../architecture/frontend.md) ;
- [Agent Windows](../architecture/windows-agent.md) ;
- [EITAS Identity](../architecture/identity.md) ;
- [Architecture de sécurité](../architecture/security.md).

## Limites actuelles

Le projet ne fournit pas encore dans le dépôt :

- un installateur Linux complet et idempotent ;
- un installateur Windows unique pour tous les workers ;
- un mécanisme tracké unique de synchronisation `frontend/dist` vers `api/static/app` ;
- une procédure automatisée complète de restauration infrastructure.

Ces limites doivent rester explicites tant que les mécanismes correspondants ne sont pas implémentés et validés.

## Règle de maintenance

Toute évolution concernant les chemins installation, comptes système, listeners réseau, services systemd, emplacement des secrets, runtime frontend ou Identity doit mettre à jour cette documentation après validation réelle du déploiement.
