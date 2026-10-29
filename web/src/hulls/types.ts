// Shape of public/hulls/data/hulls.json, written by tools/build_catalogue.py.
// Body frame (SIM_SPEC §4.1): +x forward, +y port; bearings in degrees CCW from +x.

export type Vec2 = [number, number];

export interface Arc {
  from_deg: number;
  /** May be less than from_deg when the arc wraps through ±180°. */
  to_deg: number;
  mult: number;
  name: string;
}

export interface Thruster {
  id: string;
  pos: Vec2;
  /** Unit direction the force pushes the ship. */
  dir: Vec2;
  max_force: number;
}

export interface Turret {
  id: string;
  pos: Vec2;
  rest_deg: number;
  /** 0 = fixed gun. */
  arc_deg: number;
  slew_deg_s: number;
  weapon: string;
}

export interface Weapon {
  name: string;
  kind: string;
  kind_label: string;
  damage: number;
  range: number;
  speed: number;
  interval: number;
  rate: number;
  dps: number;
  spread_deg: number;
  burst_radius: number;
}

export interface Hull {
  name: string;
  role: string;
  role_label: string;
  control_scheme: string;
  flying: string[];
  hp: number;
  shield: { hp: number; regen_rate: number; regen_delay: number; radius: number } | null;
  mass: number;
  inertia: number;
  speed_cap: number;
  cost: number;
  static: boolean;
  bound_radius: number;
  thrust: { forward: number; reverse: number; lateral: number; turn: number };
  armour: Arc[];
  impact: Arc[];
  collision: Array<{ pos: Vec2; r: number }>;
  thrusters: Thruster[];
  turrets: Turret[];
  source: string;
}

export interface Catalogue {
  schema: string;
  hulls: Hull[];
  weapons: Record<string, Weapon>;
}
