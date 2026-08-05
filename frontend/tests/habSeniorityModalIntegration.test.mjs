import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const frontendRoot =
  new URL('../', import.meta.url)

function readSource(relativePath) {
  return readFileSync(
    new URL(relativePath, frontendRoot),
    'utf8'
  )
}

const page = readSource(
  'src/features/active-directory/AdExplorerPage.jsx'
)

const hook = readSource(
  'src/features/active-directory/hooks/useHabSenioritySimulation.js'
)

const modal = readSource(
  'src/features/active-directory/components/AdObjectPropertiesModal.jsx'
)

test(
  'le chargement du mode retourne la valeur réellement chargée',
  () => {
    assert.match(
      page,
      /const nextMode = data\?\.mode \|\| 'Inconnu'/
    )

    assert.match(
      page,
      /setAdAgentMode\(nextMode\)\s+return nextMode/
    )
  }
)

test(
  'le hook peut ouvrir avec un mode explicitement chargé',
  () => {
    assert.match(
      hook,
      /function open\(modeOverride = agentMode\)/
    )

    assert.match(
      hook,
      /agentMode: modeOverride/
    )
  }
)

test(
  'le bouton HAB dépend du RBAC et du type utilisateur, pas du mode initial',
  () => {
    const canManageLine = modal
      .split('\n')
      .find(line =>
        line.includes('const canManageHab')
      )

    assert.ok(canManageLine)

    const sectionStart =
      modal.indexOf('const canManageHab')

    const section = modal.slice(
      sectionStart,
      sectionStart + 120
    )

    assert.match(
      section,
      /Boolean\(canManageActiveDirectory\)/
    )

    assert.match(
      section,
      /isUserObject/
    )

    assert.doesNotMatch(
      section,
      /agentMode === 'Simulation'/
    )
  }
)

test(
  'l’ouverture HAB utilise le mode chargé et reste Simulation uniquement',
  () => {
    assert.match(
      modal,
      /const loadedMode =\s+await loadAgentMode\?\.\(\)/
    )

    assert.match(
      modal,
      /habSimulation\.open\(effectiveMode\)/
    )
  }
)

test(
  'l’éditeur HAB remplace les propriétés au lieu de se superposer',
  () => {
    assert.match(
      modal,
      /\{habSimulationActive \? \(\s+<HabSenioritySimulationEditor/
    )

    assert.doesNotMatch(
      modal,
      /\{habSimulationActive && \(/
    )

    const callStart =
      modal.indexOf(
        '<HabSenioritySimulationEditor'
      )

    const callEnd =
      modal.indexOf('/>', callStart) + 2

    const editorCall =
      modal.slice(callStart, callEnd)

    assert.match(
      editorCall,
      /editor=\{habSimulation\}/
    )

    assert.doesNotMatch(
      editorCall,
      /onClose=/
    )
  }
)

test(
  'le footer HAB permet de revenir aux propriétés',
  () => {
    assert.match(
      modal,
      /<footer className="aduc-modal-actions">\s+\{habSimulationActive \? \(/
    )

    assert.match(
      modal,
      /habSimulation\.close\(\)\s+setHabSimulationActive\(false\)/
    )

    assert.match(
      modal,
      /Retour aux propriétés/
    )
  }
)

test('HAB action uses footer layout', () => {
  const headerStart = modal.indexOf(
    '<div className="aduc-object-properties-header-actions">'
  )

  const headerEnd = modal.indexOf(
    '</div>',
    headerStart
  )

  const header = modal.slice(
    headerStart,
    headerEnd
  )

  assert.doesNotMatch(
    header,
    /beginHabSimulation/
  )

  const footerStart = modal.indexOf(
    '<footer className="aduc-modal-actions">'
  )

  const footer = modal.slice(footerStart)

  assert.match(
    footer,
    /className="aduc-properties-hab-button"/
  )

  assert.match(
    footer,
    /onClick=\{beginHabSimulation\}/
  )
})

test('HAB unavailable notice uses warning state', () => {
  assert.match(
    modal,
    /const isHabWarningNotice =/
  )

  assert.match(
    modal,
    /aduc-object-properties-notice\$\{/
  )

  assert.match(
    modal,
    /isHabWarningNotice[\s\S]*\? '!'/
  )
})

test('HAB layout CSS prevents header overlap', () => {
  const css = readSource(
    'src/styles/07-active-directory.css'
  )

  assert.match(
    css,
    /\/\* EITAS HAB modal action layout \*\//
  )

  assert.match(
    css,
    /\.aduc-properties-hab-button/
  )

  assert.match(
    css,
    /\.aduc-object-properties-notice\.warning/
  )

  assert.match(
    css,
    /button\[aria-label="Fermer"\]/
  )

  assert.match(
    css,
    /white-space: nowrap/
  )

  assert.match(
    css,
    /@media \(max-width: 760px\)/
  )
})
