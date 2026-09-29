These are deliberately tiny, original media fixtures for the embed browser tests.

- `sample.pdf`: one valid PDF 1.4 page with Helvetica text, five indirect objects, and byte-accurate cross-reference offsets. It contains no JavaScript or external resources.
- `sample.webm`: a short, 160 × 90 silent VP8 canvas recording made with Chromium MediaRecorder and 25 explicitly captured frames. It alternates blue/red backgrounds with a moving white rectangle; no image assets or external media are used.

The video test checks metadata, decoded pixels, playback progress, and pause. The PDF test checks the iframe document response and complete downloadable PDF bytes; it does not claim visual inspection of Chromium's native PDF viewer.
