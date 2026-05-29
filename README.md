# binpocalypse 🗃️
 
**AI-powered bin cataloging for the organizationally overwhelmed.**
 
## Origin
 
I'm "neuro-spicy". My garage is full of bins. Useful things in every one of them -- I just had no idea which bin held what, so I kept buying things I already owned.
 
Solutions exist. They cost money and require trusting some SaaS with my deeply important collection of spare ethernet cables and half-used caulk tubes. So I built this instead, because building something is more fun than subscribing to something, and because the problem was genuinely annoying me.
 
The result is BinTracker: a self-hosted bin inventory system with a Python REST API, SQLite backend, item checkout/check-in tracking, full-text search, and a bulk import workflow powered by Claude Vision that can catalog an entire garage's worth of bins from photos in one shot.
 
Photograph your bins. Claude identifies the contents. Import the JSON. Done.
 
---

## How it works

1. **Photograph your bins** — one photo per bin, named descriptively (`cables.jpg`, `ram_parts.jpg`, etc.)
2. **Send the photos to Claude** along with the prompt from `VISION_RULESET.md`
3. **Claude returns a JSON array** — one object per photo, with a bin label and itemized contents
4. **Paste the JSON** into the **Import JSON** button in BinTracker
5. Bins are created automatically with the next available bin numbers

---

## Output format

```json
[
  {
    "label": "Short descriptive bin name based on contents",
    "location": "",
    "items": [
      {"name": "Item Name", "qty": 1, "description": "optional detail"},
      {"name": "Another Item", "qty": 2, "description": ""}
    ]
  }
]
```

- `label` — auto-generated from what Claude sees in the photo
- `location` — left blank intentionally; fill it in after import
- `items` — every distinct item Claude can confidently identify, with quantity and any useful detail (color, size, condition, brand)

---

## Prompt rules

Claude follows these rules when identifying items:

- **Be specific** — "Klein Tools Hacksaw Frame" beats "saw". Brand names are included when visible.
- **Group identical items** into one entry with `qty > 1`
- **Skip obscured items** — if it can't be identified confidently, it's left out
- **No hallucinations** — description is left blank if there's nothing useful to add

---

## Tips for best results

- **Flat lay photos with good lighting** give significantly better results — spread items out and shoot from above
- **Batch the whole folder at once** — Claude produces one JSON array covering all bins in a single response
- **Clean up after import** — open each bin in BinTracker to adjust names and add locations
- **File naming helps** — descriptive filenames (`electrical_misc.jpg`) give Claude useful context

---

## Files

| File | Description |
|------|-------------|
| `VISION_RULESET.md` | The full prompt and workflow instructions to copy into Claude |

---

## Future ideas

- Wire Claude Vision directly into BinTracker (skip the copy/paste step entirely)
- Barcode scanning support for boxed/packaged items
- Confidence scores per identified item
- Batch re-scan to update existing bins

---

## Requirements

- A Claude account with vision support (claude.ai works great)
- BinTracker with JSON import enabled
- A camera and some bins full of stuff you've been meaning to sort through for two years

---

*Built to survive the binpocalypse.*
