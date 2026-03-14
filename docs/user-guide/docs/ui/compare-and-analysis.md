# Compare & Analysis

The current compare workflow is centered on the experiments page and is much smoother than the older single-page compare patterns.

---

## Enter compare mode

You can enter compare mode by:

- selecting multiple runs from the experiments table
- opening a compare-related action from a run
- following a URL that already contains compare state

The current UI keeps compare state in the URL, so refresh and browser-back behavior are more predictable.

---

## What compare mode shows

- common metric detection across selected runs
- aliases and tags alongside run labels
- synchronized multi-run charts
- visibility toggles for individual runs

<figure markdown>
  ![Compare mode](../assets/main_page/comparison.png)
  <figcaption>Compare mode keeps multiple runs on one synchronized set of charts.</figcaption>
</figure>

---

## Hover and focus behavior

Runicorn 0.7.0 adds cross-chart hover highlighting. Hovering a run in the compare panel can highlight the same run across charts without forcing a full rerender.

---

## Why tags matter here

Tags now appear in the compare panel, which makes it easier to interpret mixed selections such as:

- baseline vs ablation
- different seeds
- resumed runs
- production candidates

---

## Good comparison habits

- compare runs from the same logical experiment family
- set a primary metric in code for clearer tables
- use aliases and tags so charts stay readable

---

## Next steps

- [Experiments & Paths](experiments-and-paths.md)
- [Logs, Assets & Images](logs-assets-and-images.md)
- [Settings & Themes](settings-and-themes.md)
