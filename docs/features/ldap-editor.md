# Éditeur d’attributs LDAP

Ce document décrit l’éditeur LDAP contrôlé actuellement intégré à l’Explorateur Active Directory EITAS.

Il complète [la vue générale de l’Explorateur AD](ad-explorer.md).

## Objectif

L’éditeur LDAP permet de préparer des modifications d’attributs Active Directory qui ne sont pas nécessairement exposées dans les formulaires classiques de propriétés.

Il ne s’agit pas d’un éditeur LDAP libre.

EITAS applique une politique explicite de candidats revus, de classes d’objets, de types de valeurs, de rôles et d’opérations autorisées.

## Politique deny-by-default

La politique LDAP générique utilise actuellement :

- `LDAP_ATTRIBUTE_POLICY_DEFAULT = "deny"`.

Un attribut inconnu ou non revu n’est donc pas accepté simplement parce qu’il existe dans le schéma Active Directory.

Pour être proposé par l’éditeur générique, un attribut doit appartenir au catalogue explicitement revu par EITAS.

## Catalogue générique actuel

Le catalogue revu contient actuellement cinq attributs.

| Attribut | Classe(s) autorisée(s) | Type | Minimum | Maximum | Effaçable |
|---|---|---|---:|---:|---|
| `employeeType` | `user` | `single_text` | 1 caractère | 256 caractères | oui |
| `preferredLanguage` | `user` | `single_text` | 0 caractère | 64 caractères | oui |
| `personalTitle` | `user`, `contact` | `single_text` | 1 caractère | 64 caractères | oui |
| `middleName` | `user`, `contact` | `single_text` | 0 caractère | 64 caractères | oui |
| `comment` | `user`, `contact` | `single_text` | 0 caractère | 1024 caractères | oui |

Les définitions frontend et backend sont alignées sur ce premier catalogue contrôlé.

## Rôles requis

Les cinq candidats génériques actuels nécessitent les rôles :

- `ADAdmin` ;
- `UltraAdmin`.

La présence du composant dans l’interface ne remplace pas l’autorisation backend.

## Classes d’objets

L’éditeur générique est actuellement limité aux objets compatibles avec les candidats revus.

Dans le catalogue actuel :

- `employeeType` et `preferredLanguage` sont limités à `user` ;
- `personalTitle`, `middleName` et `comment` sont autorisés pour `user` et `contact`.

Une combinaison attribut / classe non autorisée doit être rejetée.

## Opérations

Le contrat de validation générique accepte uniquement :

- `set` ;
- `clear`.

### Set

`set` prépare une valeur pour l’attribut.

La valeur doit respecter :

- le type attendu ;
- les contraintes de longueur ou de valeur ;
- la classe d’objet autorisée ;
- les règles spécifiques au candidat.

Pour un attribut texte dont la longueur minimale est supérieure à zéro, une valeur vide n’est pas une valeur `set` valide.

### Clear

`clear` représente la suppression de la valeur de l’attribut.

Un changement `clear` ne doit pas transporter de valeur à appliquer.

Le backend vérifie également que le candidat est effectivement déclaré `clearable`.

Les cinq candidats génériques actuels sont effaçables.

## Nombre maximal de changements

Une requête LDAP générique peut actuellement contenir au maximum :

- **5 changements**.

Cette limite est définie par `LDAP_ATTRIBUTE_UPDATE_MAX_CHANGES = 5`.

Le backend refuse également les doublons d’attribut dans une même requête normalisée.

## Types de valeurs supportés

L’infrastructure de normalisation LDAP supporte actuellement les types :

- `single_text` ;
- `boolean` ;
- `integer32` ;
- `integer64`.

Cela ne signifie pas que chacun de ces types est actuellement exposé par le catalogue générique.

Les **cinq candidats génériques actuellement revus sont tous de type `single_text`**.

Les autres types sont des capacités du contrat de normalisation et peuvent être utilisés par des chemins spécialisés ou de futurs candidats explicitement revus.

## Texte simple

Le type `single_text` applique notamment des contrôles de :

- présence lorsque la longueur minimale l’exige ;
- longueur minimale ;
- longueur maximale ;
- caractères interdits par le contrat de normalisation.

La valeur normalisée reste une chaîne unique et non une liste LDAP multivaluée.

## Booléens

Le normaliseur typé possède un support `boolean`.

Aucun des cinq candidats génériques actuels n’utilise ce type.

La présence de cette capacité dans le normaliseur ne constitue donc pas une autorisation d’éditer arbitrairement un attribut booléen du schéma.

## Entiers

Le normaliseur prend également en charge :

- `integer32` : de `-2147483648` à `2147483647` au niveau du type ;
- `integer64` : bornes du contrat entier 64 bits, avec normalisation backend contrôlée.

Des bornes fonctionnelles plus restrictives peuvent être appliquées par une politique spécialisée.

L’utilisation d’un type entier ne suffit pas à rendre un attribut éditable génériquement.

