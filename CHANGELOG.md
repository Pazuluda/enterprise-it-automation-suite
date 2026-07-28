# Journal des modifications

Toutes les modifications importantes d'Enterprise IT Automation Suite sont consignées dans ce fichier.

## [À venir]

### Prévu

- démarrage de C2 — Éditeur d'attributs LDAP ;
- suivi GitHub de la version `v0.2.0` ;
- préversions `v0.2.0-alpha.N` pendant le développement de C2.

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
