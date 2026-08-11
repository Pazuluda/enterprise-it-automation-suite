# Feuille de route EITAS

Cette feuille de route décrit uniquement l’état actuel du projet, les chantiers fonctionnels et les prochaines étapes. L’historique détaillé des versions et checkpoints est conservé dans [`CHANGELOG.md`](../CHANGELOG.md).

## État actuel

| Indicateur | État |
|---|---:|
| Version actuelle | `v0.9.0` |
| Dernière version stable | `v0.8.0` |
| Projet EITAS global | **97 %** |
| Explorateur Active Directory | **100 %** |
| Chantier actif | **C10 — 0 %** |

EITAS reste en développement actif. Les chantiers C1 à C9 de l’Explorateur Active Directory sont terminés. C10 devient le chantier actif et constitue la phase finale de performance, audit, tests et finition avant la première version générale stable.

## Vue d’ensemble

| Chantier | Objectif | Version cible | État |
|---|---|---:|---|
| C1 | Fenêtres Propriétés complètes | `v0.1.0` | Terminé — 100 % |
| C2 | Éditeur d’attributs LDAP | `v0.2.0` | Terminé — 100 % |
| C3 | Gestion avancée des utilisateurs | `v0.3.0` | Terminé — 100 % |
| C4 | Groupes, imbrication et appartenances | `v0.4.0` | Terminé — 100 % |
| C5 | Ordinateurs, OU, conteneurs et contacts | `v0.5.0` | Terminé — 100 % |
| C6 | Recherche, colonnes, filtres et requêtes | `v0.6.0` | Terminé — 100 % |
| C7 | Sélection multiple, copie et glisser-déposer | `v0.7.0` | Terminé — 100 % |
| C8 | ACL, sécurité et délégation | `v0.8.0` | Terminé — 100 % |
| C9 | Corbeille Active Directory et restauration | `v0.9.0` | Terminé — 100 % |
| C10 | Performance, audit, tests et finition | `v0.10.0` | En cours — 0 % |

La progression globale d’un chantier est pondérée selon le travail restant ; elle ne correspond pas nécessairement à la moyenne arithmétique de ses sous-lots.

## C9 — Corbeille Active Directory et restauration

C9 apporte une gestion sûre des objets supprimés Active Directory, depuis leur inventaire jusqu’à une restauration réelle strictement contrôlée.

| Sous-lot | Objectif | État |
|---|---|---|
| C9.1 | Inventaire read-only des objets supprimés | Terminé — 100 % |
| C9.2 | Préflight, revalidation live et Simulation contrôlée | Terminé — 100 % |
| C9.3 | Préparation Corbeille et garde-fous du changement irréversible | Terminé — 100 % |
| C9.4 | Activation contrôlée de la Corbeille Active Directory | Terminé — 100 % |
| C9.5 | Restauration réelle contrôlée | Terminé — 100 % |
| C9-FINAL | Interface, régressions et publication stable | Terminé — 100 % |

### C9.1 — inventaire read-only

Inventorier les objets supprimés sans introduire de chemin d’écriture Active Directory.

**Résultat :** inventaire et lecture des objets supprimés validés avec séparation stricte des opérations d’écriture.

### C9.2 — préflight et Simulation

Préparer une restauration, vérifier son éligibilité et produire une Simulation sans autoriser de restauration réelle.

**Résultat :** préflight sécurisé, revalidation live, Simulation et preview Windows validés sans ouverture d’un runtime de restauration.

### C9.3 — préparation de la Corbeille

Établir les préconditions techniques et les garde-fous nécessaires avant toute activation forest-wide de la Corbeille Active Directory.

**Résultat :** état forêt/domaine, réplication, identité opérateur et séparation des autorisations validés avant activation.

### C9.4 — activation contrôlée

Activer la Corbeille Active Directory comme une opération distincte de toute restauration d’objet.

**Résultat :** activation forest-wide autorisée explicitement, exécutée une seule fois puis vérifiée. La restauration est restée hors du périmètre de C9.4.

### C9.5 — restauration contrôlée

