const API_BASE_URL = "__WORKFLOW_ENDPOINT__";

const elements = {
  viewSelect: document.getElementById("viewSelect"),
  refreshButton: document.getElementById("refreshButton"),
  statusMessage: document.getElementById("statusMessage"),
  ticketBoard: document.getElementById("ticketBoard"),
  columnTitle: document.getElementById("columnTitle"),
  ticketCountBadge: document.getElementById("ticketCountBadge"),
  detailModal: document.getElementById("detailModal"),
  modalBackdrop: document.getElementById("modalBackdrop"),
  closeModalButton: document.getElementById("closeModalButton"),
  modalContent: document.getElementById("modalContent"),
};

let currentView = "open";
let cachedClosedTickets = [];

function getApiBaseUrl() {
  return API_BASE_URL.trim().replace(/\/$/, "");
}

function setStatusMessage(message) {
  elements.statusMessage.textContent = message;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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

function normaliseOpenStatus(ticket) {
  const rawStatus = String(ticket.status || "").toLowerCase();

  if (rawStatus === "in progress" || rawStatus === "in_progress") {
    return "in progress";
  }

  return "to-do";
}

function renderEmptyState() {
  const message =
    currentView === "open" ? "No open tickets found." : "No closed tickets found.";

  elements.ticketCountBadge.textContent = "0";
  elements.ticketBoard.innerHTML = `<div class="empty-state">${message}</div>`;
}

function renderOpenTickets(tickets) {
  elements.ticketCountBadge.textContent = String(tickets.length);

  if (!Array.isArray(tickets) || tickets.length === 0) {
    renderEmptyState();
    return;
  }

  elements.ticketBoard.innerHTML = tickets
    .map((ticket) => {
      const ticketId = ticket.id || "";
      const title = ticket.summary || ticket.title || "Untitled ticket";
      const repo = ticket.repo || "N/A";
      const workflowName = ticket.workflowName || "N/A";
      const jobName = ticket.jobName || "N/A";
      const occurrenceCount = ticket.occurrenceCount ?? "N/A";
      const lastSeenAt = formatDate(ticket.lastSeenAt);
      const displayStatus = normaliseOpenStatus(ticket);

      return `
        <article class="ticket-card ticket-card--open">
          <div class="ticket-card__main">
            <h2 class="ticket-card__title">${escapeHtml(title)}</h2>

            <div class="ticket-card__meta">
              <div><span class="ticket-card__label">Repository:</span>${escapeHtml(repo)}</div>
              <div><span class="ticket-card__label">Workflow:</span>${escapeHtml(workflowName)}</div>
              <div><span class="ticket-card__label">Job:</span>${escapeHtml(jobName)}</div>
              <div><span class="ticket-card__label">Occurrences:</span>${escapeHtml(String(occurrenceCount))}</div>
              <div><span class="ticket-card__label">Last Seen:</span>${escapeHtml(lastSeenAt)}</div>
            </div>
          </div>

          <div class="ticket-card__status-block">
            <div class="ticket-card__status-pill">${escapeHtml(displayStatus)}</div>
            <button
              class="ticket-card__button"
              type="button"
              onclick="markTicketDone('${escapeHtml(ticketId)}')"
            >
              Done
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderClosedTickets(tickets) {
  cachedClosedTickets = tickets;
  elements.ticketCountBadge.textContent = String(tickets.length);

  if (!Array.isArray(tickets) || tickets.length === 0) {
    renderEmptyState();
    return;
  }

  elements.ticketBoard.innerHTML = tickets
    .map((ticket, index) => {
      const title = ticket.summary || ticket.title || "Untitled ticket";
      const details = ticket.details || "No further details available.";
      const repo = ticket.repo || "N/A";
      const workflowName = ticket.workflowName || "N/A";
      const lastSeenAt = formatDate(ticket.lastSeenAt);

      return `
        <article
          class="ticket-card ticket-card--closed"
          role="button"
          tabindex="0"
          onclick="openClosedTicketDetail(${index})"
          onkeydown="handleClosedCardKeydown(event, ${index})"
        >
          <div class="ticket-card__main">
            <h2 class="ticket-card__title">${escapeHtml(title)}</h2>
            <p class="ticket-card__summary">${escapeHtml(details)}</p>

            <div class="ticket-card__meta">
              <div><span class="ticket-card__label">Repository:</span>${escapeHtml(repo)}</div>
              <div><span class="ticket-card__label">Workflow:</span>${escapeHtml(workflowName)}</div>
              <div><span class="ticket-card__label">Closed Status:</span>done</div>
              <div><span class="ticket-card__label">Last Seen:</span>${escapeHtml(lastSeenAt)}</div>
            </div>

            <div class="ticket-card__hint">Click to view more details.</div>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderTickets(tickets) {
  if (currentView === "open") {
    renderOpenTickets(tickets);
    return;
  }

  renderClosedTickets(tickets);
}

async function fetchTickets() {
  const apiBaseUrl = getApiBaseUrl();

  if (!apiBaseUrl || apiBaseUrl === "__WORKFLOW_ENDPOINT__") {
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
    renderEmptyState();
  }
}

async function markTicketDone(ticketId) {
  const apiBaseUrl = getApiBaseUrl();

  if (!ticketId) {
    setStatusMessage("Missing ticket id.");
    return;
  }

  if (!apiBaseUrl || apiBaseUrl === "__WORKFLOW_ENDPOINT__") {
    setStatusMessage("Missing API base URL injection for frontend build.");
    return;
  }

  setStatusMessage(`Marking ticket ${ticketId} as done...`);

  try {
    const response = await fetch(`${apiBaseUrl}/todos/${encodeURIComponent(ticketId)}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status: "done" }),
    });

    if (!response.ok) {
      throw new Error(`PATCH /todos/{id} failed with status ${response.status}`);
    }

    setStatusMessage(`Ticket ${ticketId} marked as done.`);
    await fetchTickets();
  } catch (error) {
    console.error("Failed to update ticket:", error);
    setStatusMessage(
      `Unable to mark ticket done. Check browser console and API logs. ${error.message}`
    );
  }
}

function openClosedTicketDetail(index) {
  const ticket = cachedClosedTickets[index];

  if (!ticket) {
    return;
  }

  const runUrl = ticket.runUrl || "";
  const details = ticket.details || "No further details available.";

  elements.modalContent.innerHTML = `
    <div class="modal__row">
      <span class="modal__row-label">Summary</span>
      <div class="modal__row-value">${escapeHtml(ticket.summary || ticket.title || "Untitled ticket")}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Details</span>
      <div class="modal__row-value">${escapeHtml(details)}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Repository</span>
      <div class="modal__row-value">${escapeHtml(ticket.repo || "N/A")}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Workflow</span>
      <div class="modal__row-value">${escapeHtml(ticket.workflowName || "N/A")}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Job</span>
      <div class="modal__row-value">${escapeHtml(ticket.jobName || "N/A")}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Severity</span>
      <div class="modal__row-value">${escapeHtml(ticket.severity || "N/A")}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Occurrences</span>
      <div class="modal__row-value">${escapeHtml(String(ticket.occurrenceCount ?? "N/A"))}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Last Seen</span>
      <div class="modal__row-value">${escapeHtml(formatDate(ticket.lastSeenAt))}</div>
    </div>

    <div class="modal__row">
      <span class="modal__row-label">Run URL</span>
      <div class="modal__row-value">
        ${
          runUrl
            ? `<a class="modal__link" href="${escapeHtml(runUrl)}" target="_blank" rel="noopener noreferrer">Open workflow run</a>`
            : "N/A"
        }
      </div>
    </div>
  `;

  elements.detailModal.classList.remove("hidden");
}

function closeModal() {
  elements.detailModal.classList.add("hidden");
}

function handleClosedCardKeydown(event, index) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openClosedTicketDetail(index);
  }
}

function registerEventListeners() {
  elements.viewSelect.addEventListener("change", (event) => {
    currentView = event.target.value;
    fetchTickets();
  });

  elements.refreshButton.addEventListener("click", fetchTickets);
  elements.closeModalButton.addEventListener("click", closeModal);
  elements.modalBackdrop.addEventListener("click", closeModal);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeModal();
    }
  });
}

function init() {
  registerEventListeners();
  fetchTickets();
}

window.markTicketDone = markTicketDone;
window.openClosedTicketDetail = openClosedTicketDetail;
window.handleClosedCardKeydown = handleClosedCardKeydown;

init();