## Frontend

La logique fonctionnelle principale se trouve notamment dans :

- `frontend/src/features/active-directory/components/LdapAttributeEditor.jsx` ;
- `frontend/src/features/active-directory/utils/ldapAttributeEditor.js` ;
- `frontend/src/features/active-directory/utils/ldapAttributeValueTypes.js`.

Le frontend :

- sélectionne les candidats compatibles avec l’objet ;
- expose `set` ou `clear` ;
- applique des contrôles de saisie ;
- construit un payload normalisé ;
- affiche le résultat de Simulation.

Les contrôles frontend servent à empêcher les erreurs évidentes mais ne sont jamais considérés comme la frontière d’autorisation finale.

## Backend

Le backend sépare plusieurs responsabilités :

- `ldap_attribute_policy.py` : politique générale et résolution ;
- `ldap_attribute_candidates.py` : candidats explicitement revus ;
- `ldap_attribute_validation.py` : validation attribut / classe / opération / valeur ;
- `ldap_attribute_value_types.py` : normalisation des valeurs typées ;
- `ldap_attribute_update.py` : contrat de modification et préparation Simulation.

Cette séparation évite qu’un simple nom d’attribut envoyé par le navigateur soit directement transformé en écriture LDAP.

## Windows

Le worker Windows possède un handler spécialisé :

- `Invoke-EitasAdAdminUpdateLdapAttributesSimulation`.

Il revalide le contrat reçu, les attributs, opérations et types avant de produire le résultat de Simulation.

Le code Windows vérifie explicitement :

- l’autorisation de Simulation LDAP ;
- l’interdiction de Production LDAP ;
- les opérations `set` / `clear` ;
- la présence ou l’absence de valeur selon l’opération ;
- les types attendus ;
- les bornes nécessaires.

## Simulation uniquement

Le contrat actuel de modification LDAP générique est :

- `LDAP_ATTRIBUTE_UPDATE_EXECUTION_POLICY = "simulation_only"` ;
- `LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED = False`.

Le composant frontend indique également que la fonction est indisponible en mode Production.

Une Simulation peut donc valider la demande et calculer le résultat attendu sans appliquer la modification à Active Directory.

La présence d’un attribut dans le catalogue ne constitue jamais une autorisation Production.

## Création de jobs génériques

Le flag générique `LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED` reste actuellement à `False`.

Ce point doit être distingué des enveloppes ou chemins spécialisés utilisés pour préparer des Simulations validées dans EITAS.

La documentation ne doit donc pas transformer ce flag en affirmation qu’un moteur générique libre de jobs LDAP serait ouvert.

## HAB Seniority Index

`msDS-HABSeniorityIndex` est un cas spécialisé et **ne fait pas partie des cinq candidats génériques éditables**.

Le backend conserve pour HAB une politique et un candidat dormant séparés.

Les invariants imposent notamment :

- politique générique `deny` ;
- absence d’exposition publique par le résolveur générique ;
- `write_authorized = False` dans le candidat dormant ;
- interdiction d’édition générique.

HAB possède son propre workflow de Simulation, son propre contrat et son propre composant frontend.

## Contrat HAB dédié

Le workflow HAB actuellement validé impose notamment :

- attribut : `msDS-HABSeniorityIndex` ;
- classe EITAS autorisée : `user` ;
- type : `integer32` ;
- opérations : `set` et `clear` ;
- minimum EITAS : `0` ;
- maximum EITAS : `2147483647` ;
- rôles : `ADAdmin` ou `UltraAdmin` ;
- Production désactivée.

Le composant `HabSenioritySimulationEditor.jsx` indique explicitement qu’aucun chemin Production n’est disponible.

La politique détaillée HAB reste une politique technique séparée de cette documentation fonctionnelle.

## Valeurs sensibles et audit

Le chemin HAB dédié évite d’exposer les valeurs brutes dans ses métadonnées d’audit lorsque cette exposition n’est pas nécessaire.

La documentation fonctionnelle ne doit pas être utilisée pour justifier l’enregistrement de valeurs LDAP sensibles en clair.

## Principe de sécurité

Le modèle retenu est :

1. refuser par défaut ;
2. revoir explicitement un attribut ;
3. limiter ses classes d’objets ;
4. définir son type et ses contraintes ;
5. limiter les opérations ;
6. vérifier les rôles ;
7. valider côté backend ;
8. revalider côté Windows ;
9. conserver Simulation et Production comme chemins distincts.

Une capacité du schéma Active Directory ou du normaliseur de types ne constitue jamais, à elle seule, une permission d’écriture.

## Maintenance

Ce document doit être mis à jour après validation réelle si changent :

- le catalogue d’attributs revus ;
- les classes autorisées ;
- les types de valeurs ;
- la limite de changements ;
- les opérations `set` / `clear` ;
- les rôles requis ;
- le chemin Simulation ;
- l’état Production ;
- la séparation du cas HAB.
