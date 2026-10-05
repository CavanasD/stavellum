# Bundled score fonts

These are unmodified OpenType font files bundled with the application.
They are registered from package resources; installed system fonts are not used
for score titles or other rendered metadata.

Western score directions use the bundled Edwin Italic face; other Western text
uses Edwin Roman. Chinese text and punctuation use Source Han Serif SC Regular,
including within an italic playing instruction.

| File | Font version | SHA-256 | Upstream |
| --- | --- | --- | --- |
| Edwin-Roman.otf | 0.54 | edf9bddcdf7a62d0d799151d863556cf5e0958ad0a01e9f1d46afbaaa5a36e1c | https://github.com/MuseScoreFonts/Edwin |
| Edwin-Italic.otf | 0.54 | 07fb34383b545f162603513798d11fd27382a562d512535ac652a32ffbc8692f | https://github.com/MuseScoreFonts/Edwin |
| SourceHanSerifSC-Regular.otf | 2.003 | 78aa7a328fd974df2d688c8a9fd74a33d8334dfa84ab24d9d11efb2ffc464117 | https://github.com/adobe-fonts/source-han-serif |

Both fonts are distributed under the SIL Open Font License 1.1. The complete
copyright notices and license texts are included in Edwin-LICENSE.txt and
SourceHanSerif-LICENSE.txt. The original license files were obtained on
2026-10-04 from:

- https://raw.githubusercontent.com/MuseScoreFonts/Edwin/main/LICENSE.txt
- https://raw.githubusercontent.com/adobe-fonts/source-han-serif/release/LICENSE.txt

No fonts were subset, renamed, or otherwise modified.

## Leland music symbols

Score engraving uses Verovio's bundled **Leland**, with **Bravura** as its
missing-symbol fallback. The metronome's quarter-note mark uses the same
Verovio font resources (`data/Leland/ECA5.xml` and `data/Leland.xml`) through
the public `getResourcePath()` API. Its native outlines are rendered as SVG
paths, so no additional OTF registration or system font installation is needed.
The original glyph transform and matching bounds are retained.

The locked Verovio 6.3.0 dependency contains Leland **0.80**. Its upstream
metadata recommends Edwin for ordinary text. These resource hashes document
the version verified here; the files are distributed with the dependency,
rather than copied into this package:

| Verovio resource | SHA-256 | Source |
| --- | --- | --- |
| data/Leland.xml | 4ff2d18c33e69d6073d19da66071ced9a3f55198c996b9752b6d7a21825c37e9 | https://github.com/rism-digital/verovio/blob/version-6.3.0/data/Leland.xml |
| data/Leland/ECA5.xml | 491e955e7da48c09f8e29ad6219ef1b66a09485a880e56695c6ff9e41441f5bf | https://github.com/rism-digital/verovio/blob/version-6.3.0/data/Leland/ECA5.xml |

Leland is distributed under SIL Open Font License 1.1. The complete license
and font log are included here without modification. They were retrieved on
2026-10-04 from MuseScore commit
`6b65de368ae08cfbd8c780494d1275e62b4799af`:

| File | SHA-256 | Source |
| --- | --- | --- |
| Leland-LICENSE.txt | eb60b6a7d8c70b05c9fbd6f257e725ec2bc161cc82e78e299a34344ac9c4c1bb | https://github.com/musescore/MuseScore/blob/6b65de368ae08cfbd8c780494d1275e62b4799af/fonts/leland/LICENSE.txt |
| Leland-FONTLOG.txt | 0826532cd64af8386fd1808e619b238eab2066e6345823c66c9d490f2ee0d564 | https://github.com/musescore/MuseScore/blob/6b65de368ae08cfbd8c780494d1275e62b4799af/fonts/leland/FONTLOG.txt |
