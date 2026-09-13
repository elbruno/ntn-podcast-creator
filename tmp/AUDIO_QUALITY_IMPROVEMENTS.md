# NTN Podcast Creator — Audio Quality Improvements

## Goal

Improve the audio pipeline so that `ntn-podcast-creator` can detect and prevent episodes where:

- Voice is too quiet.
- Music masks the voice.
- Final loudness is outside the expected podcast range.
- True peaks or clipping are unsafe.
- A small problematic section is hidden by otherwise good average values.
- The LUFS two-pass normalization silently falls back to single-pass because loudnorm statistics are not parsed correctly.

The goal is not to make the audio pipeline "perfect". The goal is to make bad audio obvious before publication and provide actionable fixes.

---

# Priority 0 — Fix two-pass LUFS normalization

## Problem

The current `_get_loudness_stats()` implementation appears to expect FFmpeg `loudnorm` JSON output to exist on a single line.

FFmpeg normally emits the JSON block over multiple lines in stderr.

As a result, stats may not be parsed and the implementation can fall back to single-pass normalization.

## Required changes

Update the LUFS normalizer so that it:

1. Captures the complete JSON block emitted by FFmpeg `loudnorm`.
2. Parses the multiline JSON safely.
3. Extracts at least:
   - `input_i`
   - `input_tp`
   - `input_lra`
   - `input_thresh`
   - `target_offset`
4. Uses those values in the second pass.
5. Includes `offset=target_offset` in the second-pass `loudnorm` filter.
6. Fails gracefully if the stats cannot be parsed.
7. Logs whether true two-pass normalization was used.

## Suggested implementation

Search stderr for the last JSON object rather than checking line-by-line.

Example approach:

```python
def extract_loudnorm_json(stderr: str) -> dict | None:
    start = stderr.rfind("{")
    end = stderr.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    raw_json = stderr[start:end + 1]

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        return None
```

A more robust implementation is welcome if needed.

## Second pass

The second pass should use the measured values from pass one.

Conceptually:

```text
loudnorm=
I=-16:
TP=-1.5:
LRA=11:
measured_I=<input_i>:
measured_TP=<input_tp>:
measured_LRA=<input_lra>:
measured_thresh=<input_thresh>:
offset=<target_offset>:
linear=true
```

Do not hardcode these values if the application already exposes them through settings.

## Acceptance criteria

- A normal podcast WAV is processed using true two-pass loudness normalization.
- Logs clearly state that two-pass normalization was used.
- If stats cannot be parsed, the fallback is explicit and visible.
- Unit tests cover multiline FFmpeg loudnorm output.
- Tests cover malformed or missing loudnorm JSON.

---

# Priority 0 — Add Final Audio Quality Gate

## Goal

Do not assume that because the individual tracks looked good, the rendered file is good.

Analyze the final rendered audio file before considering the episode ready.

The Quality Gate should run after:

1. Voice processing.
2. Music mixing.
3. Final rendering.
4. LUFS normalization.

It must analyze the exact file that would be published.

---

## Final QC checks

At minimum calculate:

### Loudness

- Integrated LUFS.
- Target default: `-16 LUFS`.
- Warning tolerance: approximately ±1 LU.
- Failure tolerance: approximately ±2 LU.

These should be configurable.

### True Peak

- Target maximum: `-1.5 dBTP`.
- Warning above `-1.5 dBTP`.
- Fail above `-1.0 dBTP`.

Keep thresholds configurable.

### Clipping

Detect samples at or above digital full scale.

Return:

```text
clipped_samples
clipped_percentage
```

### Silence anomalies

Detect unusually long silent sections.

Example defaults:

```text
Warning: silence > 5 seconds
Failure: silence > 10 seconds
```

Ignore intentional silence at the beginning or end if that behavior already exists in the app.

---

# Priority 1 — Windowed Voice / Music Ratio

## Problem

Average voice-vs-music levels can hide short sections where music masks speech.

For example:

```text
25 minutes: good balance
30 seconds: music too loud
```

The average can still look healthy.

## Required behavior

Measure voice/music separation over short windows while speech is active.

Recommended window:

```text
500 ms to 1000 ms
```

Do not analyze silent voice sections as voice-vs-music failures.

Use existing voice activity information if already available.

Otherwise introduce a lightweight speech detector.

---

## Metrics to calculate

For each speech-active window:

```text
voice_level_dbfs
music_level_dbfs
voice_music_ratio_db
timestamp_start
timestamp_end
```

Aggregate:

```text
median_vmr
p10_vmr
worst_vmr
percentage_below_warning
percentage_below_failure
```

