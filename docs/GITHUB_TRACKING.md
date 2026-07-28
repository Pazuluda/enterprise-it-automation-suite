# Suivi GitHub EITAS

GitHub devient la source de suivi officielle des chantiers, versions, anomalies et décisions techniques d'EITAS.

## Project recommandé

Nom : `EITAS Roadmap`

Vues :

- Roadmap ;
- Board ;
- Table ;
- Releases.

## Milestones

- `v0.2.0 — C2 Éditeur LDAP`
- `v0.3.0 — C3 Utilisateurs avancés`
- `v0.4.0 — C4 Groupes`
- `v0.5.0 — C5 Objets AD`
- `v0.6.0 — C6 Recherche`
- `v0.7.0 — C7 Actions multiples`
- `v0.8.0 — C8 ACL et délégation`
- `v0.9.0 — C9 Corbeille AD`
- `v0.10.0 — C10 Finition`

## Labels

### Type

- `type: feature`
- `type: bug`
- `type: documentation`
- `type: security`
- `type: maintenance`
- `type: audit`

### Zone

- `area: frontend`
- `area: api`
- `area: windows-agent`
- `area: active-directory`
- `area: identity`
- `area: deployment`
- `area: documentation`

### Priorité et état

- `priority: critical`
- `priority: high`
- `priority: medium`
- `priority: low`
- `status: blocked`
- `status: needs-validation`
- `status: needs-design`
- `status: ready`

## Cycle de travail

```text
Issue
→ cadrage
→ développement
→ validation technique
→ validation visuelle
→ contrôle de sécurité
→ commit groupé
→ fermeture de l'issue
→ mise à jour du changelog
→ release
```

## Définition de terminé

Une issue est terminée lorsque son périmètre, ses validations, sa sécurité, sa documentation, son commit et ses preuves sont complets.

## Commits

Les petits changements sont regroupés par lot cohérent.

Exemples :

```text
feat(ad-explorer): add controlled LDAP attribute editing
fix(ad-explorer): preserve empty multivalue attributes
docs(project): document v0.2.0 release process
test(api): cover LDAP attribute validation
```
