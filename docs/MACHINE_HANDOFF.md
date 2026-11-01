# Moving NTN Podcast Creator to another computer

## Plan and implementation

1. **Publish the approved audio library.** Track the existing intro, outro, and
   six background tracks with explicit Git ignore exceptions. Other local audio
   remains ignored. The owner confirmed permission to publish these eight files
   in this public repository. They total about 33 MB, so Git LFS is not required.
2. **Bootstrap portable settings.** Track `core/config.initial.json`, containing
   the current settings snapshot and repository-relative audio paths.
   `ConfigManager` validates and atomically saves it as `core/config.json` only
   when the local configuration does not exist. Existing settings, including
   disabled audio selections, are never replaced by the snapshot.
3. **Keep local state local.** Continue ignoring `core/config.json`, recordings,
   generated episodes, temporary uploads, and `.env` credentials. Docker Compose
   already mounts the audio folders and the whole `core` directory, so no
   container export or Docker volume migration is necessary.
4. **Verify and publish.** Run configuration regression tests and validate a
   clean checkout in Docker before committing and pushing the scoped changes.

The initial snapshot includes:

| Setting | Value |
|---------|-------|
| Intro | `25 11 22 NTN-Intro.MP3` |
| Outro | `24 12 03 NTN-Outro.m4a` |
| Background pool | Six tracks in `audios/background_music` |
| Background volume | 5% |
| Per-track volume overrides | None |
| LUFS normalization | Enabled, -16 LUFS |
| Intro/voice and voice/outro overlaps | Enabled |
| Quiet-opening correction and auto-ducking | Enabled |
| Denoising, voice enhancement, transcription, quality gate | Disabled |
| Last output name | `ntn590` (editable for the next episode) |
| Saved templates | None on the source computer at handoff |

All other saved processing thresholds and naming settings are included in
[the initial configuration](../core/config.initial.json).

### Validation performed

- 134 targeted tests passed in an isolated Python 3.12 Docker runtime, covering
  portable bootstrap, saved settings, and existing quality configuration.
- A checkout containing only tracked files matched the source settings and all
  eight audio file hashes. All eight files decoded with FFmpeg/pydub.
- The repository Dockerfile built successfully from that clean checkout.
- Docker Compose started the clean checkout on an isolated test port, created
  local settings automatically, and served the Gradio configuration with HTTP 200.
- A 15-second excerpt of `audios/test/251121-ntn443-Recording.m4a` produced and
  downloaded a 54.487-second MP3 through the episode API, using the real intro,
  outro, background pool, ducking, overlaps, and two-pass normalization.
  The normalizer reported its existing true-peak-headroom warning and completed
  with transient peak limiting. This smoke test is not a full-length listening
  review or certification of measured -16 LUFS.
- A saved 7% local volume override survived container restart while the
  published 5% initial setting remained unchanged.

## New computer: first start

### Prerequisites

- Install Git.
- Install Docker Desktop (or Docker Engine with Docker Compose on Linux).
  Start the engine and use Linux containers.
- Internet access is needed for the first image build and Python dependencies.
  Local Python and FFmpeg are not required for the Docker web interface.
- Ensure port 7860 is available.

Run these commands in PowerShell. Choose your own parent directory before cloning:

```powershell
git clone https://github.com/elbruno/ntn-podcast-creator.git
cd ntn-podcast-creator
docker version
docker compose version
docker compose -f .\deployment\docker-compose.yml up -d --build
docker compose -f .\deployment\docker-compose.yml logs --tail 80
```

The first build can take several minutes. Open **http://localhost:7860** when
the application is ready. On a fresh clone, startup logs include
`Initializing settings from core/config.initial.json`.

The intro, outro, background music, and saved defaults are ready without
manually uploading music. Docker mounts the checked-out files rather than
embedding the audio library in the image. Use this Compose workflow, not a bare
`docker run` without the documented mounts.

### Check that migration worked

From the repository root:

```powershell
Test-Path .\core\config.json
Get-Content .\core\config.json
docker compose -f .\deployment\docker-compose.yml ps
Invoke-WebRequest http://localhost:7860 -UseBasicParsing
```

Confirm that:

1. The container is running and the web page responds.
2. **Settings** shows the expected intro, outro, six background tracks, 5%
   background volume, and -16 LUFS normalization.
3. Upload a recording, create an episode, and listen to the intro, voice,
   background, and outro. Generated files appear in the local `outputs` folder.
4. Change an option, choose **Save settings**, restart, and confirm it persists:

```powershell
docker compose -f .\deployment\docker-compose.yml restart
```

Restarting, rebuilding, or pulling newer code does not overwrite an existing
`core/config.json`.

## Daily use and updates

Run all commands from the repository root:

```powershell
# Start again without rebuilding.
docker compose -f .\deployment\docker-compose.yml up -d

# Stop without deleting host settings, music, or episodes.
docker compose -f .\deployment\docker-compose.yml down

# Update code and rebuild when repository changes are available.
git pull --ff-only
docker compose -f .\deployment\docker-compose.yml up -d --build
```

For terminal-based episode creation, see the
[PowerShell CLI workflow](DOCKER.md#command-line-episode-creation) or the
[Python pending-folder workflow](DOCKER.md#pending-episode-folders-python).
The PowerShell client additionally requires PowerShell 7; the pending-folder
client requires local Python and a recording root appropriate for the new
computer. OneDrive paths and recording files are not transferred by cloning.

## Existing checkout or later handoff

The tracked snapshot is a starting point, not automatic synchronization between
computers. An existing `core/config.json` always wins, even if it is empty or
invalid. Invalid local JSON keeps the existing logged fallback behavior; it is
not replaced by the published snapshot.

To intentionally use the published settings on an existing computer:

1. Stop the application with the Compose `down` command.
2. Move `core/config.json` to a private backup outside the repository.
3. Start with Compose `up -d --build`. It creates fresh local settings from the
   published snapshot. Do not do this if you want to retain local changes.

To move settings changed after this handoff, use **Export settings** and
**Import and apply settings** in the UI, or privately copy `core/config.json`
while the application is stopped. Transfer any new audio files and
`core/templates` too. Use paths relative to the repository (`audios/...`), not
Windows host paths or another machine's absolute paths.

To publish an updated starting point, review exported settings, replace
`core/config.initial.json` with the reviewed portable values, and explicitly
add any newly approved library files. Review `git diff --cached` before
committing. Do not publish credentials, private recordings, or music without
redistribution permission. Existing computers will still retain their own local
configuration after a pull.

## Not transferred by Git

- Adobe credentials and other `.env` secrets. Reconfigure them privately if
  needed, following the enhancement setup documentation.
- Uploaded voice recordings and generated podcasts in `uploads` and `outputs`.
- Runtime caches, model downloads, and the built Docker image.
- Later local setting changes or local-only templates.
- New music files unless explicitly approved and added to version control.

Keep a separate private backup for those files. No production recording is
needed just to start the application on the new computer.
