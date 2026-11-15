# Local access and credential handling

- Bind only to 127.0.0.1. Do not expose this development service to your LAN or the public internet.
- The browser sends an entered login only to this same-origin local backend. Credentials are attached only to urs.earthdata.nasa.gov, including redirect requests; NASA science-file cookies stay in RAM. Verification reads a science-file header rather than using the legacy ASF cookie gate. Credentials and cookies remain in RAM.
- No credential is hardcoded, written to `.env`/`.netrc`, logged in access logs, returned by status endpoints, or included in scientific exports. Stopping the service erases the session; Disconnect closes it immediately when no job is active.
- Login errors return a generic message. Backend access logs are disabled. Do not add request-body logging.
- The service rejects unfamiliar Host headers and cross-origin requests, and does not enable CORS. Loopback is a development boundary, not multi-user authentication.
- Data source URLs are resolved from catalog results and restricted to HTTPS NASA/ASF domains. Clients cannot supply arbitrary download URLs.
- File imports are limited to 8 GiB, checked for an HDF5 signature and the expected NISAR science group, and saved under generated identifiers.
- Artifact paths use validated identifiers and filenames. Imported/source/result files are outside the static-web directory.
- Download partial files are removed on failure. Jobs and exported results are stored without credentials under ignored `data/`.
- Library source URLs and Esri basemaps/reference labels make ordinary external web requests. Basemap interaction exposes viewed map tiles to the tile provider; no Earthdata credentials accompany those requests.
- A public deployment would require TLS, user authentication, per-user credential isolation, quotas and a dedicated job queue. It is deliberately not configured by this first local release.


## Baseline 0.1.1 hardening

The normal launcher always creates an empty in-memory credential store. Each user signs in through Connection; the UI has no account defaults or application browser-storage persistence. Login inputs request autocomplete off and are cleared after successful login or disconnect. Browser password managers are controlled by the user/browser and may ignore autocomplete preferences; the app does not implement credential saving.

Password request fields use SecretStr. Validation errors deliberately omit submitted values; even malformed or oversized login requests cannot echo the supplied password. Starting a new login erases the previous account first, so a failed account switch cannot silently continue using another person's session. Authentication and file-transfer redirects require HTTPS, no URL-embedded credentials, and the standard HTTPS port. Basic authentication is attached only to Earthdata Login. Single-action admission prevents login/logout/inspection from racing a newly admitted processing or download job.

Science range probes read only a bounded header and check Content-Range. Subsequent ranges must match the requested offsets and total length. Full downloads with a declared length are not published until the whole payload has arrived. Data and cache files contain science arrays and non-credential provenance, not passwords.

Job writes use a reentrant lock and atomic replacement; API callers receive snapshots. Analysis settings reject unsupported fields, malformed dates, invalid quality switches. Frame embedding is denied; API responses are not cached. Logs never intentionally include request bodies or credentials.

An exact-match check for the supplied account identifier and password found no matches in 696 inspected workspace files, including Word XML. Environments, large science/image binaries and PDFs were outside that scan. Test credentials in source are invented examples. The application cannot erase credentials already present in the user's conversation history or manage the operating system's memory/swap policy.

Dependency audit reports are saved in `dependency-audit.json` and `audit/browser-dependencies.json`. Reported advisories in older Pillow, Starlette and pytest pins were addressed with compatible upgrades. The refreshed 48-package PyPI metadata check and bundled Leaflet/Plotly OSV checks reported no known advisories for the versions checked. This is not a guarantee of vulnerability absence or a full audit of bundled native libraries.

This remains one trusted local server instance and one shared in-memory NASA session, not isolated accounts for simultaneous people using one hosted server. For team members, run a separate local instance per person. Public hosting requires an explicit design for application accounts, per-user sessions and data isolation, HTTPS, quotas, a durable worker queue, monitoring, backups and deployment-specific security testing.

## Native area extracts

`/api/download-area` accepts catalog identifiers and a validated WGS84 rectangle, never arbitrary URLs or paths. It uses the existing Earthdata RAM session and checked range reader. Extracts use generated `subset-` identifiers under `data/subsets/`; HDF5 object references are omitted rather than copied across files. A partial extract is removed on failure or cancellation. Full originals are retained. Extract manifests record sources, bounds, retained/omitted layers and actual local size, with no credentials. Processing rejects rectangles extending outside a saved extract. The existing single-worker admission rule applies to area downloads.

New subset files use product/UTC batch folders with validated relative storage paths; path traversal and symlink escapes outside the managed subsets directory are rejected. Manual imports recognize embedded subset bounds and original source names, reject conflicting/incomplete subset provenance, and retain area restrictions. A SHA-256 checksum detects byte-identical subset imports. New HDF5 provenance contains selected science-source metadata only, without account credentials or session data. Existing flat-layout data are read without automatic migration.

