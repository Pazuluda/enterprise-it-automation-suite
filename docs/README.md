# Documentation EITAS

Bienvenue dans la documentation de **Enterprise IT Automation Suite (EITAS)**.

Le `README.md` principal présente le projet de manière synthétique. Ce répertoire constitue la référence documentaire détaillée pour l’architecture, les fonctionnalités, la sécurité, l’exploitation et les politiques du projet.

## Commencer ici

| Besoin | Document |
|---|---|
| Comprendre EITAS | [README principal](../README.md) |
| Voir l’état du projet | [Feuille de route](ROADMAP.md) |
| Consulter les versions publiées | [Journal des modifications](../CHANGELOG.md) |
| Comprendre le versionnement | [Politique de versionnement](policies/versioning.md) |
| Installer ou préparer EITAS | [Installation et prérequis](operations/installation.md) |
| Signaler un problème de sécurité | [Politique de sécurité](../SECURITY.md) |
| Contribuer au projet | [Guide de contribution](../CONTRIBUTING.md) |

## Organisation documentaire cible

La documentation EITAS est progressivement organisée autour des catégories suivantes :

```text
docs/
├── README.md                 # index documentaire
├── ROADMAP.md                # état actuel et prochaines étapes
├── architecture/             # architecture du produit
├── features/                 # documentation fonctionnelle
├── operations/               # installation, déploiement et exploitation
├── policies/                 # règles et politiques techniques
└── archive/                  # documents historiques et clôtures de lots
```

La migration vers cette structure est en cours. Les documents existants restent accessibles tant qu’ils n’ont pas été relus, consolidés et déplacés vers leur emplacement définitif.

## Architecture

### Architecture générale

EITAS repose sur plusieurs composants complémentaires :

- un portail React ;
- une API Python / FastAPI ;
- EITAS Identity pour l’authentification et la gestion d’identité ;
- des agents PowerShell exécutés sur Windows Server ;
- Microsoft Active Directory ;
- Nginx et systemd pour l’exposition et l’exploitation côté Linux ;
- des mécanismes dédiés d’audit, de validation et de contrôle des opérations sensibles.

Références d’architecture actuelles :

- [Vue d’ensemble](architecture/overview.md)
- [Backend et API](architecture/backend-api.md)
- [Frontend](architecture/frontend.md)
- [Agents Windows](architecture/windows-agent.md)
- [EITAS Identity](architecture/identity.md)
- [Sécurité](architecture/security.md)

### Sécurité

- [Architecture de sécurité actuelle](architecture/security.md)
- [Politique de sécurité du dépôt](../SECURITY.md)
- [Archive — architecture de sécurité Forteresse](archive/architecture/security-fortress-architecture.md)

L’architecture de sécurité détaillée sera relue afin de distinguer clairement l’état actuel du produit des anciennes phases de migration.

### EITAS Identity

La documentation du composant d’identité est actuellement maintenue dans [`eitas-identity/`](../eitas-identity/README.md).

Documents spécialisés existants :

- [Architecture EITAS Identity](../eitas-identity/docs/architecture.md)
- [État du déploiement](../eitas-identity/docs/deployment-state.md)
- [Centre de mise à jour](../eitas-identity/docs/IDENTITY_UPDATE_CENTER.md)
- [Architecture UI downstream](../eitas-identity/docs/ui-downstream-architecture.md)
- [Packaging du thème](../eitas-identity/docs/theme-packaging.md)
- [Realm de validation](../eitas-identity/docs/validation-realm.md)

## Fonctionnalités

### Explorateur Active Directory

L’Explorateur Active Directory couvre notamment :

- propriétés des objets ;
- édition des attributs LDAP ;
- gestion avancée des utilisateurs ;
- groupes et appartenances ;
- ordinateurs, OU, conteneurs et contacts ;
- recherche, colonnes et filtres ;
- sélection multiple et glisser-déposer ;
- ACL, sécurité et délégation ;
- Corbeille Active Directory et restauration contrôlée.

Une documentation fonctionnelle consolidée sera maintenue dans `docs/features/` afin d’éviter de dupliquer ces informations dans le README et la roadmap.

### Documents fonctionnels et politiques existants

- [Politique LDAP HAB Seniority Index](policies/ldap-hab-seniority.md)
- [Politique d’activation de la Corbeille Active Directory](policies/ad-recycle-bin.md)

Ces fichiers restent des références tant que leur contenu n’a pas été intégré ou reclassé dans la structure définitive.

## Exploitation

La documentation d’exploitation finale couvrira notamment :

- installation et prérequis ;
- configuration ;
- déploiement Linux ;
- agents et workers Windows ;
- EITAS Identity ;
- sauvegarde et restauration ;
- mises à jour ;
- supervision ;
- diagnostic et dépannage.

Document existant :

- [Installation et prérequis](operations/installation.md)
- [Configuration](operations/configuration.md)
- [Déploiement](operations/deployment.md)
- [Workers Windows](operations/windows-workers.md)
- [Sauvegarde et reprise](operations/backup-recovery.md)
- [Dépannage](operations/troubleshooting.md)

## Politiques et processus

- [Politique de versionnement](policies/versioning.md)
- [Suivi GitHub](GITHUB_TRACKING.md)
- [Guide de contribution](../CONTRIBUTING.md)
- [Politique de sécurité](../SECURITY.md)

## Historique et archives

Les documents de clôture constituent des preuves historiques utiles, mais ne doivent pas être confondus avec la documentation de référence actuelle.

Documents actuellement concernés :

- [Clôture C1 — Fenêtres Propriétés complètes](archive/milestones/c1-properties-closure.md)
- [Clôture C3 — Gestion avancée des utilisateurs](archive/milestones/c3-users-closure.md)

Ils seront déplacés dans `docs/archive/` après vérification de leurs liens et de leur valeur historique.

L’historique des versions publiées reste centralisé dans [`CHANGELOG.md`](../CHANGELOG.md).

## Règles de maintenance documentaire

Pour conserver une documentation durable :

- le README principal reste synthétique et orienté présentation ;
- `docs/README.md` sert d’index et de point d’entrée ;
- `ROADMAP.md` décrit le présent et le futur, pas l’historique détaillé ;
- `CHANGELOG.md` conserve l’historique des releases ;
- les documents d’architecture décrivent l’état technique réel ;
- les procédures d’exploitation doivent être reproductibles ;
- les anciennes preuves et clôtures sont archivées plutôt que mélangées à la documentation courante ;
- une information ne doit pas être copiée dans plusieurs fichiers sans nécessité ;
- les versions, états et pourcentages doivent rester synchronisés ;
- toute nouvelle fonctionnalité importante doit mettre à jour la documentation de référence correspondante.

## État de la refonte documentaire

La documentation historique d’EITAS est actuellement en cours de consolidation avant la fin du chantier C9.

Priorités :

1. refondre le README et la roadmap ;
2. créer l’index documentaire central ;
3. consolider l’architecture ;
4. créer la documentation fonctionnelle de référence ;
5. réorganiser l’exploitation et les politiques ;
6. archiver les documents de clôture historiques ;
7. vérifier tous les liens et éliminer les informations obsolètes ou contradictoires.
