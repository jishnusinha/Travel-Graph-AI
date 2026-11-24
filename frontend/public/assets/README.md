# Placeholder assets

All imagery here is **generated, original SVG gradient art** (no third-party photos), produced by
`frontend/scripts/generate-assets.mjs`:

```
node scripts/generate-assets.mjs
```

| Path | Used by | Notes |
|---|---|---|
| `destinations/{goa,manali,jaipur,udaipur,munnar,kerala,darjeeling,rishikesh,generic}.svg` | `TripCard`, trip detail hero, day/activity images | The backend stores cover paths as `/assets/destinations/<name>.jpg`. `CoverImage` maps `.jpg/.jpeg/.png/.webp` to `.svg`, and falls back to `generic.svg` if a file is missing. |
| `hero/beach.svg` | Dashboard hero, Plan-a-Trip hero | Soft pastel beach scene. |
| `auth/{mountains,beach,lake,santorini}.svg` | Login, signup, forgot/reset password, onboarding side panels | Mockup style: scenic gradient + headline overlay. |
| `studio/night.svg` | Reserved texture for dark workspace hero cards | Optional. |

## Replacing with real photography

Drop real images next to the SVGs using the same base name, e.g. `destinations/goa.jpg`, then change
`resolveAsset()` in `src/components/ui/CoverImage.tsx` to stop rewriting `.jpg` to `.svg` (or keep the
`onError` fallback). Make sure you hold the licence for any photo you add.
