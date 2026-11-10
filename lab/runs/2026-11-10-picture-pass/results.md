# A second pass on the picture

Shipped to the live page on 2026-11-10. The game is unchanged (`SIM_VERSION` 7).

<!-- summary: The live page is drawn better and costs about the same. Planets are lit as spheres and stay sharp when the view zooms in, engines leave trails that show when a pilot was thrusting, smoke and fire look like smoke and fire, and big ships cast shadows. Five films put the old picture and the new one side by side on the same seconds of the same match. -->

Nothing here changes the game or the pilots. The same matches play out, tick for tick.
What changed is how they are drawn.

Each film below is one stretch of one match, drawn twice: by the old page on the left of
the divider and by the new page on the right. Drag the divider to compare.

<div data-figure="compare" data-src="dogfight.mp4" data-view="wide" data-caption="Eight seconds of a three against three. Same seed, same frames on both sides."></div>

## What changed

**Planets are lit, not painted.** The old page painted each planet once into a small
picture and stretched it. Zoom in on a ship and the planet behind it turned to blocks.
Now each planet's surface is painted once per match and lit as a sphere on every frame.
It has a day side and a night side, relief, air at the edge, clouds that drift and throw
shadows, city lights on the dark side, and rings that shade the planet and are shaded by
it. It stays sharp at any zoom. Each seed still gets the planets it had before.

<div data-figure="compare" data-src="planet.mp4" data-view="phone" data-caption="Following one fighter on a phone. The planet behind it fills the screen."></div>

**Engines leave trails.** Each fighter's main engines lay a thin line in the team's colour
that fades in about a second. The line is as bright as the throttle was when it was laid,
so a coasting ship leaves nothing. You can see where a pilot burned and where it let go.

**Smoke, fire and explosions.** Smoke used to be grey dots. It is now lit by the same
light as the ships and breaks up as it thins. A burning ship has flames. A ship that
blows up makes a fireball that goes from white to orange to red to soot, with a shock
ring that bends the picture behind it. The first flash and ring of a kill keep the shape
they had.

<div data-figure="compare" data-src="explosion.mp4" data-view="wide" data-caption="A four against four, close in. One ship is killed two seconds in and blows up."></div>

**Light and shadow.** Up close, turrets and decks now cast shadows. Hull plates have seams
and wear that fade out with distance. Explosions and jump flashes light the ships near
them. The light on the ships now comes from the same side as the sun on the biggest
planet.

<div data-figure="compare" data-src="carrier.mp4" data-view="wide" data-caption="Close on a carrier under fire."></div>

**Smaller things.** More stars, thicker along the band of the galaxy. Engine flames with a
hot core. Sparks that streak. Running lights on carriers and freighters. Smoke from a slow
ship is laid thinner so it doesn't hide the ship it comes from.

<div data-figure="compare" data-src="convoy.mp4" data-view="phone" data-caption="A convoy on a phone, with fighters and freighters burning."></div>

## What it costs

About the same as before. This is the time to draw one frame on the lab laptop (Intel
Iris Xe graphics) at the laptop's full 2256×1504 and at a phone's size. Both pages were
open together and took turns, which makes each slower than it is alone. Read the
difference, not the size.

| Scene | Old page, ms | New page, ms |
|---|---|---|
| Laptop, three against three | 18.7 | 19.2 |
| Laptop, four against four | 19.9 | 20.9 |
| Laptop, carrier battle | 20.5 | 21.7 |
| Laptop, convoy | 23.9 | 20.5 |
| Laptop, close on a fighter | 18.6 | 19.0 |
| Laptop, close on a carrier | 20.2 | 19.7 |
| Phone size, three against three | 9.1 | 9.2 |
| Phone size, close on a fighter | 9.2 | 9.9 |
| Phone size, carrier battle | 9.3 | 9.1 |

Alone, in a test browser on that laptop, the new page held 60 frames a second at full
laptop size in every scene we tried.
The two close-up rows were measured before the last round of trimming.

The page can now also give up sharpness to keep its frame rate. If many frames run long
it draws the scene smaller and scales it up, and it tries full size again after a quiet
spell. It never needed to in these runs.

**One thing we tried and dropped.** The first version of that rule watched how long the
graphics chip spent on each frame. That looked like the better signal and it was wrong.
A laptop chip slows its own clock when it has spare time, so a frame took 8 to 11 ms at
every size we gave it, and the rule kept shrinking the picture for nothing. The rule now
counts dropped frames and nothing else.

## After a first look on an iPhone

The first look on a phone found black bands across the big ships, flickering as they
moved. They were not new. The old page had them too and nobody had caught it.

On a phone held upright the camera sits about two and a half times as far from the fight
as it does on a laptop, to fit the arena across the narrow screen. From that far it could
only tell depths apart to about a metre, and a hull is built of plates stacked closer
than that. So the dark layer under the paint showed through in stripes. The camera now
measures depth only across the stretch where the ships are, which makes it about a
thousand times finer. The bands are gone in our phone-size test.

## What we don't know yet

- **The fix hasn't been seen on an iPhone yet.** It was checked in Chrome on the laptop
  at a phone's size, where the bands also showed before the fix.
- **The shrink-to-keep-up rule hasn't had to work.** No machine we ran it on dropped
  enough frames to set it off.

## How the films were made

`tools/web/film.mjs` loads the page with its clock replaced, so time only moves when the
tool says so. It steps the old page and the new page one frame at a time, takes a
picture of each, and joins the two into one video with the old on the left half and the
new on the right. Both get the same seed, and the game is deterministic, so every ship is
in the same place on both sides. The divider on this page shows the left half of the
video on one side and the right half on the other.
