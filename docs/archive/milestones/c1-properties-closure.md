# Clôture C1 — Fenêtres Propriétés complètes

**Projet :** Enterprise IT Automation Suite
**Périmètre :** Explorateur Active Directory
**Lot :** C1 — Fenêtres Propriétés complètes
**Statut officiel :** terminé à 100 %
**Date de clôture :** 28 juillet 2026

## Résultat de clôture

Le lot C1 est officiellement terminé et validé.

### Couverture fonctionnelle

- 46 propriétés éditables sur 46 sont couvertes de bout en bout.
- `directReports` est disponible en lecture seule et ne peut pas être modifié depuis le formulaire.
- `countryCode` est correctement géré comme attribut technique du triplet pays.
- Les six types d’objets prévus dans C1 sont représentés :
  - utilisateur ;
  - groupe ;
  - ordinateur ;
  - unité organisationnelle ;
  - contact ;
  - conteneur.
- Les surfaces de propriétés attendues sont présentes :
  - Général ;
  - Compte ;
  - Profil ;
  - Adresse ;
  - Téléphones ;
  - Organisation ;
  - Membres ;
  - Membre de ;
  - Géré par ;
  - Système d’exploitation ;
  - Emplacement ;
  - Objet ;
  - Historique ;
  - Historique EITAS.

### Métadonnées de l’onglet Objet

Les huit métadonnées attendues sont disponibles :

- nom canonique ;
- classe de l’objet ;
- GUID ;
- SID ;
- date de création ;
- date de modification ;
- USN actuel ;
- USN original.

### Couverture runtime

Lors de l’audit final :

- snapshot EITAS : 43 objets sur 43 avec DN, nom canonique, GUID, date de création et date de modification ;
- catalogue du domaine : 85 objets sur 85 avec DN, nom canonique, GUID, date de création et date de modification ;
- champ `updated_at` : 43/43 dans le snapshot et 85/85 dans le catalogue.

### Validation visuelle

L’affichage des métadonnées a été validé dans Microsoft Edge sur plusieurs types d’objets :

- utilisateur `Liam Ve` ;
- ordinateur `SRV-DC01` ;
- groupe `GG_IT_Admins`.

### Historique et encodage

La table de normalisation de l’historique contient 34 corrections intentionnelles d’anciens textes mal encodés.

L’audit final confirme :

- 34 corrections reconnues sur 34 ;
- aucun mojibake réel restant dans l’interface Active Directory.

### Commits de référence

- `4d54cd346f296df516edbeb54f07a5840d5fba2b` — propriétés Contact ;
- `0bdcb3006d399155a6775a07a931b63a663b21f4` — protection Contact ;
- `0daf5483123aac956ded2e9d381abb6e3d8e7e74` — propriétés avancées Contact ;
- `a3f445115114132d1c6aa7cfeb9ac966f65bbf08` — propriétés de profil utilisateur ;
- `6dfec84e6cf4cbffcac5ae09ed25e48d6415d0ba` — UPN et expiration du compte ;
- `baab393da1dfd55c45c5d32abfa3d008557f343f` — restrictions de connexion.

## Limite de périmètre

La clôture de C1 n’inclut pas les fonctionnalités des lots suivants :

- C2 — éditeur d’attributs LDAP ;
- C3 — gestion avancée des utilisateurs ;
- C4 — groupes, imbrication et appartenances ;
- C5 — gestion avancée des ordinateurs, OU, conteneurs et contacts ;
- C6 — recherche, colonnes, filtres et requêtes ;
- C7 — sélection multiple, copie et glisser-déposer ;
- C8 — ACL, sécurité et délégation.

Ces lots restent indépendants et n’ont pas été mélangés à C1.

## Décision

**C1 est officiellement clôturé à 100 %.**
