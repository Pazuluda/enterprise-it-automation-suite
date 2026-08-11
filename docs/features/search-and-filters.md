# Recherche, filtres, colonnes et sélection

Ce document décrit les capacités actuelles de recherche et d’organisation des résultats dans l’Explorateur Active Directory EITAS.

Il complète [la vue générale de l’Explorateur AD](ad-explorer.md).

## Périmètre

Le frontend dispose de quatre utilitaires principaux :

- `adExplorerColumns.js` ;
- `adExplorerFilters.js` ;
- `adExplorerSavedSearches.js` ;
- `adExplorerSelection.js`.

Ils couvrent respectivement :

- les colonnes et le tri ;
- les filtres avancés ;
- les recherches enregistrées ;
- la sélection simple ou multiple.

## Recherche dans l’arbre

L’arbre Active Directory possède un filtre textuel local.

La valeur saisie est normalisée puis comparée au contenu des objets disponibles dans l’arbre afin de réduire immédiatement la liste affichée.

Cette fonction agit sur les données déjà présentes dans l’interface et ne doit pas être confondue avec une interrogation live de l’annuaire.

## Filtre de la vue courante

La liste centrale possède également son propre filtre textuel.

Ce filtre est appliqué aux objets de la vue courante avant les filtres avancés et le tri.

La recherche locale et la recherche Active Directory globale sont donc deux mécanismes distincts.

## Recherche dans une OU

L’Explorateur possède un workflow permettant de rechercher un texte à l’intérieur d’un périmètre Active Directory déterminé.

La recherche utilise le DN du conteneur ou de l’OU comme base lorsqu’il est disponible.

L’interface refuse notamment de démarrer ce workflow lorsqu’aucun texte de recherche exploitable n’est fourni.

## Recherche Active Directory globale

Une recherche globale Active Directory est également disponible.

Elle utilise un workflow distinct pouvant déclencher une recherche AD et produire une vue de résultats dédiée.

Le frontend gère explicitement :

- la requête saisie ;
- l’état de recherche ;
- les résultats retournés ;
- les erreurs éventuelles ;
- la création d’une vue correspondant à la recherche globale.

Cette recherche ne doit pas être assimilée au simple filtre local de la liste.

## Colonnes

Les colonnes disponibles sont centralisées dans `adExplorerColumns.js`.

Le module fournit notamment :

- la liste des définitions de colonnes ;
- un ensemble de colonnes affichées par défaut ;
- la normalisation des identifiants de colonnes ;
- l’extraction de la valeur correspondant à une colonne ;
- le chargement des préférences ;
- la sauvegarde des préférences.

Les colonnes couvrent plusieurs propriétés Active Directory, dont le nom, le type et, lorsque pertinent, des propriétés spécialisées comme la portée de groupe.

### Colonnes visibles

L’utilisateur peut afficher ou masquer les colonnes configurables depuis le menu dédié.

Les colonnes obligatoires restent protégées contre une désactivation incompatible avec l’interface.

Une action permet également de réinitialiser la configuration des colonnes.

## Tri

Le tri est lié aux définitions de colonnes.

Le modèle de tri contient notamment :

- l’identifiant de la colonne ;
- la direction de tri.

La configuration par défaut utilise la colonne `name`.

Cliquer sur un en-tête de colonne permet d’utiliser cette colonne comme critère de tri ou d’en modifier la direction selon l’état courant.

La préférence de tri possède son propre mécanisme de chargement et de sauvegarde.

## Filtres avancés

Les filtres sont centralisés dans `adExplorerFilters.js`.

Le modèle actuel prend en charge :

- un filtre principal par type d’objet ;
- des conditions supplémentaires ;
- une colonne cible par condition ;
- un opérateur ;
- une valeur ;
- un état d’activation lorsque pertinent.

Le système normalise les filtres avant leur application afin d’écarter ou corriger les configurations non reconnues.

## Filtre par type d’objet

Le filtre principal propose plusieurs catégories d’objets Active Directory et possède une valeur par défaut `all`.

Ce filtre est appliqué en complément des conditions avancées.

Les types disponibles sont issus d’une liste contrôlée et ne sont pas des valeurs libres arbitraires.

## Conditions par colonne

Une condition avancée cible une colonne connue de l’Explorateur.

