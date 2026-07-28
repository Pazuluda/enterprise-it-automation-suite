# Politique de versionnement EITAS

## Format

Les versions utilisent le format `MAJEURE.MINEURE.CORRECTIF`.

- **MAJEURE** : version générale stable ou rupture majeure ;
- **MINEURE** : achèvement d'un chantier C1, C2, C3, etc. ;
- **CORRECTIF** : correction rétrocompatible d'une version publiée.

## Correspondance avec les chantiers

| Chantier terminé | Version officielle |
|---|---:|
| C1 | `v0.1.0` |
| C2 | `v0.2.0` |
| C3 | `v0.3.0` |
| C4 | `v0.4.0` |
| C5 | `v0.5.0` |
| C6 | `v0.6.0` |
| C7 | `v0.7.0` |
| C8 | `v0.8.0` |
| C9 | `v0.9.0` |
| C10 | `v0.10.0` |

La première version générale stable sera `v1.0.0`.

## Préversions

Exemple pour C2 :

```text
v0.2.0-alpha.1
v0.2.0-alpha.2
v0.2.0-beta.1
v0.2.0-rc.1
v0.2.0
```

- `alpha` : développement actif et incomplet ;
- `beta` : fonctionnalités principales présentes, validations restantes ;
- `rc` : candidate à la publication ;
- sans suffixe : version officielle.

## Correctifs

`v0.1.1` et `v0.1.2` corrigent `v0.1.0` sans représenter l'avancement de C2.

## Tags Git

Chaque version publiée possède un tag annoté. Un tag publié ne doit pas être déplacé ou réécrit.

## GitHub Releases

Chaque release doit contenir le résumé, les fonctionnalités, les corrections, les validations, les limitations connues et le lien vers le changelog.

## Tag historique

`v0.4-mvp-secured` est conservé pour la traçabilité mais ne détermine pas l'ordre des nouvelles versions.
