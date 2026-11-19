import { clear, h } from "../utils.js";

export function showEmpty(node, title, message) {
  clear(node);
  node.append(h("div", { class: "empty" }, [
    h("h2", { text: title }),
    h("p", { text: message }),
  ]));
}