Suggested initial thresholds:

```text
>= 18 dB    Excellent
12-18 dB    Good
8-12 dB     Warning
< 8 dB      Failure
<= 0 dB     Critical
```

Make them configurable.

---

# Priority 1 — Detect worst section

The analysis should identify the worst section of the episode.

Return something similar to:

```json
{
  "start_seconds": 872.5,
  "end_seconds": 887.5,
  "voice_music_ratio_db": 7.2
}
```

The UI should display:

```text
Possible music masking detected
14:32 - 14:47

[ Preview worst section ]
```

If easy to implement, automatically extract a temporary preview audio clip containing approximately 10–20 seconds around the problematic section.

---

# Priority 1 — Improve ducking

## Current concern

Block-based attenuation can create abrupt volume changes or audible pumping.

## Desired behavior

Replace or improve coarse ducking with smooth gain transitions.

Suggested defaults:

```text
Attack: 50–150 ms
Release: 300–600 ms
Reduction: 8–16 dB
```

Keep values configurable.

Possible approaches:

1. Smooth envelope over the existing ducking system.
2. FFmpeg sidechain compression.
3. Another DSP method already compatible with the project.

Prefer the simplest implementation that sounds natural.

---

# Priority 1 — Regression tests using real NTN failures

Add regression coverage based on the real production incident.

Create test fixtures from short excerpts if licensing/privacy permits.

Suggested structure:

```text
tests/
  audio/
    bad/
      ntn567_bad.wav
      ntn568_bad.wav
    good/
      ntn567_fixed.wav
      ntn568_fixed.wav
```

The clips only need to be long enough to reproduce the issue.

Expected behavior:

```text
NTN567 bad    -> FAIL
NTN567 fixed  -> PASS

NTN568 bad    -> FAIL
NTN568 fixed  -> PASS
```

Tests should verify the reason for failure, not only a generic false result.

Example:

```text
FAIL
reason = MUSIC_MASKING_VOICE
```

---

# Priority 2 — Audio Quality Report

Introduce a structured object instead of passing isolated values.

Example:

```python
@dataclass
class AudioQualityReport:
    integrated_lufs: float | None
    true_peak_dbtp: float | None
    clipped_samples: int
    clipped_percentage: float
    longest_silence_seconds: float | None

    median_voice_music_ratio_db: float | None
    p10_voice_music_ratio_db: float | None
    worst_voice_music_ratio_db: float | None

    speech_below_warning_percentage: float | None
    speech_below_failure_percentage: float | None

    worst_section_start_seconds: float | None
    worst_section_end_seconds: float | None

    warnings: list[str]
    failures: list[str]

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0
```

Names can be adapted to the project's style.

---

# Priority 2 — Quality score

Optionally produce a human-friendly score from 0–100.

Example UI:

```text
FINAL AUDIO QUALITY

Integrated loudness     -16.1 LUFS   OK
True peak                -1.7 dBTP   OK
Clipping                  0 samples  OK

Voice / Music
Target separation          18 dB
Median                    21.3 dB    OK
Worst                      7.2 dB    FAIL
Speech below 12 dB           1.8%    WARN

QUALITY SCORE
91 / 100
```

Do not make the score the source of truth.

The individual checks and failures are more important.

---

# Priority 2 — UI behavior

The existing pre-mix inspector should remain informative.

The new final inspector should be stronger.

Suggested states:

```text
GREEN
Ready to publish

YELLOW
Review recommended

RED
Audio Quality Check Failed
Publishing is not recommended
```

For RED:

```text
[ Preview problem ]
[ Apply suggested fix ]
[ Override and continue ]
```

Do not completely block export.

The user should still be able to override the warning deliberately.

---

# Priority 2 — Suggested fixes

When possible, map failures to actionable recommendations.

Examples:

```text
VOICE_TOO_QUIET
-> Normalize or increase voice level

MUSIC_MASKING_VOICE
-> Reduce music by X dB
-> Increase ducking
-> Preview worst section

LOUDNESS_TOO_LOW
-> Run LUFS normalization

LOUDNESS_TOO_HIGH
-> Normalize to target

TRUE_PEAK_TOO_HIGH
-> Apply limiter / reduce output gain

CLIPPING_DETECTED
-> Reduce gain before final render
```

---

# Priority 2 — Reproducible music selection

If background music selection currently uses randomness, make episode rendering reproducible.

Either:

1. Store the selected tracks in episode metadata, or
2. Store and reuse a random seed.

Two renders of the same episode should be able to reproduce the same music selection.

This is important for debugging audio issues.

---

# Priority 2 — Fix inspector threshold consistency

