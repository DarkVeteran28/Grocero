import { api } from "../api.js";
import { showEmpty } from "../components/empty.js";
import { showError } from "../components/error.js";
import { showLoader } from "../components/loader.js";
import { mountNavbar } from "../components/navbar.js";
import { toast } from "../components/toast.js";
import { debounce, errorText, h } from "../utils.js";

mountNavbar("lists");
const status = document.getElementById("status");
const workspace = document.getElementById("workspace");
const results = document.getElementById("results");

let lists = [];
let current = null;
let samples = [];
let month = "";
let maxStores = 2;
let searchText = "";
let searchHits = [];

function payload(list, items) {
  return {
    name: list.name,
    items: items.map((item) => ({ product_id: item.product_id, quantity: item.quantity })),
  };
}

async function refresh(selectId) {
  lists = (await api.lists()).lists;
  if (selectId) current = lists.find((row) => row.id === selectId) || null;
  else if (current) current = lists.find((row) => row.id === current.id) || lists[0] || null;
  else current = lists[0] || null;
  render();
}

function render() {
  const aside = h("section", { class: "card stack" }, [
    h("button", { type: "button", text: "New list", onclick: createList }),
    h("label", { for: "sample", text: "Sample list" }),
    h("select", { id: "sample" }, [h("option", { value: "", text: "Choose" })].concat(samples.map((sample) => h("option", { value: sample.name, text: `${sample.name} (${sample.item_count})` })))),
    h("button", { type: "button", class: "secondary", text: "Load sample", onclick: loadSample }),
    lists.length
      ? h("div", {}, lists.map((list) => h("button", {
        type: "button",
        class: "list-button",
        ...(current && current.id === list.id ? { "aria-current": "true" } : {}),
        text: `${list.name} (${list.item_count})`,
        onclick: () => { current = list; results.replaceChildren(); render(); },
      })))
      : h("p", { class: "muted", text: "No lists yet." }),
  ]);
  workspace.replaceChildren(h("div", { class: "layout-2" }, [aside, editor()]));
}

function editor() {
  if (!current) {
    return h("section", { class: "card" }, h("p", { text: "Create a list or load a sample to start." }));
  }
  const name = h("input", { id: "list-name", value: current.name, maxlength: "120" });
  const search = h("input", { id: "product-search", value: searchText, placeholder: "Search products to add" });
  search.addEventListener("input", debounce(async () => {
    searchText = search.value.trim();
    if (searchText.length < 2) {
      searchHits = [];
      render();
      return;
    }
    const data = await api.products(new URLSearchParams({ q: searchText, per_page: "8" }));
    searchHits = data.products;
    render();
  }, 300));
  const items = current.items.length
    ? h("div", { class: "table-wrap" }, h("table", {}, [
      h("thead", {}, h("tr", {}, ["Product", "Pack", "Quantity", ""].map((label) => h("th", { scope: "col", text: label })))),
      h("tbody", {}, current.items.map((item) => {
        const qty = h("input", { type: "number", min: "0.01", step: "0.01", value: item.quantity, "aria-label": `Quantity for ${item.product_name}` });
        qty.addEventListener("change", () => changeQty(item, qty.value));
        return h("tr", {}, [
          h("td", { text: `${item.brand} ${item.product_name}` }),
          h("td", { text: item.pack_size }),
          h("td", {}, qty),
          h("td", {}, h("button", { type: "button", class: "secondary", text: "Remove", onclick: () => removeItem(item) })),
        ]);
      })),
    ]))
    : h("p", { text: "This list has no products yet." });
  return h("section", { class: "card stack" }, [
    h("div", { class: "field" }, [h("label", { for: "list-name", text: "List name" }), name]),
    h("div", { class: "inline" }, [
      h("button", { type: "button", text: "Save name", onclick: () => rename(name.value) }),
      h("button", { type: "button", class: "danger", text: "Delete list", onclick: removeList }),
    ]),
    h("div", { class: "field" }, [h("label", { for: "product-search", text: "Add a product" }), search]),
    h("div", { class: "search-results" }, searchHits.map((product) => h("div", { class: "inline" }, [
      h("span", { text: `${product.brand} ${product.name} · ${product.pack_size}` }),
      h("button", { type: "button", class: "secondary", text: "Add", onclick: () => addProduct(product) }),
    ]))),
    items,
    h("div", { class: "inline" }, [
      h("label", { for: "max-stores", text: "Max stores in a split" }),
      h("select", { id: "max-stores" }, [1, 2, 3].map((value) => {
        const option = h("option", { value, text: String(value) });
        if (value === maxStores) option.selected = true;
        return option;
      })),
      h("label", { for: "record-month", text: "Record in" }),
      h("input", { id: "record-month", type: "month", value: month }),
      h("button", { type: "button", text: "Estimate", onclick: () => estimate() }),
    ]),
  ]);
}

async function createList() {
  const created = await api.createList({ name: "New list", items: [] });
  toast("List created");
  await refresh(created.id);
}

async function loadSample() {
  const name = document.getElementById("sample").value;
  if (!name) {
    toast("Choose a sample list", "error");
    return;
  }
  const created = await api.loadSample(name);
  toast(`Loaded ${created.name}`);
  await refresh(created.id);
}

