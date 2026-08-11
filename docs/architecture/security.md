# Architecture de sécurité EITAS

Ce document décrit les contrôles de sécurité actuellement implémentés et vérifiés dans **Enterprise IT Automation Suite (EITAS)**.

Il ne constitue pas une liste d’objectifs futurs. Lorsqu’une capacité n’est pas déployée ou n’a pas été vérifiée, elle est explicitement présentée comme telle.

## Principes appliqués

L’architecture actuelle suit plusieurs principes de défense en profondeur :

- refus par défaut sur les frontières sensibles ;
- validation des autorisations côté backend ;
- séparation entre identités humaines et identités techniques ;
- séparation entre code, configuration sensible et données runtime ;
- exposition minimale des services internes ;
- exécution de l’API sous un compte système non privilégié ;
- utilisation de workers Windows dédiés pour les opérations Active Directory ;
- validation spécifique des opérations pouvant produire des écritures sensibles ;
- conservation de mécanismes de Simulation et de prévalidation lorsque le workflow le prévoit.

## Frontières de confiance

### Frontière publique

Nginx constitue la frontière HTTP/HTTPS publique du déploiement observé.

Les utilisateurs accèdent à EITAS via HTTPS sur le port `62443`.

L’API FastAPI n’est pas directement exposée sur le réseau utilisateur : elle écoute sur `127.0.0.1:8000` et est atteinte à travers le reverse proxy.

L’instance d’identité principale écoute également en loopback sur `127.0.0.1:8180`, avec son interface de management sur `127.0.0.1:9000`.

### Frontière Active Directory

FastAPI ne réalise pas directement les opérations nécessitant les cmdlets Windows Active Directory.

Ces opérations sont déportées vers des workers PowerShell Windows Server. Cette séparation constitue une frontière technique entre :

- le portail et l’API Debian ;
- les workers Windows ;
- Active Directory.

## Authentification humaine

Les utilisateurs humains utilisent une authentification OIDC avec des jetons Bearer.

La validation backend observée comprend notamment :

- JWT signé en `RS256` ;
- issuer OIDC attendu ;
- récupération et validation via JWKS ;
- contrôle du client autorisé ;
- validation des dates et de l’expiration du jeton ;
- présence d’un sujet OIDC ;
- rejet des jetons invalides ou expirés.

La confiance accordée par le frontend ne remplace jamais la validation backend.

## Autorisation humaine

L’API applique un contrôle d’accès basé sur les rôles.

Les routes protégées utilisent des contrôles backend dédiés afin qu’une modification de l’interface ou un appel API direct ne permette pas de contourner l’autorisation.

Certaines opérations sensibles disposent en plus de validations spécifiques d’identité, de contexte ou de confirmation.

Ces mécanismes spécialisés ne doivent pas être confondus avec un système ABAC généralisé ou une règle des quatre yeux globale.

## Authentification des workers

Les workers Windows existants s’authentifient actuellement auprès de l’API avec `X-API-Key`.

Le backend distingue cette identité technique des utilisateurs OIDC. Certaines frontières worker exigent explicitement l’API key et refusent une identité Bearer humaine.

Cette séparation évite qu’un jeton utilisateur soit automatiquement traité comme une identité worker.

### Limite actuelle

L’authentification généralisée par certificat client mTLS par worker n’a pas été identifiée comme implémentée dans le périmètre applicatif audité.

`X-API-Key` reste donc le mécanisme worker réellement documenté aujourd’hui.

## Durcissement du service API

`eitas-api.service` s’exécute actuellement sous :

- utilisateur : `eitas` ;
- groupe : `eitas`.

Les protections systemd vérifiées comprennent :

- `UMask=0027` ;
- `NoNewPrivileges=yes` ;
- `PrivateTmp=yes` ;
- `ProtectHome=yes` ;
- `ProtectSystem=strict` ;
- `ReadWritePaths=/var/lib/eitas`.

L’API n’a donc pas besoin d’être exécutée en root et son périmètre d’écriture système est volontairement restreint.

## Séparation code, données et secrets

Les emplacements vérifiés sont :

