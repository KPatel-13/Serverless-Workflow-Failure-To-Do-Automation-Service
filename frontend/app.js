const API_BASE_URL = "https://ol54oe1gs9.execute-api.eu-west-2.amazonaws.com";

const elements = {
  openViewButton: document.getElementById("openViewButton"),
  closedViewButton: document.getElementById("closedViewButton"),
  refreshButton: document.getElementById("refreshButton"),
  statusMessage: document.getElementById("statusMessage"),
  ticketBoard: document.getElementById("ticketBoard"),
  columnTitle: document.getElementById("columnTitle"),
};

let currentView = "open";

function getApiBaseUrl() {
  return API_BASE_URL.trim().replace(/\/$/, "");
}

function setStatusMessage(message) {
  elements.statusMessage.textContent = message;
}

function formatDate(value) {
  if (!value) {
    return "N/A";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderEmptyState() {
  const message =
    currentView === "open" ? "No open tickets found." : "No closed tickets found.";

  elements.ticketBoard.innerHTML = `
    <div class="empty-state">${message}</div>
  `;
}

function createMetaRow(label, value) {
  return `
    <div>
      <span class="ticket-card__label">${escapeHtml(label)}:</span>
      <span>${escapeHtml(value ?? "N/A")}</span>
    </div>
  `;
}

function renderTickets(tickets) {
  if (!Array.isArray(tickets) || tickets.length === 0) {
    renderEmptyState();
    return;
  }

  elements.ticketBoard.innerHTML = tickets
    .map((ticket) => {
      const ticketId = ticket.id || "N/A";
      const title = ticket.summary || ticket.title || "Untitled ticket";
      const repo = ticket.repo || "N/A";
      const workflowName = ticket.workflowName || "N/A";
      const jobName = ticket.jobName || "N/A";
      const severity = ticket.severity || "N/A";
      const occurrenceCount = ticket.occurrenceCount ?? "N/A";
      const lastSeenAt = formatDate(ticket.lastSeenAt);
      const status = ticket.status || "N/A";
      const runUrl = ticket.runUrl || "";

      return `
        <article class="ticket-card">
          <div>
            <h2 class="ticket-card__title">${escapeHtml(title)}</h2>

            <div class="ticket-card__meta">
              ${createMetaRow("Ticket ID", ticketId)}
              ${createMetaRow("Repository", repo)}
              ${createMetaRow("Workflow", workflowName)}
              ${createMetaRow("Job", jobName)}
              ${createMetaRow("Severity", severity)}
              ${createMetaRow("Status", status)}
              ${createMetaRow("Occurrences", String(occurrenceCount))}
              ${createMetaRow("Last Seen", lastSeenAt)}
              ${
                runUrl
                  ? `<div><span class="ticket-card__label">Run URL:</span> <a class="ticket-card__link" href="${escapeHtml(
                      runUrl
                    )}" target="_blank" rel="noopener noreferrer">Open run</a></div>`
                  : ""
              }
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

async function fetchTickets() {
  const apiBaseUrl = getApiBaseUrl();

  if (!apiBaseUrl || apiBaseUrl === "https://ol54oe1gs9.execute-api.eu-west-2.amazonaws.com") {
    setStatusMessage("Missing API base URL injection for frontend build.");
    renderEmptyState();
    return;
  }

  elements.columnTitle.textContent =
    currentView === "open" ? "Open Tickets" : "Closed Tickets";

  setStatusMessage(
    currentView === "open"
      ? "Loading open tickets..."
      : "Loading closed tickets..."
  );

  try {
    const response = await fetch(
      `${apiBaseUrl}/todos?status=${encodeURIComponent(currentView)}`
    );

    if (!response.ok) {
      throw new Error(`GET /todos failed with status ${response.status}`);
    }

    const payload = await response.json();
    const tickets = Array.isArray(payload) ? payload : payload.items || [];

    renderTickets(tickets);

    setStatusMessage(
      currentView === "open"
        ? "Open tickets loaded successfully."
        : "Closed tickets loaded successfully."
    );
  } catch (error) {
    console.error("Failed to fetch tickets:", error);
    setStatusMessage(
      `Unable to load tickets. Check browser console. ${error.message}`
    );
    elements.ticketBoard.innerHTML = `
      <div class="empty-state">Failed to load tickets.</div>
    `;
  }
}

function setActiveView(view) {
  currentView = view;

  if (view === "open") {
    elements.openViewButton.classList.add("active");
    elements.closedViewButton.classList.remove("active");
  } else {
    elements.closedViewButton.classList.add("active");
    elements.openViewButton.classList.remove("active");
  }

  fetchTickets();
}

function registerEventListeners() {
  elements.openViewButton.addEventListener("click", () => setActiveView("open"));
  elements.closedViewButton.addEventListener("click", () => setActiveView("done"));
  elements.refreshButton.addEventListener("click", fetchTickets);
}

function init() {
  registerEventListeners();
  fetchTickets();
}

init();
