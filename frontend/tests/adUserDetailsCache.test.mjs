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
    '../src/features/active-directory/hooks/useAdObjectUpdate.js',
    import.meta.url
  ),
  'utf8'
)

test(
  'conserve le lookup utilisateur historique',
  () => {
    assert.match(
      page,
      /async function runAdUserDetailsJobUncached\(target\)/
    )
  }
)

test(
  'utilise un cache dedie par utilisateur',
  () => {
    assert.match(
      page,
      /userDetailsCacheRef = useRef\(new Map\(\)\)/
    )

    assert.match(
      page,
      /userDetailsPromisesRef = useRef\(new Map\(\)\)/
    )
  }
)

test(
  'indexe le cache par identite et revision',
  () => {
    assert.match(
      page,
      /function getUserDetailsCacheKey/
    )

    assert.match(
      page,
      /getUserDetailsIdentity\(target\)/
    )

    assert.match(
      page,
      /getUserDetailsRevision\(target\)/
    )
  }
)

test(
  'retourne le cache avant le lookup reel',
  () => {
    const start = page.indexOf(
      'async function runAdUserDetailsJob('
    )

    const end = page.indexOf(
      'function prefetchUserDetails',
      start
    )

    const source = page.slice(start, end)

    assert.ok(
      source.indexOf(
        'userDetailsCacheRef.current.has'
      ) >= 0
    )

    assert.ok(
      source.indexOf(
        'runAdUserDetailsJobUncached'
      )
      >
      source.indexOf(
        'userDetailsCacheRef.current.has'
      )
    )
  }
)

test(
  'partage les requetes deja en cours',
  () => {
    assert.match(
      page,
      /userDetailsPromisesRef\.current\.has/
    )

    assert.match(
      page,
      /userDetailsPromisesRef\.current\.set/
    )

    assert.match(
      page,
      /userDetailsPromisesRef\.current\.delete/
    )
  }
)

test(
  'prefetch les details lors de la selection',
  () => {
    const start = page.indexOf(
      'function selectObject(item)'
    )

    const end = page.indexOf(
      '\n  function ',
      start + 10
    )

    const source = page.slice(start, end)

    assert.match(
      source,
      /prefetchUserDetails\(item\)/
    )
  }
)

test(
  'enrichit uniquement l objet encore selectionne',
  () => {
    assert.match(
      page,
      /getUserDetailsIdentity\(current\)[\s\S]*!== identity/
    )

    assert.match(
      page,
      /setSelectedObject\(mergeCurrent\)/
    )

    assert.match(
      page,
      /setPropertiesModal\(mergeCurrent\)/
    )
  }
)

test(
  'invalide le cache apres une sauvegarde',
  () => {
    assert.match(
      page,
      /invalidateUserDetailsCache,/
    )

    assert.match(
      hook,
      /invalidateUserDetailsCache,/
    )

    assert.match(
      hook,
      /invalidateUserDetailsCache\?\.\([\s\S]*updateModal[\s\S]*\)/
    )
  }
)


test(
  'resout le premier affichage depuis le snapshot avant le job',
  () => {
    assert.match(
      page,
      /function resolveUserUpdateTargetSync\(target\)/
    )

    assert.match(
      page,
      /adSnapshot\.findByDnSync\(targetDn\)/
    )

    assert.match(
      page,
      /adDomainCatalog\.findByDnSync\(targetDn\)/
    )

    assert.match(
      page,
      /mergeAdUserDetails\([\s\S]*target,[\s\S]*availableTarget/
    )
  }
)

test(
  'transmet la resolution synchrone au formulaire',
  () => {
    assert.match(
      page,
      /resolveUserUpdateTargetSync,/
    )

    assert.match(
      hook,
      /resolveUserUpdateTargetSync,/
    )
  }
)

test(
  'consulte le snapshot avant de construire le formulaire',
  () => {
    const start = hook.indexOf(
      'async function prepareUpdateObject'
    )

    const end = hook.indexOf(
      '\n  function openUpdateObject',
      start
    )

    const source = hook.slice(start, end)

    const syncIndex = source.indexOf(
      'resolveUserUpdateTargetSync(target)'
    )

    const formIndex = source.indexOf(
      'const rawSamAccountName'
    )

    const openIndex = source.indexOf(
      'setUpdateEditorOpen(openModal)'
    )

    const backgroundIndex = source.indexOf(
      'void resolveUserUpdateTarget(target)'
    )

    assert.ok(syncIndex >= 0)
    assert.ok(formIndex > syncIndex)
    assert.ok(openIndex > formIndex)
    assert.ok(backgroundIndex > openIndex)

    assert.doesNotMatch(
      source,
      /setLoading\?\.\(true\)/
    )

    assert.doesNotMatch(
      source,
      /await resolveUserUpdateTarget\(target\)/
    )
  }
)

test(
  'charge en arriere-plan les options absentes du snapshot',
  () => {
    const start = hook.indexOf(
      'async function prepareUpdateObject'
    )

    const end = hook.indexOf(
      '\n  function openUpdateObject',
      start
    )

    const source = hook.slice(start, end)

    assert.match(
      source,
      /pendingAccountFields/
    )

    assert.match(
      source,
      /setPendingUserAccountOptionFields\([\s\S]*pendingAccountFields/
    )

    assert.match(
      source,
      /void resolveUserUpdateTarget\(target\)/
    )

    assert.match(
      source,
      /setUpdateSaveError/
    )
  }
)



const nonBlockingForm = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/UpdateObjectForm.jsx',
    import.meta.url
  ),
  'utf8'
)

test(
  'ouvre le formulaire sans attendre le lookup detaille',
  () => {
    assert.doesNotMatch(
      hook,
      /await resolveUserUpdateTarget\(target\)/
    )

    assert.match(
      hook,
      /void resolveUserUpdateTarget\(target\)/
    )
  }
)

test(
  'ouvre le formulaire avant le chargement en arriere-plan',
  () => {
    const start = hook.indexOf(
      'async function prepareUpdateObject'
    )

    const end = hook.indexOf(
      '\n  function openUpdateObject',
      start
    )

    const source = hook.slice(start, end)

    const openIndex = source.indexOf(
      'setUpdateEditorOpen(openModal)'
    )

    const backgroundIndex = source.indexOf(
      'void resolveUserUpdateTarget(target)'
    )

    assert.ok(openIndex >= 0)
    assert.ok(backgroundIndex > openIndex)
  }
)

test(
  'ignore une reponse appartenant a une ancienne preparation',
  () => {
    assert.match(
      hook,
      /updatePreparationRequestIdRef\.current[\s\S]*!== preparationRequestId/
    )

    assert.match(
      hook,
      /updatePreparationRequestIdRef\.current \+= 1/
    )
  }
)

test(
  'ne remplace pas une option deja modifiee',
  () => {
    assert.match(
      hook,
      /updateDirtyFieldsRef\.current\.add\(name\)/
    )

    assert.match(
      hook,
      /!updateDirtyFieldsRef\.current\.has\([\s\S]*field/
    )
  }
)

test(
  'desactive seulement les options encore inconnues',
  () => {
    for (const field of [
      'passwordNeverExpires',
      'cannotChangePassword',
      'smartcardLogonRequired',
      'accountNotDelegated',
    ]) {
      assert.match(
        nonBlockingForm,
        new RegExp(
          `pendingUserAccountOptionFields[\\s\\S]*includes\\('${field}'\\)`
        )
      )
    }
  }
)