Whole-folder import uses the user-selected browser directory tree and uploads only visible HDF5 files through the existing file-import endpoint. Directory paths are used only as escaped display labels, not as server file paths. JSON/README/hidden files are not uploaded by this flow. The backend does not receive permission to enumerate arbitrary local directories.

## Protected example inputs

The seven curated examples use a fixed allowlist of case identifiers, exact source names and recorded SHA-256 hashes. Their HDF5 copies reside in `Examples/<case>/inputs/`, outside `data/jobs`, `data/arrays` and ordinary downloads. The app exposes tutorial assets through bounded paths and does not serve arbitrary input files or accept caller-supplied filesystem paths. Opening a setup registers only the curated verified inputs; execution still passes the normal typed run validation, local-only boundary and single-job admission checks. Missing or altered inputs disable the example. Protection is at the application level; the machine owner can still modify or remove files directly. Credentials and cookies are never written to the example folders.

### Login verification resilience

Login requests only one public catalog record. If CMR fails or returns no usable record, catalog-resolved NASA file links in `docs/science-access-probes.json` provide fallback probes. Each authenticated request asks only for bytes 0–7 and requires an HTTP 206 range response with exactly the eight-byte HDF5 signature. No session is marked connected without a successful science-file check. Credentials are still sent only to Earthdata Login, never to the science hosts. Missing/busy files may fall through to another probe; an explicit HTTP 401/403 ends verification without retrying credentials across additional files.

Network, TLS, timeout and service failures use sanitized messages that never include upstream URLs, authentication headers or submitted fields. TLS verification stays enabled. Local examples remain independent of authentication and catalog availability.

- Optional PNG basemap export uses a fixed Esri service allowlist, validates map extent, limits tiles and image bytes/dimensions, rejects redirects and uses bounded timeouts. It sends no Earthdata credentials. Provider failures are returned as an explanatory error; numeric rasters are never modified. The global no-referrer policy remains in place; Streets uses an Esri service rather than the OSM public endpoint that requires a referrer.

- Current-view PNG bounds must be four finite, ordered Web Mercator coordinates inside the single-world extent; malformed or unbounded requests are rejected. Output size and tile budgets remain fixed. This display crop never rewrites science files or changes the data-download extent.

## Runtime ownership and job recovery · October 2026

`runtime_storage.py` holds an operating-system advisory lock for the resolved runtime root, including an optional absolute `NISAR_DATA_DIR`. A second cooperating server cannot start on the same root. This is a single-owner safeguard, not user authentication or filesystem protection against the machine owner. Lock files are never unlinked during release. Symbolic or hard-linked lock files are rejected.

Job records use unique temporary names, flush/fsync, atomic replacement and a directory flush on POSIX. Only the runtime owner performs restart recovery. Importing modules reads existing metadata without marking live jobs interrupted. Interrupted jobs retain inputs and committed outputs, with no automatic transfer or processing retry. Invalid records are reported and preserved. Credentials stay RAM-only and are cleared on graceful shutdown.

## Offline snapshots and disk pressure · 0.8.2

The backup CLI is local-only, is not an HTTP upload/restore endpoint and requires runtime ownership. Its explicit file-type/root allowlist excludes environment files, secrets outside the runtime data types, locks and temporary artifacts. It does not invent a guarantee that user-supplied scientific files cannot contain private information: keep backups private. Protected example inputs and source are backed up separately.

Verification rejects unsafe/nonportable member paths, duplicate ZIP names or JSON keys, special files, manifest disagreement, checksum mismatch and payloads above the selected uncompressed limit. Extraction never calls `extractall`; it writes only validated relative files into its own staging directory. Existing profiles and snapshots cannot be overwritten. A restore-interruption marker blocks ordinary startup. This mechanism is not an encrypted backup service or a multi-user access boundary.

Disk checks retain a configurable reserve and repeat at write boundaries. They do not delete user data or provide kernel-enforced quotas. Unexpected file-system failures remain possible; worker admission/finalization prevents an abandoned queued/running state from permanently blocking the local session.

## Workflow contract delivery · 0.8.3

Processing rules are defined in backend source and delivered as a fixed-vocabulary data bundle. The browser interpreter never uses `eval` or accepts rule expressions from recipe JSON. Operator identifiers come from the typed parameter registry; product, parameter limits and order are revalidated on the server. An incompatible/missing rule version disables client execution rather than guessing compatible steps. A rule hash identifies content and is not a signature/authentication mechanism. Draft inspection reads no satellite files or Earthdata credentials.
