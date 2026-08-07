# Journal des modifications

Toutes les modifications importantes d'Enterprise IT Automation Suite sont consignées dans ce fichier.

## [À venir]

## [0.4.0-alpha.06] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- sixième checkpoint fonctionnel du chantier C4 ;
- C4.5 « Cycle de vie structurel des groupes » clôturé ;
- `create_group` contrôle l’existence réelle du groupe avant le retour Simulation ;
- `delete_object` résout l’objet réel et vérifie le `confirm_dn` avant le retour Simulation ;
- `rename_object` résout l’objet réel avant le retour Simulation ;
- `move_object` résout la source et la destination réelles avant le retour Simulation ;
- destination de déplacement limitée aux classes Active Directory `organizationalUnit` et `container` ;
- faux positif de Simulation sur une destination groupe détecté puis corrigé et revalidé au runtime ;
- destination OU réelle acceptée en Simulation sans déplacement Active Directory ;
- mauvais `confirm_dn` de suppression refusé avant le retour Simulation ;
- renommage simulé validé sans création ni renommage réel de l’objet ;
- création simulée validée pour un groupe inexistant, sans création Active Directory ;
- module final validé sous Windows PowerShell 5.1 puis déployé avec sauvegarde ;
- SHA-256 actif final `A914BD58FA8519C903CB9E397C2F56B841D6FE7E5FE9D2E73CC5683829AA0C8D` ;
- worker `EITAS AD Admin Worker` redémarré afin de recharger le module final ;
- 6 tests dédiés au contrat de cycle de vie C4.5 validés ;
- suite backend complète : 382 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` propre.

## [0.4.0-alpha.05] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- cinquième checkpoint fonctionnel du chantier C4 ;
- C4.4 « Conversion contrôlée de la portée et de la catégorie des groupes » clôturé ;
- prévalidation de `GroupScope` et `GroupCategory` sur l’état Active Directory réel avant le retour Simulation ;
- conversion directe `Global ↔ DomainLocal` refusée avec passage intermédiaire par `Universal` ;
- transitions `Global → Universal`, `DomainLocal → Universal`, `Universal → Global` et `Universal → DomainLocal` validées au runtime ;
- changement `Security → Distribution` validé en Simulation avec avertissement explicite sur l’impact des ACE ;
- helper de prévalidation confirmé strictement read-only, sans commande d’écriture Active Directory ;
- module Windows validé sous PowerShell 5.1 puis déployé avec sauvegarde et contrôle SHA-256 ;
- SHA-256 actif `93049F5F5DB033707B2FA61D1EE6C1E6832308C0FAC9CE96A3DF0BEBFEDD320A` ;
- groupe Universal temporaire `GG_C44_UNIVERSAL_TEST` supprimé après validation et absence confirmée dans Active Directory ;
- 35 tests dédiés C4.2/C4.3/C4.4 validés, avec 16 sous-tests ;
- suite backend complète : 376 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` propre et contrôle de sécurité pré-commit validé sur les fichiers fonctionnels.

## [0.4.0-alpha.04] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- quatrième checkpoint fonctionnel du chantier C4 ;
- C4.3 « Membre de / groupe principal » validé de bout en bout ;
- groupe principal exposé dans l’onglet `Membre de` sans duplication de l’appartenance directe ;
- groupes directs éligibles proposés comme nouveau groupe principal depuis le portail ;
- groupe principal actuel protégé contre le retrait depuis l’interface ;
- action `set_primary_group` intégrée à l’API AD Admin et au dispatcher Windows ;
- seuls les utilisateurs et ordinateurs sont acceptés comme objets cibles ;
- groupe cible obligatoire de catégorie Security, dans le même domaine SID et sous le périmètre EITAS ;
- changement de groupe principal conditionné par une appartenance directe réelle au groupe cible ;
- RID cible dérivé du SID Active Directory et comparé au `primaryGroupID` actuel ;
- chemin idempotent pris en charge lorsque le groupe cible est déjà le groupe principal ;
- Production strictement refusée pour cette action ;
- résultat Simulation explicite avec `simulated=true` et `production_authorized=false` ;
- garde-fou hors périmètre EITAS validé au runtime ;
- Simulation runtime validée vers `GG_IT_Admin` RID 1118 ;
- validation réelle depuis l’interface vers `GG_Server_Admin` RID 1119 ;
- worker `SRV-DC01` confirmé sur les jobs C4.3 ;
- Active Directory confirmé inchangé après les validations Simulation ;
- audit `created → claimed → completed/failed` validé ;
- 365 tests backend et 317 sous-tests validés ;
- tests frontend C4.2/C4.3, lint et build de production validés ;
- aucun secret détecté dans le diff du checkpoint.


