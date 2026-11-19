import { api } from "../api.js";
import { showError } from "../components/error.js";
import { showLoader } from "../components/loader.js";
import { mountNavbar } from "../components/navbar.js";
import { toast } from "../components/toast.js";
import { errorText, h, moneyPatternOk } from "../utils.js";

mountNavbar("admin");
const status = document.getElementById("status");
const root = document.getElementById("admin-app");
const TYPES = ["supermarket", "local kirana", "online", "wholesale"];
let categories = [];
let stores = [];
let editingStore = null;
let editingProduct = null;

function section(title, ...nodes) {
  return h("section", { class: "card stack", style: "margin-top:1rem" }, [h("h2", { text: title }), ...nodes]);
}

async function reload() {
  const [categoryPayload, storePayload] = await Promise.all([api.categories(), api.stores()]);
  categories = categoryPayload.categories;
  stores = storePayload.stores;
  render();
}

function render() {
  root.replaceChildren(ioPanel(), storePanel(), productPanel(), pricePanel());
}

function ioPanel() {
  const file = h("input", { id: "csv-file", type: "file", accept: ".csv,text/csv" });
  const report = h("div", { id: "import-report" });
  return section("Import and export",
    h("p", { text: "Price CSV columns: product_id, store_id, price, date, in_stock. Valid rows are saved. Invalid rows are listed and skipped." }),
    h("div", { class: "inline" }, [
      file,
      h("button", { type: "button", text: "Import prices", onclick: () => importFile(file, report) }),
      ...["stores", "products", "prices", "categories"].map((name) => h("button", {
        type: "button",
        class: "secondary",
        text: `Export ${name}`,
        onclick: () => api.download(name).then(() => toast(`Downloaded ${name}.csv`)).catch(() => toast("Export failed", "error")),
      })),
    ]),
    report
  );
}

async function importFile(input, report) {
  const file = input.files && input.files[0];
  if (!file) {
    toast("Choose a CSV file", "error");
    return;
  }
  showLoader(report, "Importing…");
  try {
    const result = await api.importPrices(file);
    const lines = [`Imported ${result.imported}, updated ${result.updated}.`];
    report.replaceChildren(h("p", { text: lines[0] }));
    if (result.errors && result.errors.length) {
      report.append(h("table", {}, [
        h("thead", {}, h("tr", {}, [h("th", { text: "Row" }), h("th", { text: "Reason" })])),
        h("tbody", {}, result.errors.map((row) => h("tr", {}, [h("td", { text: String(row.row) }), h("td", { text: row.reason })]))),
      ]));
    }
    toast("Import finished");
  } catch (error) {
    const errors = error.payload && error.payload.details && error.payload.details.errors;
    report.replaceChildren(h("p", { text: errorText(error) }));
    if (errors) {
      report.append(h("table", {}, [
        h("thead", {}, h("tr", {}, [h("th", { text: "Row" }), h("th", { text: "Reason" })])),
        h("tbody", {}, errors.map((row) => h("tr", {}, [h("td", { text: String(row.row) }), h("td", { text: row.reason })]))),
      ]));
    }
    toast("Import failed", "error");
  }
}

function storePanel() {
  const form = h("form", { class: "grid-2" }, [
    field("store-name", "Name", editingStore ? editingStore.name : ""),
    selectField("store-type", "Type", TYPES, editingStore ? editingStore.type : TYPES[0]),
    field("store-area", "Area", editingStore ? editingStore.area : ""),
    field("store-distance", "Distance (km)", editingStore ? editingStore.distance_km : ""),
    field("store-delivery", "Delivery fee", editingStore ? editingStore.delivery_fee_input : "0.00"),
    field("store-free", "Free delivery above", editingStore && editingStore.free_delivery_above_input ? editingStore.free_delivery_above_input : ""),
    field("store-rating", "Rating", editingStore ? editingStore.rating : "4.0"),
  ]);
  return section("Stores",
    form,
    h("div", { class: "inline" }, [
      h("button", { type: "button", text: editingStore ? "Update store" : "Add store", onclick: saveStore }),
      editingStore ? h("button", { type: "button", class: "secondary", text: "Cancel edit", onclick: () => { editingStore = null; render(); } }) : null,
    ]),
    h("div", { class: "table-wrap" }, h("table", {}, [
      h("thead", {}, h("tr", {}, ["Name", "Type", "Area", "Distance", "Delivery", ""].map((label) => h("th", { text: label })))),
      h("tbody", {}, stores.map((store) => h("tr", {}, [
        h("td", { text: store.name }),
        h("td", { text: store.type }),
        h("td", { text: store.area }),
        h("td", { text: store.distance_display }),
        h("td", { text: store.delivery_fee_display }),
        h("td", {}, h("button", { type: "button", class: "secondary", text: "Edit", onclick: () => { editingStore = store; render(); } })),
      ]))),
    ]))
  );
}

