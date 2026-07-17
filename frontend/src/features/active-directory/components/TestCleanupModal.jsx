import {
  getObjectDn,
  objectIcon,
} from '../utils/adExplorerCore'

function TestCleanupModal({
  open,
  cleanup,
  isProduction,
  onClose,
}) {
  const {
    testCleanupLoading,
    testCleanupItems,
    testCleanupError,
    testCleanupDeletingDn,
    testCleanupResults,
    testCleanupBulkRunning,
    getTestCleanupIdentity,
    deleteTestCleanupObject,
    isTestCleanupOu,
    runBulkTestCleanup,
    scanTestCleanupObjects,
  } = cleanup

  if (!open) return null

  return (
    <div className="aduc-modal-backdrop" onClick={() => onClose()}>
              <section className="aduc-modal aduc-test-cleanup-modal" onClick={event => event.stopPropagation()}>
                <header>
                  <div>
                    <span>Maintenance Active Directory</span>
                    <h3>Nettoyage des objets de test</h3>
                  </div>

                  <button type="button" onClick={() => onClose()}>×</button>
                </header>

                <div className="aduc-test-cleanup-summary">
                  <strong>{testCleanupLoading ? 'Scan en cours...' : `${testCleanupItems.length} objet(s) détecté(s)`}</strong>
                  <span>Patterns : TMP_*, TEST_*, GG_TMP_*, test.*</span>
                </div>

                {testCleanupError && (
                  <div className="aduc-member-submit-error">
                    {testCleanupError}
                  </div>
                )}

                {!testCleanupLoading && !testCleanupError && testCleanupItems.length === 0 && (
                  <div className="aduc-empty-state">
                    Aucun objet de test détecté dans l’arbre AD courant.
                  </div>
                )}

                {testCleanupItems.length > 0 && (
                  <div className="aduc-test-cleanup-list">
                    {testCleanupItems.map((item, index) => (
                      <article key={getObjectDn(item) || `${getTestCleanupIdentity(item)}-${index}`} className="aduc-test-cleanup-item">
                        <div className="aduc-test-cleanup-icon">{objectIcon(item)}</div>

                        <div>
                          <strong>{getTestCleanupIdentity(item) || item?.name || 'Objet AD'}</strong>
                          <span>{item?.type || item?.objectClass || 'objet'} · {item.cleanup_reason}</span>
                          <code>{getObjectDn(item)}</code>

                          {testCleanupResults[getObjectDn(item)] && (
                            <em className={`aduc-test-cleanup-result ${testCleanupResults[getObjectDn(item)].type}`}>
                              {testCleanupResults[getObjectDn(item)].message}
                            </em>
                          )}
                        </div>

                        <button
                          type="button"
                          className="aduc-test-cleanup-delete"
                          disabled={testCleanupDeletingDn === getObjectDn(item)}
                          onClick={() => deleteTestCleanupObject(item)}
                        >
                          {testCleanupDeletingDn === getObjectDn(item)
                            ? 'Suppression...'
                            : isProduction
                              ? isTestCleanupOu(item) ? 'Supprimer OU' : 'Supprimer'
                              : 'Simuler'}
                        </button>
                      </article>
                    ))}
                  </div>
                )}

                <footer className="aduc-modal-actions">
                  <button type="button" onClick={() => onClose()}>Fermer</button>
                  {testCleanupItems.length > 0 && (
                    <button
                      type="button"
                      className="danger"
                      onClick={runBulkTestCleanup}
                      disabled={testCleanupLoading || testCleanupBulkRunning || Boolean(testCleanupDeletingDn)}
                    >
                      {testCleanupBulkRunning
                        ? 'Nettoyage...'
                        : isProduction ? 'Tout supprimer' : 'Tout simuler'}
                    </button>
                  )}

                  <button type="button" onClick={scanTestCleanupObjects} disabled={testCleanupLoading || testCleanupBulkRunning}>
                    {testCleanupLoading ? 'Scan...' : 'Relancer le scan'}
                  </button>
                </footer>
              </section>
            </div>
  )
}

export default TestCleanupModal
