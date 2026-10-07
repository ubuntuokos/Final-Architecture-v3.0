# FA3 ChatGPT donor-history bridge

The non-authoritative contract is `FA3-DONOR-CHAT-INGEST-001`. The adapter extends
the existing Donor & Reference Registry, not a new capability or architectural authority.

## Supported input paths

1. User-supplied ChatGPT exports (ZIP, `conversations.json`, numbered JSON). Authenticated user-role messages may authorize intake only with one exact command: `donornak`, `vedd fel donornak`, or `add a donorlistához`. Commands before or after same-message links are equivalent; negated/near-match/URL-contained commands are ignored. A link-free command may target only the immediately preceding owner message and only when no owner message intervened.
2. Owner-authorized local JSONL events. Structured events must attest `speaker_role=user`, `owner_submitted_link=true`, and an exact `owner_donor_command` (legacy `owner_donor_marker=donornak` remains accepted for compatibility). A potential-donor flag alone does not enroll a link.

This importer is NOT subscribed to ChatGPT and cannot automatically monitor conversations, request exports or fetch account data. It never publishes a registry commit. The existing GitHub intake gate must be used before publishing the resultant changes. Up to five conversations may have genuine canonical donor-intake requests active at once; policy-only and reference-only PRs do not claim a slot. Waiting requests enter FIFO as active slots are released.

## Local operator commands

From the FA3 checkout:

```bash
bash bin/fa3-donor-chat-import --export "$HOME/Downloads/chatgpt-export.zip" --dry-run
bash bin/fa3-donor-chat-import --export "$HOME/Downloads/chatgpt-export.zip"
bash bin/fa3-donor-chat-import --export "$HOME/Downloads/conversations.json"
cat /private/local/events.jsonl | bash bin/fa3-donor-chat-import --events -
```

For a privacy-sensitive first pass, use `--roles user`. The default scans user and
assistant text-only messages and ignores tool messages, images and file attachments.
Only source metadata, tags and generic import provenance enter the public repository:
not raw messages, conversation titles, account identifiers, attachments, or export files.
Never commit the export, event stream or private workspace files.

**Privacy:** Uncommanded links and assistant suggestions are never inserted or queued. Any source-less name is analysis only. Only exact authenticated owner-commanded links, or the separately committed approved-plan exact donor set, are eligible for reference registration. Import stores source metadata, generic provenance, never raw chats, titles, private token strings or attachments. Malformed input or a rejected-source conflict fails without partial registry writes.

**Coordination and visibility:** Local concurrent imports against the same checkout return `DONOR_INTAKE_ALREADY_ACTIVE_WAIT_FOR_COMPLETION` because registry bytes remain single-writer per checkout. Cross-conversation/cross-host GitHub publication uses the rolling five-slot live donor-intake gate. Within the active window, the smallest canonical donor-mutation workload finalizes first, with FIFO ties. Planning always uses the exact published main registry, never a pending import or unmerged donor PR. License, adoption and runtime gates remain separate.

## Hardware Audit

Metadata-only, vendor- and accelerator-neutral, CPU-only viable. Accelerator inventory
0..N; no global accelerator requirement, no runtime hardware mutation, and no resource
authority beyond the existing HRB.

## Validation

```bash
PYTHONPATH=src python3 -m unittest tests.test_donor_chat_import -v
PYTHONPATH=src python3 -m unittest tests.test_reuse_discovery_gate -v
./bin/fa3-enforce reuse-discovery
./bin/fa3-enforce hardware-portability
```

The repository workflow runs the importer tests with synthetic conversation fixtures.
No private ChatGPT export is required or used in CI.

## Optional automatic local inbox (Linux/systemd user)

Run `bash bin/fa3-donor-chat-watch-install` from the FA3 checkout to install an
opt-in user-level `systemd.path` watcher. It creates a private
`~/.local/share/fa3/donor-import/inbox/` (mode 0700) and imports ZIP or
conversations JSON **after you put an export there**. A private SHA-256 checkpoint
(mode 0600) prevents repeated processing of the same export. The importer
never sends conversation content to a server and never pushes a commit.

```bash
mkdir -p "$HOME/.local/share/fa3/donor-import/inbox"
cp "$HOME/Downloads/chatgpt-export.zip" "$HOME/.local/share/fa3/donor-import/inbox/"
systemctl --user status fa3-donor-chat-import.path
# To disable:
systemctl --user disable --now fa3-donor-chat-import.path
```

Exports remain private files in your inbox until **you** remove them. Keep the
folder private, and do not sync it to the public repository. The watcher only
processes user-supplied exports; it does not monitor, log in to, or request new
ChatGPT conversations. For ongoing near-real-time capture from another system,
connect a separately approved event source to the `--events -` adapter.

Test the inbox locally without installing the service:

```bash
PYTHONPATH=src python3 -m unittest tests.test_donor_chat_inbox -v
bash bin/fa3-donor-chat-inbox
```


### Repair existing units generated before the systemd path fix

If `systemctl --user status fa3-donor-chat-import.service` reports
`WorkingDirectory= path is not absolute` because the old installer wrote
`WorkingDirectory="/absolute/path"`, remove those literal quote characters
in **your own** installed service file, then reload and restart the path watcher:

```bash
unit="$HOME/.config/systemd/user/fa3-donor-chat-import.service"
sed -i 's|^WorkingDirectory="\\(.*\\)"$|WorkingDirectory=\\1|' "$unit"
systemctl --user daemon-reload
systemctl --user reset-failed fa3-donor-chat-import.service fa3-donor-chat-import.path
systemctl --user restart fa3-donor-chat-import.path
systemctl --user status fa3-donor-chat-import.path --no-pager
```

The healthy path unit shows `active (waiting)`. The one-shot service can
legitimately remain inactive until an export arrives. Do **not** use `sudo`
with these user-level systemd units, and do not rerun the installer over
existing user-unit files; it deliberately refuses to overwrite them.
