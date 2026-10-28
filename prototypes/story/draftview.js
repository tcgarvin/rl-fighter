// Fast replay of a precomputed draft: a quick mission title, then each pick as a short
// beat (a hand of cards dealt in from that side, one lights up and flies onto the
// roster while the rest drop away). Beats speed up as the draft goes, so the whole
// thing reads as a riffle of decisions rather than a deliberation.

import { DRAFT_HULLS, draftLabel } from "./draft.js";

const TEAM_NAMES = ["AZURE", "EMBER"];
const TEAM_CLASSES = ["team-a", "team-b"];
const FIXED_LABELS = { carrier: "FLAGSHIP", station: "STATION" };
const INTRO = 0.9;
// Beat length for pick i: FIRST_BEAT * BEAT_DECAY^i, never below MIN_BEAT.
const FIRST_BEAT = 0.55;
const BEAT_DECAY = 0.8;
const MIN_BEAT = 0.2;
// Fraction of a beat spent with the hand on show before the choice lights up.
const LOCK_AT = 0.4;
const OUTRO = 0.7;
const CLOSE = 0.35;

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

export function createDraftView({ root, thumbnails }) {
  let token = null;

  function chip(hull, team, fixed, fixedLabel = FIXED_LABELS[hull]) {
    const node = el("div", `chip ${fixed ? "fixed" : ""}`);
    const img = el("img");
    img.src = thumbnails[hull][team];
    img.alt = "";
    node.append(img, el("span", "chip-label", fixed ? fixedLabel : draftLabel(hull)));
    return node;
  }

  function card(hull, team, affordable, index) {
    const node = el("div", `card ${affordable ? "" : "broke"}`);
    node.style.animationDelay = `${index * 0.02}s`;
    const img = el("img");
    img.src = thumbnails[hull][team];
    img.alt = "";
    const info = DRAFT_HULLS[hull];
    node.append(img, el("div", "card-name", draftLabel(hull)), el("div", "card-cost", `${info.cost} CR`));
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
    const reason = el("div", "reason");
    const cards = el("div", "cards");
    stage.append(who, reason, cards);
    root.append(title, sides, stage);
    return { sideEls, stage, who, reason, cards };
  }

  function setBudget(side, left, total) {
    side.querySelector(".budget-bar i").style.width = `${(100 * left) / total}%`;
    side.querySelector(".budget-num").textContent = `${left} CR`;
  }

  /** Fly a copy of the chosen card's image onto its (still hidden) roster chip. */
  function fly(cardEl, chipEl, team, seconds, onLand) {
    const from = cardEl.querySelector("img").getBoundingClientRect();
    const to = chipEl.querySelector("img").getBoundingClientRect();
    const ghost = el("img", `ghost ${TEAM_CLASSES[team]}`);
    ghost.src = cardEl.querySelector("img").src;
    Object.assign(ghost.style, { left: `${from.left}px`, top: `${from.top}px`, width: `${from.width}px`, height: `${from.height}px` });
    root.append(ghost);
    const scale = to.width / from.width;
    const flight = ghost.animate(
      [
        { transform: "translate(0, 0) scale(1)", opacity: 1 },
        { transform: `translate(${to.left - from.left}px, ${to.top - from.top}px) scale(${scale})`, opacity: 0.9 },
      ],
      { duration: seconds * 1000, easing: "cubic-bezier(0.55, 0, 0.25, 1)", fill: "forwards" },
    );
    flight.finished.then(
      () => {
        ghost.remove();
        onLand();
      },
      // Cancelled along with the draft; the overlay is being torn down anyway.
      () => ghost.remove(),
    );
  }

  async function run({ number, mission, personas, draft }, t) {
    const ui = buildLayout({ number, mission, personas });
    root.hidden = false;
    root.classList.remove("closing");
    root.classList.add("intro");
    ui.sideEls.forEach((side, team) => {
      setBudget(side, mission.budgets[team], mission.budgets[team]);
      for (const hull of mission.fixed[team]) {
        const wing = hull === "carrier" && mission.airWing ? Object.values(mission.airWing).reduce((a, b) => a + b, 0) : 0;
        side.querySelector(".roster").append(chip(hull, team, true, wing ? `${FIXED_LABELS[hull]} +${wing} WING` : FIXED_LABELS[hull]));
      }
    });
    await wait(INTRO, t);
    root.classList.remove("intro");
    for (const [i, pick] of draft.picks.entries()) {
      const beat = Math.max(MIN_BEAT, FIRST_BEAT * BEAT_DECAY ** i);
      const team = pick.team;
      const side = ui.sideEls[team];
      ui.sideEls.forEach((s, k) => s.classList.toggle("active", k === team));
      ui.stage.className = `stage ${TEAM_CLASSES[team]}`;
      ui.who.textContent = `${TEAM_NAMES[team]} · ${personas[team].name}`;
      ui.cards.className = `cards from-${team === 0 ? "left" : "right"}`;
      ui.cards.innerHTML = "";
      ui.reason.textContent = "";
      const cardEls = pick.hand.map((hull, k) => card(hull, team, pick.affordable[k], k));
      ui.cards.append(...cardEls);
      await wait(beat * LOCK_AT, t);
      cardEls.forEach((c, k) => c.classList.add(k === pick.chosenIndex ? "locked" : "rejected"));
      const chosenEl = cardEls[pick.chosenIndex];
      ui.reason.replaceChildren(el("span", "stamp", pick.reason));
      const added = chip(pick.chosen, team, false);
      added.classList.add("pending");
      side.querySelector(".roster").append(added);
      fly(chosenEl, added, team, Math.min(0.32, beat * 0.9), () => {
        added.classList.remove("pending");
        added.classList.add("slam");
        setBudget(side, pick.budgetLeft, mission.budgets[team]);
      });
      await wait(beat * (1 - LOCK_AT), t);
    }
    ui.sideEls.forEach((s) => s.classList.remove("active"));
    ui.cards.innerHTML = "";
    ui.reason.textContent = "";
    // Let the last flight land before the sign-off.
    await wait(0.3, t);
    ui.stage.className = "stage done";
    ui.who.innerHTML = `FLEETS LOCKED <span class="jump">JUMP IN</span>`;
    await wait(OUTRO, t);
    root.classList.add("closing");
    await wait(CLOSE, t);
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
      root.getAnimations({ subtree: true }).forEach((a) => a.cancel());
      root.hidden = true;
    },
  };
}
