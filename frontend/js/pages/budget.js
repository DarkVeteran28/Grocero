import { api } from "../api.js";
import { showEmpty } from "../components/empty.js";
import { showError } from "../components/error.js";
import { showLoader } from "../components/loader.js";
import { mountNavbar } from "../components/navbar.js";
import { toast } from "../components/toast.js";
import { errorText, h, moneyPatternOk, renderChart } from "../utils.js";

mountNavbar("budget");
const status = document.getElementById("status");
const root = document.getElementById("budget-app");
let categories = [];
let lists = [];
let month = "";
let summary = null;

function limitValue(categoryId) {
  if (!summary) return "";
  const row = summary.categories.find((item) => item.category_id === categoryId);
  return row && row.limit_input ? row.limit_input : "";
}

function render() {
  const total = summary && summary.total_input ? summary.total_input : "";
  const form = h("form", { id: "budget-form", class: "card stack" }, [
    h("h2", { text: "Budget settings" }),
    h("div", { class: "grid-2" }, [
      h("div", { class: "field" }, [h("label", { for: "month", text: "Month" }), h("input", { id: "month", type: "month", value: month, required: "true" })]),
      h("div", { class: "field" }, [h("label", { for: "total", text: "Total budget" }), h("input", { id: "total", inputmode: "decimal", required: "true", value: total, placeholder: "15000.00" })]),
    ]),
    h("h3", { text: "Category limits (optional)" }),
    h("div", { class: "grid-2" }, categories.map((category) => h("div", { class: "field" }, [
      h("label", { for: `cat-${category.id}`, text: category.name }),
      h("input", { id: `cat-${category.id}`, "data-category": category.id, inputmode: "decimal", value: limitValue(category.id), placeholder: "No limit" }),
    ]))),
    h("button", { type: "submit", text: "Save budget" }),
  ]);
  form.addEventListener("submit", save);
  const monthInput = form.querySelector("#month");
  monthInput.addEventListener("change", (event) => {
    loadMonth(event.target.value).catch((error) => toast(errorText(error), "error"));
  });
  root.replaceChildren(form);
  if (summary) root.append(dashboard(summary), fitPanel());
}

function dashboard(data) {
  const width = data.percent_used == null ? 0 : Math.min(data.percent_used, 100);
  const warnings = data.warnings.length
    ? data.warnings.map((row) => h("p", { class: `notice ${row.level}`, text: row.message }))
    : [h("p", { class: "notice ok", text: data.budget_set ? "Spending is within the warning thresholds." : "Set a budget to turn on warnings." })];
  const canvas = h("canvas", { id: "spend-chart", role: "img", "aria-label": "Spending by category" });
  const section = h("section", { class: "stack", style: "margin-top:1rem" }, [
    h("div", { class: "stats" }, [
      stat("Budget", data.total_display || "Not set"),
      stat("Actual", data.actual_display),
      stat("Planned", data.planned_display),
      stat("Remaining", data.remaining_display || "—"),
    ]),
    h("section", { class: "card" }, [
      h("h2", { text: data.month_label }),
      ...warnings,
      h("div", { class: `progress ${data.progress_tone}`, role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(data.percent_used ?? 0) }, [
        h("span", { style: `width:${width}%` }),
      ]),
      h("p", { text: data.percent_used == null ? "No budget set." : `${data.percent_used}% of the budget is committed.` }),
      h("p", { text: `At the current actual pace, month-end spend is ${data.projected_display}. ${data.projection_note}` }),
    ]),
    h("section", { class: "card" }, [h("h2", { text: "Category spending" }), canvas]),
    expensesTable(data),
  ]);
  queueMicrotask(() => {
    if (!canvas.isConnected) return;
    if (!data.chart.labels.length) {
      canvas.replaceWith(h("p", { text: "Category bars appear after you record a basket or set a limit." }));
      return;
    }
    renderChart(canvas, {
      type: "bar",
      data: {
        labels: data.chart.labels,
        datasets: [
          { label: "Committed", data: data.chart.values, displays: data.chart.displays, backgroundColor: "#1f6b3a" },
          { label: "Limit", data: data.chart.limits, displays: data.chart.limit_displays, backgroundColor: "#c4840b" },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          tooltip: {
            callbacks: {
              label(context) {
                const display = context.dataset.displays[context.dataIndex];
                return `${context.dataset.label}: ${display || "no limit"}`;
              },
            },
          },
        },
      },
    });
  });
  return section;
}

function stat(label, value) {
  return h("article", { class: "card" }, [h("p", { class: "muted", text: label }), h("p", { class: "price", text: value })]);
}

