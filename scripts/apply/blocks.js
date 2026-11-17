// Generic question-block finder for application systems without known selectors (Gem, Recruitee, Workable, ...).
// Marks each question's smallest wrapper with data-hj-block and returns them. A block is the highest ancestor of a
// control that holds no OTHER control, so it includes that question's label text; a radio/checkbox set counts as one
// control. Blocks inside the known Ashby/Lever/Greenhouse containers are left to those selectors.
(() => {
  const KNOWN = "[class*=application-form-field-entry], li.application-question, .select__container, .field-wrapper, .phone-input__phone";
  const CTRL = "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=image]), textarea, select";
  const isChoice = (el) => el.type === "radio" || el.type === "checkbox";
  if (document.querySelector(KNOWN)) return 0;       // a known system: its own selectors already cover the form
  document.querySelectorAll("[data-hj-block]").forEach((e) => e.removeAttribute("data-hj-block"));
  const ctrls = [...document.querySelectorAll(CTRL)].filter((c) => !c.closest(KNOWN) && !c.closest("[hidden]") &&
    !(c.type === "text" && c.closest("[class*=iti]") && c.placeholder === "Search") && c.getClientRects().length + (c.type === "file" ? 1 : 0) > 0);
  const blocks = new Set();
  for (const c of ctrls) {
    let node = c;
    while (node.parentElement && node.parentElement !== document.body && node.parentElement.tagName !== "FORM") {
      const p = node.parentElement;
      const other = [...p.querySelectorAll(CTRL)].some((x) => x !== c && !(isChoice(c) && isChoice(x)));
      if (other) break;
      node = p;
    }
    blocks.add(node);
  }
  // drop a block that wraps another block (keep the innermost)
  const list = [...blocks].filter((b) => ![...blocks].some((o) => o !== b && b.contains(o)));
  list.forEach((b) => b.setAttribute("data-hj-block", "1"));
  return list.length;
})()
