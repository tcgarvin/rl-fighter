// Keeps the live page at the display's rate by trading resolution for time: the scene
// is drawn at `scale` times the canvas's full pixel ratio. The scale steps down when
// many frames run long, and tries a step back up after a quiet spell, waiting longer
// each time a step up doesn't hold.
//
// Dropped frames are the only signal used. The GPU's own time for a frame (timer
// queries) looks like a better one but isn't: an integrated GPU's governor slows its
// clock until a frame fills a steady share of the interval whatever the load, so a rule
// on that time walks the scale down for nothing (measured on Iris Xe: 8 to 11 ms at
// every scale from 1.0 to 0.8, with no frame dropped at any of them).

const MIN_SCALE = 0.5;
// Scales are kept to steps this size, so the render targets take few distinct sizes.
const SCALE_STEP = 0.05;
// A frame this many display intervals long was dropped; this share of dropped frames in
// a window of WINDOW frames steps the scale down by DOWN.
const DROPPED = 1.5;
const DROPPED_SHARE = 0.2;
const WINDOW = 90;
const DOWN = 0.85;
// A window with more than this share of dropped frames is not quiet.
const QUIET_SHARE = 0.02;
// The first try at stepping back up comes after this long without trouble, seconds; each
// failed try doubles the wait, up to RETRY_MAX.
const RETRY_FIRST = 20;
const RETRY_MAX = 300;
// A step up that has to be taken back within this long counts as failed, seconds.
const RETRY_TRIAL = 8;
// Gaps longer than this are a hidden tab or a stall, not a frame, seconds.
const STALL = 0.25;
// Start a huge canvas (a 4K monitor) below full scale: about this many pixels.
const START_PIXELS = 3.6e6;

export class RenderScale {
  /** The share of the full pixel ratio the scene is drawn at. */
  scale = 1;
  private readonly pinned: boolean;
  /** The display's frame interval, seconds, as far as the frames have shown it. */
  private interval = 1 / 60;
  private frames = 0;
  private dropped = 0;
  private quiet = 0;
  private retry = RETRY_FIRST;
  private sinceUp = Infinity;

  /**
   * `pixels` is the canvas's size at full scale. `pin` holds the scale at that value
   * (screenshots, comparisons); null lets it follow the frame rate.
   */
  constructor(pixels: number, pin: number | null) {
    this.pinned = pin !== null;
    this.scale = clampScale(pin ?? Math.sqrt(START_PIXELS / Math.max(1, pixels)));
  }

  /**
   * Take the last frame's real interval (seconds) and decide the scale. Returns true when
   * it changed, and the caller must resize what it draws into.
   */
  update(realDt: number): boolean {
    if (this.pinned || !(realDt > 0) || realDt > STALL) return false;
    // The shortest a frame has recently taken, eased upward slowly: a page that cannot
    // reach the display's rate at any scale stops counting every frame as dropped.
    this.interval = Math.max(1 / 240, Math.min(realDt, this.interval + (realDt - this.interval) * 0.002));
    this.sinceUp += realDt;
    this.quiet += realDt;
    this.frames += 1;
    // Sixty frames a second is the aim even on a faster display.
    if (realDt > Math.max(this.interval, 1 / 70) * DROPPED) this.dropped += 1;
    if (this.frames < WINDOW) return false;
    const share = this.dropped / this.frames;
    this.frames = this.dropped = 0;
    const before = this.scale;
    if (share > DROPPED_SHARE) {
      // A step up that didn't hold: wait twice as long before the next.
      if (this.sinceUp < RETRY_TRIAL) this.retry = Math.min(RETRY_MAX, this.retry * 2);
      this.quiet = 0;
      this.scale = clampScale(Math.floor((this.scale * DOWN) / SCALE_STEP + 1e-6) * SCALE_STEP);
    } else if (share > QUIET_SHARE) {
      this.quiet = 0;
    } else if (this.quiet > this.retry && this.scale < 1) {
      this.quiet = 0;
      this.sinceUp = 0;
      this.scale = clampScale(this.scale + 2 * SCALE_STEP);
    }
    return this.scale !== before;
  }
}

function clampScale(s: number): number {
  return Math.max(MIN_SCALE, Math.min(1, Math.round(s / SCALE_STEP) * SCALE_STEP));
}