## [0.4.0-alpha.03] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- troisième checkpoint fonctionnel du chantier C4 ;
- sécurisation du chemin `remove_group_member` ;
- résolution réelle du groupe et du membre avant le retour Simulation ;
- vérification de l’appartenance directe réelle avant toute réponse Simulation ;
- retour Simulation enrichi avec `was_member=true/false` selon l’état réel d’Active Directory ;
- retrait d’un membre déjà absent conservé comme opération idempotente ;
- `Remove-ADGroupMember` reste strictement réservé au chemin Production ;
- retrait groupe vers groupe pris en charge ;
- validation runtime directe des cas membre présent et membre absent ;
- validation E2E des deux cas via le worker SRV-DC01 ;
- Active Directory confirmé inchangé après les validations ;
- worker Windows déployé avec le SHA-256 `1DEA242C976515059024FF59BC86D97DEF45ED8A6B0CD59E57BD8E0C77DEBD49` ;
- PowerShell 5.1 validé sans erreur de parsing ;
- 25 tests ciblés C4.2 validés ;
- suite backend complète : 334 tests et 301 sous-tests validés.

## [0.4.0-alpha.02] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- second checkpoint fonctionnel du chantier C4 ;
- ajout d’une matrice de compatibilité des portées pour l’imbrication de groupes ;
- groupe cible Global : seuls les groupes Global compatibles sont acceptés ;
- groupe cible Universal : groupes Global et Universal pris en charge ;
- groupe cible DomainLocal : groupes Global, Universal et DomainLocal pris en charge dans le périmètre autorisé ;
- résolution réelle de `GroupScope` avant le retour Simulation ;
- combinaison incompatible `Global <- DomainLocal` refusée avant toute écriture Active Directory ;
- validation runtime sur SRV-DC01 des combinaisons disponibles dans le lab ;
- validation E2E Simulation de `Global <- Global` avec résultat `completed` ;
- validation E2E Simulation de `Global <- DomainLocal` avec résultat `failed` et motif de compatibilité attendu ;
- Active Directory confirmé inchangé après les deux scénarios E2E ;
- PowerShell 5.1 validé sans erreur de parsing sur SRV-DC01 ;
- 17 tests ciblés C4.2A/C4.2B validés ;
- suite backend complète : 326 tests et 301 sous-tests validés ;
- aucun groupe Universal n’étant actuellement présent dans le lab, ces branches restent couvertes par les tests automatisés.

## [0.4.0-alpha.01] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- premier checkpoint fonctionnel du chantier C4 ;
- ajout groupe vers groupe prévalidé sur les objets Active Directory réels ;
- auto-imbrication d’un groupe explicitement refusée ;
- détection transitive des cycles par parcours des groupes membres directs ;
- protection contre les boucles de parcours avec suivi des groupes visités ;
- mode Simulation conservé sans écriture Active Directory ;
- résolution réelle du groupe cible et du membre avant validation Simulation ;
- comportement idempotent conservé lorsqu’un membre direct existe déjà ;
- validation PowerShell 5.1 effectuée sur SRV-DC01 ;
- module AD Admin Windows déployé avec sauvegarde et contrôle SHA-256 ;
- job `add_group_member` validé de bout en bout en Simulation ;
- absence d’écriture vérifiée directement dans Active Directory après le job ;
- 7 tests ciblés C4 validés ;
- 316 tests backend complets validés.

## [0.3.1] — 2026-08-06

### Documentation

