# Politique LDAP HAB Seniority Index

## Objet

Cette décision décrit la politique EITAS prévue pour l’attribut Active Directory `msDS-HABSeniorityIndex`.

L’attribut permet de représenter un niveau de priorité dans une liste d’adresses hiérarchique. Cette politique ne constitue pas une autorisation d’écriture et ne rend pas l’attribut disponible dans l’interface publique.

## Informations de schéma validées

L’audit en lecture seule du schéma Active Directory a confirmé les propriétés suivantes :

| Propriété | Valeur |
|---|---|
| Nom LDAP | `msDS-HABSeniorityIndex` |
| Syntaxe LDAP | `2.5.5.9` |
| Syntaxe OM | `2` |
| Type EITAS | `integer32` |
| Cardinalité | Valeur unique |
| Attribut système uniquement | Non |
| Obsolète | Non |
| Indexé | Oui |
| Catalogue global | Oui |
| Property set | `Public Information` |
| Bornes déclarées dans le schéma | Aucune |

L’absence de bornes déclarées par le schéma ne supprime pas les limites techniques du type `Integer32`.

## Politique EITAS

La politique contrôlée retient les règles suivantes :

- type de valeur : `integer32` ;
- portée initiale EITAS : objets `user` uniquement ;
- minimum EITAS : `0` ;
- maximum EITAS : `2147483647` ;
- suppression de la valeur autorisée ;
- valeurs dupliquées autorisées ;
- valeurs élevées prioritaires ;
- repli alphabétique lorsque la priorité ne départage pas les objets ;
- rôles prévus : `ADAdmin` et `UltraAdmin`.

## État de sécurité actuel

L’intégration HAB est active uniquement dans un chemin runtime dédié en Simulation :

- candidat toujours absent du registre LDAP public ;
- attribut toujours absent du frontend ;
- validation publique générique indisponible ;
- création de job autorisée uniquement par la route HAB dédiée ;
- accès réservé aux rôles `ADAdmin` et `UltraAdmin` ;
- valeur conservée strictement au format `integer32` ;
- exécution en Production désactivée ;
- autorisation d’écriture Active Directory désactivée ;
- handler Windows limité à la génération d’un aperçu ;
- aucune commande `Set-AD*` dans le handler dédié ;
- action absente du registre générique AD Admin ;
- valeurs brutes exclues des métadonnées d’audit ;
- Simulation réelle validée avec un état Active Directory identique avant et après.

Le catalogue du schéma, la présence dans une allowlist de Simulation et les métadonnées de candidat ne constituent jamais une autorisation d’écriture.

## Conditions avant toute activation en Production

Une activation en Production nécessiterait au minimum :

1. une décision explicite et documentée ;
2. une exposition frontend contrôlée et validée selon les rôles ;
3. une autorisation Production distincte du chemin Simulation ;
4. un handler Windows d’écriture séparé et explicitement audité ;
5. une stratégie de sauvegarde, de restauration et de retour arrière ;
6. un test réel contrôlé avec restauration de la valeur initiale ;
7. une nouvelle revue de sécurité et d’audit avant activation.

## Données d’environnement

La documentation ne conserve aucun nom d’utilisateur, nom de domaine, nom de serveur, GUID d’objet ou distinguished name issu de l’environnement de validation.
