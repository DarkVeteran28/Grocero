import { h } from "../utils.js";

export function toast(message, kind = "ok") {
  let root = document.getElementById("toasts");
  if (!root) {
    root = h("div", { id: "toasts", "aria-live": "polite" });
    document.body.append(root);
  }
  const item = h("div", { class: kind === "error" ? "toast error" : "toast", text: message, role: "status" });
  root.append(item);
  setTimeout(() => item.remove(), 4500);
}
