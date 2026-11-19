import { clear, h } from "../utils.js";

export function showError(node, message, onRetry) {
  clear(node);
  const box = h("div", { class: "error-box", role: "alert" }, [
    h("h2", { text: "Something went wrong" }),
    h("p", { text: message }),
  ]);
  if (onRetry) box.append(h("button", { type: "button", text: "Try again", onclick: onRetry }));
  node.append(box);
}
