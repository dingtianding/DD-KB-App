const { ItemView, MarkdownRenderer, Notice, Plugin } = require("obsidian");

const VIEW_TYPE = "dd-kb-assistant-view";
const API_URL = "http://127.0.0.1:8787";

class AssistantView extends ItemView {
  getViewType() {
    return VIEW_TYPE;
  }

  getDisplayText() {
    return "Ask DD-KB";
  }

  getIcon() {
    return "message-circle-question";
  }

  async onOpen() {
    this.render();
  }

  render() {
    const root = this.contentEl;
    root.empty();
    root.addClass("dd-kb-assistant");

    const header = root.createDiv({ cls: "dd-kb-header" });
    header.createEl("h3", { text: "Ask DD-KB" });
    const status = header.createEl("span", { cls: "dd-kb-status", text: "Checking…" });

    const form = root.createEl("form");
    const input = form.createEl("textarea", {
      attr: {
        placeholder: "Ask about your projects, experience, decisions, or notes…",
        rows: "5",
      },
    });
    const button = form.createEl("button", { text: "Ask", attr: { type: "submit" } });
    const output = root.createDiv({ cls: "dd-kb-output" });

    this.checkStatus(status);

    input.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        form.requestSubmit();
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = input.value.trim();
      if (!question) return;
      button.disabled = true;
      button.setText("Searching…");
      output.empty();
      output.createDiv({ cls: "dd-kb-loading", text: "Searching your vault…" });
      try {
        const response = await fetch(`${API_URL}/api/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        });
        if (!response.ok) throw new Error(`Request failed (${response.status})`);
        const data = await response.json();
        await this.renderAnswer(output, data);
      } catch (error) {
        output.empty();
        output.createDiv({
          cls: "dd-kb-error",
          text: "DD-KB is unavailable. Start it from ../DD-KB-App with: python3 app.py",
        });
        new Notice(error.message);
      } finally {
        button.disabled = false;
        button.setText("Ask");
      }
    });
  }

  async checkStatus(element) {
    try {
      const response = await fetch(`${API_URL}/api/status`);
      if (!response.ok) throw new Error();
      const data = await response.json();
      element.setText(`${data.documents} notes · ${data.chunks} sections`);
      element.addClass("is-online");
    } catch (_) {
      element.setText("Server offline");
      element.addClass("is-offline");
    }
  }

  async renderAnswer(root, data) {
    root.empty();
    const mode = data.mode === "generated" ? `Generated · ${data.model}` : "Retrieved excerpts";
    root.createDiv({ cls: "dd-kb-mode", text: mode });
    const answer = root.createDiv({ cls: "dd-kb-answer markdown-rendered" });
    await MarkdownRenderer.render(this.app, data.answer || "", answer, "", this);

    if (!data.sources?.length) return;
    root.createEl("h4", { text: "Sources" });
    const sources = root.createDiv({ cls: "dd-kb-sources" });
    data.sources.forEach((source, index) => {
      const item = sources.createEl("button", { cls: "dd-kb-source", attr: { type: "button" } });
      item.createSpan({ cls: "dd-kb-source-number", text: `S${index + 1}` });
      const label = item.createSpan();
      label.createDiv({ cls: "dd-kb-source-title", text: source.title });
      label.createDiv({ cls: "dd-kb-source-path", text: `${source.section} · line ${source.line}` });
      item.addEventListener("click", async () => {
        await this.app.workspace.openLinkText(source.path, "", false);
      });
    });
  }
}

module.exports = class DdKbAssistantPlugin extends Plugin {
  async onload() {
    this.registerView(VIEW_TYPE, (leaf) => new AssistantView(leaf));
    this.addRibbonIcon("message-circle-question", "Ask DD-KB", () => this.activateView());
    this.addCommand({ id: "open-assistant", name: "Open assistant", callback: () => this.activateView() });
    this.app.workspace.onLayoutReady(() => this.activateView());
  }

  async activateView() {
    let leaf = this.app.workspace.getLeavesOfType(VIEW_TYPE)[0];
    if (!leaf) {
      leaf = this.app.workspace.getRightLeaf(false);
      await leaf.setViewState({ type: VIEW_TYPE, active: true });
    }
    this.app.workspace.revealLeaf(leaf);
  }
};