| Usage | Emplacement | État observé |
|---|---|---|
| Code EITAS | `/opt/enterprise-it-automation-suite` | propriété `root:root` |
| Runtime applicatif | `/var/lib/eitas` | `eitas:eitas`, mode 0750 |
| Configuration sensible API | `/etc/eitas-api.env` | `root:root`, mode 0600 |

Les secrets et données runtime ne doivent pas être versionnés dans Git.

Le compte `eitas` dispose de l’écriture nécessaire sur le runtime sans obtenir un accès en écriture général au système protégé par systemd.

## Sécurité des opérations Active Directory

Les opérations Active Directory sont distribuées entre handlers et workers spécialisés.

Les chemins sensibles peuvent inclure, selon la fonctionnalité :

- validation de la cible ;
- validation de l’identité appelante ;
- contrôle des rôles ;
- préflight ;
- Simulation ;
- confirmation dédiée ;
- enveloppes d’identité ou d’exécution ;
- vérification du résultat ;
- audit.

Ces protections sont définies par fonctionnalité. L’existence d’un mécanisme pour un flux particulier ne signifie pas qu’il est automatiquement appliqué à toutes les opérations EITAS.

## Simulation et écritures sensibles

La Simulation constitue une barrière importante pour les fonctionnalités qui la supportent : elle permet de préparer et valider une opération sans appliquer la mutation Active Directory correspondante.

Les chemins de Production ou d’écriture réelle doivent rester distincts, explicitement autorisés et vérifiables.

Les opérations exceptionnellement sensibles peuvent utiliser une frontière d’exécution dédiée plutôt que le dispatcher générique.

La documentation fonctionnelle de chaque capacité doit décrire ses propres conditions de passage de Simulation vers une écriture réelle.

## Audit

EITAS dispose de mécanismes d’audit applicatif pour tracer les opérations et workflows sensibles.

La présence de cet audit applicatif ne doit pas être présentée comme équivalente à un stockage WORM distant, à un SIEM ou à une chaîne d’audit externe inviolable tant que ces capacités n’ont pas été déployées et vérifiées.

## Identité

Keycloak / EITAS Identity fournit actuellement la couche d’identité OIDC utilisée par le portail et l’API.

La configuration du fournisseur d’identité, la gestion des realms, les mécanismes MFA et les capacités propres à Keycloak sont documentés séparément dans `eitas-identity/`.

Une capacité disponible dans Keycloak ne doit pas être présentée comme intégrée à tous les workflows EITAS tant que cette intégration n’a pas été validée.

## Capacités non considérées comme déployées

L’ancien plan Forteresse mentionne plusieurs objectifs avancés. L’audit du code applicatif actuel n’a pas identifié d’implémentation généralisée des capacités suivantes :

- mTLS par worker ;
- ABAC complet ;
- élévation JIT généralisée ;
- règle des quatre yeux généralisée ;
- WebAuthn ou FIDO2 comme couche applicative EITAS propre ;
- audit distant WORM généralisé ;
- stockage applicatif PostgreSQL via `psycopg`, `SQLAlchemy` ou `asyncpg`.

Ces éléments peuvent rester des orientations futures ou appartenir à des composants spécialisés, mais ils ne font pas partie de la référence des contrôles actuellement vérifiés sans validation supplémentaire.

## Ancienne architecture Forteresse

Le document historique [Architecture de sécurité Forteresse](../archive/architecture/security-fortress-architecture.md) contient à la fois :

- des principes toujours pertinents ;
- des architectures cibles ;
- les anciennes phases de migration 303 à 311 ;
- des objectifs qui ne sont pas encore généralisés dans le produit.

Il est conservé comme document historique, plutôt que comme source de vérité de l’architecture actuelle.

## Maintenance

Toute évolution d’authentification, d’autorisation, de frontière réseau, de worker ou de mécanisme d’écriture sensible doit mettre à jour cette documentation après validation réelle du changement.

La documentation de sécurité doit toujours distinguer :

1. ce qui est déployé ;
2. ce qui est spécifique à une fonctionnalité ;
3. ce qui est prévu mais non encore implémenté.
