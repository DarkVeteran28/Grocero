import { clear, h } from "../utils.js";

export function showLoader(node, message = "Loading…") {
  clear(node);
  node.append(h("div", { class: "loading", role: "status", text: message }));
}
