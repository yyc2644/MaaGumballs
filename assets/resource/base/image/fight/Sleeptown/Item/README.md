# Sleeptown Item Assets

This directory contains reusable image-recognition templates captured from two
passes through the Sleeptown backpack.

- `Item_PageNN_RowNN_ColNN.png` contains the 40 templates from the initial
  three-page pass.
- `Item_Floor48_PageNN_RowNN_ColNN.png` contains all 81 non-empty slots from
  the later six-page pass on floor 48.
- All 121 backpack source slots are retained. Visually identical icons are not merged,
  because different backpack positions may still represent different items.
- `Item_ShopDoubleSpiral.png` and `Item_ShopSingleSpiral.png` add two distinct
  goods found in the Cloud Shop screenshot audit.
- Backpack templates are 60x60; the two shop templates are 72x60. Every image
  is an unscaled crop of its original screenshot.
- The crop keeps the item body and stable inner-cell background.
- Stack counts, `NEW` corner labels, equipment stars, and the outer cell frame
  are intentionally excluded because they may differ between players or runs.
- `Item_Candidates_Index.png` contains the initial pass, while
  `Item_All_Candidates_Index.png` shows both passes together for review and
  later semantic renaming.

The images have not been generated, sharpened, recolored, or background-removed.
