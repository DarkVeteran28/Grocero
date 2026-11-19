import { api } from "../api.js";
import { showEmpty } from "../components/empty.js";
import { showError } from "../components/error.js";
import { showLoader } from "../components/loader.js";
import { mountNavbar } from "../components/navbar.js";
import { h } from "../utils.js";

mountNavbar("home");
const form = document.getElementById("quick-search");
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const q = new FormData(form).get("q").toString().trim();
  if (!q) return;
  window.location.href = `/compare.html?q=${encodeURIComponent(q)}`;
});

const drops = document.getElementById("drops");

async function load() {
  showLoader(drops, "Loading recent price drops…");
  try {
    const data = await api.insights();
    const rows = data.price_drops || [];
    if (!rows.length) {
      showEmpty(drops, "No drops yet", "Price drops appear when a product is cheaper at the end of the latest month than at the start.");
      return;
    }
    const table = h("table", {}, [
      h("thead", {}, h("tr", {}, ["Product", "Store", "Was", "Now", "Drop"].map((label) => h("th", { text: label, scope: "col" })))),
      h("tbody", {}, rows.slice(0, 5).map((row) => h("tr", {}, [
        h("td", {}, h("a", { href: `/product.html?id=${row.product_id}`, text: `${row.brand} ${row.name}` })),
        h("td", { text: row.store_name }),
        h("td", { text: row.old_display }),
        h("td", { text: row.new_display }),
        h("td", { text: row.drop_display }),
      ]))),
    ]);
    drops.replaceChildren(h("div", { class: "card table-wrap" }, table));
  } catch (error) {
    showError(drops, error.message || "Could not load insights.", load);
  }
}

load();