function productPanel() {
  const form = h("form", { class: "grid-2" }, [
    field("product-name", "Name", editingProduct ? editingProduct.name : ""),
    field("product-brand", "Brand", editingProduct ? editingProduct.brand : ""),
    selectField("product-category", "Category", categories.map((row) => row.name), editingProduct ? editingProduct.category_name : (categories[0] && categories[0].name), categories.map((row) => String(row.id))),
    field("product-pack", "Pack size", editingProduct ? editingProduct.pack_size : ""),
    selectField("product-unit", "Unit", ["kg", "g", "L", "ml", "piece"], editingProduct ? editingProduct.unit : "kg"),
    field("product-base", "Base unit quantity", editingProduct ? editingProduct.base_unit_qty : "1"),
    field("new-category", "Or add a category", ""),
  ]);
  return section("Products",
    h("p", { class: "muted", text: "Base unit quantity is the pack in kg, litres, or pieces. 500 g is 0.5." }),
    form,
    h("div", { class: "inline" }, [
      h("button", { type: "button", text: "Add category", onclick: addCategory }),
      h("button", { type: "button", text: editingProduct ? "Update product" : "Add product", onclick: saveProduct }),
      editingProduct ? h("button", { type: "button", class: "secondary", text: "Cancel edit", onclick: () => { editingProduct = null; render(); } }) : null,
    ]),
    h("div", { class: "field" }, [h("label", { for: "product-filter", text: "Find a product to edit" }), h("input", { id: "product-filter", placeholder: "Search" })]),
    h("div", { id: "product-results" })
  );
}

function pricePanel() {
  return section("Prices",
    h("form", { class: "grid-2", id: "price-form" }, [
      field("price-product", "Product id", ""),
      field("price-store", "Store id", ""),
      field("price-amount", "Price", ""),
      field("price-date", "Date", ""),
    ]),
    h("label", { for: "price-stock", class: "inline", text: "" }, [
      h("input", { id: "price-stock", type: "checkbox", checked: "checked" }),
      document.createTextNode(" In stock"),
    ]),
    h("button", { type: "button", text: "Save price", onclick: savePrice }),
    h("div", { id: "recent-prices" })
  );
}

function field(id, label, value) {
  return h("div", { class: "field" }, [h("label", { for: id, text: label }), h("input", { id, value: value == null ? "" : String(value) })]);
}

function selectField(id, label, labels, selected, values = null) {
  const select = h("select", { id });
  labels.forEach((text, index) => {
    const option = h("option", { value: values ? values[index] : text, text });
    if (text === selected || (values && values[index] === selected)) option.selected = true;
    select.append(option);
  });
  return h("div", { class: "field" }, [h("label", { for: id, text: label }), select]);
}

async function addCategory() {
  const name = document.getElementById("new-category").value.trim();
  if (!name) return;
  try {
    await api.createCategory(name);
    toast("Category added");
    await reload();
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function saveStore() {
  const body = {
    name: value("store-name"),
    type: value("store-type"),
    area: value("store-area"),
    distance_km: value("store-distance"),
    delivery_fee: value("store-delivery") || "0",
    free_delivery_above: value("store-free"),
    rating: value("store-rating"),
  };
  if (body.free_delivery_above === "") delete body.free_delivery_above;
  if (!moneyPatternOk(body.delivery_fee) && body.delivery_fee !== "0") {
    toast("Check the delivery fee", "error");
    return;
  }
  try {
    await api.saveStore(editingStore && editingStore.id, body);
    editingStore = null;
    toast("Store saved");
    await reload();
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function saveProduct() {
  const body = {
    name: value("product-name"),
    brand: value("product-brand"),
    category_id: value("product-category"),
    pack_size: value("product-pack"),
    unit: value("product-unit"),
    base_unit_qty: value("product-base"),
  };
  try {
    const saved = await api.saveProduct(editingProduct && editingProduct.id, body);
    editingProduct = null;
    toast(`Saved ${saved.brand} ${saved.name}`);
    await reload();
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function savePrice() {
  const body = {
    product_id: value("price-product"),
    store_id: value("price-store"),
    price: value("price-amount"),
    date: value("price-date"),
    in_stock: document.getElementById("price-stock").checked,
  };
  if (!moneyPatternOk(body.price)) {
    toast("Enter a price with up to 2 decimal places", "error");
    return;
  }
  try {
    await api.savePrice(body);
    toast("Price saved");
    const rows = await api.prices(new URLSearchParams({ product_id: body.product_id, limit: "10" }));
    const box = document.getElementById("recent-prices");
    box.replaceChildren(h("table", {}, [
      h("thead", {}, h("tr", {}, ["Date", "Store", "Price", "Stock"].map((label) => h("th", { text: label })))),
      h("tbody", {}, rows.prices.map((row) => h("tr", {}, [
        h("td", { text: row.date }),
        h("td", { text: String(row.store_id) }),
        h("td", { text: row.price_display }),
        h("td", { text: row.in_stock ? "In stock" : "Out of stock" }),
      ]))),
    ]));
  } catch (error) {
    toast(errorText(error), "error");
  }
}

function value(id) {
  return document.getElementById(id).value.trim();
}

document.addEventListener("input", async (event) => {
  if (event.target.id !== "product-filter") return;
  const q = event.target.value.trim();
  const box = document.getElementById("product-results");
  if (q.length < 2) {
    box.replaceChildren();
    return;
  }
  const data = await api.products(new URLSearchParams({ q, per_page: "8" }));
  box.replaceChildren(...data.products.map((product) => h("div", { class: "inline" }, [
    h("span", { text: `${product.id}. ${product.brand} ${product.name} · ${product.pack_size}` }),
    h("button", { type: "button", class: "secondary", text: "Edit", onclick: () => { editingProduct = product; render(); } }),
    h("button", { type: "button", class: "danger", text: "Delete", onclick: () => deleteProduct(product) }),
  ])));
});

async function deleteProduct(product) {
  if (!confirm(`Delete ${product.name}?`)) return;
  try {
    await api.deleteProduct(product.id);
    toast("Product deleted");
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function init() {
  showLoader(status, "Loading data tools…");
  try {
    await reload();
    status.textContent = "";
    const date = (await api.config()).server_date;
    const input = document.getElementById("price-date");
    if (input) input.value = date;
  } catch (error) {
    showError(status, error.message || "Could not load admin data.", init);
  }
}

init();