Ensure UI text and implementation use the same thresholds.

For example, if the UI says:

```text
Optimal voice level: -14 to -22 dBFS
```

then the code should not silently classify `-11 dBFS` as optimal.

Use named constants or configuration values so the UI and analyzer share the same source.

---

# Proposed pipeline

The desired final architecture is:

```text
RAW VOICE
   |
   +-- Input QC
   |    - dBFS
   |    - peaks
   |    - noise
   |
   v
Denoise / Enhance
   |
   v
Voice Gain / Normalization
   |
   v
VOICE + MUSIC
   |
   +-- Mix QC
   |    - speech detection
   |    - windowed voice/music ratio
   |    - smooth ducking
   |
   v
RENDER
   |
   v
LUFS NORMALIZATION
   |
   v
FINAL FILE
   |
   +-- Final QC
   |    - Integrated LUFS
   |    - True Peak
   |    - Clipping
   |    - Silence anomalies
   |    - Worst voice/music section
   |
   v
READY TO PUBLISH
```

---

# Configuration

Avoid scattering magic numbers.

Create a central configuration object or constants for:

```text
target_lufs
target_true_peak_dbtp

voice_target_dbfs

vmr_excellent_db
vmr_warning_db
vmr_failure_db

ducking_reduction_db
ducking_attack_ms
ducking_release_ms

silence_warning_seconds
silence_failure_seconds
```

Use existing configuration mechanisms if possible.

---

# Logging

Add clear logs around audio processing.

Examples:

```text
[AudioQC] Running loudness analysis
[AudioQC] Pass 1 LUFS stats parsed successfully
[AudioQC] Running two-pass LUFS normalization
[AudioQC] Final loudness: -16.1 LUFS
[AudioQC] True peak: -1.7 dBTP
[AudioQC] Worst VMR: 7.2 dB at 14:32
[AudioQC] RESULT: FAIL - MUSIC_MASKING_VOICE
```

Avoid hiding failures behind generic exceptions.

---

# Tests

Add tests for at least:

## LUFS parser

- Multiline valid JSON.
- Missing JSON.
- Malformed JSON.
- Expected measured values.
- `target_offset` passed to second pass.

## Voice/music analysis

- Voice clearly above music.
- Music slightly too loud.
- Music louder than voice.
- No music.
- No voice.
- Very short clips.
- One short problematic section inside an otherwise good episode.

## Final QC

- Good audio passes.
- Loudness too low fails or warns.
- True peak too high fails.
- Clipping is detected.
- Long silence is detected.
- Music masking voice fails.

## Regression

- Real bad NTN sample fails.
- Fixed NTN sample passes.

---

# Non-goals

Do not:

- Add machine learning unless it clearly improves the result.
- Replace FFmpeg if it already solves the problem.
- Add cloud dependencies for basic audio QC.
- Completely prevent the user from exporting.
- Over-engineer a broadcast mastering suite.

Prefer deterministic local DSP and FFmpeg-based checks.

---

# Definition of Done

This work is complete when:

1. True two-pass LUFS normalization works reliably.
2. Final rendered audio is analyzed before publication.
3. Short sections of music masking voice can be detected.
4. The UI points to the worst section.
5. The user receives actionable recommendations.
6. Bad NTN regression samples fail.
7. Corrected NTN regression samples pass.
8. Thresholds are configurable.
9. The final pipeline logs clearly why an episode passed or failed.
10. Existing episode creation still works when the Quality Gate is disabled.

---

# Recommended implementation order

Implement in this order:

1. Fix multiline `loudnorm` JSON parser.
2. Add unit tests for the parser.
3. Add final LUFS / true-peak analysis.
4. Introduce `AudioQualityReport`.
5. Add clipping and silence checks.
6. Add windowed voice/music ratio analysis.
7. Detect and report worst section.
8. Add final QC UI.
9. Improve ducking attack/release.
10. Add real NTN regression audio fixtures.
11. Add optional quality score.
12. Add suggested automatic fixes.

Keep each step in a small, reviewable commit where possible.

---

# Copilot task

Please inspect the current repository before changing code.

Reuse existing abstractions and project conventions instead of creating duplicate systems.

Implement the priorities above incrementally.

For each change:

1. Explain the existing behavior.
2. Identify the smallest safe change.
3. Implement it.
4. Add or update tests.
5. Run the relevant test suite.
6. Report:
   - files changed,
   - behavior changed,
   - tests added,
   - tests executed,
   - remaining risks or follow-up items.

Do not refactor unrelated code.

Preserve existing CLI/UI behavior unless required for the Audio Quality Gate.
