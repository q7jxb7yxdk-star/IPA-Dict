# IPA Phoneme Audio Attribution

Most phoneme audio files were downloaded from Wikimedia Commons and converted
from OGG to MP3 for use in IPA Dict. Some original consonant samples contain
multiple demonstration sounds; where those still sounded multi-syllabic in the
app, the app bundle now uses shorter single-phoneme MP3 files from IPAHelp.
Follow each source file license terms when redistributing the app or repository.

## Conversion

- Source format: OGG from Wikimedia Commons
- App format: MP3
- Tool: ffmpeg
- Changes: audio format conversion, local filename normalization, and for multi-segment samples, trimming to a single main phoneme segment. The full converted MP3 files and the trimming report are preserved under `Tools/AudioArchive/WikimediaCommonsSources/`.

### IPAHelp consonant replacements

The following bundled consonant files use the shorter IPAHelp versions archived
under `Tools/AudioArchive/IPAHelpPhonemes/`, because the Wikimedia-derived
versions sounded like multi-segment demonstrations when used as tappable
single-phoneme audio:

```text
ipa_eth.mp3
ipa_h.mp3
ipa_j.mp3
ipa_l.mp3
ipa_m.mp3
ipa_n.mp3
ipa_ng.mp3
ipa_s.mp3
ipa_sh.mp3
ipa_tap.mp3
ipa_theta.mp3
ipa_v.mp3
ipa_w.mp3
ipa_w_voiceless.mp3
ipa_x.mp3
ipa_z.mp3
ipa_zh.mp3
```

IPAHelp source: https://ipahelp.languagetechnology.org/

The previous Wikimedia-derived versions remain preserved in
`Tools/AudioArchive/WikimediaCommonsSources/` for comparison.

## Files

### ipa_a.mp3

- Source file: `Open front unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open_front_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/6/65/Open_front_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided.  Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_ae.mp3

- Source file: `Near-open front unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Near-open_front_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/c/c9/Near-open_front_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_alpha.mp3

- Source file: `Open back unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open_back_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/e/e5/Open_back_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_aw.mp3

- Source file: `Open-mid back rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open-mid_back_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/0/02/Open-mid_back_rounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_b.mp3

- Source file: `Voiced bilabial plosive.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_bilabial_plosive.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/2/2c/Voiced_bilabial_plosive.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_caret.mp3

- Source file: `Open-mid back unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open-mid_back_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/9/92/Open-mid_back_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_d.mp3

- Source file: `Voiced alveolar plosive.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_alveolar_plosive.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/0/01/Voiced_alveolar_plosive.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_e.mp3

- Source file: `Close-mid front unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Close-mid_front_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/6/6c/Close-mid_front_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_e_open.mp3

- Source file: `Open-mid front unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open-mid_front_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/7/71/Open-mid_front_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_er_open.mp3

- Source file: `Open-mid central unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open-mid_central_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/0/01/Open-mid_central_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_eth.mp3

- Source file: `Voiced dental fricative.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_dental_fricative.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/6/6a/Voiced_dental_fricative.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_f.mp3

- Source file: `Voiceless labiodental fricative.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_labiodental_fricative.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/3/33/Voiceless_labiodental_fricative.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_g.mp3

- Source file: `Voiced velar plosive.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_velar_plosive.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/b/b4/Voiced_velar_plosive.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_glottal_stop.mp3

- Source file: `Glottal stop.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Glottal_stop.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/4/4d/Glottal_stop.ogg
- Author / artist: No machine-readable author provided. Peter Isotalo assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_h.mp3

- Source file: `Voiceless glottal fricative.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_glottal_fricative.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/d/da/Voiceless_glottal_fricative.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_i.mp3

- Source file: `Close front unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Close_front_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/9/91/Close_front_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_i_bar.mp3

- Source file: `Close central unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Close_central_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/5/53/Close_central_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_i_short.mp3

- Source file: `Near-close near-front unrounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Near-close_near-front_unrounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/4/4c/Near-close_near-front_unrounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_j.mp3

- Source file: `Palatal approximant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Palatal_approximant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/e/e8/Palatal_approximant.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_k.mp3

- Source file: `Voiceless velar plosive.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_velar_plosive.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/e/e3/Voiceless_velar_plosive.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_l.mp3

