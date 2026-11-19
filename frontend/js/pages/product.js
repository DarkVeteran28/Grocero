import { api } from "../api.js";
import { showError } from "../components/error.js";
import { showLoader } from "../components/loader.js";
import { mountNavbar } from "../components/navbar.js";
import { h, queryValue, renderChart } from "../utils.js";

mountNavbar("compare");
const status = document.getElementById("status");
const root = document.getElementById("product");
const id = Number(queryValue("id"));

function renderProduct(product, history, symbol) {
  const rows = product.offers.map((offer) => h("tr", { class: offer.is_cheapest ? "cheapest" : "" }, [
    h("td", { text: offer.store_name }),
    h("td", { text: offer.store_type }),
    h("td", { text: offer.area }),
    h("td", { text: offer.distance_display }),
    h("td", { text: offer.price_display }),
    h("td", { text: offer.per_unit_display }),
    h("td", {}, offer.in_stock ? h("span", { class: "badge ok", text: "In stock" }) : h("span", { class: "badge over", text: "Out of stock" })),
    h("td", { text: offer.is_cheapest ? "Cheapest" : "" }),
  ]));
  const canvas = h("canvas", { id: "history-chart", role: "img", "aria-label": "Price history by store" });
  root.replaceChildren(
    h("h1", { text: `${product.brand} ${product.name}` }),
    h("p", { text: `${product.category_name} · ${product.pack_size}` }),
    h("p", { text: product.summary }),
    h("div", { class: "card table-wrap" }, h("table", {}, [
      h("thead", {}, h("tr", {}, ["Store", "Type", "Area", "Distance", "Pack price", "Per unit", "Stock", ""].map((label) => h("th", { scope: "col", text: label })))),
      h("tbody", {}, rows),
    ])),
    h("section", { class: "card", style: "margin-top:1rem" }, [
      h("h2", { text: "Price history" }),
      canvas,
    ])
  );
  if (!history.dates.length) return;
  renderChart(canvas, {
    type: "line",
    data: {
      labels: history.dates,
      datasets: history.series.map((series, index) => ({
        label: series.store_name,
        data: series.values,
        displays: series.displays,
        borderColor: `hsl(${index * 47} 45% 32%)`,
        backgroundColor: "transparent",
        spanGaps: false,
        tension: 0.15,
      })),
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label(context) {
              const display = context.dataset.displays[context.dataIndex];
              return `${context.dataset.label}: ${display || "no price"}`;
            },
          },
        },
      },
      scales: {
        y: { title: { display: true, text: `Pack price (${symbol})` } },
      },
    },
  });
}

async function load() {
  if (!id) {
    showError(root, "Open a product from the compare page.", () => { window.location.href = "/compare.html"; });
    return;
  }
  showLoader(status, "Loading prices…");
  try {
    const [config, product, history] = await Promise.all([api.config(), api.product(id), api.productPrices(id)]);
    status.textContent = "";
    renderProduct(product, history, config.currency_symbol);
  } catch (error) {
    status.textContent = "";
    showError(root, error.message || "Could not load this product.", load);
  }
}

load();
