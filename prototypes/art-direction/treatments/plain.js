// Baseline treatment: standard PBR materials, one key light, no post-processing.
// It exists to check the shared modules; real treatments live alongside it.
import * as THREE from "three";

const TEAM = [0x4fb3ff, 0xff8a3d];
const cache = new Map();

export default {
  id: "plain",
  name: "Plain",
  blurb: "Baseline lighting and materials, no post-processing.",
  hud: { "--bg": "#05060a", "--fg": "#e8ecf2", "--muted": "#7d8696", "--team-a": "#4fb3ff", "--team-b": "#ff8a3d", "--font": "ui-monospace, monospace" },
  fonts: [],
  palette: { team: TEAM, exhaust: 0xfff1b0, projectile: [0x9fd6ff, 0xffc08a], shield: [0x7fd0ff, 0xffb070] },

  init({ scene, renderer }) {
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    scene.add(new THREE.HemisphereLight(0xbfd4ff, 0x1a1410, 0.8));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(400, 900, 300);
    scene.add(key);
  },

  materials(team) {
    if (!cache.has(team)) {
      cache.set(team, {
        paint: new THREE.MeshStandardMaterial({ color: TEAM[team], roughness: 0.5, metalness: 0.2 }),
        trim: new THREE.MeshStandardMaterial({ color: 0xd8d8d0, roughness: 0.6 }),
        machinery: new THREE.MeshStandardMaterial({ color: 0x30363c, roughness: 0.7, metalness: 0.4 }),
        glow: new THREE.MeshBasicMaterial({ color: 0xffffff }),
        marking: new THREE.MeshStandardMaterial({ color: 0xf4f4f0, roughness: 0.5 }),
        exhaust: new THREE.MeshBasicMaterial({ color: 0xfff1b0, transparent: true, opacity: 0.85, depthWrite: false, blending: THREE.AdditiveBlending }),
      });
    }
    return cache.get(team);
  },

  render(renderer, scene, camera) {
    renderer.render(scene, camera);
  },

  onResize() {},
};
