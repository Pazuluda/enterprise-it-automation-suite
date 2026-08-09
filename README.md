# Enterprise IT Automation Suite

![Version](https://img.shields.io/badge/version-v0.8.0--alpha.05-2563eb)
![Statut](https://img.shields.io/badge/statut-développement_actif-f59e0b)
![C1](https://img.shields.io/badge/C1-terminé_à_100_%25-16a34a)
![C2](https://img.shields.io/badge/C2-terminé_à_100_%25-16a34a)
![C3](https://img.shields.io/badge/C3-terminé_à_100_%25-16a34a)
![C4](https://img.shields.io/badge/C4-terminé_à_100_%25-16a34a)
![C5](https://img.shields.io/badge/C5-terminé_à_100_%25-16a34a)
![C6](https://img.shields.io/badge/C6-terminé_à_100_%25-16a34a)
![C7](https://img.shields.io/badge/C7-termine_100_%25-2ea44f)
![C8](https://img.shields.io/badge/C8-en_cours_55_%25-f59e0b)

**Enterprise IT Automation Suite (EITAS)** est une plateforme d'administration et d'automatisation pour les environnements informatiques d'entreprise.

Elle centralise les workflows du cycle de vie des collaborateurs, l'administration Active Directory, les validations, l'audit et l'exécution sécurisée des opérations par des agents Windows Server.

## Version actuelle

La version officielle actuelle est **v0.7.0**.

La version de développement **v0.8.0-alpha.05** valide **C8.3 « préparation et simulation de délégation ACL »** à 100 %. C8 progresse à 55 %.

État des chantiers de l’Explorateur Active Directory :

> **C1 — Fenêtres de propriétés complètes de l'Explorateur Active Directory**

> **C2 — Éditeur d’attributs LDAP**

> **C3 — Gestion avancée des utilisateurs**

> **C4 — Groupes, imbrication et appartenances — terminé à 100 %**

> **C5 — Ordinateurs, OU, conteneurs et contacts — terminé à 100 %**

> **C6 — Recherche, colonnes, filtres et requêtes — terminé à 100 %**

> **C7 — Sélection multiple, copie et glisser-déposer — terminé à 100 %**

> **C8 — ACL, sécurité et délégation — en cours à 55 %**

C3 valide la gestion avancée des utilisateurs : actions de compte, sécurité, copie contrôlée, profils avancés, RDS, Unix / POSIX, HAB dédié et lookup live complet. Les propriétés s’ouvrent immédiatement et les informations détaillées sont chargées en arrière-plan.

EITAS reste en développement actif. `v0.8.0-alpha.05` valide C8.3 : préparation et simulation de délégations ACL via le pipeline AD Admin existant, résolution réelle de la cible et du principal, droits et portée contrôlés, aperçu lisible dans l’onglet Sécurité et invariants stricts garantissant l’absence d’écriture Active Directory. Progression actuelle : C8.3 100 %, C8 55 %, Explorateur Active Directory 96 %, EITAS global 91 %. La prochaine étape poursuit C8 avec les mécanismes contrôlés précédant toute future écriture ACL.

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
- métadonnées complètes de l'objet ;
- consultation détaillée en lecture seule de `msDS-HABSeniorityIndex` pour les utilisateurs ;
- validation et simulation HAB dédiées, limitées aux rôles autorisés et sans écriture Active Directory.

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
| Version officielle actuelle | `v0.6.0` |
| Premier checkpoint C4 | `v0.4.0-alpha.01` |
| Deuxième checkpoint C4 | `v0.4.0-alpha.02` |
| Troisième checkpoint C4 | `v0.4.0-alpha.03` |
| Quatrième checkpoint C4 | `v0.4.0-alpha.04` |
| Cinquième checkpoint C4           | `v0.4.0-alpha.05` |
| Sixième checkpoint C4             | `v0.4.0-alpha.06` |
| Septième checkpoint C4            | `v0.4.0-alpha.07` |
| C4 terminé                         | `v0.4.0` |
| Premier checkpoint C5              | `v0.5.0-alpha.01` |
| Deuxième checkpoint C5              | `v0.5.0-alpha.02` |
| Troisième checkpoint C5             | `v0.5.0-alpha.03` |
| Quatrième checkpoint C5              | `v0.5.0-alpha.04` |
| Version stable C5                    | `v0.5.0` |
| Premier checkpoint C6                | `v0.6.0-alpha.01` |
| Deuxième checkpoint C6               | `v0.6.0-alpha.02` |
| Troisième checkpoint C6               | `v0.6.0-alpha.03` |
| Quatrième checkpoint C6             | `v0.6.0-alpha.04` |
| Version stable C6                    | `v0.6.0` |
| Premier checkpoint C7                 | `v0.7.0-alpha.01` |
| Deuxième checkpoint C7                | `v0.7.0-alpha.02` |
| Troisième checkpoint C7               | `v0.7.0-alpha.03` |
| C7 stable                              | `v0.7.0` |
| Premier checkpoint C8                 | `v0.8.0-alpha.01` |
| Deuxième checkpoint C8                | `v0.8.0-alpha.02` |
| Troisième checkpoint C8                | `v0.8.0-alpha.03` |
| Quatrième checkpoint C8                | `v0.8.0-alpha.04` |
| Cinquième checkpoint C8               | `v0.8.0-alpha.05` |
| C1 terminé | `v0.1.0` |
| Correctif de C1 | `v0.1.1` |
| C2 terminé | `v0.2.0` |
| C3 terminé | `v0.3.0` |
| Correctif documentaire de C3 | `v0.3.1` |
| C10 terminé | `v0.10.0` |
| Première version générale stable | `v1.0.0` |

La politique complète est décrite dans [`docs/VERSIONING.md`](docs/VERSIONING.md).

## Feuille de route

1. C1 — Fenêtres Propriétés complètes — terminé dans `v0.1.0` ;
2. C2 — Éditeur d'attributs LDAP — terminé dans `v0.2.0` ;
3. C3 — Gestion avancée des utilisateurs — terminé dans `v0.3.0` ;
4. C4 — Groupes, imbrication et appartenances — terminé dans `v0.4.0` ;
5. C5 — Ordinateurs, OU, conteneurs et contacts — terminé dans `v0.5.0` ;
6. C6 — Recherche, colonnes, filtres et requêtes — terminé dans `v0.6.0` ;
7. C7 — Sélection multiple, copie et glisser-déposer — terminé dans `v0.7.0` ;
8. C8 — ACL, sécurité et délégation — en cours à 36 %, C8.1, C8.2A, C8.2B et C8.2C read-only validés ;
9. C9 — Corbeille Active Directory et restauration ;
10. C10 — Performance, audit, tests et finition.

Documents :

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/GITHUB_TRACKING.md`](docs/GITHUB_TRACKING.md)