async function rename(name) {
  try {
    const saved = await api.updateList(current.id, payload({ name: name.trim() }, current.items));
    toast("Name saved");
    await refresh(saved.id);
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function removeList() {
  if (!confirm(`Delete ${current.name}?`)) return;
  await api.deleteList(current.id);
  current = null;
  results.replaceChildren();
  toast("List deleted");
  await refresh();
}

async function addProduct(product) {
  if (current.items.some((item) => item.product_id === product.id)) {
    toast("That product is already on the list", "error");
    return;
  }
  const items = current.items.concat([{ product_id: product.id, quantity: "1.00" }]);
  try {
    const saved = await api.updateList(current.id, payload(current, items));
    searchHits = [];
    toast("Product added");
    await refresh(saved.id);
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function changeQty(item, quantity) {
  const items = current.items.map((row) => row.product_id === item.product_id ? { ...row, quantity } : row);
  try {
    const saved = await api.updateList(current.id, payload(current, items));
    await refresh(saved.id);
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function removeItem(item) {
  const items = current.items.filter((row) => row.product_id !== item.product_id);
  const saved = await api.updateList(current.id, payload(current, items));
  await refresh(saved.id);
}

function strategyCard(plan, strategy) {
  const recommended = plan.recommended_key === strategy.key;
  const record = async (state) => {
    const chosenMonth = document.getElementById("record-month").value;
    try {
      const saved = await api.recordExpense(chosenMonth, {
        list_id: current.id,
        strategy: strategy.key,
        max_stores: Number(document.getElementById("max-stores").value),
        status: state,
      });
      toast(`Recorded ${saved.total_display} as ${state}`);
    } catch (error) {
      toast(errorText(error), "error");
    }
  };
  return h("article", { class: recommended ? "card strategy recommended" : "card strategy" }, [
    h("h2", { text: strategy.title }),
    recommended ? h("span", { class: "badge warn", text: "Recommended" }) : null,
    h("p", { class: "price", text: strategy.total_display }),
    h("p", { text: `Items ${strategy.subtotal_display} · delivery ${strategy.delivery_display}` }),
    h("p", { text: strategy.complete ? "Every item is available." : "Incomplete — some items are unavailable." }),
    strategy.savings_display ? h("p", { text: `Saves ${strategy.savings_display} versus the most expensive complete store.` }) : null,
    h("ul", {}, strategy.stores_used.map((store) => h("li", { text: `${store.name}: ${store.subtotal_display} + ${store.delivery_display} delivery` }))),
    strategy.missing.length ? h("p", { text: `Unavailable: ${strategy.missing.map((row) => row.name).join(", ")}` }) : null,
    strategy.complete ? h("div", { class: "inline" }, [
      h("button", { type: "button", text: "Record as planned", onclick: () => record("planned") }),
      h("button", { type: "button", class: "secondary", text: "Record as actual", onclick: () => record("actual") }),
    ]) : null,
  ]);
}

async function estimate() {
  maxStores = Number(document.getElementById("max-stores").value);
  month = document.getElementById("record-month").value;
  showLoader(results, "Estimating stores…");
  try {
    const plan = await api.estimate(current.id, maxStores);
    const keys = ["cheapest_single", "cheapest_split", "nearest"];
    const matrix = h("table", {}, [
      h("thead", {}, h("tr", {}, ["Product", "Qty", "Single store", "Split", "Nearest"].map((label) => h("th", { scope: "col", text: label })))),
      h("tbody", {}, plan.items.map((item) => h("tr", {}, [
        h("td", { text: `${item.brand} ${item.name} · ${item.pack_size}` }),
        h("td", { text: item.quantity }),
        ...keys.map((key) => h("td", { text: item.choices[key].available ? `${item.choices[key].store_name} · ${item.choices[key].line_display}` : "Unavailable" })),
      ]))),
    ]);
    const stores = h("table", {}, [
      h("thead", {}, h("tr", {}, ["Store", "Basket", "Subtotal", "Delivery", "Total"].map((label) => h("th", { scope: "col", text: label })))),
      h("tbody", {}, plan.store_estimates.map((row) => h("tr", {}, [
        h("td", { text: row.stores_used[0] ? row.stores_used[0].name : "No purchase" }),
        h("td", { text: row.complete ? "Complete" : "Incomplete" }),
        h("td", { text: row.subtotal_display }),
        h("td", { text: row.delivery_display }),
        h("td", { text: row.total_display }),
      ]))),
    ]);
    const note = plan.most_expensive
      ? `Most expensive complete store: ${plan.most_expensive.stores_used[0].name} at ${plan.most_expensive.total_display}.`
      : "No single store has every item in stock, so savings versus the dearest complete basket are not shown.";
    results.replaceChildren(
      h("h2", { text: "Ways to buy this list" }),
      h("p", { text: note }),
      h("div", { class: "strategy-grid" }, keys.map((key) => strategyCard(plan, plan.strategies[key]))),
      h("section", { class: "card", style: "margin-top:1rem" }, [h("h2", { text: "Buy here" }), h("div", { class: "table-wrap" }, matrix)]),
      h("section", { class: "card", style: "margin-top:1rem" }, [h("h2", { text: "Every store" }), h("div", { class: "table-wrap" }, stores)]),
    );
  } catch (error) {
    showError(results, errorText(error), estimate);
  }
}

async function init() {
  showLoader(status, "Loading lists…");
  try {
    const config = await api.config();
    month = config.default_month;
    samples = (await api.samples()).samples;
    status.textContent = "";
    await refresh();
    if (!lists.length) showEmpty(results, "No basket yet", "Load Weekly essentials or add products to a new list.");
  } catch (error) {
    showError(status, error.message || "Could not load lists.", init);
  }
}

init();
