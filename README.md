# Enterprise IT Automation Suite

![Version](https://img.shields.io/badge/version-v0.8.0--alpha.07-2563eb)
![Statut](https://img.shields.io/badge/statut-développement_actif-f59e0b)
![C1](https://img.shields.io/badge/C1-terminé_à_100_%25-16a34a)
![C2](https://img.shields.io/badge/C2-terminé_à_100_%25-16a34a)
![C3](https://img.shields.io/badge/C3-terminé_à_100_%25-16a34a)
![C4](https://img.shields.io/badge/C4-terminé_à_100_%25-16a34a)
![C5](https://img.shields.io/badge/C5-terminé_à_100_%25-16a34a)
![C6](https://img.shields.io/badge/C6-terminé_à_100_%25-16a34a)
![C7](https://img.shields.io/badge/C7-termine_100_%25-2ea44f)
![C9](https://img.shields.io/badge/C9-en_cours_52_%25-3b82f6)

**Enterprise IT Automation Suite (EITAS)** est une plateforme d'administration et d'automatisation pour les environnements informatiques d'entreprise.

Elle centralise les workflows du cycle de vie des collaborateurs, l'administration Active Directory, les validations, l'audit et l'exécution sécurisée des opérations par des agents Windows Server.

## Version actuelle

La version officielle actuelle est **v0.8.0**.

La version **v0.9.0-alpha.09** clôt **C9.5 — restauration contrôlée**. Une restauration réelle strictement isolée a été validée sur l’objet de test jetable `GG_C95_RECYCLE_TEST` après autorisation humaine, revalidations live, consommation one-shot, transport signé et opt-in Windows temporaire. Le même GUID a été restauré au DN attendu puis vérifié directement dans Active Directory. Le mode global EITAS est resté en `Simulation`, Production n’a jamais été ouverte et le dispatcher AD Admin générique reste déconnecté de `Restore-ADObject`. C9.5 atteint 100 %, C9 global 52 %, l’Explorateur Active Directory 100 % et EITAS global 95 %.

État des chantiers de l’Explorateur Active Directory :

> **C1 — Fenêtres de propriétés complètes de l'Explorateur Active Directory**

> **C2 — Éditeur d’attributs LDAP**

> **C3 — Gestion avancée des utilisateurs**

> **C4 — Groupes, imbrication et appartenances — terminé à 100 %**

> **C5 — Ordinateurs, OU, conteneurs et contacts — terminé à 100 %**

> **C6 — Recherche, colonnes, filtres et requêtes — terminé à 100 %**

> **C7 — Sélection multiple, copie et glisser-déposer — terminé à 100 %**

> **C9 — Corbeille Active Directory et restauration — en cours à 52 %**

C3 valide la gestion avancée des utilisateurs : actions de compte, sécurité, copie contrôlée, profils avancés, RDS, Unix / POSIX, HAB dédié et lookup live complet. Les propriétés s’ouvrent immédiatement et les informations détaillées sont chargées en arrière-plan.

EITAS reste en développement actif. `v0.9.0-alpha.09` valide la restauration réelle contrôlée C9.5 de bout en bout. Le chemin reste fail-closed : autorisation humaine OIDC, revalidation live après autorisation, tickets courts one-shot, transport dédié signé, routes worker protégées par clé API et opt-in Windows explicite. Une restauration réelle du groupe jetable `GG_C95_RECYCLE_TEST` a réussi avec conservation du GUID et restauration au DN exact attendu. Le mode global est resté en `Simulation`, Production n’a pas été ouverte et le worker normal a été restauré automatiquement après exécution. Validation : 350 tests C9.5 réussis, 1303 tests backend réussis, 339 sous-tests réussis et 63 tests de sécurité ciblés réussis ; 45 warnings de dépréciation `datetime.utcnow()` connus subsistent. Progression : C9.1 100 %, C9.2 100 %, C9.3 100 %, C9.4 100 %, C9.5 100 %, C9 global 52 %, Explorateur Active Directory 100 %, EITAS global 95 %.

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
| Sixième checkpoint C8                 | `v0.8.0-alpha.06` |
| Septième checkpoint C8                | `v0.8.0-alpha.07` |
| Huitième checkpoint C8                 | `v0.8.0-alpha.08` |
| Neuvième checkpoint C8                 | `v0.8.0-alpha.09` |
| Version finale C8                      | `v0.8.0` |
| Premier checkpoint C9                 | `v0.9.0-alpha.01` |
| Checkpoint C9.2A                      | `v0.9.0-alpha.02` |
| Checkpoint C9.2B                      | `v0.9.0-alpha.03` |
| Clôture C9.2                           | `v0.9.0-alpha.04` |
| Checkpoint C9.3                       | `v0.9.0-alpha.05` |
| Pré-activation C9.4                  | `v0.9.0-alpha.06` |
| Clôture C9.4                         | `v0.9.0-alpha.07` |
| Checkpoint C9.5-A4 — barrière sécurité | `v0.9.0-alpha.08` |
| Clôture C9.5 — restauration contrôlée réelle | `v0.9.0-alpha.09` |
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
8. C8 — ACL, sécurité et délégation — terminé à 100 % ;
9. C9 — Corbeille Active Directory et restauration ;
10. C10 — Performance, audit, tests et finition.

Documents :

- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/GITHUB_TRACKING.md`](docs/GITHUB_TRACKING.md)

<!-- C9.3-ALPHA05-STATUS -->
### C9.3 — préparation Corbeille et garde-fou irréversible

C9.3 est terminé à **100 %** en préparation et sécurité.

- audit forêt/domaine et niveaux fonctionnels validé ;
- état de la Corbeille Active Directory relu en lecture seule ;
- contrôle de réplication validé ;
- contrat d'intention d'activation dormant et non autorisant ;
- persistance dédiée `dormant`, hors file `pending` ;
- preuve serveur fraîche collectée via le worker AD Lookup en lecture seule ;
- identité de l'opérateur liée à l'identité OIDC côté serveur ;
- route humaine de préparation protégée par `AD_ACCESS` ;
- aucune exécution de `Enable-ADOptionalFeature` ;
- aucune exécution de `Restore-ADObject` ;
- aucun runtime d'activation ouvert ;
- mode agent maintenu en `Simulation`.

### C9.4 — activation contrôlée de la Corbeille Active Directory

C9.4 est **terminé à 100 %** dans `v0.9.0-alpha.07`. Après autorisation humaine explicite et revalidation finale de la forêt, la Corbeille Active Directory a été activée sur `API.LOCAL`. La vérification post-activation confirme `recycle_bin_enabled=true`, `recycle_bin_enabled_scope_count=2`, `replication_failure_count=0` et `replication_ready=true`. L’activation n’a pas ouvert de dispatcher générique EITAS ni de runtime Windows d’activation permanent. L’agent reste en `Simulation`, aucune restauration n’a été effectuée et `Restore-ADObject` demeure explicitement hors de C9.4.

### C9.5 — restauration contrôlée

C9.5 est **terminé à 100 %** dans `v0.9.0-alpha.09`. La chaîne A5 conserve les barrières A4 puis ajoute un transport d’exécution dédié, signé et court, des endpoints worker strictement séparés, un opt-in Windows temporaire et un handler `Restore-ADObject` isolé du dispatcher AD Admin générique. La restauration réelle du groupe jetable `GG_C95_RECYCLE_TEST` a réussi : GUID `b1018519-8b6e-4788-81c8-3108a188e7b4` conservé, DN final `CN=GG_C95_RECYCLE_TEST,OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL`, objet supprimé absent après restauration. Le transport a été claimé et terminé par `SRV-DC01`, puis le worker a été automatiquement remis dans son état normal sans opt-in. Le mode global est resté `Simulation` et `production_authorized=false`.
