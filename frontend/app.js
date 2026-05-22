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
    modalBackdrop: document.getElementById("modalBackdrop")
};

let currentView = "open";

function setStatus(message) {
    elements.statusMessage.textContent = message;
}

function getApiBaseUrl() {
    return String(API_BASE_URL || "").trim().replace(/\/$/, "");
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

    await updateTicketOnServer(ticketId, {
        status: "open",
        workflowState
    });
};

// --- API Calls ---
async function fetchTickets() {
    console.log("DEBUG fetchTickets started");

    const apiBaseUrl = getApiBaseUrl();
    console.log("DEBUG apiBaseUrl inside fetchTickets:", apiBaseUrl);

    if (!apiBaseUrl) {
        setStatus("Missing API base URL.");
        clearBoard();
        updateBoardLayout();
        return;
    }

    setStatus(currentView === "open" ? "Loading open tickets..." : "Loading closed tickets...");

    try {
        const statusFilter = currentView === "open" ? "open" : "done";
        const requestUrl = `${apiBaseUrl}/todos?status=${encodeURIComponent(statusFilter)}`;

        console.log("DEBUG about to fetch:", requestUrl);

        const response = await fetch(requestUrl);

        console.log("DEBUG fetch response status:", response.status);

        if (!response.ok) {
            throw new Error(`GET /todos failed with status ${response.status}`);
        }

        const payload = await response.json();
        const tickets = Array.isArray(payload) ? payload : payload.items || [];

        console.log("DEBUG tickets loaded:", tickets);

        renderBoard(tickets);
        updateBoardLayout();
        setStatus(currentView === "open" ? "Open ticket board up to date." : "Closed ticket board up to date.");
    } catch (error) {
        console.error("Failed to fetch tickets:", error);
        setStatus(`Error loading tickets. ${error.message}`);
        clearBoard();
        updateBoardLayout();
    }
}

async function updateTicketOnServer(id, patchBody) {
    const apiBaseUrl = getApiBaseUrl();

    if (!apiBaseUrl) {
        setStatus("Missing API base URL.");
        return;
    }

    setStatus(`Updating ${id}...`);

    try {
        const requestUrl = `${apiBaseUrl}/todos/${encodeURIComponent(id)}`;

        console.log("DEBUG patch URL:", requestUrl);
        console.log("DEBUG patch body:", patchBody);

        const response = await fetch(requestUrl, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(patchBody)
        });

        console.log("DEBUG patch response status:", response.status);

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

// --- Rendering ---
function clearBoard() {
    elements.todoTasks.innerHTML = "";
    elements.inprogressTasks.innerHTML = "";
    elements.doneTasks.innerHTML = "";
    elements.todoCount.textContent = "0";
    elements.inprogressCount.textContent = "0";
    elements.doneCount.textContent = "0";
}

function renderBoard(tickets) {
    clearBoard();

    const counts = {
        todo: 0,
        in_progress: 0,
        done: 0
    };

    tickets.forEach((ticket) => {
        const lifecycleStatus = String(ticket.status || "open").toLowerCase();
        const workflowState = String(ticket.workflowState || "todo").toLowerCase();

        const card = document.createElement("article");
        card.className = "task";
        card.id = ticket.id;
        card.draggable = currentView === "open";
        card.addEventListener("dragstart", window.drag);
        card.addEventListener("click", () => openModal(ticket));

        const summary = escapeHtml(ticket.summary || ticket.title || "Untitled ticket");
        const repo = escapeHtml(ticket.repo || "No Repo");
        const badgeText =
            lifecycleStatus === "done"
                ? "Closed"
                : workflowState === "in_progress"
                ? "In Progress"
                : "To Do";

        const showDoneButton = lifecycleStatus !== "done";

        card.innerHTML = `
            <div class="task__top-row">
                <h3 class="ticket-card__title">${summary}</h3>
                <span class="task__badge">${badgeText}</span>
            </div>
            <small class="task__repo">${repo}</small>
            ${
                showDoneButton
                    ? `<div class="task__actions">
                           <button class="task__done-button" type="button" data-ticket-id="${escapeHtml(ticket.id)}">
                               Mark Done
                           </button>
                       </div>`
                    : ""
            }
        `;

        const doneButton = card.querySelector(".task__done-button");
        if (doneButton) {
            doneButton.addEventListener("click", async (event) => {
                event.stopPropagation();
                await updateTicketOnServer(ticket.id, { status: "done" });
            });
        }

        if (lifecycleStatus === "done") {
            elements.doneTasks.appendChild(card);
            counts.done += 1;
            return;
        }

        if (workflowState === "in_progress") {
            elements.inprogressTasks.appendChild(card);
            counts.in_progress += 1;
            return;
        }

        elements.todoTasks.appendChild(card);
        counts.todo += 1;
    });

    elements.todoCount.textContent = String(counts.todo);
    elements.inprogressCount.textContent = String(counts.in_progress);
    elements.doneCount.textContent = String(counts.done);
}

// --- Modal ---
function openModal(ticket) {
    const runUrl = ticket.runUrl
        ? `<a href="${escapeHtml(ticket.runUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(ticket.runUrl)}</a>`
        : "N/A";

    elements.modalContent.innerHTML = `
        <p><strong>Summary:</strong> ${escapeHtml(ticket.summary || ticket.title || "Untitled ticket")}</p>
        <p><strong>Repository:</strong> ${escapeHtml(ticket.repo || "N/A")}</p>
        <p><strong>Workflow:</strong> ${escapeHtml(ticket.workflowName || "N/A")}</p>
        <p><strong>Job:</strong> ${escapeHtml(ticket.jobName || "N/A")}</p>
        <p><strong>Status:</strong> ${escapeHtml(ticket.status || "N/A")}</p>
        <p><strong>Board State:</strong> ${escapeHtml(ticket.workflowState || "todo")}</p>
        <p><strong>Occurrences:</strong> ${escapeHtml(ticket.occurrenceCount ?? "N/A")}</p>
        <p><strong>Last Seen:</strong> ${escapeHtml(formatDate(ticket.lastSeenAt))}</p>
        <p><strong>Details:</strong> ${escapeHtml(ticket.details || "N/A")}</p>
        <p><strong>Run URL:</strong> ${runUrl}</p>
    `;

    elements.detailModal.classList.remove("hidden");
}

function closeModal() {
    elements.detailModal.classList.add("hidden");
}

function init() {
    elements.refreshButton.onclick = fetchTickets;
    elements.viewSelect.onchange = (event) => {
        currentView = event.target.value;
        fetchTickets();
    };
    elements.closeModalButton.onclick = closeModal;
    elements.modalBackdrop.onclick = closeModal;

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeModal();
        }
    });

    updateBoardLayout();
    fetchTickets();
}

init();