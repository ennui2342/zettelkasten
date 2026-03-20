const btn = document.getElementById("btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const portInput = document.getElementById("port-input");
// Persist port across popup opens
chrome.storage.local.get(["port"], ({ port }) => {
  if (port) portInput.value = port;
});
portInput.addEventListener("change", () => {
  chrome.storage.local.set({ port: portInput.value });
});

function showStatus(cls, msg) {
  statusEl.className = cls;
  statusEl.textContent = msg;
  statusEl.style.display = "block";
}

function renderResults(results) {
  if (!results || results.length === 0) return;
  resultsEl.innerHTML = results
    .map(r => {
      const opClass = "op-" + (r.operation || "NOTHING");
      const title = r.title ? r.title.slice(0, 50) : "—";
      return `<div class="result-row">
        <span class="op ${opClass}">${r.operation}</span>${title}
      </div>`;
    })
    .join("");
}

btn.addEventListener("click", async () => {
  const port = parseInt(portInput.value, 10) || 7842;
  btn.disabled = true;
  resultsEl.innerHTML = "";
  showStatus("info", "Capturing page…");

  // Inject a content script to grab the rendered HTML
  let tab;
  try {
    [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  } catch (e) {
    showStatus("err", "Could not get active tab: " + e.message);
    btn.disabled = false;
    return;
  }

  let html, url;
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        html: document.documentElement.outerHTML,
        url: document.URL,
      }),
    });
    html = result.html;
    url = result.url;
  } catch (e) {
    showStatus("err", "Could not read page: " + e.message);
    btn.disabled = false;
    return;
  }

  showStatus("info", "Sending to server…");

  let data;
  try {
    const resp = await fetch(`http://127.0.0.1:${port}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html, url }),
    });
    data = await resp.json();
    if (!resp.ok) {
      showStatus("err", "Server error: " + (data.error || resp.status));
      btn.disabled = false;
      return;
    }
  } catch (e) {
    showStatus("err", "Fetch failed — is the server running on port " + port + "? (" + e.message + ")");
    btn.disabled = false;
    return;
  }

  showStatus("ok", "✅ " + (data.summary || "Done"));
  renderResults(data.results);
  btn.disabled = false;
});
