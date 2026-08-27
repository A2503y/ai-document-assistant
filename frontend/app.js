const state = { documents: [], selected: new Set() };
const $ = (selector) => document.querySelector(selector);

function showError(message) { const notice = $("#notice"); notice.textContent = message; notice.hidden = false; }
function clearError() { $("#notice").hidden = true; }
function detail(error) { return error?.detail || "Something went wrong. Please try again."; }
async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw data;
  return data;
}
function escapeText(value) { const node = document.createElement("span"); node.textContent = value; return node.innerHTML; }
function updateSelectionStatus() {
  const count = state.selected.size;
  $("#selection-status").textContent = count ? `${count} document${count === 1 ? "" : "s"} selected` : "All documents will be searched";
  $("#clear-selection").hidden = !count;
}
function renderDocuments() {
  const list = $("#document-list");
  $("#document-count").textContent = `${state.documents.length} document${state.documents.length === 1 ? "" : "s"}`;
  $("#empty-state").hidden = state.documents.length > 0;
  if (!state.documents.length) { list.innerHTML = '<p class="no-documents">No documents uploaded yet.</p>'; updateSelectionStatus(); return; }
  list.innerHTML = state.documents.map((doc) => `
    <label class="document-card">
      <input type="checkbox" data-select="${doc.document_id}" ${state.selected.has(doc.document_id) ? "checked" : ""} />
      <div class="document-main"><p class="filename" title="${escapeText(doc.filename)}">${escapeText(doc.filename)}</p><p class="document-meta">${doc.page_count || "?"} page${doc.page_count === 1 ? "" : "s"} · ${doc.chunk_count} chunks</p></div>
      <button class="delete-button" data-delete="${doc.document_id}" type="button" title="Delete document" aria-label="Delete ${escapeText(doc.filename)}">×</button>
    </label>`).join("");
  updateSelectionStatus();
}
async function loadDocuments() {
  try { clearError(); state.documents = await api("/documents"); const known = new Set(state.documents.map((doc) => doc.document_id)); state.selected = new Set([...state.selected].filter((id) => known.has(id))); renderDocuments(); }
  catch (error) { showError(detail(error)); }
}
function setBusy(button, busy, label) { button.disabled = busy; if (busy) { button.dataset.label = button.textContent; button.textContent = label; } else { button.textContent = button.dataset.label || button.textContent; } }
$("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault(); clearError(); const file = $("#file-input").files[0]; if (!file) return showError("Choose a PDF to upload.");
  const button = $("#upload-button"); setBusy(button, true, "Uploading…");
  try { const form = new FormData(); form.append("file", file); await api("/upload", { method: "POST", body: form }); $("#file-input").value = ""; await loadDocuments(); }
  catch (error) { showError(detail(error)); } finally { setBusy(button, false); }
});
$("#file-input").addEventListener("change", (event) => {
  const file = event.target.files[0];
  $("#upload-title").textContent = file ? file.name : "Choose a PDF";
  $("#upload-detail").textContent = file ? `${Math.ceil(file.size / 1024)} KB selected` : "Up to 15 MB";
});
$("#document-list").addEventListener("change", (event) => { const id = event.target.dataset.select; if (!id) return; event.target.checked ? state.selected.add(id) : state.selected.delete(id); updateSelectionStatus(); });
$("#document-list").addEventListener("click", async (event) => {
  const id = event.target.dataset.delete; if (!id) return; event.preventDefault(); event.stopPropagation(); const doc = state.documents.find((item) => item.document_id === id);
  if (!confirm(`Delete ${doc?.filename || "this document"}?`)) return;
  try { clearError(); await api(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" }); state.selected.delete(id); await loadDocuments(); }
  catch (error) { showError(detail(error)); }
});
$("#clear-selection").addEventListener("click", () => { state.selected.clear(); renderDocuments(); });
$("#refresh-button").addEventListener("click", loadDocuments);
$("#ask-form").addEventListener("submit", async (event) => {
  event.preventDefault(); clearError(); const question = $("#question-input").value.trim(); if (!question) return showError("Enter a question first.");
  const button = $("#ask-button"); setBusy(button, true, "Thinking…"); $("#answer-area").hidden = false; $("#answer-area").innerHTML = '<div class="loading">Searching your documents and preparing an answer</div>';
  const payload = { question, top_k: 4 }; const selected = [...state.selected]; if (selected.length === 1) payload.document_id = selected[0]; if (selected.length > 1) payload.document_ids = selected;
  try { const result = await api("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); renderAnswer(result); }
  catch (error) { $("#answer-area").hidden = true; showError(detail(error)); } finally { setBusy(button, false); }
});
function renderAnswer(result) {
  const sources = result.sources.map((source) => `<article class="source-card"><div class="source-title"><span>${escapeText(source.filename)}</span><span>${source.page_number ? `Page ${source.page_number}` : "Page unavailable"}</span></div><p>${escapeText(source.excerpt)}</p></article>`).join("");
  $("#answer-area").innerHTML = `<article class="answer-card">${escapeText(result.answer)}</article><h3 class="sources-heading">Retrieved sources</h3>${sources || '<p class="no-documents">No source excerpts returned.</p>'}`;
}
loadDocuments();
