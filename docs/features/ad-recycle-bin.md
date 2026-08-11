# Corbeille Active Directory et restauration contrôlée

Ce document décrit les capacités actuellement validées dans EITAS pour l’inventaire des objets supprimés, la Corbeille Active Directory et la restauration contrôlée.

Il complète [la vue générale de l’Explorateur AD](ad-explorer.md), [l’architecture de sécurité](../architecture/security.md) et [l’architecture des agents Windows](../architecture/windows-agent.md).

## État fonctionnel

Le moteur C9 couvre actuellement :

- inventaire read-only des objets supprimés ;
- préflight de restauration ;
- revalidation live ;
- Simulation de restauration ;
- activation contrôlée de la Corbeille Active Directory ;
- autorisation humaine dédiée à une restauration ;
- chaîne one-shot anti-rejeu ;
- WhatIf Windows ;
- exécution réelle contrôlée de `Restore-ADObject` ;
- vérification du résultat après restauration.

L’interface utilisateur C9 finale reste en revanche à terminer dans **C9-FINAL**.

## Séparation des opérations

EITAS traite comme opérations indépendantes :

1. l’activation de la Corbeille Active Directory ;
2. la restauration d’un objet supprimé.

Une autorisation d’activation ne vaut jamais autorisation de restauration.

Une restauration ne doit pas réutiliser implicitement une preuve ou autorisation créée pour l’activation.

## Inventaire des objets supprimés

Le chemin C9.1 permet d’inventorier les objets supprimés sans introduire d’écriture Active Directory.

Le worker de lookup possède une action dédiée à la lecture des objets supprimés et retourne des informations permettant notamment d’identifier :

- le GUID de l’objet ;
- sa classe ;
- son état supprimé ;
- les informations de nom et de conteneur disponibles ;
- les métadonnées nécessaires aux décisions de restauration.

Cette phase reste read-only.

## Préflight de restauration

Avant toute Simulation ou restauration, EITAS évalue l’éligibilité de l’objet.

Le préflight tient notamment compte de :

- la présence d’un `object_guid` ;
- l’état réellement supprimé de l’objet ;
- la cible demandée ;
- la présence ou l’état du parent ;
- les collisions sur la cible finale ;
- le besoin éventuel d’un nouveau nom ;
- la politique correspondant à la classe de l’objet.

Le résultat peut signaler qu’une cible explicite ou une restauration préalable du parent est nécessaire.

## Revalidation live

Une décision issue d’un inventaire ancien ne suffit pas à autoriser la suite du workflow.

EITAS possède une revalidation live dédiée afin de vérifier de nouveau l’objet, son état supprimé, la cible, le parent et les éventuelles collisions.

Les différentes chaînes sensibles utilisent des preuves live fraîches plutôt que de faire confiance uniquement à l’état mémorisé par le navigateur.

## Simulation de restauration

La Simulation utilise l’action :

- `simulate_deleted_object_restore`.

Elle prépare le résultat attendu à partir du préflight sans effectuer la restauration réelle.

Le contrat de Simulation maintient notamment :

- Production désactivée ;
- écriture AD désactivée ;
- `restore_performed = false`.

## WhatIf Windows

Le worker Windows possède également une primitive spécialisée basée sur :

- `Restore-ADObject -WhatIf`.

Elle permet de valider le comportement du cmdlet Windows dans le contexte réel sans effectuer l’écriture.

Cette primitive est distincte de l’exécution réelle contrôlée.

## Activation de la Corbeille

L’activation de la Corbeille Active Directory est une opération **forest-wide**.

Elle est traitée comme un changement opérationnel irréversible.

Le workflow d’activation exige notamment :

- une forêt explicitement identifiée ;
- des preuves serveur de l’état de la forêt ;
- la validation des préconditions ;
- une identité humaine autorisée ;
- la reconnaissance explicite du caractère forest-wide ;
- la reconnaissance explicite du caractère irréversible ;
- des tickets et preuves à durée limitée ;
- une revalidation immédiatement avant exécution.

## Rôles d’activation

La préparation contrôlée exige actuellement l’un des rôles :

- `ADAdmin` ;
- `UltraAdmin`.

L’identité est dérivée de l’identité OIDC authoritative côté serveur et non d’un acteur librement fourni par le navigateur.

## Activation et restauration restent indépendantes

