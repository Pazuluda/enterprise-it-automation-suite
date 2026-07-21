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

const startSwitcher = () => {
  ensureAccountSwitcher();

  for (const delay of [250, 1000, 2500]) {
    window.setTimeout(
      ensureAccountSwitcher,
      delay,
    );
  }

  const observer = new MutationObserver(() => {
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
