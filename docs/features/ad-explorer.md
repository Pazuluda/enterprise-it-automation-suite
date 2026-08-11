# Explorateur Active Directory

Ce document présente les capacités fonctionnelles actuelles de l’**Explorateur Active Directory EITAS**.

Il décrit le produit tel qu’il existe actuellement, sans reprendre l’historique détaillé des chantiers C1 à C9.

Pour les frontières techniques et de sécurité, consulter [l’architecture générale](../architecture/overview.md), [la sécurité](../architecture/security.md) et [les agents Windows](../architecture/windows-agent.md).

## Objectif

L’Explorateur Active Directory fournit une interface centralisée permettant de parcourir, consulter et administrer les objets Active Directory autorisés depuis le portail EITAS.

Il combine :

- navigation dans l’annuaire ;
- affichage détaillé des objets ;
- opérations administratives contrôlées ;
- historique des actions ;
- recherche et filtrage ;
- gestion des groupes ;
- édition LDAP spécialisée ;
- lecture et délégation ACL ;
- fonctions liées à la Corbeille Active Directory.

## Interface actuelle

La feature frontend est principalement organisée sous :

- `frontend/src/features/active-directory/`.

La page principale est :

- `AdExplorerPage.jsx`.

Elle s’appuie sur des composants, hooks et utilitaires spécialisés pour séparer les différentes opérations.

## Types d’objets

L’interface actuelle sait distinguer et présenter notamment :

- unités d’organisation ;
- conteneurs Active Directory ;
- utilisateurs ;
- groupes ;
- ordinateurs ;
- contacts.

Des conteneurs particuliers du domaine peuvent également être représentés, comme les conteneurs utilisateurs, ordinateurs, contrôleurs de domaine ou Builtin.

## Navigation

L’Explorateur permet de parcourir les objets et conteneurs disponibles dans son périmètre.

Lorsqu’une OU ou un conteneur est sélectionné, l’utilisateur peut explorer son contenu et ouvrir les objets liés.

Les informations présentées peuvent provenir du snapshot disponible ou d’un job Windows live selon la fonctionnalité et le besoin de fraîcheur.

## Détails des objets

`ObjectDetailsPanel.jsx` centralise une grande partie de l’affichage détaillé.

Les sections disponibles dépendent du type d’objet sélectionné.

Elles peuvent inclure notamment :

- identité de l’objet ;
- DN et métadonnées Active Directory ;
- propriétés générales ;
- informations organisationnelles ;
- informations de compte ;
- informations ordinateur ;
- informations contact ;
- appartenance aux groupes ;
- membres d’un groupe ;
- restrictions de connexion ;
- historique des actions ;
- sécurité et permissions.

Toutes les propriétés ne sont pas pertinentes pour tous les types d’objets.

## Propriétés et modification

L’Explorateur possède des formulaires et modales dédiés à la consultation et à la modification des propriétés.

Les composants actuels comprennent notamment :

- `AdObjectPropertiesModal.jsx` ;
- `UpdateObjectModal.jsx` ;
- `UpdateObjectForm.jsx`.

La validation des opérations ne repose pas uniquement sur les champs du navigateur : le backend et les workers appliquent leurs propres contrôles.

## Création d’objets

L’interface contient des workflows de création pour plusieurs catégories d’objets :

- OU ;
- conteneur ;
- utilisateur ;
- groupe ;
- ordinateur ;
- contact.

Les composants spécialisés comprennent notamment `CreateUserModal.jsx`, `CreateComputerModal.jsx` et `AdminCreationModal.jsx`.

La disponibilité d’une création réelle dépend du mode, du type d’objet, des droits et des garde-fous propres à l’action.

## Cycle de vie des objets

L’Explorateur fournit également des opérations administratives telles que :

- renommage ;
- déplacement ;
- suppression ;
- mise à jour des propriétés.

Ces actions disposent de hooks et modales dédiés, par exemple :

- `RenameObjectModal.jsx` ;
- `MoveObjectModal.jsx` ;
- `DeleteObjectModal.jsx`.

Une opération affichée par le frontend n’est jamais une autorisation suffisante à elle seule : les contrôles backend et worker restent obligatoires.

## Actions de compte

Pour les objets compatibles, EITAS possède également des actions de compte dédiées.

Le code actuel comporte notamment des mécanismes pour :

- activation ;
- désactivation ;
- déverrouillage ;
- réinitialisation du mot de passe.

La disponibilité exacte dépend de la classe de l’objet, du périmètre géré, du mode agent et des contrôles de sécurité.

## Groupes et appartenances

L’Explorateur affiche les appartenances aux groupes et les membres des groupes.

Pour un groupe, l’utilisateur peut consulter :

- les membres directs ;
- les membres imbriqués ;
- le niveau d’imbrication ;
- le groupe parent lorsqu’il est disponible.

Des opérations contrôlées permettent également :

- la recherche d’un candidat ;
- l’ajout d’un membre ;
- le retrait d’un membre direct ;
- l’ouverture d’un objet lié.

