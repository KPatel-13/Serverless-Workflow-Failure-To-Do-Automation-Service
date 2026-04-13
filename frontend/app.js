const API_BASE_URL = "__API_BASE_URL__";

const elements = {
  todoColumn: document.getElementById("todo-column"),
  inProgressColumn: document.getElementById("in-progress-column"),
  doneColumn: document.getElementById("done-column"),
  todoTasks: document.getElementById("todo-tasks"),
  inprogressTasks: document.getElementById("inprogress-tasks"),
  doneTasks: document.getElementById("done-tasks"),
  todoCount: document.getElementById("todo-count"),
  inprogressCount: document.getElementById("inprogress-count"),
  doneCount: document.getElementById("done-count"),
  refreshButton: document.getElementById("refreshButton"),
  statusMessage: document.getElementById("statusMessage"),
  viewSelect: document.getElementById("viewSelect"),
  detailModal: document.getElementById("detailModal"),
  modalContent: document.getElementById("modalContent"),
  closeModalButton: document.getElementById("closeModalButton"),
  modalBackdrop: document.getElementById("modalBackdrop"),
};

let currentView = "open";

function setStatus(message) {
  elements.statusMessage.textContent = message;
}

function getApiBaseUrl() {
  const value = String(API_BASE_URL || "").trim().replace(/\/$/, "");
  if (!value || value === "__API_BASE_URL__") {
    throw new Error("Frontend API base URL has not been injected");
  }
  return value;
}

function escapeHtml(value) {
  return String(value ?? "")
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

function updateBoardLayout() {
  if (currentView === "open") {
    elements.todoColumn.style.display = "block";
    elements.inProgressColumn.style.display = "block";
    elements.doneColumn.style.display = "none";
    return;
  }

  elements.todoColumn.style.display = "none";
  elements.inProgressColumn.style.display = "none";
  elements.doneColumn.style.display = "block";
}

// --- Drag and Drop ---

window.allowDrop = (event) => {
  event.preventDefault();
};

window.drag = (event) => {
  event.dataTransfer.setData("text/plain", event.currentTarget.id);
};

window.drop = async (event, newColumn) => {
  event.preventDefault();

  if (currentView !== "open") {
    return;
  }

  const ticketId = event.dataTransfer.getData("text/plain");
  if (!ticketId) {
    return;
  }

  if (newColumn === "done") {
    await updateTicketOnServer(ticketId, { status: "done" });
    return;
  }

  const workflowState = newColumn === "in-progress" ? "in_progress" : "todo";
  await updateTicketOnServer(ticketId, { status: "open", workflowState });
};

// --- API Calls ---

async function fetchTickets() {
  let apiBaseUrl;

  try {
    apiBaseUrl = getApiBaseUrl();
  } catch (error) {
    setStatus(error.message);
    clearBoard();
    updateBoardLayout();
    return;
  }

  setStatus(currentView === "open" ? "Loading open tickets..." : "Loading closed tickets...");

  try {
    const statusFilter = currentView === "open" ? "open" : "done";
    const requestUrl = `${apiBaseUrl}/todos?status=${encodeURIComponent(statusFilter)}`;

    const response = await fetch(requestUrl);

    if (!response.ok) {
      throw new Error(`GET /todos failed with status ${response.status}`);
    }

    const payload = await response.json();
    const tickets = Array.isArray(payload) ? payload : payload.items || [];

    renderBoard(tickets);
    updateBoardLayout();
    setStatus(currentView === "open" ? "Open board up to date." : "Closed board up to date.");
  } catch (error) {
    console.error("Failed to fetch tickets:", error);
    setStatus(`Error loading tickets. ${error.message}`);
    clearBoard();
    updateBoardLayout();
  }
}

async function updateTicketOnServer(id, patchBody) {
  let apiBaseUrl;

  try {
    apiBaseUrl = getApiBaseUrl();
  } catch (error) {
    setStatus(error.message);
    return;
  }

  setStatus(`Updating ${id}...`);

  try {
    const requestUrl = `${apiBaseUrl}/todos/${encodeURIComponent(id)}`;
    const response = await fetch(requestUrl, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patchBody),
    });

    if (!response.ok) {
      throw new Error(`PATCH /todos/{id} failed with status ${response.status}`);
    }

    setStatus("Saved.");
    await fetchTickets();
  } catch (error) {
    console.error("Failed to update ticket:", error);
    setStatus(`Failed to save move. ${error.message}`);
  }
}

