# Audio Quality Gate

## Use

Open **Settings → Output & quality**, enable **Final Audio Quality Gate**, and click **Save settings**
before returning to **Create Episode**. It is disabled by default for compatibility.
Unsaved drafts do not enable QC: the render
uses a detached snapshot of saved defaults, including thresholds and music seed.
The existing pre-mix inspector remains advisory; final QC analyzes the exact
exported MP3 after mastering and encoding.

- **Green / PASS:** “Ready to publish” — the measured checks passed, not a guarantee of production quality.
- **Yellow / WARN:** “Review recommended.”
- **Red / FAIL:** “Quality check failed — review before publishing.”
- **Disabled:** No final QC was requested for this render; this is not a PASS.
- **Unavailable:** The export is not certified; a missing, stale, or unreadable report is not a PASS.

Once audio is successfully exported, **Download episode** remains available in
all these states. QC does not block export or require an override to unlock it.
For WARN/FAIL, **Download anyway — acknowledge warning** records a deliberate
acknowledgement without erasing findings or converting the result to PASS. This
action records the decision; use **Download episode** to retrieve the audio.

For WARN/FAIL, **Apply suggested settings for next render** immediately saves
appropriate balance, ducking, or normalization defaults and refreshes the Settings
form, replacing its draft values. Unlike ordinary Settings edits, no additional
**Save settings** click is required. It never rewrites current audio or automatically
rerenders it; the current QC result remains unchanged.
Keep the original recordings available for rerendering. Clipping already baked
into a source cannot be repaired by normalization.

Results appear after a successful export. Open **Technical details** for the
final inspector and **Download quality report (JSON)** when a valid report is
available. Disabled/unavailable QC does not display a report download. A **Preview
worst section** player appears only when a preview exists; not every render has
one. Reports can include reason codes and a readable worst-section time range.
Cleaned voice and transcript downloads are also conditional on their files being
available. **Check for background transcript** can reveal a transcript that finishes
later. **Create another** resets episode inputs/results without deleting the export.
Preview files are cleaned on replacement/session reset and normal process exit;
abrupt process termination can leave temporary files for OS cleanup.

## Shared configuration

In **Settings → Advanced**, edit **Audio quality thresholds (JSON)** and set
**Music seed** as needed, then click **Save settings**. The thresholds editor is
directly in **Advanced**, not in a nested accordion. This group also contains
denoise method, enhancement preset, Whisper model, and minimum voice/music
separation. Auto-balance and auto-ducking are in **Voice processing** alongside
trim, denoise, and enhancement toggles. The gate toggle, normalization, target
LUFS, transcript toggle, and uploaded-recording deletion are in **Output & quality**.
**Discard changes** restores the saved form; it does not undo already applied
library, template, import, or suggested-settings actions.

Thresholds persist under `audio_quality` in `core/config.json` and in templates.
**Load and apply template** and **Import and apply settings** apply saved values
immediately and replace drafts; template saving and JSON export use saved settings.
`target_lufs` follows **Target LUFS Level**. An empty object uses defaults.
Invalid saved thresholds remain editable and cannot produce a certified PASS.

Startup audio discovery fills only missing `intro_file`, `outro_file`, or
`background_tracks` configuration keys. Saved file choices, explicit **None**
intro/outro selections (`null` in JSON), and an empty background pool (`[]`)
survive restart; discovery does not overwrite them.

| Check | Default |
|---|---|
| Integrated loudness | −16 LUFS; warn outside ±1 LU, fail outside ±2 LU |
| True peak | Warn above −1.5 dBTP; fail above −1.0 dBTP |
| Clipping | Any decoded channel sample at full scale fails |
| Internal silence | Warn above 5 seconds; fail above 10 seconds |
| Voice optimal range | −22 to −14 dBFS; target −18 dBFS |
| VMR | Excellent ≥18 dB; good ≥12; warning <12; failure <8; critical ≤0 |
| Speech analysis window | 500 ms |
| Ducking | 12 dB reduction; 100 ms attack / 450 ms release time constants |

Intentional edge silence is excluded, but an entirely silent file fails.
Unavailable measurements fail explicitly; missing metrics are `null`, not zero.

## Implementation and behavior changes

