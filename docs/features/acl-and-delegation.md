# ACL, sécurité et délégation Active Directory

Ce document décrit les capacités ACL actuellement intégrées à l’Explorateur Active Directory EITAS.

Il complète [la vue générale de l’Explorateur AD](ad-explorer.md), [l’architecture de sécurité](../architecture/security.md) et [l’architecture des agents Windows](../architecture/windows-agent.md).

## Principe général

La gestion ACL EITAS sépare strictement :

- la lecture du descripteur de sécurité ;
- la Simulation d’une délégation ;
- la préparation d’un chemin Production ;
- le binding avec l’état réel de la DACL ;
- l’identité humaine ;
- l’anti-rejeu ;
- la validation pre-write par Windows ;
- la confirmation humaine finale.

Ces étapes ne constituent pas actuellement un chemin général d’écriture ACL Active Directory.

## Lecture du descripteur de sécurité

La lecture est exécutée par le worker de lookup Windows via `Get-Acl`.

Le chemin actuel expose notamment :

- le propriétaire ;
- le SID du propriétaire ;
- l’état d’héritage ;
- l’état de protection des règles d’accès ;
- les ACE de la DACL ;
- le nombre de règles explicites ;
- le nombre de règles héritées ;
- le nombre total de règles d’accès ;
- une empreinte SHA-256 du SDDL DACL.

## DACL uniquement

Le worker demande actuellement la section `Access` du descripteur de sécurité.

La SACL n’est pas chargée.

Le résultat retourne explicitement :

- `sacl_included = false`.

L’interface affiche donc le propriétaire et la DACL sans prétendre fournir l’audit SACL.

## ACE affichées

Les règles retournées exposent les informations disponibles comme :

- principal ;
- SID ;
- type d’accès ;
- droits Active Directory ;
- héritage ;
- état hérité ou explicite ;
- GUID d’objet ou de classe lorsqu’ils sont disponibles et résolus.

L’interface permet de rechercher et filtrer les ACE et de distinguer les règles Allow et Deny déjà présentes dans la DACL.

Cette capacité de lecture ne signifie pas que EITAS autorise la création de nouvelles ACE Deny.

## Simulation de délégation

La Simulation possède un contrat dédié et n’autorise aucune écriture Active Directory.

Les flags du contrat maintiennent notamment :

- création de job Simulation autorisée ;
- exécution Simulation autorisée ;
- Production non autorisée ;
- écriture AD non autorisée.

Le worker Windows calcule un aperçu de la délégation sans appeler de primitive d’écriture ACL.

## Type d’ACE autorisé pour une délégation

Le contrat de Simulation accepte actuellement uniquement :

- `Allow`.

Le write-intent contrôlé utilise la même restriction.

Une ACE `Deny` existante peut être affichée en lecture, mais elle ne fait pas partie de l’allowlist de création de délégation actuelle.

## Droits autorisés

La liste contrôlée actuelle contient exactement :

- `ReadProperty` ;
- `WriteProperty` ;
- `CreateChild` ;
- `DeleteChild` ;
- `ListChildren` ;
- `ReadControl` ;
- `ExtendedRight` ;
- `GenericRead`.

Un droit absent de cette allowlist doit être refusé par le contrat.

## Héritage autorisé

Les types d’héritage actuellement acceptés sont :

- `None` ;
- `All` ;
- `Descendents` ;
- `SelfAndChildren` ;
- `Children`.

La Simulation et le write-intent contrôlé partagent cette même surface.

## Principal

Une Simulation exige un principal Active Directory.

Le workflow résout le principal afin de lier la délégation à une identité AD concrète plutôt qu’à un simple texte fourni par le navigateur.

Le résultat peut notamment conserver le DN et le SID du principal résolu.

## Résultat de Simulation

La Simulation produit une preuve structurée contenant notamment :

- la cible résolue ;
- le principal résolu ;
- l’ACE proposée ;
- les droits ;
- l’héritage ;
- les GUID spécialisés éventuels ;
- un indicateur confirmant qu’aucune écriture n’a été effectuée.

Cette preuve est nécessaire aux étapes suivantes.

## État réel de la DACL

