const SWITCHER_ID =
  "eitas-admin-account-switcher";

const ACCOUNT_REALM = "eitas";

const getAccountUrl = () => {
  const match = window.location.pathname.match(
    /^(.*)\/admin\/[^/]+\/console(?:\/|$)/,
  );

  if (!match) {
    return null;
  }

  const basePath = match[1] || "";

  return (
    `${window.location.origin}${basePath}`
    + `/realms/${encodeURIComponent(
      ACCOUNT_REALM,
    )}/account/`
  );
};

const ensureAccountSwitcher = () => {
  const accountUrl = getAccountUrl();

  if (!accountUrl || !document.body) {
    return;
  }

  let link =
    document.getElementById(SWITCHER_ID);

  if (!link) {
    link = document.createElement("a");

    link.id = SWITCHER_ID;
    link.textContent = "Espace personnel";

    link.setAttribute(
      "aria-label",
      "Ouvrir mon espace personnel EITAS Identity",
    );

    link.setAttribute(
      "title",
      "Ouvrir mon espace personnel",
    );
  }

  link.href = accountUrl;

  Object.assign(link.style, {
    position: "fixed",
    right: "24px",
    bottom: "24px",
    zIndex: "2147483647",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "42px",
    padding: "0 18px",
    border: "1px solid rgba(255, 255, 255, 0.25)",
    borderRadius: "8px",
    background: "#29265f",
    color: "#ffffff",
    fontFamily: "inherit",
    fontSize: "14px",
    fontWeight: "700",
    lineHeight: "1",
    textDecoration: "none",
    boxShadow: "0 10px 28px rgba(15, 23, 42, 0.28)",
  });

  if (!link.isConnected) {
    document.body.append(link);
  }
};


const ADMIN_TEXT_TRANSLATIONS = [
  [
    "Actions taken after first broker login with identity provider account, which is not yet linked to any Keycloak account",
    "Actions exécutées lors de la première connexion via un fournisseur d’identité lorsque le compte n’est pas encore lié à EITAS Identity",
  ],
  [
    "Used by Docker clients to authenticate against the IDP",
    "Utilisé par les clients Docker pour s’authentifier auprès du fournisseur d’identité",
  ],
  [
    "Reset credentials for a user if they forgot their password or something",
    "Réinitialisation des identifiants d’un utilisateur ayant perdu son mot de passe",
  ],
  [
    "OpenID Connect Resource Owner Grant",
    "Flux OpenID Connect avec les identifiants de l’utilisateur",
  ],
  [
    "Base authentication for clients",
    "Authentification de base des clients",
  ],
  [
    "Browser based authentication",
    "Authentification via navigateur",
  ],
  [
    "Registration flow",
    "Flux d’inscription",
  ],
  [
    "KEYCLOAK",
    "EITAS Identity",
  ],
  [
    "first broker login",
    "Première connexion via un fournisseur d’identité",
  ],
  [
    "reset credentials",
    "Réinitialisation des identifiants",
  ],
  [
    "direct grant",
    "Accès direct",
  ],
  [
    "docker auth",
    "Authentification Docker",
  ],
  [
    "browser",
    "Navigateur",
  ],
  [
    "registration",
    "Inscription",
  ],
];

const translateAdminValue = (originalValue) => {
  const trimmedValue = originalValue.trim();

  if (trimmedValue === "clients") {
    return originalValue.replace(
      trimmedValue,
      "Authentification des clients",
    );
  }

  let translatedValue = originalValue;

  for (
    const [sourceValue, targetValue]
    of ADMIN_TEXT_TRANSLATIONS
  ) {
    translatedValue = translatedValue.replaceAll(
      sourceValue,
      targetValue,
    );
  }

  return translatedValue;
};

const translateAdminText = () => {
  if (!document.body) {
    return;
  }

  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
  );

  const nodes = [];

  while (walker.nextNode()) {
    nodes.push(walker.currentNode);
  }

  for (const node of nodes) {
    const parent = node.parentElement;

    if (
      !parent
      || parent.closest(
        "script, style, textarea, [contenteditable='true']",
      )
    ) {
      continue;
    }

    const originalValue = node.nodeValue || "";
    const translatedValue =
      translateAdminValue(originalValue);

    if (translatedValue !== originalValue) {
      node.nodeValue = translatedValue;
    }
  }

  for (
    const element
    of document.body.querySelectorAll(
      "[title], [aria-label], [placeholder]",
    )
  ) {
    for (
      const attribute
      of ["title", "aria-label", "placeholder"]
    ) {
      const originalValue =
        element.getAttribute(attribute);

      if (!originalValue) {
        continue;
      }

      const translatedValue =
        translateAdminValue(originalValue);

      if (translatedValue !== originalValue) {
        element.setAttribute(
          attribute,
          translatedValue,
        );
      }
    }
  }
};


const startSwitcher = () => {
  ensureAccountSwitcher();
  translateAdminText();

  for (const delay of [250, 1000, 2500]) {
    window.setTimeout(
      ensureAccountSwitcher,
      delay,
    );
  }

  const observer = new MutationObserver(() => {
    translateAdminText();
    if (
      !document.getElementById(SWITCHER_ID)
    ) {
      ensureAccountSwitcher();
    }
  });

  observer.observe(
    document.documentElement,
    {
      childList: true,
      subtree: true,
    },
  );

  window.addEventListener(
    "hashchange",
    ensureAccountSwitcher,
  );

  window.addEventListener(
    "popstate",
    ensureAccountSwitcher,
  );
};

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    startSwitcher,
    { once: true },
  );
} else {
  startSwitcher();
}
