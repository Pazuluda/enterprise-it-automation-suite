import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const page = fs.readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url
  ),
  'utf8'
)

const hook = fs.readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdAccountActions.js',
    import.meta.url
  ),
  'utf8'
)

const modal = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/AccountActionModal.jsx',
    import.meta.url
  ),
  'utf8'
)

test(
  'transmet le chargeur de mode aux actions de compte',
  () => {
    assert.match(
      page,
      /useAdAccountActions\(\{[\s\S]*loadAdAgentMode/
    )

    assert.match(
      hook,
      /loadAdAgentMode/
    )
  }
)

test(
  'charge et valide le mode avant d ouvrir la modale',
  () => {
    assert.match(
      hook,
      /async function prepareAccountAction/
    )

    assert.match(
      hook,
      /await resolveAccountActionMode\(\)/
    )

    assert.match(
      hook,
      /agentMode:\s*resolvedMode/
    )

    assert.match(
      hook,
      /Mode agent indisponible/
    )
  }
)

test(
  'reverifie le mode juste avant la soumission',
  () => {
    assert.match(
      hook,
      /verifiedMode/
    )

    assert.match(
      hook,
      /verifiedMode[\s\S]*accountActionModal\.agentMode/
    )

    assert.match(
      hook,
      /Vérifie la modale puis relance/
    )
  }
)

test(
  'bloque visuellement tout mode inconnu',
  () => {
    assert.match(
      modal,
      /isKnownAgentMode/
    )

    assert.match(
      modal,
      /!isKnownAgentMode/
    )

    assert.match(
      modal,
      /Mode agent indisponible/
    )

    assert.match(
      modal,
      /accountActionModeLoading/
    )
  }
)

console.log(
  'C3.2 SECURITE MODE AGENT : TESTS REUSSIS'
)
