import { api } from "../api.js";
import { showEmpty } from "../components/empty.js";
import { showError } from "../components/error.js";
import { showLoader } from "../components/loader.js";
import { mountNavbar } from "../components/navbar.js";
import { debounce, h, queryValue } from "../utils.js";

mountNavbar("compare");
const status = document.getElementById("status");
const results = document.getElementById("results");
const form = document.getElementById("filters");
let page = 1;

document.getElementById("q").value = queryValue("q") || "";

function params() {
  const data = new FormData(form);
  const search = new URLSearchParams();
  search.set("q", data.get("q") || "");
  if (data.get("category")) search.set("category_id", data.get("category"));
  if (data.get("brand")) search.set("brand", data.get("brand"));
  search.set("sort", data.get("sort") || "price_asc");
  if (document.getElementById("stock").value === "1") search.set("in_stock", "1");
  search.set("page", String(page));
  search.set("per_page", "30");
  return search;
}

function render(data) {
  if (!data.products.length) {
    showEmpty(results, "No products", "Try another name, category, or brand.");
    status.textContent = "";
    return;
  }
  status.textContent = `${data.total} products`;
  const table = h("table", {}, [
    h("thead", {}, h("tr", {}, ["Product", "Category", "Pack", "Cheapest", "Per unit", "Store", "Stock"].map((label) => h("th", { scope: "col", text: label })))),
    h("tbody", {}, data.products.map((product) => {
      const cheap = product.cheapest;
      return h("tr", {}, [
        h("td", {}, h("a", { href: `/product.html?id=${product.id}`, text: `${product.brand} ${product.name}` })),
        h("td", { text: product.category_name }),
        h("td", { text: product.pack_size }),
        h("td", { text: cheap ? cheap.price_display : "—" }),
        h("td", { text: cheap ? cheap.per_unit_display : "—" }),
        h("td", { text: cheap ? cheap.store_name : "—" }),
        h("td", { text: cheap ? "In stock" : "Out of stock" }),
      ]);
    })),
  ]);
  const pager = h("div", { class: "pager" }, [
    h("button", { type: "button", class: "secondary", text: "Previous", disabled: data.page <= 1, onclick: () => { page -= 1; load(); } }),
    h("span", { text: `Page ${data.page} of ${data.pages}` }),
    h("button", { type: "button", class: "secondary", text: "Next", disabled: data.page >= data.pages, onclick: () => { page += 1; load(); } }),
  ]);
  results.replaceChildren(h("div", { class: "card table-wrap" }, table), pager);
}

async function load() {
  showLoader(results, "Searching products…");
  try {
    render(await api.products(params()));
  } catch (error) {
    status.textContent = "";
    showError(results, error.message || "Search failed.", load);
  }
}

async function fillFilters() {
  const [categories, brands] = await Promise.all([api.categories(), api.brands()]);
  const category = document.getElementById("category");
  categories.categories.forEach((row) => category.append(h("option", { value: row.id, text: row.name })));
  const brand = document.getElementById("brand");
  brands.brands.forEach((name) => brand.append(h("option", { value: name, text: name })));
}

form.addEventListener("submit", (event) => event.preventDefault());
form.addEventListener("input", debounce(() => { page = 1; load(); }, 300));
form.addEventListener("change", () => { page = 1; load(); });

fillFilters().then(load).catch((error) => showError(results, error.message || "Could not load filters.", () => location.reload()));