Valider une restauration réelle sur un objet de test jetable créé après activation de la Corbeille.

**Résultat :** restauration réelle contrôlée validée de bout en bout avec conservation du GUID, cible vérifiée, audit complet, transport dédié et retour automatique du worker à son état normal. Le mode global EITAS est resté `Simulation`.

### C9-FINAL — interface, régressions et publication stable

Phase de clôture de C9, finalisée avec la publication de `v0.9.0`.

**Résultat :**

- interface Corbeille intégrée directement dans l’Explorateur Active Directory ;
- inventaire, préflight, revalidations Windows et Simulation accessibles dans un parcours cohérent ;
- challenge humain, autorisation exacte et post-autorisation validés de bout en bout dans le navigateur ;
- expiration du challenge de deux minutes rendue visible et bloquée localement lorsqu’elle est dépassée ;
- aucune route d’exécution réelle `/execution/queue` exposée dans le frontend ;
- mécanisme réel de restauration C9.5 conservé derrière sa chaîne backend dédiée et ses garde-fous indépendants ;
- régression C9 : 550 tests backend passés ;
- régression backend complète : 1307 tests passés, 339 subtests passés et 45 warnings connus ;
- régression frontend : 375 tests passés, lint sans erreur avec 34 warnings connus et build Vite réussi ;
- documentation, progression et version synchronisées pour la publication stable `v0.9.0`.

### Séparation de sécurité C9

Les frontières suivantes restent obligatoires :

- C9.3 prépare l’activation mais ne constitue pas une autorisation de restauration ;
- C9.4 active la Corbeille mais ne restaure aucun objet ;
- C9.5 utilise une autorisation de restauration indépendante ;
- une autorisation n’est jamais réutilisée implicitement pour une autre opération sensible ;
- les écritures Active Directory sensibles restent isolées des dispatchers génériques ;
- le mode global `Simulation` ne doit pas être transformé implicitement en mode Production.

## C10 — performance, audit, tests et finition

C10 constitue la dernière phase de stabilisation avant la première version générale d’EITAS.

Objectifs prévus :

- mesurer et améliorer les performances du portail, de l’API et des workers ;
- consolider l’audit fonctionnel et de sécurité ;
- renforcer les tests de non-régression ;
- traiter les derniers défauts fonctionnels et techniques ;
- finaliser l’exploitation, la sauvegarde, la restauration et le dépannage ;
- effectuer la revue finale de sécurité ;
- terminer la finition générale du produit ;
- préparer la publication `v0.10.0`.

Le découpage détaillé de C10 sera figé à son ouverture afin d’éviter de transformer cette feuille de route en journal de développement.

## Objectif v1.0.0

La première version générale stable devra réunir :

- les chantiers C1 à C10 terminés ;
- une documentation utilisateur, technique et d’exploitation complète ;
- une stratégie documentée de migration, sauvegarde et restauration ;
- des tests de non-régression représentatifs des parcours critiques ;
- une revue de sécurité globale ;
- une installation et une exploitation reproductibles ;
- une stabilisation du portail, de l’API, d’EITAS Identity et des agents Windows ;
- une cohérence complète entre README, documentation, roadmap, changelog et versionnement.

## Règles de maintenance de cette feuille de route

Pour éviter les dérives documentaires :

- `ROADMAP.md` décrit le présent et le futur, pas l’historique détaillé des releases ;
- `CHANGELOG.md` conserve l’historique des versions et checkpoints publiés ;
- les détails d’architecture, de sécurité et d’exploitation appartiennent aux documents dédiés ;
- les preuves techniques détaillées et anciens documents de clôture ne sont pas dupliqués ici ;
- les versions et pourcentages doivent rester synchronisés avec `VERSION` et le README.

## Références

- [README principal](../README.md)
- [Journal des modifications](../CHANGELOG.md)
- [Politique de versionnement](policies/versioning.md)
- [Architecture de sécurité](architecture/security.md)
- [Politique d’activation de la Corbeille Active Directory](policies/ad-recycle-bin.md)
