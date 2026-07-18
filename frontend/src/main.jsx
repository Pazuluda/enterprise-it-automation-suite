import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { initializeAuthentication } from './auth/keycloak.js'

const root = createRoot(document.getElementById('root'))

function AuthenticationStartupError({ error }) {
  const message = error?.message || 'Erreur d’authentification inconnue.'

  return (
    <main className="auth-startup-page">
      <section className="auth-startup-card">
        <span className="auth-startup-badge">Sécurité Forteresse</span>
        <h1>Connexion au portail impossible</h1>
        <p>{message}</p>
        <p>
          Vérifie l’accès HTTPS à Keycloak, puis recharge la page.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
        >
          Réessayer
        </button>
      </section>
    </main>
  )
}

async function startPortal() {
  try {
    window.localStorage.removeItem(
      ['eitas', 'api', 'key'].join('_')
    )

    const authClient = await initializeAuthentication()

    root.render(
      <StrictMode>
        <App authClient={authClient} />
      </StrictMode>,
    )
  } catch (error) {
    console.error('Initialisation OIDC impossible.', error)

    root.render(
      <StrictMode>
        <AuthenticationStartupError error={error} />
      </StrictMode>,
    )
  }
}

startPortal()
