import "./site.css";

export type PageId = "live" | "notebook" | "hulls";

const LINKS: ReadonlyArray<{ id: PageId; label: string; href: string }> = [
  { id: "live", label: "Live", href: "/" },
  { id: "notebook", label: "Notebook", href: "/notebook/" },
  { id: "hulls", label: "Hulls", href: "/hulls/" },
];

/**
 * Render the site nav at the top of the page.
 *
 * @param current The page being shown; its link is marked `aria-current`.
 * @param overlay Float the nav over a full-screen canvas (the live page).
 * @returns The nav element, already inserted as the body's first child.
 */
export function mountNav(current: PageId, overlay = false): HTMLElement {
  const nav = document.createElement("nav");
  nav.className = overlay ? "site-nav site-nav--overlay" : "site-nav";
  nav.setAttribute("aria-label", "Site");

  const brand = document.createElement("a");
  brand.className = "site-nav__brand";
  brand.href = "/";
  brand.textContent = "RL Fighter";
  nav.append(brand);

  const links = document.createElement("div");
  links.className = "site-nav__links";
  for (const link of LINKS) {
    const a = document.createElement("a");
    a.className = "site-nav__link";
    a.href = link.href;
    a.textContent = link.label;
    if (link.id === current) a.setAttribute("aria-current", "page");
    links.append(a);
  }
  nav.append(links);

  document.body.prepend(nav);
  return nav;
}
