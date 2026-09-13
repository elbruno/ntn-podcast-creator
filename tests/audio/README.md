# Opt-in NTN regressions from ORIGINAL recordings

## Current evidence and required sources

The final regressions must render from the **original recordings**, in order,
from these Windows folders:

- NTN567: `c:\od\OneDrive\Podcast\26 09 07 NTN 567 Reflexiones Modelos pesos abiertos\`
- NTN568: `c:\od\OneDrive\Podcast\26 09 10 NTN 568 OpenAI Navier-Stokes Millennium Prize Problem\`

Read-only searching confirmed these folders are unavailable in this Linux
workspace. Only denoised concatenated intermediates and final episodes were
available. They are **not substitutes**: do not supply final MP3s (including
`outputs/ntn567.mp3`, `outputs/ntn567-fix.mp3`, `outputs/ntn568.mp3`), processed
stems, excerpts, or previously concatenated/denoised files as voice recordings.
No production fixtures, incident failure codes, or corrected results have been
invented. Production verification remains pending original sources and settings.

After checking privacy/licensing, mount the original folders read-only or copy
the original files, unchanged, into `audios/test/ntn567/` and
`audios/test/ntn568/`. Preserve filenames and explicitly establish recording order;
the tests never guess order from directory listings. Use absolute native paths
for those copy targets, e.g. `/workspaces/ntn-podcast-creator/audios/test/ntn567/`
plus the actual filename. Windows drive paths do not become Linux mounts simply
by appearing in JSON. Nothing is copied or downloaded by these tests. Keep private
audio and the local manifest out of commits; check local ignore rules yourself.

## Manifest contract (replaces the old stem/render manifest)

Opt in by providing `tests/audio/manifest.json`. It is a JSON object with **exactly
two keys**, `ntn567` and `ntn568`, each containing:

| Episode field | Required value |
| --- | --- |
| `approved_for_testing` | Boolean `true`, after privacy/licensing approval. |
| `originals_confirmed` | Boolean `true`: supplier attests these are full original recordings from the corresponding folder, not derivatives or final episodes. |
| `original_recordings` | Nonempty ordered array of distinct original file paths. |
| `baseline_settings` | Explicit `AudioProcessor.create_podcast` keyword settings described below. |
| `fixed_settings` | Explicit corrected keyword settings; must differ from baseline. |
| `expected_baseline_failure_codes` | Nonempty array of unique uppercase reason codes, explicitly supplied from verified incident expectations. No default or guessed masking code. Exact set equality is required; analysis-unavailable codes cannot stand in for an incident. |
| `expected_original_duration_seconds` | Optional positive finite total duration of the ordered original recordings, before trim/intro/outro; checked within 0.1 seconds. Does not crop or limit processing. |

All file paths (including intro, outro, music and track-volume keys) must identify
existing nonempty regular files. Relative paths are resolved against `tests/audio`
and must remain inside it after symlink resolution. `..` traversal, relative
Windows paths/backslashes on Linux, URLs and globs are not supported. Native
absolute mounted paths are allowed, including files outside the repository.
Original paths resolving into `outputs`, known episode-render names such as
`ntn567-fix`, or filenames containing derivative markers (`denois`, `noisereduce`,
`rnnoise`, `enhanced`, `concatenat`, `processed`, `render`, `final`) are rejected.
Filename checks cannot prove provenance: renaming an intermediate is not permitted
and does not turn it into an original. Original MP3 recordings are acceptable;
published episode MP3s are not.

### Required keys in BOTH settings objects

There are no implicit production settings. Each object must contain **all and only**
these supported pipeline keyword parameters:

| Keys | Contract |
| --- | --- |
| `intro_file`, `outro_file` | Input path or explicit `null` for no intro/outro. Same resolved inputs in both runs. |
| `background_files` | Ordered array of input music paths, or `[]`. Same resolved list/order in both runs. |
| `music_seed` | Integer, not boolean. Same seed in both runs; no global random-state changes. |
| `background_segments` | `null` = music across all voice; `[]` = no background sections; otherwise ordered `[start_ms, end_ms]` pairs, integer `0 <= start < end`. Coordinates refer to voice after optional edge trim, before intro offset. Pipeline clips ranges to voice duration and sums overlaps. May differ explicitly between baseline/fixed; it never crops the voice. |
| `background_volume` | Finite number in `[0, 100]`. |
| `track_volumes` | Object mapping music input paths to finite percentages in `[0, 100]`, or `{}`. Keys must resolve to distinct members of `background_files`. Unlisted tracks use `background_volume`. |
| `trim_silence`, `normalize_lufs` | Explicit booleans. Only edge silence is trimmed; full recordings are otherwise processed. |
| `intro_voice_overlap`, `voice_outro_overlap` | Explicit booleans controlling the pipeline's intro/voice and voice/outro overlap. |
| `auto_balance_levels`, `auto_ducking` | Explicit booleans; may differ between baseline/fixed. |
| `min_voice_music_separation_db` | Finite nonnegative number. |
| `target_lufs` | Finite number in `[-70, -5]`; same in both runs. |
| `quality_config` | Object of valid numeric `AudioQualityConfig` field overrides, or `{}` to use current code defaults. Unknown keys, strings, booleans, nulls and nonfinite values fail. Same object in both runs so thresholds cannot be relaxed to manufacture PASS. If it includes `target_lufs`, it must match the keyword above. |
| `denoise_audio`, `enhance_voice_enabled`, `generate_transcript` | All must be explicitly `false` in BOTH runs. |

The test owns `voice_file`, `output_file`, `quality_gate_enabled`,
`quality_report_callback` and `log_callback`: they are forbidden in the manifest.
Other kwargs, including `denoise_method`, `voice_enhancement_preset`,
`whisper_model`, `defer_transcription`, output paths and arbitrary callbacks, are
also rejected. Duplicate JSON keys and unknown episode fields fail validation.
Do not copy current UI/config settings blindly: supply the verified baseline and
intended correction explicitly. No guessed manifest is shipped with this suite.

## Execution and assertions

Run from the repository root with
`/usr/local/py-utils/venvs/pytest/bin/python -m pytest tests/test_ntn_quality_regression.py tests/test_ntn_regression_manifest.py -v -rs`.
The environment needs local FFmpeg/ffprobe, pytest, pydub, numpy and soundfile
(plus the Python-version-appropriate pydub audioop compatibility dependency).
No browser, Adobe credentials, Whisper, PyTorch models or network downloads are
used. Avoid combining with legacy tests that replace pipeline modules globally.

- There are four opt-in cases: `ntn567_bad`, `ntn567_fixed`, `ntn568_bad`,
	`ntn568_fixed`. **Absent manifest = four explicit skips**, not production PASS.
	Once configured, malformed/incomplete manifests, missing assets, unavailable
	decoding/analysis dependencies and incomplete QC **fail**, not skip. Both episode
	entries are validated before each render, even when selecting a single case.
- The actual `AudioProcessor` loads complete originals. For multiple files its
	existing `concatenate_audio_files` method produces an ordered MP3 in pytest's
	temporary directory. A single original is read directly. No synthetic tones,
	mock reports, pre-rendered finals or inferred/subtracted stems enter these runs.
- Both runs force `quality_gate_enabled=True`. Reports come from the pipeline's
	request-local callback: mix metrics use the actual post-gain/post-duck,
	pre-master stems (including speech-overlapping intro/outro); loudness, true
	peak, clipping and silence measure the exact exported MP3 after optional
	normalization. The test does not independently analyze a supplied final file.
- Baseline must be `FAIL` with exactly the supplied failure-code set. Fixed must
	be **`PASS`**, not `WARN`. Analysis must be complete/error-free with finite,
	non-null loudness, peak, clipping, silence, voice level, active-speech and
	percentage metrics. Speech windows must exist. Applicable VMR metrics and
	music-window values must be finite; music-free windows have infinite VMR,
	serialized as null. With selective music, median/p10 may legitimately be null
	when music covers less than 50%/10% of active-speech duration. Worst VMR must be
	finite whenever any active-speech window contains music.
- Outputs, concatenations and sidecars live under pytest's `tmp_path`, never
	beside inputs or in `outputs/`. Pytest manages temporary-output retention.
	The processor's identity-checked `_cleanup_quality_preview` helper retires only
	this run's owned QC previews in `finally`, even on assertion failure.
	Device, inode, size, mtime and ctime are compared for every voice/intro/outro/music
	source before/after each run, including failures. This avoids hashing huge files;
	it detects ordinary changes but is not cryptographic proof of unchanged bytes.

### Scope limitations

These regressions deliberately test **local mixing/mastering from originals**, not
historical AI/cloud preprocessing. Denoising, enhancement and transcription are
disabled, even for the baseline; if an incident depended on those stages, these
runs may not reproduce it. Do not replace originals with denoised intermediates,
invent failure codes, or weaken thresholds to make it pass. Resolve the scope and
verified settings with the source owner first. The existing multi-file concatenator
re-encodes to MP3 before rendering; this known extra lossy generation is shared
by baseline/fixed and is not an exact reconstruction of historical preprocessing.
Full-length runs can be memory/CPU intensive; no excerpt or duration shortcut is
silently applied. Separate manifest unit tests use temporary non-audio files solely
for validation and are never represented as production-quality evidence.
