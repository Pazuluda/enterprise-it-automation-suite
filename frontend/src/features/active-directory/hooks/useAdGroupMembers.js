import { useState } from 'react'

import {
  getObjectDn,
  getObjectName,
  isEitasManagedObject,
  isGroupObject,
} from '../utils/adExplorerCore'

function useAdGroupMembers({
  setMessage,
  setStatus,
  setContextMenu,
  runJob,
  runAdAdminJob,
  loadGroupMembers,
  openProperties,
  selectedObject,
  cleanAdAdminMessage,
}) {
  const [memberModal, setMemberModal] = useState(null)
  const [memberIdentity, setMemberIdentity] = useState('')
  const [memberSearchResults, setMemberSearchResults] = useState([])
  const [memberSearchLoading, setMemberSearchLoading] = useState(false)
  const [memberSearchError, setMemberSearchError] = useState('')
  const [selectedMemberCandidate, setSelectedMemberCandidate] = useState(null)
  const [memberSubmitError, setMemberSubmitError] = useState('')
  const [memberActionLoading, setMemberActionLoading] = useState(false)

  function openAddMemberModal(group) {
    if (!isEitasManagedObject(group)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    if (!group || !isGroupObject(group)) {
      setMessage?.('Sélectionne un groupe avant d’ajouter un membre.')
      return
    }

    resetMemberPicker()
    setMemberModal(group)
  }

  function resetMemberPicker() {
    setMemberIdentity('')
    setMemberSearchResults([])
    setMemberSearchLoading(false)
    setMemberSearchError('')
    setSelectedMemberCandidate(null)
    setMemberSubmitError('')
  }

  function closeMemberModal() {
    setMemberModal(null)
    resetMemberPicker()
  }

  function decorateMemberCandidate(candidate, kind) {
    return {
      ...candidate,
      _member_candidate_kind: kind,
      _member_candidate_label: kind === 'group' ? 'Groupe AD' : 'Utilisateur AD'
    }
  }

  function getMemberCandidateKindLabel(candidate) {
    return candidate?._member_candidate_label || (
      isGroupObject(candidate) ? 'Groupe AD' : 'Utilisateur AD'
    )
  }

  function getMemberCandidateIdentity(candidate) {
    return String(
      candidate?.sam_account_name ||
      candidate?.samAccountName ||
      candidate?.user_principal_name ||
      candidate?.upn ||
      candidate?.name ||
      candidate?.distinguished_name ||
      candidate?.dn ||
      ''
    )
  }

  function getMemberCandidateTitle(candidate) {
    return String(candidate?.display_name || candidate?.name || candidate?.sam_account_name || 'Utilisateur')
  }

  function getMemberCandidateSubtitle(candidate) {
    const parts = [
      candidate?.sam_account_name,
      candidate?.user_principal_name || candidate?.upn,
      candidate?.distinguished_name || candidate?.dn
    ].filter(Boolean)

    return parts.join(' • ')
  }

  function selectMemberCandidate(candidate) {
    const identity = getMemberCandidateIdentity(candidate)

    setSelectedMemberCandidate(candidate)
    setMemberIdentity(identity)
    setMemberSearchError('')
  }

  async function searchMemberCandidates() {
    const query = memberIdentity.trim()

    setSelectedMemberCandidate(null)
    setMemberSearchError('')
    setMemberSubmitError('')

    if (query.length < 2) {
      setMemberSearchResults([])
      setMemberSearchError('Tape au moins 2 caractères pour rechercher un utilisateur ou un groupe.')
      return
    }

    setMemberSearchLoading(true)

    try {
      const [users, groups] = await Promise.all([
        runJob('search_users', {
          query,
          baseDn: 'OU=Users,OU=EITAS,DC=API,DC=LOCAL',
          limit: 50,
          recursive: true
        }),
        runJob('list_groups', {
          baseDn: 'OU=Groups,OU=EITAS,DC=API,DC=LOCAL',
          limit: 500,
          recursive: true
        })
      ])

      const normalizedQuery = query.toLowerCase()

      const matchingGroups = groups.filter(group =>
        [
          group?.name,
          group?.sam_account_name,
          group?.samAccountName,
          group?.description,
          group?.distinguished_name,
          group?.dn
        ]
          .filter(Boolean)
          .some(value => String(value).toLowerCase().includes(normalizedQuery))
      )

      const decoratedUsers = users.map(user => decorateMemberCandidate(user, 'user'))
      const decoratedGroups = matchingGroups.map(group => decorateMemberCandidate(group, 'group'))

      const results = [...decoratedUsers, ...decoratedGroups]

      setMemberSearchResults(results)

      if (!results.length) {
        setMemberSearchError('Aucun utilisateur ou groupe trouvé.')
      }
    } catch (error) {
      setMemberSearchResults([])
      setMemberSearchError(error.message || 'Recherche utilisateur/groupe impossible.')
    } finally {
      setMemberSearchLoading(false)
    }
  }

  async function submitAddMember(event) {
    event.preventDefault()

    if (!memberModal) return

    const identity = selectedMemberCandidate ? getMemberCandidateIdentity(selectedMemberCandidate).trim() : memberIdentity.trim()

    if (memberSearchResults.length > 0 && !selectedMemberCandidate) {
      setMemberSearchError('Sélectionne un utilisateur ou un groupe exact dans la liste avant d’ajouter.')
      setMessage?.('Sélectionne un utilisateur ou un groupe exact dans la liste avant d’ajouter.')
      return
    }

    if (!identity) {
      setMessage?.('Identifiant utilisateur ou groupe obligatoire.')
      return
    }

    setMemberActionLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'add_group_member',
        group_identity: memberModal.sam_account_name || memberModal.name || getObjectDn(memberModal),
        member_identity: identity
      })

      const output = job?.output || {}
      const groupName = output.group || memberModal.sam_account_name || memberModal.name || getObjectDn(memberModal)
      const memberName = output.member || (selectedMemberCandidate ? getMemberCandidateTitle(selectedMemberCandidate) : identity)
      const rawMessage = cleanAdAdminMessage(output.message || job?.message || '')

      await loadGroupMembers(memberModal, { silent: true })

      if (output.already_member || rawMessage.toLowerCase().includes('déjà')) {
        setMemberSubmitError(`${memberName} est déjà membre de ${groupName}.`)
        setMessage?.(`${memberName} est déjà membre de ${groupName}.`)
        return
      }

      const simulated = output.simulated === true || rawMessage.toLowerCase().includes('simulation')

        if (simulated) {
          setMessage?.(`Simulation : ${memberName} non ajouté réellement à ${groupName}.`)
        } else {
          setMessage?.(`Production : ${memberName} ajouté à ${groupName}.`)
        }
      closeMemberModal()
    } catch (err) {
      setMessage?.(err.message || 'Impossible d’ajouter le membre.')
    } finally {
      setMemberActionLoading(false)
    }
  }

  async function removeGroupMember(group, member) {
    if (!isEitasManagedObject(group)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    if (!group || !member) return

    const memberLabel = getObjectDn(member) || member.sam_account_name || member.name
    const groupLabel = getObjectDn(group) || group.sam_account_name || group.name

    if (!window.confirm(`Retirer ${memberLabel} du groupe ${groupLabel} ?`)) {
      return
    }

    setMemberActionLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'remove_group_member',
        group_identity: groupLabel,
        member_identity: memberLabel
      })

      const output = job?.output || {}
      const rawMessage = cleanAdAdminMessage(output.message || job?.message || '')
      const simulated = output.simulated === true || rawMessage.toLowerCase().includes('simulation')
      const memberName = output.member || member.sam_account_name || member.name || getObjectName(member) || memberLabel
      const groupName = output.group || group.sam_account_name || group.name || getObjectName(group) || groupLabel

      if (simulated) {
        setMessage?.(`Simulation : ${memberName} non retiré réellement de ${groupName}.`)
      } else {
        setMessage?.(`Production : ${memberName} retiré de ${groupName}.`)
      }

      if (isGroupObject(group)) {
        await loadGroupMembers(group, { silent: true })
      }

      if (selectedObject && !isGroupObject(selectedObject)) {
        await openProperties(selectedObject)
      }
    } catch (err) {
      setMessage?.(err.message || 'Impossible de retirer le membre.')
    } finally {
      setMemberActionLoading(false)
    }
  }

  return {
    memberModal,
    setMemberModal,
    memberIdentity,
    setMemberIdentity,
    memberSearchResults,
    setMemberSearchResults,
    memberSearchLoading,
    setMemberSearchLoading,
    memberSearchError,
    setMemberSearchError,
    selectedMemberCandidate,
    setSelectedMemberCandidate,
    memberSubmitError,
    setMemberSubmitError,
    memberActionLoading,
    setMemberActionLoading,
    openAddMemberModal,
    resetMemberPicker,
    closeMemberModal,
    decorateMemberCandidate,
    getMemberCandidateKindLabel,
    getMemberCandidateIdentity,
    getMemberCandidateTitle,
    getMemberCandidateSubtitle,
    selectMemberCandidate,
    searchMemberCandidates,
    submitAddMember,
    removeGroupMember,
  }
}

export default useAdGroupMembers
