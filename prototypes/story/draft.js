// Scripted fleet draft. Two "commanders" alternate picks against a budget. Each pick
// deals a hand of cards; the commander scores the affordable ones by mission fit,
// counters to what the enemy already has, and a taste for variety. The whole draft is
// computed up front so the UI can replay it; nothing here is learned (yet).

export const DRAFT_HULLS = {
  fighter: { cost: 8, label: "FIGHTER", blurb: "Fast gun platform. Hunts bombers." },
  strafer: { cost: 11, label: "STRAFER", blurb: "Shielded side-slipper with a beam." },
  bomber: { cost: 14, label: "BOMBER", blurb: "Torpedo runs on capital ships." },
  gunship: { cost: 22, label: "GUNSHIP", blurb: "Flak anchor. Shreds small craft." },
};

// counters[a][b] > 0: a is good against b.
const COUNTERS = {
  fighter: { bomber: 1.0, strafer: 0.2 },
  strafer: { gunship: 0.5, fighter: 0.3 },
  bomber: { carrier: 1.2, station: 1.4, gunship: 0.8 },
  gunship: { fighter: 0.9, strafer: 0.5, bomber: 0.6 },
};

// How much each mission values a hull before counters.
const MISSION_FIT = {
  deathmatch: { fighter: 1.0, strafer: 0.9, bomber: 0.3, gunship: 0.8 },
  flagship: { fighter: 0.8, strafer: 0.7, bomber: 0.9, gunship: 0.6 },
  beacon: { fighter: 0.6, strafer: 0.9, bomber: 0.3, gunship: 1.1 },
  station: { fighter: 0.6, strafer: 0.7, bomber: 1.0, gunship: 0.7 },
};

export const PERSONAS = [
  { name: "VANGUARD", fit: 1.0, counter: 0.6, variety: 0.25, noise: 0.25, favourite: "fighter" },
  { name: "BASTION", fit: 1.0, counter: 0.7, variety: 0.35, noise: 0.2, favourite: "gunship" },
  { name: "GAMBIT", fit: 0.7, counter: 1.3, variety: 0.3, noise: 0.3, favourite: "bomber" },
  { name: "WARDEN", fit: 1.1, counter: 0.8, variety: 0.5, noise: 0.15, favourite: "strafer" },
];

const MAX_PICKS = 8;
const HAND_SIZE = 5;

function score(hull, mission, persona, own, enemy, rng) {
  const fit = MISSION_FIT[mission.id][hull] ?? 0.5;
  let counter = 0;
  let countered = 0;
  const victims = {};
  for (const e of enemy) {
    const c = COUNTERS[hull]?.[e] ?? 0;
    counter += c;
    if (c > 0) victims[e] = (victims[e] ?? 0) + 1;
    countered += COUNTERS[e]?.[hull] ?? 0;
  }
  const copies = own.filter((h) => h === hull).length;
  const parts = {
    fit: persona.fit * fit,
    counter: persona.counter * (counter - 0.6 * countered) * 0.35,
    variety: -persona.variety * copies * copies * 0.35,
    favourite: hull === persona.favourite ? 0.15 : 0,
    noise: persona.noise * (rng() - 0.5),
  };
  const total = Object.values(parts).reduce((a, b) => a + b, 0);
  return { hull, total, parts, victims, countered };
}

/** One short reason the commander "gives" for its pick, from the dominant score term. */
function reasonFor(choice, mission) {
  const { parts, victims } = choice;
  const victimList = Object.entries(victims).sort((a, b) => b[1] - a[1]);
  if (parts.counter > 0.15 && victimList.length) {
    const [hull, n] = victimList[0];
    return `COUNTERS ${n > 1 ? `${n}× ` : ""}${hull.toUpperCase()}`;
  }
  if (parts.counter < -0.15) return "RISKY — ENEMY HAS ANSWERS";
  if (parts.fit >= 0.95) {
    const why = { beacon: "HOLDS THE RING", station: "BREAKS FORTIFICATIONS", flagship: "PRESSURES THE FLAGSHIP", deathmatch: "WINS DOGFIGHTS" };
    return why[mission.id];
  }
  if (parts.favourite > 0) return "DOCTRINE PICK";
  return "FILLS THE LINE";
}

/** Deal a hand from all hulls (repeats allowed), guaranteeing one affordable card. */
function dealHand(affordable, rng) {
  const all = Object.keys(DRAFT_HULLS);
  const hand = Array.from({ length: HAND_SIZE }, () => all[Math.floor(rng() * all.length)]);
  if (!hand.some((h) => affordable.includes(h))) {
    hand[Math.floor(rng() * HAND_SIZE)] = affordable[Math.floor(rng() * affordable.length)];
  }
  return hand;
}

/**
 * Run the whole draft. Returns the ordered pick list (each with the hand dealt and the
 * index chosen from it) and the final rosters, fixed capital ships included.
 */
export function runDraft(mission, personas, rng) {
  const rosters = [[...mission.fixed[0]], [...mission.fixed[1]]];
  const budgets = [...mission.budgets];
  const picks = [];
  // Whoever has the bigger budget picks first; ties go to a coin flip.
  let team = budgets[0] === budgets[1] ? (rng() < 0.5 ? 0 : 1) : budgets[0] > budgets[1] ? 0 : 1;
  const done = [false, false];
  const pickCounts = [0, 0];
  while (!done[0] || !done[1]) {
    if (done[team]) {
      team = 1 - team;
      continue;
    }
    const affordable = Object.keys(DRAFT_HULLS).filter((h) => DRAFT_HULLS[h].cost <= budgets[team]);
    if (!affordable.length || pickCounts[team] >= MAX_PICKS) {
      done[team] = true;
      team = 1 - team;
      continue;
    }
    const hand = dealHand(affordable, rng);
    const scored = [...new Set(hand)]
      .filter((h) => affordable.includes(h))
      .map((h) => score(h, mission, personas[team], rosters[team], rosters[1 - team], rng))
      .sort((a, b) => b.total - a.total);
    const chosen = scored[0];
    budgets[team] -= DRAFT_HULLS[chosen.hull].cost;
    rosters[team].push(chosen.hull);
    pickCounts[team] += 1;
    picks.push({
      team,
      chosen: chosen.hull,
      reason: reasonFor(chosen, mission),
      hand,
      chosenIndex: hand.indexOf(chosen.hull),
      affordable: hand.map((h) => affordable.includes(h)),
      budgetLeft: budgets[team],
    });
    team = 1 - team;
  }
  return { picks, rosters };
}
