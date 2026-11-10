// A before/after figure for the notebook. The film (tools/web/film.mjs) is one video
// with the old picture on its left half and the new one on its right, the same frames
// of the same match, so the two can never drift apart. It is served from the storage
// bucket (another origin, which taints the canvas; nothing here reads it back). It is
// drawn into a canvas:
// before to the left of a divider and after to the right. Drag anywhere on the picture
// (or use the arrow keys on the divider) to move it.
//
// The film plays only while it is on screen. Where the viewer asks for reduced motion,
// or the browser refuses to start it unasked, it waits for the play button.

// The half-frame's shape by the film's --view (CSS px of the page that was filmed).
const VIEWS: Record<string, [number, number]> = { wide: [960, 600], phone: [390, 844] };
// How much of the figure must be on screen for the film to run.
const VISIBLE = 0.35;
const KEY_STEP = 0.04;

function make<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

/** The figure for the film at `src` (and its poster), filmed with `view` ("wide" or "phone"). */
export function compareFigure(src: string, poster: string, view: string, caption: string): HTMLElement {
  const shape = VIEWS[view];
  if (!shape) throw new Error(`compare: unknown view ${view}`);
  const figure = make("figure", `figure nb-compare nb-compare--${view}`);
  const stage = make("div", "nb-compare__stage");
  stage.style.aspectRatio = `${shape[0]} / ${shape[1]}`;
  // Until the film has a frame to draw, its poster (the first frame, split down the middle).
  stage.style.backgroundImage = `url("${poster}")`;
  const canvas = make("canvas", "nb-compare__picture");
  const video = make("video", "nb-compare__film");
  video.muted = true;
  video.loop = true;
  video.playsInline = true;
  video.preload = "metadata";
  video.src = src;
  const divider = make("div", "nb-compare__divider");
  divider.tabIndex = 0;
  divider.setAttribute("role", "slider");
  divider.setAttribute("aria-label", "Divider between the picture before and after");
  divider.setAttribute("aria-valuemin", "0");
  divider.setAttribute("aria-valuemax", "100");
  divider.append(make("span", "nb-compare__handle"));
  const before = make("span", "nb-compare__label nb-compare__label--before", "Before");
  const after = make("span", "nb-compare__label nb-compare__label--after", "After");
  const play = make("button", "nb-compare__play", "Play");
  play.type = "button";
  play.hidden = true;
  stage.append(canvas, video, before, after, divider, play);
  figure.append(stage);
  if (caption) figure.append(make("figcaption", "figure__caption", caption));

  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("compare: 2D canvas is not available");
  const still = window.matchMedia("(prefers-reduced-motion: reduce)");
  let split = 0.5;
  let onScreen = false;
  let wanted = !still.matches;

  /** Draw the film's current frame: before left of the divider, after right of it. */
  const draw = (): void => {
    const w = video.videoWidth / 2;
    const h = video.videoHeight;
    if (!w || !h) return;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    const x = Math.round(split * w);
    if (x > 0) ctx.drawImage(video, 0, 0, x, h, 0, 0, x, h);
    if (x < w) ctx.drawImage(video, w + x, 0, w - x, h, x, 0, w - x, h);
  };
  const place = (): void => {
    divider.style.left = `${split * 100}%`;
    divider.setAttribute("aria-valuenow", String(Math.round(split * 100)));
    // A label fades as its side closes up.
    before.style.opacity = String(Math.min(1, split * 6));
    after.style.opacity = String(Math.min(1, (1 - split) * 6));
    draw();
  };
  const loop = (): void => {
    draw();
    if (!video.paused) requestAnimationFrame(loop);
  };
  const sync = (): void => {
    if (onScreen && wanted) {
      video.play().then(
        () => {
          play.hidden = true;
        },
        () => {
          // The browser will not start a film unasked (low power mode, a data saver).
          wanted = false;
          play.hidden = false;
        },
      );
    } else {
      video.pause();
      play.hidden = wanted;
    }
  };

  video.addEventListener("loadeddata", draw);
  video.addEventListener("seeked", draw);
  video.addEventListener("play", () => requestAnimationFrame(loop));
  play.addEventListener("click", () => {
    wanted = true;
    sync();
  });
  new IntersectionObserver(
    (entries) => {
      onScreen = entries.some((e) => e.isIntersecting);
      sync();
    },
    { threshold: VISIBLE },
  ).observe(stage);

  const moveTo = (clientX: number): void => {
    const box = stage.getBoundingClientRect();
    split = Math.min(1, Math.max(0, (clientX - box.left) / Math.max(1, box.width)));
    place();
  };
  stage.addEventListener("pointerdown", (e) => {
    if (e.target === play) return;
    stage.setPointerCapture(e.pointerId);
    moveTo(e.clientX);
  });
  stage.addEventListener("pointermove", (e) => {
    if (stage.hasPointerCapture(e.pointerId)) moveTo(e.clientX);
  });
  divider.addEventListener("keydown", (e) => {
    const step = e.key === "ArrowLeft" ? -KEY_STEP : e.key === "ArrowRight" ? KEY_STEP : 0;
    if (!step) return;
    e.preventDefault();
    split = Math.min(1, Math.max(0, split + step));
    place();
  });
  place();
  return figure;
}
