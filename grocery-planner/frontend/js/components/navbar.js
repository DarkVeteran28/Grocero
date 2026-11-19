import { h } from "../utils.js";

const LINKS = [
  ["home", "Home", "/"],
  ["compare", "Compare", "/compare.html"],
  ["lists", "My Lists", "/lists.html"],
  ["budget", "Budget", "/budget.html"],
  ["insights", "Insights", "/insights.html"],
  ["admin", "Admin", "/admin.html"],
];

export function mountNavbar(active) {
  const header = document.getElementById("navbar");
  if (!header) return;
  const nav = h("nav", { id: "site-nav", "aria-label": "Primary" }, LINKS.map(([key, label, href]) => {
    const attrs = { href, text: label };
    if (key === active) attrs["aria-current"] = "page";
    return h("a", attrs);
  }));
  const toggle = h("button", { class: "nav-toggle", type: "button", "aria-expanded": "false", "aria-controls": "site-nav", text: "Menu" });
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });
  header.replaceChildren(
    h("a", { class: "skip-link", href: "#main", text: "Skip to content" }),
    h("div", { class: "header-inner" }, [
      h("a", { class: "brand", href: "/", text: "Smart Grocery" }),
      toggle,
      nav,
    ])
  );
  if (!document.getElementById("toasts")) {
    document.body.append(h("div", { id: "toasts", "aria-live": "polite" }));
  }
  const footer = document.getElementById("footer");
  if (footer && !footer.childElementCount) {
    footer.append(h("div", { class: "wrap" }, h("p", { text: "Sample prices for planning. Compare the totals the server calculates, including delivery." })));
  }
}
