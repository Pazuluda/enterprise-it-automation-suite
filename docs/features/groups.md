# Groupes Active Directory

Ce document décrit les capacités actuelles de gestion des groupes dans l’Explorateur Active Directory EITAS.

Il complète [la vue générale de l’Explorateur AD](ad-explorer.md) et [l’architecture des agents Windows](../architecture/windows-agent.md).

## Périmètre

La gestion des groupes couvre actuellement :

- affichage des propriétés d’un groupe ;
- création de groupes ;
- consultation des membres directs ;
- consultation des membres imbriqués ;
- consultation des appartenances d’un objet ;
- recherche de candidats ;
- ajout d’un membre ;
- retrait d’un membre direct ;
- navigation vers les objets liés ;
- affichage du groupe principal ;
- Simulation du changement de groupe principal ;
- gestion des propriétés de portée et de catégorie.

Toutes ces opérations ne partagent pas nécessairement le même niveau d’autorisation ou le même chemin Simulation / Production.

## Identification d’un groupe

L’Explorateur distingue les objets de classe groupe et expose les informations disponibles telles que :

- nom ;
- DN ;
- `sAMAccountName` lorsqu’il est disponible ;
- SID ;
- portée ;
- catégorie ;
- membres ;
- appartenances ;
- métadonnées générales de l’objet.

## Membres d’un groupe

Depuis les détails d’un groupe, EITAS peut charger ses membres.

Deux modes sont proposés dans l’interface actuelle :

- **Directs** ;
- **Imbriqués**.

### Membres directs

Le mode direct représente les membres directement inscrits dans le groupe.

Il peut s’appuyer sur les données disponibles dans le snapshot lorsque celles-ci sont adaptées au besoin.

Un membre direct peut être sélectionné, ouvert dans l’Explorateur ou retiré via l’action correspondante lorsque celle-ci est autorisée.

### Membres imbriqués

Le mode imbriqué permet d’explorer récursivement les appartenances traversant d’autres groupes.

Les résultats peuvent préciser :

- qu’un membre est indirect ;
- son niveau d’imbrication ;
- le groupe parent par lequel il est atteint.

Un membre indirect n’est pas traité comme un membre directement supprimable du groupe courant.

L’interface indique alors que le retrait doit être réalisé au niveau du groupe parent approprié.

## Ajout d’un membre

L’interface possède un sélecteur de membres dédié.

Le workflow permet :

1. d’ouvrir l’action d’ajout ;
2. de saisir une identité de recherche ;
3. de rechercher les candidats ;
4. de sélectionner l’utilisateur ou le groupe souhaité ;
5. de soumettre l’opération au chemin d’administration Active Directory.

La recherche doit disposer d’une identité suffisamment précise avant d’être exécutée.

L’affichage du bouton ou du candidat dans le frontend ne remplace pas les validations backend et worker.

## Retrait d’un membre

Le retrait est disponible pour les appartenances directes lorsque les conditions de l’action sont satisfaites.

Les membres imbriqués ne sont pas présentés comme directement retirables du groupe courant : leur appartenance doit être modifiée au niveau où elle est réellement définie.

## Appartenances d’un objet

Pour les objets compatibles, l’Explorateur affiche également les groupes auxquels l’objet appartient.

Les informations proviennent notamment des valeurs `memberOf` ou de leurs représentations normalisées dans les données de l’Explorateur.

L’utilisateur peut ouvrir un groupe lié directement depuis cette vue lorsque sa résolution est disponible.

## Groupe principal

Active Directory distingue le groupe principal des appartenances ordinaires.

L’interface actuelle sait présenter plusieurs informations associées, notamment lorsqu’elles sont disponibles :

- nom du groupe principal ;
- DN ;
- `sAMAccountName` ;
- SID ;
- `primaryGroupID`.

Le groupe principal peut être intégré à l’affichage des appartenances afin de conserver une vue cohérente de la relation de l’objet aux groupes.

