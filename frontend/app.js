const API_BASE_URL = "__WORKFLOW_ENDPOINT__";

const elements = {
    todoTasks: document.getElementById("todo-tasks"),
    inprogressTasks: document.getElementById("inprogress-tasks"),
    doneTasks: document.getElementById("done-tasks"),
    todoCount: document.getElementById("todo-count"),
    inprogressCount: document.getElementById("inprogress-count"),
    doneCount: document.getElementById("done-count"),
    refreshButton: document.getElementById("refreshButton"),
    statusMessage: document.getElementById("statusMessage"),
    detailModal: document.getElementById("detailModal"),
    modalContent: document.getElementById("modalContent"),
    closeModalButton: document.getElementById("closeModalButton"),
    modalBackdrop: document.getElementById("modalBackdrop")
};

function setStatus(msg) {
    elements.statusMessage.textContent = msg;
}

function getApiBaseUrl() {
    return API_BASE_URL.replace(/\/$/, "");
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

// --- Drag and Drop ---
window.allowDrop = (event) => {
    event.preventDefault();
};

window.drag = (event) => {
    event.dataTransfer.setData("text/plain", event.currentTarget.id);
};

window.drop = async (event, newColumn) => {
    event.preventDefault();

    const ticketId = event.dataTransfer.getData("text/plain");
    if (!ticketId) {
        return;
    }

    if (newColumn === "done") {
        await updateTicketOnServer(ticketId, {
            status: "done"
        });
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
    const apiBaseUrl = getApiBaseUrl();

    if (!apiBaseUrl || apiBaseUrl === "__WORKFLOW_ENDPOINT__") {
        setStatus("Missing API base URL injection for frontend build.");
        return;
    }

    setStatus("Loading board...");

    try {
        const response = await fetch(`${apiBaseUrl}/todos`);

        if (!response.ok) {
            throw new Error(`GET /todos failed with status ${response.status}`);
        }

        const payload = await response.json();
        const tickets = Array.isArray(payload) ? payload : payload.items || [];

        renderBoard(tickets);
        setStatus("Board up to date.");
    } catch (error) {
        console.error("Failed to fetch tickets:", error);
        setStatus(`Error loading tickets. ${error.message}`);
    }
}

async function updateTicketOnServer(id, patchBody) {
    const apiBaseUrl = getApiBaseUrl();

    if (!apiBaseUrl || apiBaseUrl === "__WORKFLOW_ENDPOINT__") {
        setStatus("Missing API base URL injection for frontend build.");
        return;
    }

    setStatus(`Updating ${id}...`);

    try {
        const response = await fetch(
            `${apiBaseUrl}/todos/${encodeURIComponent(id)}`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(patchBody)
            }
        );

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
function renderBoard(tickets) {
    elements.todoTasks.innerHTML = "";
    elements.inprogressTasks.innerHTML = "";
    elements.doneTasks.innerHTML = "";

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
        card.draggable = true;
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

        card.innerHTML = `
            <div class="task__top-row">
                <h3 class="ticket-card__title">${summary}</h3>
                <span class="task__badge">${badgeText}</span>
            </div>
            <small class="task__repo">${repo}</small>
        `;

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
    elements.closeModalButton.onclick = closeModal;
    elements.modalBackdrop.onclick = closeModal;

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeModal();
        }
    });

    fetchTickets();
}

init();