function expensesTable(data) {
  if (!data.expenses.length) return h("section", { class: "card" }, h("p", { text: "No expenses recorded for this month." }));
  return h("section", { class: "card table-wrap" }, [
    h("h2", { text: "Recorded lines" }),
    h("table", {}, [
      h("thead", {}, h("tr", {}, ["Date", "Item", "Store", "Amount", "Status", ""].map((label) => h("th", { scope: "col", text: label })))),
      h("tbody", {}, data.expenses.map((row) => h("tr", {}, [
        h("td", { text: row.date }),
        h("td", { text: row.product_name || "Delivery" }),
        h("td", { text: row.store_name || "" }),
        h("td", { text: row.amount_display }),
        h("td", { text: row.status }),
        h("td", {}, h("button", { type: "button", class: "secondary", text: "Delete", onclick: () => removeExpense(row.id) })),
      ]))),
    ]),
  ]);
}

function fitPanel() {
  const select = h("select", { id: "fit-list" }, [h("option", { value: "", text: "Choose a list" })].concat(lists.map((list) => h("option", { value: list.id, text: list.name }))));
  const output = h("div", { id: "fit-output" });
  return h("section", { class: "card stack", style: "margin-top:1rem" }, [
    h("h2", { text: "Fit a list to the remaining budget" }),
    h("div", { class: "inline" }, [
      select,
      h("button", { type: "button", text: "Suggest changes", onclick: () => runFit(select.value, output) }),
    ]),
    output,
  ]);
}

async function runFit(listId, output) {
  if (!listId) {
    toast("Choose a list", "error");
    return;
  }
  showLoader(output, "Looking for a cheaper basket…");
  try {
    const advice = await api.fit(listId, month, 3);
    const blocks = [h("p", { text: advice.message })];
    if (!advice.suggestions.length) {
      blocks.push(h("p", { text: advice.within_budget ? "No changes needed." : "No cheaper swap was found." }));
    }
    advice.suggestions.forEach((suggestion) => {
      blocks.push(h("article", { class: "notice" }, [
        h("strong", { text: suggestion.title }),
        h("p", { text: suggestion.detail }),
        h("p", { text: `New total ${suggestion.new_total_display}. Saves ${suggestion.saves_display}.` }),
        h("button", { type: "button", text: "Apply", onclick: () => applySuggestion(listId, suggestion.changes) }),
      ]));
    });
    output.replaceChildren(...blocks);
  } catch (error) {
    showError(output, errorText(error), () => runFit(listId, output));
  }
}

async function applySuggestion(listId, changes) {
  try {
    await api.applyFit(listId, changes);
    toast("List updated");
    lists = (await api.lists()).lists;
    render();
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function save(event) {
  event.preventDefault();
  const nextMonth = document.getElementById("month").value;
  const total = document.getElementById("total").value.trim();
  if (!moneyPatternOk(total)) {
    toast("Enter the budget with up to 2 decimal places", "error");
    return;
  }
  const categoryLimits = [];
  document.querySelectorAll("[data-category]").forEach((input) => {
    const value = input.value.trim();
    if (!value) return;
    if (!moneyPatternOk(value)) {
      categoryLimits.push(null);
      return;
    }
    categoryLimits.push({ category_id: Number(input.dataset.category), limit: value });
  });
  if (categoryLimits.includes(null)) {
    toast("Category limits need up to 2 decimal places", "error");
    return;
  }
  try {
    const exists = summary && summary.budget_set && summary.month === nextMonth;
    summary = await api.saveBudget(exists, { month: nextMonth, total, categories: categoryLimits });
    month = nextMonth;
    toast("Budget saved");
    render();
  } catch (error) {
    toast(errorText(error), "error");
  }
}

async function removeExpense(id) {
  await api.deleteExpense(month, id);
  summary = await api.summary(month);
  render();
}

async function loadMonth(next) {
  month = next;
  summary = await api.summary(month);
  render();
}

async function init() {
  showLoader(status, "Loading budget…");
  try {
    const [config, categoryPayload, listPayload] = await Promise.all([api.config(), api.categories(), api.lists()]);
    categories = categoryPayload.categories;
    lists = listPayload.lists;
    status.textContent = "";
    await loadMonth(config.default_month);
    if (!lists.length) {
      const note = document.getElementById("fit-output");
      if (note) showEmpty(note, "No lists", "Create a shopping list before using fit to budget.");
    }
  } catch (error) {
    showError(status, error.message || "Could not load the budget.", init);
  }
}

init();