Les contrats d’activation comportent explicitement des marqueurs empêchant qu’ils autorisent une restauration.

Les étapes historiques de préparation C9.3 sont restées dormantes jusqu’à l’ouverture contrôlée de C9.4.

Le workflow C9.4 a ensuite permis l’activation forest-wide avec une autorisation spécifique, sans ouvrir le workflow de restauration.

## Durées courtes pour l’activation

La chaîne d’activation utilise plusieurs fenêtres courtes.

Parmi les valeurs actuelles :

- ticket d’activation : **120 secondes** ;
- autorisation d’activation : au maximum **60 secondes** ;
- pre-execution : au maximum **45 secondes** ;
- preuve fraîche de pre-execution : au maximum **45 secondes**.

Ces TTL évitent qu’une autorisation sensible préparée dans un contexte ancien reste réutilisable indéfiniment.

## Objets supprimés avant activation

L’activation de la Corbeille ne doit pas être présentée comme rendant automatiquement restaurables tous les objets historiques.

Les objets historiques déjà recyclés restent distincts des objets éligibles au parcours de restauration contrôlée conçu après activation.

L’éligibilité est toujours déterminée par le préflight et la politique de classe.

## Chaîne de restauration contrôlée

La restauration réelle C9.5 possède sa propre chaîne, indépendante de C9.4.

Elle combine notamment :

1. inventaire read-only ;
2. préflight ;
3. revalidation live ;
4. Simulation ;
5. challenge et ticket de restauration ;
6. consommation one-shot ;
7. autorisation humaine ;
8. persistance de cette autorisation ;
9. nouvelle revalidation pre-execution ;
10. consommation de l’autorisation ;
11. runtime gate de courte durée ;
12. ticket d’exécution ;
13. consommation one-shot du ticket d’exécution ;
14. enveloppe Windows ;
15. transport d’exécution dédié ;
16. claim par le worker explicitement armé ;
17. `Restore-ADObject` ;
18. retour du résultat et vérifications post-restauration.

## Liaison à l’objet exact

Les preuves de restauration sont liées à des éléments précis tels que :

- `object_guid` ;
- classe d’objet ;
- politique de classe ;
- nom de restauration ;
- cible effective ;
- identifiants et digests des preuves précédentes ;
- identité humaine.

La chaîne refuse les divergences entre ces informations au fil des étapes.

## Autorisation humaine de restauration

L’autorisation humaine exige notamment la reconnaissance explicite :

- de l’objet exact ;
- de la cible exacte ;
- du fait qu’une écriture de restauration est demandée ;
- d’un motif d’autorisation.

L’autorisation est one-shot et possède un TTL maximal de :

- **60 secondes**.

Avant son utilisation, une nouvelle preuve live doit confirmer que les conditions restent valides.

## Pre-execution de restauration

La pre-execution impose une revalidation live plus récente que l’autorisation persistée.

Les valeurs actuelles comprennent :

- TTL pre-execution : **45 secondes** ;
- âge maximal de la preuve live : **45 secondes**.

Cette étape reste encore dormante : elle ne réalise pas elle-même la restauration.

## Runtime gate

Après consommation de l’autorisation, EITAS construit un runtime gate dédié.

Son TTL maximal est :

- **30 secondes**.

Le runtime gate reste lié à la même autorisation, au même GUID et à la même cible.

Le mode global EITAS doit toujours rester `Simulation`.

## Ticket d’exécution

La capacité réelle n’apparaît qu’au travers d’un ticket d’exécution très court.

Son TTL maximal est actuellement :

- **20 secondes**.

Ce ticket exige notamment :

- autorisation humaine déjà validée ;
- revalidation réussie ;
- preuve one-shot ;
- binding complet de la cible et de l’objet.

Il autorise une capacité étroite de restauration contrôlée sans transformer le runtime générique en Production.

## Confirmation d’exécution

La confirmation attendue est construite à partir du contexte exact du runtime gate, notamment le GUID et la cible de restauration.

Elle est ensuite représentée dans les preuves par un digest SHA-256 afin de préserver le binding sans conserver inutilement une confirmation réutilisable.

## Consommation one-shot

Les tickets et autorisations sensibles possèdent des registres de consommation dédiés.

La chaîne refuse notamment :

