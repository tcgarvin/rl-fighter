// Renders each hull, for both teams, to a small transparent image for the draft cards,
// using the real models and the treatment's materials. A throwaway renderer is used so
// the main canvas (and its post chain) is never resized; its environment map has to be
// built in that renderer's own context.
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const WIDTH = 220;
const HEIGHT = 150;
// Three-quarter view from front-left and above, so the silhouette and turrets both read.
const VIEW_PITCH = (42 * Math.PI) / 180;
const VIEW_YAW = (-35 * Math.PI) / 180;

/** `hulls` maps hull name to spec. Returns { [name]: [team0DataUrl, team1DataUrl] }. */
export function renderHullThumbnails({ THREE, hullgeo, treatment, hulls }) {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(2);
  renderer.setSize(WIDTH, HEIGHT, false);
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const env = pmrem.fromScene(room, 0.06);
  scene.environment = env.texture;
  scene.environmentIntensity = 0.3;
  const key = new THREE.DirectionalLight(0xffc58a, 4.2);
  key.position.set(-30, 40, 25);
  const rim = new THREE.DirectionalLight(0x69cde5, 2.6);
  rim.position.set(30, 15, -40);
  scene.add(key, rim, new THREE.HemisphereLight(0x659cae, 0x030813, 0.5));
  const camera = new THREE.PerspectiveCamera(28, WIDTH / HEIGHT, 0.1, 2000);

  const out = {};
  for (const [name, hull] of Object.entries(hulls)) {
    out[name] = [0, 1].map((team) => {
      const model = hullgeo.buildHull(hull, team, treatment.materials(team));
      scene.add(model.object);
      model.object.updateMatrixWorld(true);
      const size = Math.max(hull.length, hull.beam);
      const dist = size * 1.95;
      camera.position.set(Math.cos(VIEW_YAW) * Math.cos(VIEW_PITCH) * dist, Math.sin(VIEW_PITCH) * dist, -Math.sin(VIEW_YAW) * Math.cos(VIEW_PITCH) * dist);
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
      const url = renderer.domElement.toDataURL("image/png");
      model.dispose();
      return url;
    });
  }
  env.dispose();
  pmrem.dispose();
  room.dispose();
  renderer.dispose();
  renderer.forceContextLoss();
  return out;
}
