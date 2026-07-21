import {
  PersonalInfo,
} from "@keycloak/keycloak-account-ui";
import style from "./EitasPersonalInfoPage.module.css";

const ProfileIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M12 2.75a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6ZM4 20.5v-1.25c0-3.1 2.85-5.5 6.25-5.5h3.5c3.4 0 6.25 2.4 6.25 5.5v1.25h-2v-1.25c0-1.88-1.82-3.5-4.25-3.5h-3.5C7.82 15.75 6 17.37 6 19.25v1.25H4Z"
      fill="currentColor"
    />
  </svg>
);

export const EitasPersonalInfoPage = () => (
  <section className={style.page}>
    <header className={style.pageHeader}>
      <div>
        <span className={style.eyebrow}>
          Identité du compte
        </span>

        <h1>Informations personnelles</h1>

        <p>
          Gérez les informations principales associées
          à votre identité EITAS.
        </p>
      </div>

      <div className={style.profileStatus}>
        <span className={style.profileStatusIcon}>
          <ProfileIcon />
        </span>

        <div>
          <strong>Profil actif</strong>
          <span>Données personnelles sécurisées</span>
        </div>
      </div>
    </header>

    <section className={style.panel}>
      <header className={style.panelHeader}>
        <span className={style.panelIcon}>
          <ProfileIcon />
        </span>

        <div>
          <strong>Informations du compte</strong>

          <span>
            Ces informations permettent de vous identifier
            dans les services EITAS.
          </span>
        </div>
      </header>

      <div className={style.panelBody}>
        <PersonalInfo />
      </div>
    </section>
  </section>
);

export default EitasPersonalInfoPage;
