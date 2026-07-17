import {
  getObjectDn,
} from '../utils/adExplorerCore'

function AddMemberModal({
  member,
}) {
  const {
    memberModal,
    closeMemberModal,
    submitAddMember,
    memberIdentity,
    setMemberIdentity,
    setSelectedMemberCandidate,
    setMemberSearchError,
    setMemberSubmitError,
    memberSearchLoading,
    searchMemberCandidates,
    memberSearchError,
    memberSearchResults,
    getMemberCandidateIdentity,
    selectedMemberCandidate,
    getMemberCandidateKindLabel,
    selectMemberCandidate,
    getMemberCandidateTitle,
    getMemberCandidateSubtitle,
    memberSubmitError,
    memberActionLoading,
  } = member

  if (!memberModal) return null

  return (
    <div className="aduc-modal-backdrop" onClick={closeMemberModal}>
              <form className="aduc-modal aduc-member-modal" onSubmit={submitAddMember} onClick={event => event.stopPropagation()}>
                <header>
                  <div>
                    <span>Administration Active Directory</span>
                    <h3>Ajouter un membre</h3>
                  </div>

                  <button type="button" onClick={closeMemberModal}>×</button>
                </header>

                <label>
                  Groupe cible
                  <input value={memberModal.sam_account_name || memberModal.name || getObjectDn(memberModal)} readOnly />
                </label>

                <label>
                  Utilisateur ou groupe à ajouter
                  <div className="aduc-member-picker-row">
                    <input
                      value={memberIdentity}
                      onChange={event => {
                        setMemberIdentity(event.target.value)
                        setSelectedMemberCandidate(null)
                        setMemberSearchError('')
                        setMemberSubmitError('')
                      }}
                      placeholder="Ex : l.ve, liam, GG_Support_RW..."
                      autoFocus
                    />
                    <button
                      type="button"
                      className="aduc-member-search-button"
                      onClick={searchMemberCandidates}
                      disabled={memberSearchLoading || memberIdentity.trim().length < 2}
                    >
                      {memberSearchLoading ? 'Recherche...' : 'Rechercher'}
                    </button>
                  </div>
                </label>

                {memberSearchError && (
                  <div className="aduc-member-search-error">
                    {memberSearchError}
                  </div>
                )}

                {memberSearchResults.length > 0 && (
                  <div className="aduc-member-search-results">
                    {memberSearchResults.map(candidate => {
                      const identity = getMemberCandidateIdentity(candidate)
                      const selected = selectedMemberCandidate && getMemberCandidateIdentity(selectedMemberCandidate) === identity

                      return (
                        <button
                          type="button"
                          key={identity}
                          data-kind-label={getMemberCandidateKindLabel(candidate)}
                          className={selected ? 'is-selected' : ''}
                          onClick={() => selectMemberCandidate(candidate)}
                        >
                          <strong>{getMemberCandidateTitle(candidate)}</strong>
                          <small>{getMemberCandidateSubtitle(candidate)}</small>
                        </button>
                      )
                    })}
                  </div>
                )}

                <div className="aduc-modal-warning">
                  <strong>Production AD</strong>
                  <span>Cette action ajoutera l’utilisateur ou le groupe sélectionné dans le groupe via l’agent Windows.</span>
                </div>

                {memberSubmitError && (
                  <div className="aduc-member-submit-error">
                    <strong>Impossible d’ajouter ce membre</strong>
                    <span>{memberSubmitError}</span>
                  </div>
                )}

                <footer>
                  <button type="button" onClick={closeMemberModal}>Annuler</button>
                  <button type="submit" disabled={memberActionLoading}>
                    {memberActionLoading ? 'Ajout...' : 'Ajouter le membre'}
                  </button>
                </footer>
              </form>
            </div>
  )
}

export default AddMemberModal
