// One small tiling noise texture, built on the CPU so every renderer (the live page, the
// hull cards' throwaway context) can use the same object. Channels, all 0..1 and
// periodic across the tile:
//   r  soft clouds (5 octaves of gradient noise, lowest period 4)
//   g  finer clouds (4 octaves, lowest period 8, its own lattice)
//   b  billows: rounded cellular lumps (smoke puffs, fireballs)
//   a  ridges: thin bright filaments (flame tongues, cracks)
import * as THREE from 'three';

const SIZE = 256;
let texture = null;

function lattice(seed) {
  // 64 x 64 gradient directions; smaller periods read a wrapped corner of it.
  let a = seed >>> 0;
  const next = () => { a += 0x6d2b79f5; let t = Math.imul(a ^ a >>> 15, a | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const g = new Float32Array(64 * 64 * 2);
  for (let i = 0; i < 64 * 64; i++) { const t = next() * Math.PI * 2; g[i * 2] = Math.cos(t); g[i * 2 + 1] = Math.sin(t); }
  return { g, next };
}

/** Gradient noise with `period` cells across the unit tile; about -0.7..0.7. */
function gradient(lat, x, y, period) {
  const fx = x * period, fy = y * period, ix = Math.floor(fx), iy = Math.floor(fy), u = fx - ix, v = fy - iy;
  const su = u * u * u * (u * (u * 6 - 15) + 10), sv = v * v * v * (v * (v * 6 - 15) + 10);
  const at = (cx, cy, dx, dy) => { const k = ((cy % period) * 64 + (cx % period)) * 2; return lat.g[k] * dx + lat.g[k + 1] * dy; };
  const a = at(ix, iy, u, v), b = at(ix + 1, iy, u - 1, v), c = at(ix, iy + 1, u, v - 1), d = at(ix + 1, iy + 1, u - 1, v - 1);
  return a + (b - a) * su + (c - a) * sv + (a - b - c + d) * su * sv;
}

function fbm(lat, x, y, period, octaves) {
  let sum = 0, amp = .5, norm = 0;
  for (let o = 0; o < octaves; o++) { sum += amp * gradient(lat, x, y, period << o); norm += amp; amp *= .5; }
  return sum / norm;
}

/** Distance to the nearest of one jittered point per cell, `period` cells across; 0..~1. */
function cellular(points, x, y, period) {
  const fx = x * period, fy = y * period, ix = Math.floor(fx), iy = Math.floor(fy);
  let best = 9;
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
    const cx = ix + dx, cy = iy + dy, k = ((((cy % period) + period) % period) * 16 + (((cx % period) + period) % period)) * 2;
    const px = cx + points[k] - fx, py = cy + points[k + 1] - fy;
    best = Math.min(best, px * px + py * py);
  }
  return Math.sqrt(best);
}

/** The shared texture (created on first use; never disposed, it lives with the page). */
export function noiseTexture() {
  if (texture) return texture;
  const a = lattice(0x51f15e), b = lattice(0x2c1b3c), c = lattice(0x7ed55d);
  const points = new Float32Array(16 * 16 * 2);
  for (let i = 0; i < points.length; i++) points[i] = c.next();
  const data = new Uint8Array(SIZE * SIZE * 4);
  const byte = (v) => Math.max(0, Math.min(255, Math.round(v * 255)));
  for (let j = 0; j < SIZE; j++) for (let i = 0; i < SIZE; i++) {
    const x = i / SIZE, y = j / SIZE, k = (j * SIZE + i) * 4;
    data[k] = byte(.5 + fbm(a, x, y, 4, 5) * 1.25);
    data[k + 1] = byte(.5 + fbm(b, x, y, 8, 4) * 1.25);
    // Two scales of rounded lumps, warped a little so the cells don't read as a grid.
    const wx = x + gradient(b, x, y, 8) * .035, wy = y + gradient(a, x, y, 8) * .035;
    const lumps = 1 - Math.min(1, cellular(points, wx, wy, 6) * 1.25);
    const small = 1 - Math.min(1, cellular(points, wx + .37, wy + .11, 14) * 1.3);
    data[k + 2] = byte(lumps * .72 + small * .28);
    let ridge = 0, amp = .55, norm = 0;
    for (let o = 0; o < 4; o++) { const n = 1 - Math.abs(gradient(c, x, y, 8 << o)) * 2.6; ridge += amp * n * n; norm += amp; amp *= .5; }
    data[k + 3] = byte(ridge / norm);
  }
  texture = new THREE.DataTexture(data, SIZE, SIZE, THREE.RGBAFormat, THREE.UnsignedByteType);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.colorSpace = THREE.NoColorSpace;
  texture.needsUpdate = true;
  return texture;
}
