import Keycloak from 'keycloak-js'

const APP_URL = `${window.location.origin}/app/`

const keycloak = new Keycloak({
  url: `${window.location.origin}/auth`,
  realm: 'eitas',
  clientId: 'eitas-portal'
})

function getRoles(token = keycloak.tokenParsed) {
  const roles = token?.realm_access?.roles

  if (!Array.isArray(roles)) {
    return []
  }

  return roles
    .filter(role => (
      typeof role === 'string'
      && role
      && !role.startsWith('default-roles-')
      && role !== 'offline_access'
      && role !== 'uma_authorization'
    ))
    .sort((left, right) => left.localeCompare(right, 'fr'))
}

function getIdentity() {
  const token = keycloak.tokenParsed || {}
  const fallbackName = (
    token.preferred_username
    || token.email
    || token.sub
    || 'Utilisateur'
  )

  return {
    authenticated: Boolean(keycloak.authenticated),
    subject: token.sub || '',
    username: token.preferred_username || fallbackName,
    displayName: (
      token.name
      || [token.given_name, token.family_name].filter(Boolean).join(' ')
      || fallbackName
    ),
    email: token.email || '',
    roles: getRoles(token)
  }
}

async function ensureAuthenticated() {
  if (keycloak.authenticated && keycloak.token) {
    return
  }

  await keycloak.login({
    redirectUri: APP_URL
  })

  throw new Error('Redirection vers Keycloak en cours.')
}

async function getAccessToken(minValidity = 30) {
  await ensureAuthenticated()

  try {
    await keycloak.updateToken(minValidity)
  } catch (error) {
    console.error('Renouvellement du jeton Keycloak impossible.', error)

    await keycloak.login({
      redirectUri: APP_URL
    })

    throw new Error('Session Keycloak expirée.')
  }

  if (!keycloak.token) {
    throw new Error('Jeton Keycloak indisponible.')
  }

  return keycloak.token
}

async function forceRefreshAccessToken() {
  await ensureAuthenticated()

  try {
    await keycloak.updateToken(-1)
  } catch (error) {
    console.error('Actualisation forcée Keycloak impossible.', error)

    await keycloak.login({
      redirectUri: APP_URL
    })

    throw new Error('Actualisation Keycloak impossible.')
  }

  if (!keycloak.token) {
    throw new Error('Jeton Keycloak indisponible après actualisation.')
  }

  return keycloak.token
}

async function initializeAuthentication() {
  const authenticated = await keycloak.init({
    onLoad: 'login-required',
    flow: 'standard',
    pkceMethod: 'S256',
    checkLoginIframe: false,
    redirectUri: APP_URL
  })

  if (!authenticated) {
    await keycloak.login({
      redirectUri: APP_URL
    })

    throw new Error('Authentification Keycloak requise.')
  }

  keycloak.onTokenExpired = () => {
    keycloak.updateToken(30).catch(error => {
      console.error('Session Keycloak expirée.', error)
      keycloak.login({ redirectUri: APP_URL })
    })
  }

  keycloak.onAuthLogout = () => {
    window.location.assign(APP_URL)
  }

  return {
    getAccessToken,
    forceRefreshAccessToken,
    getIdentity,
    login(options = {}) {
      return keycloak.login({
        redirectUri: APP_URL,
        ...options
      })
    },
    logout() {
      return keycloak.logout({
        redirectUri: APP_URL
      })
    }
  }
}

export {
  initializeAuthentication
}
