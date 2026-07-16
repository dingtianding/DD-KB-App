# DD-KB App

A dependency-free local search and grounded-answer interface for a Markdown
knowledge base. It indexes Markdown headings and content with in-memory BM25,
automatically refreshes when notes change, and can optionally use the OpenAI
Responses API to synthesize cited answers from retrieved excerpts.

The application binds to `127.0.0.1` and does not expose the vault over the
network.

## Features

- Local BM25 retrieval with no package installation or API key required.
- Automatic refresh when Markdown files are added, edited, or removed.
- Heading-aware chunks with source paths and line numbers.
- Optional grounded answer generation through the OpenAI Responses API.
- Browser interface and an Obsidian right-sidebar plugin.
- Local dashboard with note, section, word, topic, tag, and recent-update insights.
- Excludes hidden folders, `Inbox`, `Templates`, application code, and tests.

## Run

Place this repository beside a Markdown folder named `DD-KB`:

```text
parent/
  DD-KB/
  DD-KB-App/
```

Then run:

```bash
cd DD-KB-App
python3 app.py
```

Open <http://127.0.0.1:8787>.

To use another vault location:

```bash
DD_KB_VAULT=/absolute/path/to/vault python3 app.py
```

## Optional generated answers

Retrieval works without credentials. To enable generated answers, provide the
key through the environment rather than committing it to a file:

```zsh
read -s "OPENAI_API_KEY?OpenAI API key: "
export OPENAI_API_KEY
echo
python3 app.py
```

`OPENAI_MODEL` optionally overrides the model used by the Responses API.

## Obsidian sidebar

Copy the three files in `obsidian-plugin/` to:

```text
<vault>/.obsidian/plugins/dd-kb-assistant/
```

Enable **DD-KB Assistant** under Obsidian's community plugin settings, start the
local server, and open the assistant from the ribbon or command palette.

## Tests

```bash
python3 -m unittest discover -s tests -v
node --check obsidian-plugin/main.js
```

## Security boundaries

- Keep private notes in a private vault repository; this application repository
  should contain code only.
- Never commit API keys or client data.
- The optional model receives the question and retrieved excerpts. Do not enable
  generation for material you are not permitted to send to the configured model
  provider.