### Changement de groupe principal

Le changement de groupe principal est actuellement **Simulation-only**.

Le frontend vérifie explicitement le mode de l’agent avant de proposer le workflow et bloque l’opération lorsque le mode n’est pas `Simulation`.

La confirmation indique qu’aucune écriture Active Directory ne doit être autorisée par ce workflow.

Le résultat permet donc de valider la cible et le comportement attendu sans modifier `primaryGroupID` dans Active Directory.

Cette restriction doit rester en place et documentée tant qu’un chemin Production dédié n’a pas été explicitement conçu et validé.

## Portée des groupes

Les propriétés de groupe exposent la portée Active Directory lorsqu’elle est disponible.

Le formulaire de modification contient un champ dédié à `groupScope`.

Une modification de portée n’est pas considérée comme une simple modification de texte : la transition est soumise aux règles de sécurité et de compatibilité Active Directory implémentées par le worker.

La documentation ne suppose donc pas que toutes les transitions de portée sont autorisées.

## Catégorie des groupes

La catégorie est également exposée via la propriété `groupCategory`.

Elle permet de distinguer les caractéristiques de sécurité ou de distribution du groupe selon les données Active Directory retournées.

Les changements de catégorie restent soumis aux validations applicatives et worker correspondantes.

## Création de groupes

L’Explorateur permet de préparer la création d’un groupe depuis les actions d’administration.

La création utilise le système de jobs AD Admin et reste soumise :

- au mode agent ;
- à la validation de la cible ;
- aux règles de nommage ;
- aux propriétés demandées ;
- aux contrôles backend ;
- aux contrôles Windows/AD.

La présence d’un bouton de création dans l’interface n’implique pas qu’une création réelle soit automatiquement autorisée.

## Modification des propriétés

Les groupes utilisent également le workflow général de mise à jour des propriétés d’objet.

Le formulaire actuel expose notamment la portée et la catégorie lorsqu’elles sont applicables au groupe.

Les changements sont validés avant leur prise en charge par le worker Windows.

## Historique

Les actions liées aux groupes sont intégrées à l’historique d’administration de l’objet.

La catégorie `Membres` regroupe notamment les actions telles que :

- ajout de membre ;
- retrait de membre ;
- changement de groupe principal en Simulation.

Les créations et modifications de propriétés apparaissent dans leurs catégories respectives.

## Jobs et worker Windows

Les actions d’administration de groupe passent par le backend EITAS puis par le worker Windows spécialisé.

Le worker vérifie le contrat de l’action, le mode et les garde-fous propres à l’opération avant toute interaction Active Directory.

Les lectures ou résolutions de membres peuvent également utiliser les mécanismes de snapshot ou des jobs live selon le besoin.

## Simulation et Production

La gestion des groupes ne possède pas une règle unique applicable à toutes ses opérations.

Selon l’action :

- une lecture peut être strictement read-only ;
- une opération peut être simulée ;
- une opération peut posséder un chemin Production contrôlé ;
- une fonctionnalité peut rester Simulation-only.

Le changement de groupe principal appartient actuellement à cette dernière catégorie.

Un mode global `Production` ne doit pas être interprété comme une autorisation automatique pour toute opération de groupe.

## Sécurité

Les contrôles frontend améliorent l’expérience utilisateur, mais la frontière d’autorisation finale reste côté backend et worker.

La couche Windows conserve notamment la responsabilité de vérifier la compatibilité de l’opération avec Active Directory et son contexte réel d’exécution.

Les secrets techniques worker ne sont jamais nécessaires au navigateur pour administrer un groupe.

## Maintenance

Ce document doit être mis à jour après validation réelle si changent :

- le modèle de membres directs ou imbriqués ;
- les opérations d’ajout ou de retrait ;
- le workflow du groupe principal ;
- les règles de portée ou de catégorie ;
- les chemins Simulation / Production ;
- le contrat de jobs de groupe.