Avant de construire une intention Production, EITAS utilise également une lecture distincte du descripteur de sécurité.

Le worker calcule notamment :

- `dacl_sddl_sha256` ;
- une version d’empreinte DACL ;
- un fingerprint ACL représentant l’état attendu.

La chaîne de confiance lie ainsi l’intention à la Simulation et à un état réel précis de la DACL.

## Fingerprint ACL

Le backend canonicalise les données pertinentes du descripteur et calcule une empreinte ACL.

Le binding vérifie notamment que :

- la cible correspond à la Simulation ;
- le principal correspond ;
- le type d’ACE correspond ;
- les droits correspondent ;
- l’héritage correspond ;
- les GUID spécialisés correspondent ;
- la lecture du descripteur correspond à la même cible ;
- le hash DACL est valide ;
- le fingerprint attendu n’a pas changé.

Une divergence invalide le binding.

## Fraîcheur des preuves

Les preuves utilisées pour construire la chaîne Production sont soumises à des limites temporelles.

Les valeurs actuelles comprennent :

- âge maximal de la Simulation : **900 secondes** ;
- âge maximal du descripteur de sécurité : **120 secondes** ;
- tolérance maximale d’horloge : **30 secondes**.

Une preuve trop ancienne ou incohérente doit être rejetée.

## Préparation Production

L’endpoint de préparation Production construit une preuve serveur contrôlée à partir de la Simulation et du descripteur de sécurité.

Il retourne notamment :

- cible ;
- principal ;
- ACE ;
- droits ;
- héritage ;
- hash DACL ;
- fingerprint ACL ;
- DN à confirmer ;
- phrase de confirmation requise.

Cette préparation n’est pas une autorisation d’écriture.

Ses flags restent notamment :

- création de job : `false` ;
- runtime : `false` ;
- Production : `false` ;
- écriture AD : `false`.

## Write-intent dormant

Le contrat d’intention Production utilise actuellement la politique :

- `controlled_write_dormant`.

Il exige explicitement le mode Production mais conserve :

- job creation désactivée ;
- runtime désactivé ;
- Production désactivée ;
- écriture AD désactivée.

Il définit donc un contrat futur contrôlé sans ouvrir lui-même un exécuteur ACL.

## Identité humaine

La chaîne Production construit une enveloppe d’identité à partir de l’identité OIDC validée côté serveur.

Les rôles d’écriture requis sont :

- `ADAdmin` ;
- `UltraAdmin`.

L’identité d’acteur ne doit pas être librement injectée par le client.

Les claims OIDC sont vérifiés notamment pour le sujet, l’issuer, le client autorisé, les rôles et leur cohérence avec l’identité déjà validée.

## Durée de l’enveloppe d’identité

L’enveloppe d’identité possède actuellement un TTL de :

- **60 secondes**.

Cette enveloppe lie l’acteur authentifié aux preuves ACL sans autoriser directement l’écriture.

## Anti-rejeu

EITAS possède un registre anti-rejeu dédié pour les intentions ACL.

Une Simulation / preuve contrôlée ne peut pas être réutilisée librement après consommation.

Le claim enregistre notamment :

- un identifiant de claim ;
- la cible ;
- le principal ;
- les droits ;
- l’héritage ;
- le hash DACL ;
- le fingerprint ACL ;
- la date de consommation.

Le claim reste dans un état dormant et conserve les autorisations Production et AD write à `false`.

## Ticket pre-write

Après le claim, EITAS peut créer un ticket de validation pre-write.

Le ticket est lié au claim serveur et conserve un digest de son payload afin de détecter une altération.

Les durées actuelles sont :

- âge maximal accepté du claim avant création du ticket : **300 secondes** ;
- TTL du ticket pre-write : **120 secondes**.

Un ticket expiré ou déjà dans un état incompatible est refusé.

## États pre-write

Le registre peut notamment suivre :

- `prewrite_ticketed` ;
- `prewrite_processing` ;
- `prewrite_validated` ;
- `prewrite_failed`.

Le status exposé à l’utilisateur ne transforme jamais ces états en autorisation d’écriture AD.

## Validation Windows pre-write

