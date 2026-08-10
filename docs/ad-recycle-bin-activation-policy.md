# Politique d’activation de la Corbeille Active Directory — C9.3

## Objet

Ce document définit les garde-fous obligatoires avant toute activation de la fonctionnalité Active Directory Recycle Bin dans EITAS.

C9.3 reste une phase de préparation et de sécurité uniquement.

Aucune activation n’est autorisée dans C9.3.

## État validé

Forêt :

- nom : `API.LOCAL` ;
- domaine racine : `API.LOCAL` ;
- niveau fonctionnel forêt : `Windows2025Forest` ;
- niveau fonctionnel domaine : `Windows2025Domain` ;
- contrôleur de domaine : `SRV-DC01.API.LOCAL` ;
- nombre de contrôleurs de domaine : 1 ;
- réplication : aucune erreur détectée ;
- Corbeille Active Directory : désactivée ;
- niveau fonctionnel requis par la fonctionnalité : `Windows2008R2Forest` ;
- prérequis fonctionnel : satisfait ;
- `tombstoneLifetime` : 180 jours ;
- `msDS-DeletedObjectLifetime` : non défini.

## Séparation des opérations

L’activation de la Corbeille Active Directory et la restauration d’un objet sont deux opérations distinctes.

L’autorisation d’activer la Corbeille ne doit jamais :

- autoriser une restauration ;
- rendre un job `prepared` claimable ;
- rendre `simulate_deleted_object_restore` exécutable ;
- ouvrir le runtime `Restore-ADObject` ;
- ouvrir implicitement le mode Production pour une restauration.

Une future restauration devra disposer de son propre gate.

## Caractère forest-wide

L’activation doit cibler explicitement la forêt Active Directory.

Avant toute activation, le système doit confirmer :

- la forêt cible exacte ;
- le domaine racine ;
- le contrôleur de domaine utilisé pour la revalidation ;
- le niveau fonctionnel actuel ;
- l’état actuel de la fonctionnalité ;
- l’absence d’erreur de réplication connue.

Aucune cible fournie uniquement par le client ne doit être considérée comme autorité.

## Changement irréversible

Le gate C9.4 devra traiter l’activation comme un changement irréversible au niveau opérationnel.

Une confirmation humaine explicite devra être obligatoire avant toute exécution.

Cette confirmation ne devra pas être réutilisable pour une autre forêt, une autre opération ou une restauration.

## Objets déjà supprimés

L’activation future de la Corbeille ne doit pas être présentée comme permettant de restaurer automatiquement les objets supprimés avant son activation.

Les objets historiques déjà classés `isRecycled=true` dans l’inventaire C9 restent hors du parcours de restauration contrôlée prévu pour C9.5.

La validation d’une restauration réelle devra utiliser un objet jetable créé après activation de la Corbeille.

## Préconditions C9.4

Avant toute activation, toutes les conditions suivantes devront être vraies :

1. mode EITAS explicitement revalidé ;
2. forêt cible revalidée côté serveur/Windows ;
3. Corbeille toujours désactivée immédiatement avant le gate ;
4. niveau fonctionnel forêt compatible ;
5. lecture Active Directory disponible ;
6. contrôle de réplication réussi ;
7. autorisation humaine dédiée et fraîche ;
8. confirmation explicite de la forêt cible ;
9. aucune autorisation de restauration couplée ;
10. audit de l’intention avant exécution.

## Interdictions C9.3

Pendant C9.3 :

- `Enable-ADOptionalFeature` ne doit pas être exécuté ;
- `Restore-ADObject` ne doit pas être exécuté ;
- `Restore-ADObject -WhatIf` ne doit pas être exécuté ;
- aucun record `prepared` ne doit devenir `pending` ;
- aucun claim de restauration ne doit être créé ;
- aucun runtime de restauration ne doit être ouvert ;
- aucune restauration réelle ne doit être effectuée.

## Gate de sortie C9.3

C9.3 pourra être fermé uniquement lorsque :

- les préconditions techniques sont documentées ;
- le caractère forest-wide est explicitement documenté ;
- le caractère irréversible est explicitement documenté ;
- l’activation et la restauration sont explicitement séparées ;
- les anciens objets `isRecycled=true` sont explicitement exclus de la future validation réelle ;
- aucune primitive d’activation ou de restauration n’a été exécutée ;
- le mode final reste `Simulation`.
