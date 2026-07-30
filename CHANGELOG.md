# Journal des modifications

Toutes les modifications importantes d'Enterprise IT Automation Suite sont consignées dans ce fichier.

## [À venir]

### C2 — Éditeur d’attributs LDAP

- pipeline LDAP HAB typé validé ;
- jobs HAB runtime dédiés disponibles uniquement en Simulation ;
- route dédiée protégée par OIDC et RBAC ;
- type `integer32` préservé jusqu’au worker Windows ;
- aperçu Active Directory calculé sans écriture ;
- lookup utilisateur détaillé `get_user` étendu en lecture seule ;
- valeur HAB sérialisée sous forme d’un `integer32` nullable ;
- frontend HAB déployé dans l’onglet Compte des utilisateurs ;
- valeur absente présentée sous la forme `Non défini` ;
- catalogue du domaine et snapshot générique toujours sans exposition HAB ;
- aucun contrôle frontend d’écriture HAB ;
- aucune commande `Set-AD*` ajoutée au chemin de lecture ;
- toute écriture Active Directory et toute écriture HAB en Production restent désactivées ;
- accès Compte et Administration EITAS Identity restaurés dans le portail ;
- accès d’administration Identity limité à `SecurityAdmin` et `UltraAdmin` ;
- 6 tests backend HAB ciblés et 202 tests backend complets validés ;
- tests frontend ciblés HAB et Identity, lint et build validés ;
- préversion `v0.2.0-alpha.16` préparée.

## [0.1.0] — 2026-07-28

### Version initiale officielle

Cette version marque la clôture à 100 % de C1 — Fenêtres de propriétés complètes de l'Explorateur Active Directory.

### Ajouté

- portail React ;
- API FastAPI ;
- agents PowerShell Windows Server ;
- workflows d'onboarding, modification, offboarding et réactivation ;
- authentification OIDC/PKCE et Bearer JWT ;
- authentification des workers par clé API ;
- contrôle d'accès RBAC ;
- Explorateur Active Directory ;
- snapshot EITAS et catalogue global du domaine ;
- opérations contrôlées sur les objets Active Directory ;
- propriétés complètes et métadonnées de l'onglet Objet.

### C1 validé

- 46 propriétés éditables sur 46 ;
- six types d'objets ;
- huit métadonnées de l'onglet Objet ;
- snapshot complet sur 43 objets sur 43 ;
- catalogue complet sur 85 objets sur 85 ;
- validation visuelle sur un utilisateur, un ordinateur et un groupe ;
- aucun mojibake réel restant dans l'interface.

### Documentation

- dossier de clôture C1 ;
- README professionnel ;
- politique de versionnement ;
- roadmap ;
- processus de suivi GitHub ;
- modèles d'issues et de pull requests.

## Historique antérieur

Le tag `v0.4-mvp-secured` correspond à un ancien jalon MVP créé avant le schéma de versionnement officiel actuel.
