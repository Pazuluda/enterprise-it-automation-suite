# Enterprise IT Automation Suite

![Version](https://img.shields.io/badge/version-v0.9.0-16a34a)
![Statut](https://img.shields.io/badge/statut-développement_actif-f59e0b)
![C1](https://img.shields.io/badge/C1-terminé_100_%25-16a34a)
![C2](https://img.shields.io/badge/C2-terminé_100_%25-16a34a)
![C3](https://img.shields.io/badge/C3-terminé_100_%25-16a34a)
![C4](https://img.shields.io/badge/C4-terminé_100_%25-16a34a)
![C5](https://img.shields.io/badge/C5-terminé_100_%25-16a34a)
![C6](https://img.shields.io/badge/C6-terminé_100_%25-16a34a)
![C7](https://img.shields.io/badge/C7-terminé_100_%25-16a34a)
![C8](https://img.shields.io/badge/C8-terminé_100_%25-16a34a)
![C10](https://img.shields.io/badge/C10-en_cours_0_%25-3b82f6)

**Enterprise IT Automation Suite (EITAS)** est une plateforme d’administration et d’automatisation conçue pour les environnements informatiques d’entreprise.

Elle centralise les workflows du cycle de vie des collaborateurs, l’administration Active Directory, les validations, l’audit et l’exécution sécurisée des opérations par des agents Windows Server.

## État du projet

| Indicateur | État |
|---|---:|
| Version actuelle | `v0.9.0` |
| Dernière version stable | `v0.8.0` |
| Projet EITAS global | **97 %** |
| Explorateur Active Directory | **100 %** |
| Chantier actif | **C10 — 0 %** |

C9 est terminé et publié en `v0.9.0`. La Corbeille Active Directory, les garde-fous de restauration contrôlée et l’interface de préparation sont validés. Le chantier actif devient C10, consacré aux performances, à l’audit, aux tests et à la finition générale.

[Consulter la feuille de route complète](docs/ROADMAP.md)

## Fonctionnalités principales

### Portail d’administration

- tableau de bord et suivi des demandes ;
- création, validation et traitement des opérations ;
- import CSV en masse ;
- historique, chronologie et rapports ;
- navigation adaptée aux rôles de l’utilisateur.

### Cycle de vie des collaborateurs

- onboarding ;
- modification ;
- offboarding ;
- réactivation ;
- validation administrative ;
- exécution contrôlée en Simulation ou selon les autorisations prévues ;
- retour d’exécution des agents Windows.

### Explorateur Active Directory

- navigation dans les utilisateurs, groupes, ordinateurs, OU, contacts et conteneurs ;
- consultation et modification contrôlée des propriétés ;
- gestion des appartenances et des groupes ;
- création, déplacement, renommage et suppression d’objets ;
- recherche, filtres, colonnes configurables et recherches enregistrées ;
- sélection multiple, copie et glisser-déposer ;
- consultation des ACL et délégations ;
- gestion sécurisée des objets supprimés et de la restauration ;
- prise en charge des attributs avancés, dont HAB, RDS et Unix / POSIX.

### Sécurité et audit

- authentification OIDC avec PKCE ;
- validation des jetons Bearer JWT ;
- authentification dédiée des workers ;
- contrôle d’accès RBAC ;
- séparation des opérations humaines et des opérations worker ;
- Simulation et confirmations explicites pour les opérations sensibles ;
- journalisation et audit des opérations ;
- contrôle de sécurité automatique avant commit ;
- exclusion des secrets et données runtime du dépôt.

## Architecture

```text
Administrateur ou technicien
            |
            v
       Portail React
            | HTTPS / OIDC
            v
       API FastAPI
        /       \
       v         v
EITAS Identity   Stockage / audit
       |
       +-------------------+
                           |
                           v
              Agents PowerShell Windows
                           |
                           v
                  Active Directory
```

Composants principaux :

- **Frontend :** React ;
- **API :** Python / FastAPI ;
- **Agents :** PowerShell sur Windows Server ;
- **Annuaire :** Microsoft Active Directory ;
- **Identité :** EITAS Identity, basé sur Keycloak ;
- **Reverse proxy :** Nginx ;
- **Exploitation :** systemd et tâches planifiées Windows.

## Documentation

La documentation détaillée est volontairement séparée du README afin de conserver cette page courte et lisible.

| Document | Contenu |
|---|---|
| [Feuille de route](docs/ROADMAP.md) | État actuel, chantiers et prochaines étapes |
| [Journal des modifications](CHANGELOG.md) | Historique des versions publiées |
| [Architecture de sécurité](docs/architecture/security.md) | Contrôles de sécurité actuellement déployés |
| [Politique de versionnement](docs/policies/versioning.md) | Versions, préversions et tags Git |
| [Installation et prérequis](docs/operations/installation.md) | Topologie, prérequis et base d’installation validée |
| [EITAS Identity](eitas-identity/README.md) | Composant d’identité et documentation associée |
| [Contribution](CONTRIBUTING.md) | Règles de contribution au projet |
| [Sécurité](SECURITY.md) | Signalement et politique de sécurité |

Un index documentaire centralisé sera maintenu dans `docs/README.md` au cours de la présente refonte documentaire.

## Feuille de route

| Chantier | État |
|---|---:|
| C1 — Propriétés complètes | 100 % |
| C2 — Attributs LDAP | 100 % |
| C3 — Utilisateurs avancés | 100 % |
| C4 — Groupes et appartenances | 100 % |
| C5 — Ordinateurs, OU, conteneurs et contacts | 100 % |
| C6 — Recherche, colonnes et filtres | 100 % |
| C7 — Multi-sélection et glisser-déposer | 100 % |
| C8 — ACL, sécurité et délégation | 100 % |
| **C9 — Corbeille Active Directory et restauration** | **100 % — terminé** |
| **C10 — Performance, audit, tests et finition** | **0 % — en cours** |

Les détails des sous-lots, leurs objectifs et les versions cibles sont maintenus dans [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Versionnement

EITAS utilise des versions correspondant aux grands chantiers de l’Explorateur Active Directory, complétées par des préversions `alpha` pour les checkpoints intermédiaires.

La politique complète est disponible dans [`docs/policies/versioning.md`](docs/policies/versioning.md).

## Contribution et sécurité

Avant toute contribution, consulter [`CONTRIBUTING.md`](CONTRIBUTING.md). Les vulnérabilités et données sensibles doivent être traitées conformément à [`SECURITY.md`](SECURITY.md).

---

EITAS est actuellement en développement actif. La première version générale stable sera publiée lorsque les chantiers C1 à C10 et les critères de stabilisation associés seront terminés.
