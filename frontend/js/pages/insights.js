import { api } from "../api.js";
import { showEmpty } from "../components/empty.js";
import { showError } from "../components/error.js";
import { showLoader } from "../components/loader.js";
import { mountNavbar } from "../components/navbar.js";
import { h, renderChart } from "../utils.js";

mountNavbar("insights");
const status = document.getElementById("status");
const root = document.getElementById("insights");

function render(data) {
  const cheap = data.cheapest_store;
  const cheapCard = cheap
    ? h("article", { class: "card" }, [
      h("h2", { text: "Cheapest store for a family basket" }),
      h("p", { text: cheap.basket_name }),
      h("p", { class: "price", text: cheap.total_display }),
      h("p", { text: !cheap.store_name ? "No store can price this basket." : cheap.complete ? `${cheap.store_name} is the cheapest single store with every item in stock.` : `${cheap.store_name} has the lowest priced partial basket. Some items are out of stock there.` }),
      cheap.complete && cheap.most_expensive_display ? h("p", { text: `Most expensive complete store is ${cheap.most_expensive_store} at ${cheap.most_expensive_display}. You save ${cheap.savings_display}.` }) : null,
      cheap.missing.length ? h("p", { text: `Unavailable: ${cheap.missing.map((row) => row.name).join(", ")}` }) : null,
    ])
    : h("article", { class: "card" }, h("p", { text: "Load the sample data to compare a reference basket." }));
  const savings = data.savings_achieved;
  const canvas = h("canvas", { role: "img", "aria-label": "Largest price drops" });
  const dropTable = data.price_drops.length
    ? h("div", { class: "table-wrap" }, h("table", {}, [
      h("thead", {}, h("tr", {}, ["Product", "Store", "From", "To", "Drop"].map((label) => h("th", { scope: "col", text: label })))),
      h("tbody", {}, data.price_drops.map((row) => h("tr", {}, [
        h("td", {}, h("a", { href: `/product.html?id=${row.product_id}`, text: `${row.brand} ${row.name} ${row.pack_size}` })),
        h("td", { text: row.store_name }),
        h("td", { text: row.old_display }),
        h("td", { text: row.new_display }),
        h("td", { text: `${row.drop_display} (${row.drop_percent}%)` }),
      ]))),
    ]))
    : h("p", { text: "No price fell during this period." });
  root.replaceChildren(
    h("p", { text: `Figures use ${data.period_label}, the month of the latest price in the database. Catalogue: ${data.counts.products} products, ${data.counts.stores} stores, ${data.counts.prices} prices.` }),
    h("div", { class: "grid-2" }, [
      cheapCard,
      h("article", { class: "card" }, [
        h("h2", { text: "Savings achieved" }),
        h("p", { class: "price", text: savings.total_display }),
        h("p", { text: savings.note }),
        h("p", { text: `${savings.lines_compared} actual purchases were cheaper than the dearest store that day.` }),
      ]),
    ]),
    h("section", { class: "card", style: "margin-top:1rem" }, [
      h("h2", { text: `Biggest drops in ${data.period_label}` }),
      canvas,
      dropTable,
    ])
  );
  if (data.drop_chart.labels.length) {
    renderChart(canvas, {
      type: "bar",
      data: {
        labels: data.drop_chart.labels,
        datasets: [{ label: "Drop", data: data.drop_chart.values, displays: data.drop_chart.displays, backgroundColor: "#9a3e16" }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: {
          tooltip: { callbacks: { label: (context) => context.dataset.displays[context.dataIndex] } },
        },
      },
    });
  } else {
    showEmpty(canvas.parentElement, "No drops", "Drops show up when the latest price of the month is below the first.");
  }
}

async function load() {
  showLoader(status, "Calculating insights…");
  try {
    render(await api.insights());
    status.textContent = "";
  } catch (error) {
    showError(root, error.message || "Could not load insights.", load);
    status.textContent = "";
  }
}

load();
