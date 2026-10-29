import { mountNav } from "../shell/nav";

// Stub (docs/M2_PLAN.md WP-S); the Hulls page is built in its own work package.
mountNav("hulls");
const main = document.createElement("main");
main.className = "page";
main.innerHTML = `<h1>Hulls</h1><p class="lede">Coming together on the m2-site branch.</p>`;
document.body.append(main);