- un ticket déjà consommé ;
- un digest déjà consommé ;
- une autorisation déjà utilisée ;
- un ticket expiré ;
- un changement de GUID ;
- un changement de cible ;
- une incohérence entre les preuves de la chaîne.

Cette construction empêche le rejeu d’une ancienne autorisation sur une restauration différente.

## Enveloppe Windows

Avant l’envoi au worker, le backend construit une enveloppe d’exécution Windows signée et liée au contexte contrôlé.

Elle conserve la séparation entre :

- mode global `Simulation` ;
- capacité étroite de restauration autorisée ;
- identité de l’objet ;
- cible ;
- tickets et consommations ;
- expiration ;
- secret de signature du transport.

## Transport dédié

La restauration réelle n’emprunte pas le dispatcher AD Admin générique.

Des endpoints agent spécialisés existent pour :

- lister les restaurations contrôlées en attente ;
- réclamer une exécution ;
- retourner son résultat.

Le transport générique de dispatch reste désactivé pour cette capacité.

## Opt-in Windows explicite

Le worker normal ne traite pas automatiquement les restaurations réelles.

`Run-AdAdminWorker.ps1` possède l’opt-in explicite :

- `-EnableDeletedObjectRestoreExecution`.

Sans ce switch, la boucle de restauration contrôlée n’est pas exécutée.

Cette séparation évite qu’un worker AD Admin standard hérite implicitement d’une capacité de restauration réelle.

## Primitive réelle

Le module Windows possède une fonction spécialisée d’exécution utilisant :

- `Restore-ADObject`.

Le même module conserve séparément la primitive WhatIf.

La primitive réelle n’est pas exposée comme action du dispatcher général `Invoke-EitasAdAdminJob`.

La présence de `Restore-ADObject` ne constitue donc pas une capacité générique accessible à n’importe quel job AD Admin.

## Mode global Simulation

La restauration réelle C9.5 constitue une exception d’écriture **isolée et explicitement autorisée**.

Elle ne nécessite pas de basculer le mode global EITAS en Production.

Les contrats de runtime exigent au contraire que le mode global reste `Simulation`.

Une capacité étroite issue d’un ticket d’exécution ne doit jamais être interprétée comme une autorisation Production générale.

## Résultat d’exécution

Le transport distingue notamment :

- `restore_execution_pending` ;
- `restore_execution_processing` ;
- `restore_execution_completed` ;
- `restore_execution_failed`.

Une exécution réussie doit indiquer que l’écriture a réellement été effectuée.

Après la fin du traitement, l’autorisation runtime n’est pas conservée.

## Vérification post-restauration

La validation C9.5 vérifie le résultat réel après exécution.

Les contrôles comprennent notamment :

- présence de l’objet restauré ;
- conservation du GUID ;
- cible finale attendue ;
- classe attendue ;
- disparition de l’entrée correspondante de l’inventaire des objets supprimés.

Cette vérification complète le simple code retour du cmdlet Windows.

## Interface utilisateur actuelle

L’audit frontend actuel ne trouve pas encore de véritable interface dédiée à la Corbeille, aux objets supprimés ou au workflow de restauration C9.

Les occurrences textuelles trouvées dans le frontend sont sans rapport avec ce workflow.

La finalisation de cette UX appartient à **C9-FINAL**.

La documentation ne doit donc pas présenter aujourd’hui un bouton ou un écran de restauration C9 comme une capacité frontend déjà livrée.

## C9-FINAL

La dernière phase de C9 doit encore couvrir :

- UX des objets supprimés ;
- présentation de l’éligibilité et des motifs de blocage ;
- confirmations explicites ;
- régressions backend, frontend et Windows ;
- validation navigateur ;
- revue de sécurité finale ;
- documentation finale ;
- publication stable `v0.9.0`.

## Politique d’activation

La politique détaillée d’activation de la Corbeille reste un document séparé.

Cette page décrit la fonctionnalité actuelle ; la politique décrit les règles obligatoires entourant le changement forest-wide.

## Maintenance

Ce document doit être mis à jour après validation réelle si changent :

- le modèle d’inventaire ;
- les règles d’éligibilité ;
- la politique des classes restaurables ;
- les TTL ;
- les mécanismes one-shot ;
- l’opt-in worker ;
- le transport signé ;
- le handler `Restore-ADObject` ;
- ou l’interface C9-FINAL.