Les colonnes inconnues ne sont pas considérées comme des critères valides.

Le moteur applique ensuite l’opérateur et la valeur configurés à la donnée normalisée de l’objet.

Plusieurs conditions peuvent être présentes simultanément.

## Compteur de filtres actifs

Le frontend calcule le nombre de filtres réellement actifs.

Cela permet à l’interface d’indiquer qu’un résultat est restreint même lorsque plusieurs conditions sont combinées.

## Préférences

Les utilitaires de colonnes, tri et filtres utilisent des clés de stockage versionnées :

- `eitas_ad_explorer_columns_v1` ;
- `eitas_ad_explorer_sort_v1` ;
- `eitas_ad_explorer_filters_v1`.

Ils disposent de fonctions explicites de chargement et de sauvegarde des préférences.

La persistance reste une préférence d’interface : elle ne modifie aucune donnée Active Directory.

## Recherches enregistrées

Les recherches enregistrées sont gérées dans `adExplorerSavedSearches.js`.

Une recherche enregistrée peut conserver :

- un nom ;
- la requête de recherche ;
- les colonnes visibles ;
- le tri ;
- les filtres.

Le format est normalisé avant son utilisation.

## Limite des recherches enregistrées

Le nombre maximal actuellement défini est :

- **20 recherches enregistrées**.

Cette limite est portée par `MAX_AD_EXPLORER_SAVED_SEARCHES`.

## Gestion des recherches enregistrées

L’interface permet actuellement :

- d’ajouter une recherche ;
- de remplacer une recherche existante par l’état courant ;
- de supprimer une recherche ;
- de charger une recherche.

Lors du chargement, EITAS restaure les colonnes, le tri, les filtres et la requête associée.

Si la recherche enregistrée contient une requête globale, l’Explorateur peut relancer cette recherche Active Directory.

Une recherche enregistrée représente donc un état fonctionnel de la vue, pas seulement un texte mémorisé.

## Sélection

La logique de sélection est centralisée dans `adExplorerSelection.js`.

Le module fournit notamment :

- la normalisation des identifiants de sélection ;
- la résolution d’une nouvelle sélection ;
- la prise en charge d’une ancre de sélection ;
- la sélection globale des objets visibles.

## Sélection multiple

L’Explorateur maintient plusieurs objets sélectionnés lorsque l’interaction le demande.

La présence d’une ancre permet d’appliquer une logique de sélection cohérente sur une série d’objets.

Une gestion clavier existe également pour la sélection globale.

La sélection est recalculée à partir des objets réellement disponibles afin d’éviter de conserver aveuglément des identifiants devenus invalides.

## Actions sur la sélection

Le code actuel exploite la sélection multiple pour construire une représentation des objets sélectionnés.

Il comporte notamment un workflow de copie de la sélection.

Les données copiées peuvent être construites à partir des objets sélectionnés et de leurs propriétés disponibles.

Cette capacité ne doit pas être confondue avec une opération Active Directory en masse : copier une sélection ne modifie pas l’annuaire.

Toute future action de masse réalisant une mutation devra disposer de ses propres contrôles backend et worker.

## Ordre de traitement de la vue

La vue centrale combine plusieurs étapes distinctes :

1. partir des objets disponibles ;
2. appliquer le filtre textuel de vue ;
3. appliquer les filtres avancés ;
4. appliquer le tri ;
5. afficher les colonnes actuellement visibles ;
6. gérer la sélection sur le résultat présenté.

Cette séparation permet de conserver des comportements prévisibles lorsque plusieurs options sont actives simultanément.

## Sécurité

La recherche, le tri, les colonnes et les filtres sont principalement des fonctions de présentation et d’exploration.

Ils ne modifient pas directement Active Directory.

Une recherche live peut toutefois déclencher un job technique selon le workflow utilisé ; l’authentification et les contrôles habituels de l’API et du worker restent alors applicables.

Les préférences de présentation et recherches enregistrées ne constituent pas des autorisations d’administration.

## Maintenance

Ce document doit être mis à jour après validation réelle si changent :

- les colonnes disponibles ;
- le modèle de tri ;
- les opérateurs de filtre ;
- les catégories d’objets filtrables ;
- le format des recherches enregistrées ;
- leur limite maximale ;
- la logique de sélection multiple ;
- les actions réellement disponibles sur une sélection.