- Source file: `Alveolar lateral approximant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Alveolar_lateral_approximant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/b/bc/Alveolar_lateral_approximant.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_m.mp3

- Source file: `Bilabial nasal.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Bilabial_nasal.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/a/a9/Bilabial_nasal.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_n.mp3

- Source file: `Alveolar nasal.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Alveolar_nasal.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/2/29/Alveolar_nasal.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_ng.mp3

- Source file: `Velar nasal.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Velar_nasal.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/3/39/Velar_nasal.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_o.mp3

- Source file: `Close-mid back rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Close-mid_back_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/8/84/Close-mid_back_rounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_o_open.mp3

- Source file: `Open back rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open_back_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/0/0a/Open_back_rounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_oe.mp3

- Source file: `Open-mid front rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Open-mid_front_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/0/00/Open-mid_front_rounded_vowel.ogg
- Author / artist: No machine-readable author provided. JøMa assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_p.mp3

- Source file: `Voiceless bilabial plosive.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_bilabial_plosive.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/5/51/Voiceless_bilabial_plosive.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_r.mp3

- Source file: `Alveolar approximant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Alveolar_approximant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/1/1f/Alveolar_approximant.ogg
- Author / artist: Erutuon
- Credit: Own work
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_s.mp3

- Source file: `Voiceless alveolar sibilant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_alveolar_sibilant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/a/ac/Voiceless_alveolar_sibilant.ogg
- Author / artist: Peter Isotalo
- Credit: Own work
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_schwa.mp3

- Source file: `Mid central vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Mid_central_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/d/d9/Mid-central_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_sh.mp3

- Source file: `Voiceless palato-alveolar sibilant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_palato-alveolar_sibilant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/c/cc/Voiceless_palato-alveolar_sibilant.ogg
- Author / artist: Peter Isotalo
- Credit: Own work
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_t.mp3

- Source file: `Voiceless alveolar plosive.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_alveolar_plosive.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/0/02/Voiceless_alveolar_plosive.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_tap.mp3

- Source file: `Alveolar tap.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Alveolar_tap.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/a/a0/Alveolar_tap.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_theta.mp3

- Source file: `Voiceless dental fricative.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_dental_fricative.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/8/80/Voiceless_dental_fricative.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_u.mp3

- Source file: `Close back rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Close_back_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/5/5d/Close_back_rounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_u_short.mp3

- Source file: `Near-close near-back rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Near-close_near-back_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/d/d5/Near-close_near-back_rounded_vowel.ogg
- Author / artist: No machine-readable author provided. Denelson83 assumed (based on copyright claims).
- Credit: No machine-readable source provided. Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_v.mp3

- Source file: `Voiced labiodental fricative.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_labiodental_fricative.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/8/85/Voiced_labiodental_fricative.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_w.mp3

- Source file: `Voiced labio-velar approximant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_labio-velar_approximant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/f/f2/Voiced_labio-velar_approximant.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_w_voiceless.mp3

- Source file: `Voiceless labio-velar fricative.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_labio-velar_fricative.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/a/a7/Voiceless_labio-velar_fricative.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_x.mp3

- Source file: `Voiceless velar fricative.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiceless_velar_fricative.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/0/0f/Voiceless_velar_fricative.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_z.mp3

- Source file: `Voiced alveolar sibilant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_alveolar_sibilant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/c/c0/Voiced_alveolar_sibilant.ogg
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_zh.mp3

- Source file: `Voiced palato-alveolar sibilant.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Voiced_palato-alveolar_sibilant.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/3/30/Voiced_palato-alveolar_sibilant.ogg
- Author / artist: Peter Isotalo
- Credit: Own work
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_o_bar.mp3

- Source file: `Close-mid central rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Close-mid_central_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/b/b5/Close-mid_central_rounded_vowel.ogg
- Author / artist: Denelson83
- Credit: Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.

### ipa_u_bar.mp3

- Source file: `Close central rounded vowel.ogg`
- File page: https://commons.wikimedia.org/wiki/File:Close_central_rounded_vowel.ogg
- Original audio URL: https://upload.wikimedia.org/wikipedia/commons/6/66/Close_central_rounded_vowel.ogg
- Author / artist: Denelson83
- Credit: Own work assumed (based on copyright claims).
- License: CC BY-SA 3.0
- License URL: http://creativecommons.org/licenses/by-sa/3.0/
- Usage terms: Creative Commons Attribution-Share Alike 3.0
- Local changes: Converted from OGG to MP3 using ffmpeg; filename normalized for app bundle use.