- badge de version du README corrigé ;
- version officielle actuelle mise à jour ;
- badge C3 ajouté ;
- clôtures C1, C2 et C3 présentées ensemble ;
- tableau de versionnement du README corrigé ;
- état courant et version actuelle de la roadmap corrigés ;
- aucune modification fonctionnelle de l’application.

## [0.3.0] — 2026-08-06

### C3 — Gestion avancée des utilisateurs

- chantier C3 validé fonctionnellement à 100 % ;
- actions de compte utilisateur et états Active Directory centralisés ;
- contrôles de sécurité liés au mode de l’agent renforcés ;
- réinitialisation sécurisée des mots de passe avec choix explicites ;
- options de compte et de sécurité avancées intégrées ;
- copie d’utilisateur contrôlée par liste blanche ;
- identité, profil, organisation, coordonnées et adresse enrichis ;
- restrictions de stations et horaires de connexion disponibles ;
- profils RDS complets intégrés ;
- profil Unix / POSIX intégré avec types Active Directory préservés ;
- attribut HAB consultable et simulable par son pipeline dédié ;
- ouverture immédiate des propriétés utilisateur ;
- chargement détaillé asynchrone sans fenêtre bloquante ;
- cache utilisateur dédié et invalidation après modification ;
- lookup live utilisateur complété avec toutes les propriétés attendues ;
- `directReports` conservé en lecture seule ;
- valeurs `logonHours` sérialisées sans perte ;
- valeurs multivaluées de `postOfficeBox` détectées et comptées ;
- lecture fidèle du triplet pays `c`, `co` et `countryCode` ;
- validations réelles en Simulation et en Production ;
- baseline Active Directory restaurée après les validations ;
- module Windows Lookup déployé et worker confirmé actif ;
- 309 tests backend complets validés ;
- 190 tests frontend complets validés ;
- contrôles de sécurité, lint et builds de production validés ;
- mode final de l’agent confirmé en Simulation ;
- version stable `v0.3.0` préparée.

## [0.2.0] — 2026-08-05

### C2 — Éditeur d’attributs LDAP

- chantier C2 validé fonctionnellement à 100 % ;
- pipeline LDAP HAB typé validé ;
- jobs HAB runtime dédiés disponibles uniquement en Simulation ;
- routes dédiées protégées par OIDC et RBAC ;
- accès de simulation réservé à `ADAdmin` et `UltraAdmin` ;
- type `integer32` préservé du portail au worker Windows ;
- opérations `set` et `clear` contrôlées ;
- bornes EITAS de `0` à `2147483647` appliquées ;
- validation de l’aperçu obligatoire avant la création du job ;
- confirmation explicite obligatoire avant la simulation ;
- aperçu Active Directory calculé sans écriture ;
- lookup utilisateur détaillé `get_user` étendu en lecture seule ;
- valeur HAB sérialisée sous forme d’un `integer32` nullable ;
- valeur absente présentée sous la forme `Non défini` ;
- contrôle frontend HAB dédié dans les propriétés utilisateur ;
- suivi du job et affichage persistant du résultat final ;
- défilement automatique vers le résultat de simulation ;
- ouverture des propriétés rendue immédiate ;
- enrichissement utilisateur asynchrone sans fermeture de la modale HAB ;
- identité fonctionnelle stabilisée par distinguished name ;
- catalogue du domaine et snapshot générique toujours sans exposition HAB ;
- aucune commande `Set-AD*` ajoutée aux chemins HAB ;
- aucune autorisation frontend ou backend d’écriture HAB réelle ;
- exécution HAB en Production toujours désactivée ;
- valeurs brutes HAB exclues des métadonnées d’audit ;
- état Active Directory confirmé inchangé après simulation ;
- 202 tests backend complets validés ;
- 53 tests frontend complets validés ;
- lint, build de production et contrôle de sécurité validés ;
- version `v0.2.0` finalisée.

### EITAS Identity

- accès Compte et Administration EITAS Identity restaurés dans le portail ;
- accès d’administration Identity limité à `SecurityAdmin` et `UltraAdmin`.

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
