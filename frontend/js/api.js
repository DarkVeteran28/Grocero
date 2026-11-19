async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const opts = { ...options, headers };
  if (opts.body && !(opts.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, opts);
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { error: "Unexpected response from the server." };
    }
  }
  if (!response.ok) {
    const error = new Error((data && data.error) || "Request failed");
    error.status = response.status;
    error.details = data && data.details;
    error.payload = data;
    throw error;
  }
  return data;
}

function jsonBody(value) {
  return JSON.stringify(value);
}

export const api = {
  config: () => request("/api/config"),
  categories: () => request("/api/categories"),
  createCategory: (name) => request("/api/categories", { method: "POST", body: jsonBody({ name }) }),
  brands: () => request("/api/brands"),
  products: (params) => request(`/api/products?${params.toString()}`),
  product: (id) => request(`/api/products/${id}`),
  productPrices: (id) => request(`/api/products/${id}/prices`),
  saveProduct: (id, body) => request(id ? `/api/products/${id}` : "/api/products", { method: id ? "PUT" : "POST", body: jsonBody(body) }),
  deleteProduct: (id) => request(`/api/products/${id}`, { method: "DELETE" }),
  stores: () => request("/api/stores"),
  saveStore: (id, body) => request(id ? `/api/stores/${id}` : "/api/stores", { method: id ? "PUT" : "POST", body: jsonBody(body) }),
  deleteStore: (id) => request(`/api/stores/${id}`, { method: "DELETE" }),
  prices: (params) => request(`/api/prices?${params.toString()}`),
  savePrice: (body) => request("/api/prices", { method: "POST", body: jsonBody(body) }),
  deletePrice: (id) => request(`/api/prices/${id}`, { method: "DELETE" }),
  importPrices: (file) => {
    const body = new FormData();
    body.append("file", file);
    return request("/api/prices/import", { method: "POST", body });
  },
  lists: () => request("/api/lists"),
  samples: () => request("/api/lists/samples"),
  createList: (body) => request("/api/lists", { method: "POST", body: jsonBody(body) }),
  updateList: (id, body) => request(`/api/lists/${id}`, { method: "PUT", body: jsonBody(body) }),
  deleteList: (id) => request(`/api/lists/${id}`, { method: "DELETE" }),
  loadSample: (name) => request("/api/lists/samples", { method: "POST", body: jsonBody({ name }) }),
  estimate: (id, maxStores) => request(`/api/lists/${id}/estimate`, { method: "POST", body: jsonBody({ max_stores: maxStores }) }),
  fit: (id, month, maxStores) => request(`/api/lists/${id}/fit`, { method: "POST", body: jsonBody({ month, max_stores: maxStores }) }),
  applyFit: (id, changes) => request(`/api/lists/${id}/apply`, { method: "POST", body: jsonBody({ changes }) }),
  budgets: () => request("/api/budgets"),
  saveBudget: (exists, body) => request(exists ? `/api/budgets/${body.month}` : "/api/budgets", { method: exists ? "PUT" : "POST", body: jsonBody(body) }),
  summary: (month) => request(`/api/budgets/${month}/summary`),
  recordExpense: (month, body) => request(`/api/budgets/${month}/expenses`, { method: "POST", body: jsonBody(body) }),
  deleteExpense: (month, id) => request(`/api/budgets/${month}/expenses/${id}`, { method: "DELETE" }),
  insights: () => request("/api/insights"),
  async download(dataset) {
    const response = await fetch(`/api/admin/export/${dataset}.csv`);
    if (!response.ok) {
      throw new Error("Export failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${dataset}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
