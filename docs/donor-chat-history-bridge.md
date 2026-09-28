# FA3 ChatGPT donor-history bridge

The non-authoritative contract is `FA3-DONOR-CHAT-INGEST-001`. The adapter extends
the existing Donor & Reference Registry, not a new capability or architectural authority.

## Supported input paths

1. **Historic backfill**: import a user-requested local ChatGPT data export ZIP,
   `conversations.json`, or numbered `conversations_N.json` files. ZIP members
   other than the conversation JSON files are ignored and never extracted.
2. **Future event ingestion**: an approved, user-controlled local bridge may stream
   JSONL events to standard input. A metadata event has the form
   `{"potential_donor":true,"name":"example/tool","source":"https://github.com/example/tool"}`.
   A text event has the form `{"text":"Lehet donor: https://github.com/example/tool"}`.
   Only an explicitly marked potential donor is admitted; repeated sources merge.

The importer is **not connected to the ChatGPT account** and cannot subscribe to
conversations, request exports, or collect new messages on its own. Event ingestion
becomes automatic only when an explicitly authorized external bridge actually delivers
an event. An export backfill requires a new export when later conversations should be
included. Repository agent instructions alone cannot access other ChatGPT conversations.

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

**Privacy**: source-less names from otherwise private chats are skipped by default unless
already in the donor registry. Explicit `--allow-unlinked-names` permits publishing these
names as public candidate metadata. Review before using this flag. Plain GitHub repository
links from explicitly donor-marked messages are admitted as public reference candidates.
Ambiguous oversize/multi-link mentions are counted and skipped rather than guessed.
Malformed exports fail without partially changing the canonical registry.

Import does not establish license, ownership, safety, download permission, or runtime
admission. A subsequent planning query sees active imported donor candidates via the
existing Reuse Discovery federation. Promotion and deployment retain their independent
security, provenance, hardware and admission gates.

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
