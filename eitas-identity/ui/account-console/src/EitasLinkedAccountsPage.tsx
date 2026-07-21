import {
  LinkedAccounts,
} from "@keycloak/keycloak-account-ui";
import style from "./EitasLinkedAccountsPage.module.css";
import { environment } from "./environment";
const LinkIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M9.7 7.3 7.3 9.7a3.25 3.25 0 0 0 4.6 4.6l1.4-1.4 1.4 1.4-1.4 1.4a5.25 5.25 0 0 1-7.4-7.4l2.4-2.4a5.25 5.25 0 0 1 7.4 0l.7.7L15 8l-.7-.7a3.25 3.25 0 0 0-4.6 0Zm4.6 2.4 1.4-1.4a5.25 5.25 0 0 1 7.4 7.4l-2.4 2.4a5.25 5.25 0 0 1-7.4 0l-.7-.7L14 16l.7.7a3.25 3.25 0 0 0 4.6 0l2.4-2.4a3.25 3.25 0 0 0-4.6-4.6l-1.4 1.4-1.4-1.4Zm-5 3.3 4-4 1.4 1.4-4 4L9.3 13Z"
      fill="currentColor"
    />
  </svg>
);

const FederationIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M12 2.5 20 6v5.35c0 4.75-3.2 8.63-8 10.15-4.8-1.52-8-5.4-8-10.15V6l8-3.5Zm0 2.18L6 7.3v4.05c0 3.58 2.28 6.5 6 7.83 3.72-1.33 6-4.25 6-7.83V7.3l-6-2.62Zm-2.4 4.07a2.1 2.1 0 1 1 4.2 0v.65h.7c.83 0 1.5.67 1.5 1.5v3.6c0 .83-.67 1.5-1.5 1.5h-5c-.83 0-1.5-.67-1.5-1.5v-3.6c0-.83.67-1.5 1.5-1.5h.1v-.65Zm2.1.65h.4v-.65a.1.1 0 1 0-.2 0v.65h-.2Z"
      fill="currentColor"
    />
  </svg>
);

export const EitasLinkedAccountsPage = () => (
  <section className={style.page}>
    <header className={style.pageHeader}>
      <div>
        <span className={style.eyebrow}>
          Identité fédérée
        </span>

        <h1>Comptes associés</h1>

        <p>
          Reliez votre identité EITAS à des fournisseurs
          externes approuvés par votre organisation.
        </p>
      </div>

      <div className={style.securityStatus}>
        <span className={style.securityStatusIcon}>
          <FederationIcon />
        </span>

        <div>
          <strong>Liaison sécurisée</strong>
          <span>OIDC et PKCE S256</span>
        </div>
      </div>
    </header>

    <section className={style.panel}>
      <header className={style.panelHeader}>
        <span className={style.panelIcon}>
          <LinkIcon />
        </span>

        <div>
          <strong>Fournisseurs d’identité</strong>

          <span>
            Gérez les comptes externes liés à votre
            identité professionnelle.
          </span>
        </div>
      </header>

      <div className={style.panelBody}>
        {environment.features.isLinkedAccountsEnabled ? (
          <LinkedAccounts />
        ) : (
          <div
            className={style.emptyState}
            role="status"
          >
            <span className={style.emptyStateIcon}>
              <LinkIcon />
            </span>

            <div>
              <strong>
                Aucun fournisseur d’identité configuré
              </strong>

              <p>
                Votre organisation n’a pas encore activé
                de fournisseur externe. Aucun compte ne
                peut être associé pour le moment.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  </section>
);

export default EitasLinkedAccountsPage;