Le worker Windows possède un chemin spécialisé de validation pre-write.

Il réclame le ticket, vérifie son transport et revalide l’état Active Directory réel.

Il contrôle notamment :

- la cible ;
- le principal ;
- les droits ;
- le type d’accès ;
- l’héritage ;
- le SHA-256 DACL attendu ;
- le fingerprint ACL attendu.

Le worker relit la DACL et refuse si son état a changé depuis le claim.

Un résultat pre-write réussi contient explicitement :

- `prewrite_validated = true` ;
- `write_performed = false` ;
- `production_authorized = false` ;
- `ad_write_authorized = false`.

La validation pre-write est donc un contrôle de dernière minute, pas l’écriture elle-même.

## Confirmation humaine finale

La préparation exige actuellement la phrase exacte :

- `APPLY ACL DELEGATION`.

La confirmation vérifie également le DN cible demandé.

Elle exige un pre-write réussi et suffisamment récent et vérifie que l’identité humaine est la même que celle liée au claim.

Le backend compare entre autres :

- `claim_id` ;
- `ticket_id` ;
- identité OIDC ;
- DN cible ;
- phrase de confirmation ;
- résumé pre-write ;
- hash DACL ;
- fingerprint ACL.

## Consommation de la confirmation

La confirmation humaine est persistée et consommée pour empêcher sa réutilisation.

La phrase elle-même n’est pas conservée telle quelle dans la preuve persistée : un SHA-256 est utilisé pour cette donnée de confirmation.

Même après validation et consommation de la confirmation, le contrat retourne :

- job creation : `false` ;
- runtime : `false` ;
- Production : `false` ;
- AD write : `false`.

L’état reste donc dormant.

## Absence actuelle de primitive d’écriture ACL

L’audit du worker Windows actuel ne trouve aucune utilisation ACL de :

- `Set-Acl` ;
- `AddAccessRule` ;
- `AddAccessRuleSpecific` ;
- `SetAccessRule` ;
- `CommitChanges()` pour cette implémentation.

Les compteurs audités sont :

- `SET_ACL_COUNT = 0` ;
- `ADD_ACCESS_RULE_COUNT = 0` ;
- `COMMIT_CHANGES_COUNT = 0`.

Le dispatch `EitasAdAdmin.ps1` expose actuellement la Simulation ACL, tandis que la validation pre-write utilise un transport spécialisé distinct.

Aucun handler général `apply_acl_delegation` n’a été identifié dans le worker audité.

## Conséquence

La chaîne Production ACL actuelle doit être comprise comme une chaîne **dormante, fail-closed, de préparation et de validation**.

Elle démontre que EITAS sait :

1. simuler une délégation ;
2. relire la DACL réelle ;
3. lier l’intention à cet état ;
4. vérifier l’identité humaine ;
5. empêcher le rejeu ;
6. créer un ticket de courte durée ;
7. revalider la DACL sur Windows ;
8. exiger une confirmation humaine finale.

Mais elle ne constitue pas encore un mécanisme général permettant d’écrire une ACE dans Active Directory.

## Relation avec le mode Production global

Le mode global `Production` ne suffit jamais à autoriser une délégation ACL.

Toutes les barrières ACL spécialisées restent indépendantes et, dans l’état actuel, le dernier droit d’écriture AD reste fermé.

## Sécurité

Le design actuel suit un principe de séparation des preuves :

- preuve de Simulation ;
- preuve de lecture DACL ;
- fingerprint de l’état ;
- identité serveur ;
- consommation anti-rejeu ;
- ticket pre-write ;
- validation Windows ;
- confirmation humaine.

Chaque étape vérifie les éléments dont elle dépend au lieu de faire confiance à un simple payload du navigateur.

## Maintenance

Ce document doit être mis à jour après validation réelle si changent :

- les droits autorisés ;
- les types d’héritage ;
- le support Allow / Deny en écriture ;
- les TTL et fenêtres de fraîcheur ;
- les rôles requis ;
- l’algorithme de fingerprint ;
- le transport pre-write ;
- le mécanisme de confirmation ;
- ou surtout l’apparition d’un véritable handler d’écriture ACL Active Directory.