| Files | Previous behavior → new behavior |
|---|---|
| `features/lufs_normalizer.py` | Single-line parsing → multiline JSON, validated measurements and target offset, matching pass targets, explicit fallback/pass-mode logs |
| `features/audio_quality.py` | New structured report, final LUFS/true peak/clipping/silence checks, windowed VMR and previews |
| `features/audio_processor.py` | Average/coarse ducking → post-gain/post-duck stems, smooth envelope, deterministic local RNG, final QC callback and report |
| `features/config_manager.py`, `core/config.json` | Shared defaults and validated template persistence |
| `app.py` | Opt-in gate, final inspector, report/preview, deliberate override, safe settings suggestions; seven progress outputs preserved |

Mix analysis uses the actual separate voice/music stems, including selective
music regions and intro/outro overlaps. It uses energy-based activity detection,
not speech recognition. VMR is measured **before final mastering**; LUFS, true
peak, clipping, and silence are measured on the exact final file. Nonlinear
mastering can change perceived separation, so listening remains necessary.

The processor still returns `(output_file, denoised_file, transcript_file)`.
New optional trailing arguments are `quality_gate_enabled`, `quality_config`,
`music_seed`, and `quality_report_callback`. Use the callback rather than shared
`last_quality_report` for request-specific data.

One atomic `<output>.quality.json` contains metrics, reason codes, thresholds,
selected tracks, seed and rendering settings. UI receipt/acknowledgement lives
under `ui`; file identity prevents stale reports from certifying changed audio.
Music selection is reproducible with the same seed, ordered file pool, inputs,
and settings. This does not guarantee bit-identical encodings across FFmpeg versions.
Invalid/empty music tracks no longer cause an endless selection loop.

## Tests and remaining validation

New tests cover multiline/malformed/missing loudnorm JSON, offset and target
propagation, real FFmpeg normalization, short masking sections inside healthy
averages, missing voice/music, clipping rails and float overloads, silence,
exact-file analysis, selective regions/overlaps, ducking envelopes, deterministic
selection, graceful failures, configuration/templates, report freshness,
preview lifecycle, Gradio construction, and the seven-output contract.

Run the new suites together with `python -m pytest` on:

- `tests/test_lufs_normalizer.py`
- `tests/test_audio_quality.py`
- `tests/test_quality_pipeline.py`
- `tests/test_smooth_ducking.py`
- `tests/test_quality_config.py`
- `tests/test_quality_ui.py`
- `tests/test_episode_ui.py` (upload-first UI, saved settings, and result states)
- `tests/test_saved_settings.py` (saved configuration behavior)
- `tests/test_ntn_regression_manifest.py`
- `tests/test_ntn_quality_regression.py`

Run `tests/test_audio_balance.py` separately: legacy modules install global
dependency mocks during collection. The existing outro regression uses the
obsolete `enhance_audio` argument; this is a baseline issue, not a passing test.
The new pipeline tests cover outro preservation and overlap behavior.

### Required production evidence

The user identified the original recordings in these Windows folders:

- `c:\od\OneDrive\Podcast\26 09 07 NTN 567 Reflexiones Modelos pesos abiertos\`
- `c:\od\OneDrive\Podcast\26 09 10 NTN 568 OpenAI Navier-Stokes Millennium Prize Problem\`

These folders are **not mounted in this Linux container**. Existing concatenated,
denoised intermediates are not substituted for originals. Copy originals to
`audios/test/ntn567/` and `audios/test/ntn568/`, or mount the folders and configure
the regression manifest described in `tests/audio/README.md`. Production tests
render baseline/fixed cases from those original sources into temporary outputs.
Four cases skip explicitly until originals and reviewed rendering settings are supplied.

Historical final-file measurements are diagnostic only, **not original-recording
regression validation**:

| Existing render | LUFS | dBTP | Final-file result |
|---|---:|---:|---|
| NTN567 | −29.46 | −0.37 | FAIL: low loudness, unsafe true peak |
| NTN567-fix | −16.78 | −1.68 | PASS (no stem/VMR claim) |
| NTN568 | −33.89 | −3.64 | FAIL: low loudness |

No private recordings were copied into Git or uploaded to an external service.
No optional aggregate quality score was added: individual checks remain the
source of truth. Automatic repair is limited to next-render settings, not a
limiter/mastering suite. Basic QC is local and needs no credentials.
