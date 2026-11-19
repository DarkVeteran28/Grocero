export function h(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(props).forEach(([key, value]) => {
    if (value == null || value === false) return;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else node.setAttribute(key, String(value));
  });
  const list = Array.isArray(children) ? children : [children];
  list.forEach((child) => {
    if (child == null || child === false) return;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  });
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function debounce(fn, wait = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

export function queryValue(name) {
  return new URLSearchParams(window.location.search).get(name);
}

export function errorText(error) {
  const fields = error && error.details && error.details.fields;
  if (fields && typeof fields === "object" && !Array.isArray(fields)) {
    return Object.entries(fields)
      .map(([key, value]) => `${key}: ${typeof value === "string" ? value : "check this value"}`)
      .join(" ");
  }
  const missing = error && error.details && error.details.missing;
  if (Array.isArray(missing) && missing.length) {
    return `${error.message} Missing: ${missing.map((row) => row.name).join(", ")}.`;
  }
  return (error && error.message) || "Something went wrong.";
}

export function renderChart(canvas, config) {
  if (!canvas || !window.Chart) return;
  if (canvas._chart) canvas._chart.destroy();
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  config.options = config.options || {};
  config.options.animation = reduce ? false : { duration: 400 };
  canvas._chart = new window.Chart(canvas, config);
}

export function moneyPatternOk(value) {
  return /^\d+(\.\d{1,2})?$/.test(String(value).trim());
}
