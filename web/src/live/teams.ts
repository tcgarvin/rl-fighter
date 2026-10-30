// The two sides as the page names and colours them. Team 0 is AZURE (blue), team 1
// EMBER (orange). No DOM here, so the Node smoke test can import it.

export const TEAM_NAMES = ["AZURE", "EMBER"] as const;
/** In running text: "Azure's carrier destroyed". */
export const TEAM_WORDS = ["Azure", "Ember"] as const;
export const TEAM_CLASSES = ["team-a", "team-b"] as const;

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

/** `text` in team `team`'s colour (HTML). */
export function teamSpan(team: number, text: string): string {
  return `<span class="${TEAM_CLASSES[team] ?? ""}">${text}</span>`;
}
