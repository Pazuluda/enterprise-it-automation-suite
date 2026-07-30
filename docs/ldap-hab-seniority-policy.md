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

## État de sécurité

L’intégration reste volontairement dormante :

- candidat absent du registre LDAP public ;
- attribut absent du frontend ;
- validation publique indisponible ;
- autorisation d’écriture désactivée ;
- création de job désactivée ;
- exécution en Production désactivée ;
- action absente du registre générique AD Admin.

Le catalogue du schéma et les métadonnées de candidat ne constituent jamais une autorisation.

## Conditions avant une activation future

Une activation nécessiterait au minimum :

1. une décision explicite d’exposition du candidat ;
2. des tests de visibilité selon les rôles ;
3. une validation complète du payload frontend et backend ;
4. une simulation réelle sans écriture ;
5. une vérification de l’audit sans conservation des valeurs ;
6. une autorisation distincte pour chaque niveau d’exécution ;
7. une validation séparée avant toute écriture Active Directory réelle.

## Données d’environnement

La documentation ne conserve aucun nom d’utilisateur, nom de domaine, nom de serveur, GUID d’objet ou distinguished name issu de l’environnement de validation.
