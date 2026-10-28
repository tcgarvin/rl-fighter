// Animated replay of a precomputed draft: a mission title card, then each pick as a
// short beat (the commander's top candidates with flickering preference bars, a lock-in,
// its stated reason, and the card slamming onto that side's roster).

import { DRAFT_HULLS } from "./draft.js";

const TEAM_NAMES = ["AZURE", "EMBER"];
const TEAM_CLASSES = ["team-a", "team-b"];
const FIXED_LABELS = { carrier: "FLAGSHIP", station: "STATION" };
const INTRO = 2.4;
const PICK_THINK = 0.8;
const PICK_LOCK = 0.3;
const PICK_SETTLE = 0.25;
const OUTRO = 1.2;
// Softmax temperature turning raw scores into the "preference" bars.
const BAR_TEMPERATURE = 0.25;

const wait = (seconds, token) =>
  new Promise((resolve, reject) => {
    const id = setTimeout(resolve, seconds * 1000);
    token.onCancel = () => {
      clearTimeout(id);
      reject(new DraftCancelled());
    };
  });

class DraftCancelled extends Error {}

function el(tag, className, html) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (html !== undefined) node.innerHTML = html;
  return node;
}

function softmax(scores) {
  const max = Math.max(...scores);
  const exps = scores.map((s) => Math.exp((s - max) / BAR_TEMPERATURE));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map((e) => e / sum);
}

export function createDraftView({ root, thumbnails }) {
  let token = null;

  function chip(hull, team, fixed) {
    const node = el("div", `chip ${fixed ? "fixed" : ""}`);
    const img = el("img");
    img.src = thumbnails[hull][team];
    img.alt = "";
    node.append(img, el("span", "chip-label", fixed ? FIXED_LABELS[hull] : DRAFT_HULLS[hull].label));
    return node;
  }

  function card(hull, team) {
    const node = el("div", `card ${TEAM_CLASSES[team]}`);
    const img = el("img");
    img.src = thumbnails[hull][team];
    img.alt = "";
    const info = DRAFT_HULLS[hull];
    node.append(
      img,
      el("div", "card-name", info.label),
      el("div", "card-cost", `${info.cost} CR`),
      el("div", "card-blurb", info.blurb),
      el("div", "card-bar", `<i></i>`),
    );
    return node;
  }

  function buildLayout({ number, mission, personas }) {
    root.innerHTML = "";
    const title = el(
      "div",
      "draft-title",
      `<div class="kicker">MISSION ${String(number).padStart(2, "0")}</div><div class="name">${mission.name}</div><div class="brief">${mission.brief}</div>`,
    );
    const sides = el("div", "sides");
    const sideEls = [0, 1].map((team) => {
      const side = el("div", `side ${TEAM_CLASSES[team]}`);
      side.append(
        el("div", "side-head", `${team === 0 ? "▲" : "■"} ${TEAM_NAMES[team]} <span class="persona">${personas[team].name}</span>`),
        el("div", "budget", `<div class="budget-bar"><i></i></div><span class="budget-num">${mission.budgets[team]} CR</span>`),
        el("div", "roster"),
      );
      sides.append(side);
      return side;
    });
    const stage = el("div", "stage");
    const who = el("div", "who");
    const cards = el("div", "cards");
    const reason = el("div", "reason");
    stage.append(who, cards, reason);
    root.append(title, sides, stage);
    return { title, sideEls, stage, who, cards, reason };
  }

  function setBudget(side, left, total) {
    side.querySelector(".budget-bar i").style.width = `${(100 * left) / total}%`;
    side.querySelector(".budget-num").textContent = `${left} CR`;
  }

  /** Flicker the bars around their final values, settling as `progress` reaches 1. */
  function animateBars(bars, finals, seconds, cancelToken) {
    const start = performance.now();
    return new Promise((resolve) => {
      function tick(now) {
        if (cancelToken.cancelled) return resolve();
        const p = Math.min(1, (now - start) / (seconds * 1000));
        const jitter = (1 - p) ** 1.5;
        bars.forEach((bar, i) => {
          const v = Math.max(0.02, Math.min(1, finals[i] + jitter * (Math.random() - 0.5) * 0.9));
          bar.style.width = `${v * 100}%`;
        });
        if (p < 1) requestAnimationFrame(tick);
        else resolve();
      }
      requestAnimationFrame(tick);
    });
  }

  async function run({ number, mission, personas, draft }, t) {
    const ui = buildLayout({ number, mission, personas });
    root.hidden = false;
    root.classList.remove("closing");
    root.classList.add("intro");
    ui.sideEls.forEach((side, team) => {
      setBudget(side, mission.budgets[team], mission.budgets[team]);
      for (const hull of mission.fixed[team]) side.querySelector(".roster").append(chip(hull, team, true));
    });
    await wait(INTRO, t);
    root.classList.remove("intro");
    for (const pick of draft.picks) {
      const team = pick.team;
      const side = ui.sideEls[team];
      ui.sideEls.forEach((s, i) => s.classList.toggle("active", i === team));
      ui.stage.className = `stage ${TEAM_CLASSES[team]}`;
      ui.who.innerHTML = `${TEAM_NAMES[team]} · ${personas[team].name} <span class="thinking">IS DECIDING</span>`;
      ui.reason.textContent = "";
      ui.reason.classList.remove("show");
      // Show the candidates in a shuffled order so the winner isn't always on the left.
      const order = pick.candidates.map((c, i) => [c, i]).sort(() => Math.random() - 0.5);
      const probs = softmax(pick.candidates.map((c) => c.score));
      ui.cards.innerHTML = "";
      const cardEls = order.map(([c]) => card(c.hull, team));
      cardEls.forEach((c) => ui.cards.append(c));
      const bars = cardEls.map((c) => c.querySelector(".card-bar i"));
      await Promise.all([animateBars(bars, order.map(([, i]) => probs[i]), PICK_THINK, t), wait(PICK_THINK, t)]);
      order.forEach(([c], i) => cardEls[i].classList.add(c.hull === pick.chosen ? "locked" : "rejected"));
      ui.who.innerHTML = `${TEAM_NAMES[team]} · ${personas[team].name} <span class="locked-in">LOCKS IN</span>`;
      ui.reason.textContent = pick.reason;
      ui.reason.classList.add("show");
      await wait(PICK_LOCK, t);
      const added = chip(pick.chosen, team, false);
      added.classList.add("slam");
      side.querySelector(".roster").append(added);
      setBudget(side, pick.budgetLeft, mission.budgets[team]);
      await wait(PICK_SETTLE, t);
    }
    ui.sideEls.forEach((s) => s.classList.remove("active"));
    ui.stage.className = "stage done";
    ui.who.textContent = "FLEETS LOCKED";
    ui.cards.innerHTML = "";
    ui.reason.textContent = "JUMP IN";
    ui.reason.classList.add("show");
    await wait(OUTRO, t);
    root.classList.add("closing");
    await wait(0.45, t);
    root.hidden = true;
  }

  return {
    /** Play the draft; resolves when the overlay has closed. Never resolves if cancelled. */
    play(args) {
      const t = { cancelled: false, onCancel: null };
      token = t;
      return new Promise((resolve, reject) => {
        run(args, t).then(resolve, (err) => {
          if (!(err instanceof DraftCancelled)) reject(err);
        });
      });
    },
    cancel() {
      if (!token) return;
      token.cancelled = true;
      token.onCancel?.();
      token = null;
      root.hidden = true;
    },
  };
}