Pour les utilisateurs ou objets compatibles, l’interface présente aussi le groupe principal et les appartenances connues.

### Groupe principal

Le changement de groupe principal est actuellement explicitement limité à la **Simulation** dans le frontend audité.

L’interface bloque l’opération si le mode agent est indisponible ou différent de Simulation et indique qu’aucune écriture Active Directory ne doit être autorisée pour ce workflow.

Cette restriction doit rester documentée tant qu’un chemin Production spécifique n’a pas été validé.

## Groupes — portée et catégorie

Les propriétés de groupe comprennent notamment :

- portée ;
- catégorie.

Le formulaire de mise à jour expose actuellement les valeurs correspondantes et les changements sont soumis aux règles de transition implémentées côté worker.

Les règles détaillées des groupes seront documentées séparément afin de ne pas surcharger cette page générale.

## LDAP avancé

L’Explorateur contient un éditeur LDAP spécialisé via `LdapAttributeEditor.jsx`.

Il ne s’agit pas d’un éditeur LDAP libre : seuls les attributs et classes explicitement autorisés par les politiques EITAS peuvent être proposés.

Le chemin audité comporte notamment des capacités de Simulation et des contrôles de type de valeur.

Les règles précises seront documentées dans la documentation LDAP dédiée.

## HAB Seniority Index

L’attribut `msDS-HABSeniorityIndex` possède une interface de Simulation spécialisée.

Le composant `HabSenioritySimulationEditor.jsx` permet de préparer et visualiser le résultat sans présenter cette fonction comme une écriture Production libre.

La politique HAB reste documentée séparément comme politique technique.

## Sécurité et ACL

L’onglet sécurité permet actuellement de travailler avec le descripteur de sécurité Active Directory.

Le frontend audité contient notamment :

- lecture du descripteur ;
- affichage du propriétaire ;
- affichage de la DACL ;
- recherche et filtres sur les ACE ;
- comptage Allow / Deny ;
- Simulation de délégation ;
- préparation d’un chemin Production ;
- validation pre-write ;
- confirmation spécialisée.

La SACL n’est pas chargée dans le chemin de lecture actuel documenté par l’interface.

Les écritures ACL utilisent des barrières spécialisées et ne doivent pas être assimilées à une simple bascule globale en Production.

## Corbeille Active Directory

L’Explorateur et le backend disposent de fonctions dédiées aux objets supprimés, à l’état de la Corbeille et à la restauration contrôlée.

Ces opérations possèdent des garde-fous et chaînes d’autorisation spécifiques.

Les détails seront maintenus dans la documentation fonctionnelle dédiée à la Corbeille.

## Recherche, filtres et colonnes

Le frontend possède des utilitaires spécialisés :

- `adExplorerColumns.js` ;
- `adExplorerFilters.js` ;
- `adExplorerSavedSearches.js` ;
- `adExplorerSelection.js`.

Ils fournissent la base des capacités actuelles de présentation, filtrage, recherches enregistrées et sélection.

Ces fonctions feront l’objet d’un document spécialisé afin de conserver ici une vue synthétique.

## Historique

Les opérations administratives disposent d’un historique visible depuis les détails des objets.

L’interface permet notamment de filtrer les entrées selon plusieurs catégories :

- succès ;
- en cours ;
- erreur ;
- membres ;
- créations ;
- suppressions ;
- modifications ;
- déplacements.

L’historique utilisateur complète l’audit backend mais ne doit pas être confondu avec l’intégralité des données de sécurité ou d’audit système.

## Jobs et workers

Plusieurs fonctionnalités de l’Explorateur utilisent des jobs asynchrones gérés par l’API puis exécutés par des workers Windows.

Le backend possède notamment des services pour :

- jobs Explorateur AD ;
- administration AD ;
- lookup ;
- contrôles AD ;
- snapshots.

Les workers peuvent réclamer un job, l’exécuter et renvoyer son résultat structuré vers l’API.

## Simulation et Production

L’Explorateur n’applique pas une règle uniforme selon laquelle toute fonction disponible en Simulation devient automatiquement disponible en Production.

Chaque famille d’action possède ses propres conditions.

Certaines fonctions :

- disposent de Simulation et Production ;
- sont encore Simulation-only ;
- utilisent une chaîne Production spécialisée ;
- sont strictement read-only.

La documentation spécialisée de chaque domaine constitue la référence pour ces différences.

## Périmètre de cette documentation

Cette page décrit les capacités fonctionnelles générales de l’Explorateur.

Elle ne contient volontairement pas :

- l’historique des commits C1 à C9 ;
- les numéros de tests de clôture ;
- les GUID ou objets utilisés pendant les recettes ;
- les détails complets des politiques LDAP ;
- les contrats complets ACL ;
- les procédures opérationnelles de restauration.

Ces informations appartiennent respectivement au changelog, aux archives de milestones, aux politiques ou aux documents spécialisés.

## Maintenance

Ce document doit être mis à jour lorsqu’une capacité fonctionnelle importante de l’Explorateur change réellement après validation.
