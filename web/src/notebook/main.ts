import { mountNav } from "../shell/nav";

// Stub (docs/M2_PLAN.md WP-S); the Notebook page is built in its own work package.
mountNav("notebook");
const main = document.createElement("main");
main.className = "page";
main.innerHTML = `<h1>Notebook</h1><p class="lede">Coming together on the m2-site branch.</p>`;
document.body.append(main);
