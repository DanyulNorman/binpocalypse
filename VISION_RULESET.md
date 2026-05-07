# BinTracker — Vision Identification Ruleset

## Workflow

1. Put photos in a folder, one photo per bin (name them descriptively, e.g. `cables.jpg`, `ram_parts.jpg`)
2. Share the photos with Claude along with this ruleset
3. Claude returns a single JSON array covering all bins
4. Paste the JSON into the **Import JSON** button in BinTracker
5. Bins are created automatically with the next available numbers

---

## Prompt to use

> You are a home inventory assistant helping me catalog storage bins.
> I am going to show you one or more photos. Each photo represents one bin's contents.
>
> For each photo, identify every distinct item visible and produce one entry in the output array.
>
> Rules:
> - Be specific with names. "Klein Tools Hacksaw Frame" beats "saw". Include brand if visible.
> - Group identical items into one entry with qty > 1.
> - If an item is too obscured to identify confidently, skip it.
> - `location` should be left blank — I will fill it in after import.
> - `description` should include color, size, condition, or any distinguishing detail. Leave blank if nothing useful.
>
> Respond ONLY with a valid JSON array in this exact format — no explanation, no markdown fences, no preamble:
>
> [
>   {
>     "label": "Short descriptive bin name based on contents",
>     "location": "",
>     "items": [
>       {"name": "Item Name", "qty": 1, "description": "optional detail"},
>       {"name": "Another Item", "qty": 2, "description": ""}
>     ]
>   }
> ]
>
> One object per photo. If I send 3 photos, return an array with 3 objects.

---

## Tips

- **Flat lay photos** with good lighting give the best results (like the desk photo).
- You can send a whole folder at once — Claude will produce one JSON array covering all bins in one shot.
- After importing, open each bin in BinTracker to add locations and clean up any awkward names.
- Claude Vision can be wired directly into the app as a future upgrade once the manual flow is solid.