function clearBoard() {
  elements.todoTasks.innerHTML = "";
  elements.inprogressTasks.innerHTML = "";
  elements.doneTasks.innerHTML = "";

  elements.todoCount.textContent = "0";
  elements.inprogressCount.textContent = "0";
  elements.doneCount.textContent = "0";
}

function openModal(ticket) {
  elements.modalContent.innerHTML = `
    <h2>${escapeHtml(ticket.title || "Ticket details")}</h2>
    <p><strong>Repo:</strong> ${escapeHtml(ticket.repo || "N/A")}</p>
    <p><strong>Workflow:</strong> ${escapeHtml(ticket.workflowName || "N/A")}</p>
    <p><strong>Job:</strong> ${escapeHtml(ticket.jobName || "N/A")}</p>
    <p><strong>Status:</strong> ${escapeHtml(ticket.status || "N/A")}</p>
    <p><strong>Workflow state:</strong> ${escapeHtml(ticket.workflowState || "N/A")}</p>
    <p><strong>Severity:</strong> ${escapeHtml(ticket.severity || "N/A")}</p>
    <p><strong>Occurrences:</strong> ${escapeHtml(ticket.occurrenceCount || 0)}</p>
    <p><strong>First seen:</strong> ${escapeHtml(formatDate(ticket.firstSeenAt))}</p>
    <p><strong>Last seen:</strong> ${escapeHtml(formatDate(ticket.lastSeenAt))}</p>
    <p><strong>Updated:</strong> ${escapeHtml(formatDate(ticket.updatedAt))}</p>
    <p><strong>Resolved:</strong> ${escapeHtml(formatDate(ticket.resolvedAt))}</p>
    <p><strong>Summary:</strong> ${escapeHtml(ticket.summary || "N/A")}</p>
    <p><strong>Details:</strong> ${escapeHtml(ticket.details || "N/A")}</p>
    ${
      ticket.runUrl
        ? `<p><strong>Run:</strong> <a href="${escapeHtml(ticket.runUrl)}" target="_blank" rel="noopener noreferrer">Open run</a></p>`
        : ""
    }
  `;

  elements.detailModal.classList.remove("hidden");
}

function closeModal() {
  elements.detailModal.classList.add("hidden");
}

function createTicketCard(ticket) {
  const card = document.createElement("div");
  card.className = "ticket-card";
  card.id = ticket.id;
  card.draggable = currentView === "open";
  card.addEventListener("dragstart", window.drag);
  card.addEventListener("click", () => openModal(ticket));

  card.innerHTML = `
    <div class="ticket-card-header">
      <span class="ticket-title">${escapeHtml(ticket.title || "Untitled ticket")}</span>
      <span class="ticket-badge">${escapeHtml(ticket.severity || "n/a")}</span>
    </div>
    <div class="ticket-meta">${escapeHtml(ticket.jobName || "Unknown job")}</div>
    <div class="ticket-meta">Occurrences: ${escapeHtml(ticket.occurrenceCount || 0)}</div>
    <div class="ticket-meta">Last seen: ${escapeHtml(formatDate(ticket.lastSeenAt))}</div>
  `;

  return card;
}

function renderBoard(tickets) {
  clearBoard();

  const todoTickets = [];
  const inProgressTickets = [];
  const doneTickets = [];

  for (const ticket of tickets) {
    if (ticket.status === "done") {
      doneTickets.push(ticket);
      continue;
    }

    if (ticket.workflowState === "in_progress") {
      inProgressTickets.push(ticket);
      continue;
    }

    todoTickets.push(ticket);
  }

  for (const ticket of todoTickets) {
    elements.todoTasks.appendChild(createTicketCard(ticket));
  }

  for (const ticket of inProgressTickets) {
    elements.inprogressTasks.appendChild(createTicketCard(ticket));
  }

  for (const ticket of doneTickets) {
    elements.doneTasks.appendChild(createTicketCard(ticket));
  }

  elements.todoCount.textContent = String(todoTickets.length);
  elements.inprogressCount.textContent = String(inProgressTickets.length);
  elements.doneCount.textContent = String(doneTickets.length);
}

elements.refreshButton.addEventListener("click", () => {
  fetchTickets();
});

elements.viewSelect.addEventListener("change", (event) => {
  currentView = event.target.value;
  fetchTickets();
});

elements.closeModalButton.addEventListener("click", closeModal);
elements.modalBackdrop.addEventListener("click", closeModal);

fetchTickets();