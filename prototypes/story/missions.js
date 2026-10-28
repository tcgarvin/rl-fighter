// Mission catalogue for the story demo. Each mission fixes the setup (which capital
// ships each side gets for free, draft budgets, time limit) and the win condition the
// scripted sim checks. Team 0 is AZURE, team 1 is EMBER.

export const MISSIONS = {
  deathmatch: {
    id: "deathmatch",
    name: "TEAM DEATHMATCH",
    brief: "No flagships, no objectives. Last squadron flying wins.",
    budgets: [90, 90],
    fixed: [[], []],
    timeLimit: 110,
  },
  flagship: {
    id: "flagship",
    name: "FLAGSHIP DUEL",
    brief: "Carriers launch their air wings; damaged craft return to the bays for repair. Destroy the enemy flagship.",
    budgets: [80, 80],
    fixed: [["carrier"], ["carrier"]],
    // Each carrier embarks this wing on top of the draft. Strike craft (the wing plus
    // drafted fighters and bombers) launch from the bays; everything else jumps in.
    airWing: { fighter: 9, bomber: 4 },
    launchFromBays: true,
    timeLimit: 150,
  },
  beacon: {
    id: "beacon",
    name: "HOLD THE BEACON",
    brief: "Ships inside the ring charge it for their side. First to 100% wins.",
    budgets: [85, 85],
    fixed: [[], []],
    beacon: { x: 0, y: 0, radius: 75, rate: 2.2, perShip: 0.35 },
    timeLimit: 130,
  },
  station: {
    id: "station",
    name: "STATION ASSAULT",
    brief: "The attackers must destroy the defence station before time runs out.",
    // Index = team. The attacking side is chosen per match; see stationSetup().
    budgets: [110, 55],
    fixed: [[], ["station"]],
    attacker: 0,
    timeLimit: 140,
  },
};

export const MISSION_ORDER = ["deathmatch", "flagship", "beacon", "station"];

/** Station assault with either side attacking: swap budgets and the station. */
export function missionForMatch(id, attacker) {
  const base = MISSIONS[id];
  if (id !== "station" || attacker === 0) return base;
  return { ...base, budgets: [base.budgets[1], base.budgets[0]], fixed: [["station"], []], attacker: 1 };
}
