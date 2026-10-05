# Production Import — additional source-unique GitHub donors (2026-09-29)
Status: DESIGN RESEARCH / metadata-only CANDIDATE. Parent: [final blueprint](production-import-final-blueprint-2026-09-29.md); [existing consolidated plan](production-import-migration-plan-2026-09-29.md); PR #528. Capability baseline 175; dynamic provider count; zero new authorities. The canonical record is the existing [Donor & Reference Registry](../canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json), NOT this report.

## Source-level, version-sensitive donor decisions

| Upstream | Reusable pattern | Admission boundary |
|---|---|---|
| [https://github.com/bavc/qctools](https://github.com/bavc/qctools) | video-preservation-qc; anomaly-review; ffprobe-xml-reports | Reference only: inspect pre-ingest anomalies. Mixed component licenses require independent source and transitive review; no mandatory GUI or duplicate QC authority. |
| [https://github.com/bbc/bmx](https://github.com/bbc/bmx) | mxf-essence-extraction; mxf-transwrap; broadcast-timecode | Archived historical source, not preferred execution fork. README directs ongoing work to https://github.com/ebu/bmx. Keep separate upstream provenance for version-specific comparison. |
| [https://github.com/ebu/bmx](https://github.com/ebu/bmx) | mxf-essence-extraction; mxf-transwrap; broadcast-asset-preservation | Current EBU fork is preferred reference over archived BBC origin; profile-specific MXF input/output, audio/channel mapping and timecode still need fixture and current-host checks. |
| [https://github.com/bbc/audiowaveform](https://github.com/bbc/audiowaveform) | waveform-peak-pyramid; audio-range-gui; audio-peaks-data | Historical GitHub mirror; README states ongoing development moved to https://codeberg.org/chrisn/audiowaveform. Downmixed peaks are UI derivatives only, never original multichannel audio. GPL distribution review required. |
| [https://github.com/ebu/ebu_adm_renderer](https://github.com/ebu/ebu_adm_renderer) | adm-object-audio; itu-bs2127-rendering; spatial-audio-mapping | Python implementation for ADM render interpretation. ITU-R BS.2127 takes precedence over historical EBU Tech 3388; a rendered mix does not recreate an editable object-based source. |
| [https://github.com/ebu/ebu-adm-toolbox](https://github.com/ebu/ebu-adm-toolbox) | adm-profile-conversion; adm-validation; adm-loudness; object-audio-fixups | Current EBU C++20 toolbox contains configurable processing graphs; adopt only admitted profile-specific patterns under existing Audio/Conversion/QC owners, preserving original ADM and detailed loss records. |
| [https://github.com/AMWA-TV/nmos-testing](https://github.com/AMWA-TV/nmos-testing) | nmos-is04-discovery-tests; nmos-is05-connection-tests; nmos-is09-isolated-validation | Reference-only test patterns. Upstream README warns some IS-04/IS-09 tests emit mock mDNS; run only on isolated lab segments with explicit admission, never on a production LAN. |
| [https://github.com/Netflix/vmaf](https://github.com/Netflix/vmaf) | vmaf-libvmaf; reference-video-qc; transcode-perceptual-quality | Extend already present FA3 FFmpeg/libvmaf QC instead of deploying a second quality engine; VMAF is not archival fixity, timecode, color/HDR or timeline semantic equivalence. |

## Already registered: enrich or reuse, never create duplicates
- acoustid/chromaprint: advisory fingerprint-assisted relinking only; confirm source digests or explicit operator choice.
- smacke/ffsubsync: alignment of existing subtitle text; timing correction does not certify textual accuracy.
- asteroid-team/asteroid and speechbrain/speechbrain: research candidate separation/enhancement; model and checkpoints require independent current-host/CPU, ontology, license and HRB/Router admission.
- jiixyj/libebur128: EBU loudness/true-peak analysis already recorded; it cannot certify original stem identity.
- OpenEXR and OpenColorIO: retain existing project/source records; no second image/color authority.
- FFmpeg/libvmaf path already exists in FA3 reference logic. Netflix VMAF is extra upstream research, not a second QC executor.

## Upstream provenance (verified 2026-09-29)
The BBC bmx README explicitly states that source is archived and points to [EBU/bmx](https://github.com/ebu/bmx); store two genuinely distinct source records, use the active EBU fork as the implementation research target, preserve BBC for version history. BBC/audiowaveform's README identifies the current upstream as https://codeberg.org/chrisn/audiowaveform; its GitHub repository remains a historical donor reference only. EBU ADM Renderer references ITU-R BS.2127, not an EBU Tech 3388 supersession claim. The EBU ADM Toolbox README documents ADM profile conversion, verification and configurable processing graphs. AMWA nmos-testing warns mock IS-04/IS-09 mDNS announcements and requires isolated networks. QCTools README distinguishes GPLv3 deliverable from BSD-3-Clause subcomponents. Netflix VMAF README declares BSD+Patent; GitHub API has NOASSERTION, so license must be reviewed at pinned source/packaging before copying.

## Exclusions and gates
No new conversion daemon, metadata authority, provider router, audio engine, media QC authority, network discovery service or cloud upload. Donor capture never authorizes runtime, copied source, model weights, device lease or current-host PASS. All actual format/version pair checks require real fixtures, reversible subsets only where independently verified, licence/SBOM/security, hardware non-interference and target-app reopen evidence.