# Enterprise IT Automation Suite

![Version](https://img.shields.io/badge/version-v0.1.0-2563eb)
![Statut](https://img.shields.io/badge/statut-développement_actif-f59e0b)
![C1](https://img.shields.io/badge/C1-terminé_à_100_%25-16a34a)

**Enterprise IT Automation Suite (EITAS)** est une plateforme d'administration et d'automatisation pour les environnements informatiques d'entreprise.

Elle centralise les workflows du cycle de vie des collaborateurs, l'administration Active Directory, les validations, l'audit et l'exécution sécurisée des opérations par des agents Windows Server.

## Version actuelle

La version officielle actuelle est **v0.1.0**.

Elle marque la clôture à 100 % de :

> **C1 — Fenêtres de propriétés complètes de l'Explorateur Active Directory**

EITAS reste en développement actif. `v0.1.0` est une première version fonctionnelle et validée, mais pas encore la version générale stable `v1.0.0`.

## Fonctionnalités disponibles

### Portail d'administration

- interface React déployée en production ;
- tableau de bord et suivi des demandes ;
- création, validation et traitement des demandes ;
- import CSV en masse ;
- historique, chronologie et rapports ;
- navigation contrôlée par les rôles.

### Cycle de vie des collaborateurs

- onboarding ;
- modification ;
- offboarding ;
- réactivation ;
- validation administrative obligatoire ;
- exécution en simulation ou sur Active Directory ;
- retour de résultat par l'agent Windows.

### Explorateur Active Directory

- arborescence des utilisateurs, groupes, ordinateurs, OU, contacts et conteneurs ;
- snapshot rapide du périmètre EITAS ;
- catalogue global du domaine ;
- consultation et modification contrôlée des propriétés ;
- création, déplacement, renommage et suppression d'objets ;
- gestion des appartenances ;
- historique EITAS ;
- métadonnées complètes de l'objet.

### C1 — Propriétés complètes

La version `v0.1.0` valide :

- 46 propriétés éditables sur 46 ;
- six types d'objets ;
- huit métadonnées dans l'onglet Objet ;
- `directReports` en lecture seule ;
- gestion technique du triplet pays ;
- propriétés de profil utilisateur ;
- UPN et expiration du compte ;
- restrictions de postes et horaires de connexion ;
- propriétés avancées des contacts ;
- protection contre la suppression accidentelle ;
- GUID, SID, nom canonique et USN.

Dossier de preuve :

- [`docs/ad-explorer-c1-closure.md`](docs/ad-explorer-c1-closure.md)

### Sécurité et contrôle d'accès

- authentification OIDC avec PKCE ;
- validation des jetons Bearer JWT ;
- authentification dédiée des agents Windows par clé API ;
- contrôle d'accès RBAC ;
- journalisation des opérations ;
- séparation entre portail, API et workers ;
- contrôle de sécurité avant commit ;
- exclusion des secrets et données runtime du dépôt.

## Architecture

```text
Administrateur ou technicien
            |
            v
Portail React / HTTPS
            |
            v
API FastAPI
            |
            +---- OIDC / RBAC
            +---- Stockage runtime / audit
            |
            v
Agents PowerShell Windows Server
            |
            v
Active Directory
```

Composants principaux :

- **Frontend :** React ;
- **API :** Python et FastAPI ;
- **Agents :** PowerShell sur Windows Server ;
- **Annuaire :** Microsoft Active Directory ;
- **Identité :** EITAS Identity, basé sur Keycloak ;
- **Reverse proxy :** Nginx ;
- **Déploiement :** systemd et tâches planifiées Windows.

## Versionnement

| État | Version |
|---|---:|
| C1 terminé | `v0.1.0` |
| Développement de C2 | `v0.2.0-alpha.N` |
| C2 terminé | `v0.2.0` |
| Correctif de C1 | `v0.1.1` |
| C3 terminé | `v0.3.0` |
| C10 terminé | `v0.10.0` |
| Première version générale stable | `v1.0.0` |

La politique complète est décrite dans [`docs/VERSIONING.md`](docs/VERSIONING.md).

## Feuille de route

1. C2 — Éditeur d'attributs LDAP ;
2. C3 — Gestion avancée des utilisateurs ;
3. C4 — Groupes, imbrication et appartenances ;
4. C5 — Ordinateurs, OU, conteneurs et contacts ;
5. C6 — Recherche, colonnes, filtres et requêtes ;
6. C7 — Sélection multiple, copie et glisser-déposer ;
7. C8 — ACL, sécurité et délégation ;
8. C9 — Corbeille Active Directory et restauration ;
9. C10 — Performance, audit, tests et finition.

Documents :

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/GITHUB_TRACKING.md`](docs/GITHUB_TRACKING.md)

## Contrôle avant commit

```bash
./scripts/pre-commit-security-check.sh
```

Le dépôt ne doit jamais contenir de secrets, de données client réelles, de fichiers `.env` de production, de clés privées ni de journaux runtime sensibles.

## Contribution et sécurité

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`SECURITY.md`](SECURITY.md)
- [`CHANGELOG.md`](CHANGELOG.md)

## Tag historique

`v0.4-mvp-secured` est antérieur au schéma de versionnement officiel actuel. Il est conservé pour la traçabilité et ne représente pas une version plus avancée que `v0.1.0` dans la nouvelle roadmap.
