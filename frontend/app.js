/* ==========================================================================
   AskTheCompany — Sleek RAG Controller JS
   ========================================================================== */

// User to Roles & Profile Mapping from permissions.json
const USER_PROFILES = {
    alice: { name: "Alice Chen", title: "Senior Engineer", roles: ["engineering", "all"] },
    bob: { name: "Bob Martinez", title: "VP Product", roles: ["product", "exec", "all"] },
    carol: { name: "Carol Williams", title: "HR Manager", roles: ["hr", "all"] },
    dave: { name: "Dave Kumar", title: "Finance Analyst", roles: ["finance", "all"] },
    frank: { name: "Frank Intern", title: "Summer Intern", roles: ["all"] }
};

// DOM Cache
const userSwitcher = document.getElementById("user-switcher");
const activeRolesContainer = document.getElementById("active-roles");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const latencyBadge = document.getElementById("latency-badge");
const latencyVal = document.getElementById("latency-val");
const rewritesContainer = document.getElementById("rewrites-container");
const rewritesTrigger = document.getElementById("rewrites-trigger");
const rewritesBody = document.getElementById("rewrites-body");
const citationsList = document.getElementById("citations-list");
const reingestBtn = document.getElementById("reingest-btn");
const toast = document.getElementById("toast");

let currentCitations = [];

// Init Startup State
document.addEventListener("DOMContentLoaded", () => {
    updateActiveUserUI(userSwitcher.value);
    
    // Toggle rewrites list
    rewritesTrigger.addEventListener("click", () => {
        rewritesContainer.classList.toggle("expanded");
    });

    // Switched user dropdown callback
    userSwitcher.addEventListener("change", (e) => {
        updateActiveUserUI(e.target.value);
        showToast(`Switched context to ${USER_PROFILES[e.target.value].name}`);
    });

    // Ingest trigger
    reingestBtn.addEventListener("click", triggerReingest);

    // Form submit query trigger
    chatForm.addEventListener("submit", handleQuerySubmit);
});

// Toast notification helper
function showToast(message, duration = 3000) {
    toast.innerHTML = `<i class="fa-solid fa-circle-info"></i> ${message}`;
    toast.classList.remove("hidden");
    
    setTimeout(() => {
        toast.classList.add("hidden");
    }, duration);
}

// Update Active roles badge matching select option
function updateActiveUserUI(username) {
    const profile = USER_PROFILES[username];
    activeRolesContainer.innerHTML = "";
    profile.roles.forEach(role => {
        const badge = document.createElement("span");
        badge.className = `role-badge ${role}`;
        badge.innerText = role;
        activeRolesContainer.appendChild(badge);
    });
}

// Ingest trigger handler
async function triggerReingest() {
    reingestBtn.disabled = true;
    reingestBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Ingesting...`;
    showToast("Starting local directory document ingestion...");
    
    try {
        const resp = await fetch("/api/v1/ingest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                data_dir: "./data",
                recreate_collection: true
            })
        });
        
        if (resp.ok) {
            const data = await resp.json();
            showToast(`Ingestion complete! Canonical chunks: ${data.canonical_count}`);
        } else {
            showToast("Error during ingestion pipeline execution.");
        }
    } catch (e) {
        showToast("Backend connection failed.");
    } finally {
        reingestBtn.disabled = false;
        reingestBtn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Re-ingest Index`;
    }
}

// Handle Form query submissions
async function handleQuerySubmit(e) {
    e.preventDefault();
    const queryText = userInput.value.trim();
    if (!queryText) return;
    
    const activeUser = userSwitcher.value;
    
    // Add user message bubble
    appendMessage("user", queryText);
    userInput.value = "";
    
    // Show typing loader
    const loaderId = appendTypingLoader();
    
    // Hide old latency & variants
    latencyBadge.classList.add("hidden");
    rewritesContainer.classList.add("hidden");
    rewritesContainer.classList.remove("expanded");
    
    try {
        const resp = await fetch("/api/v1/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: queryText,
                username: activeUser,
                top_k: 3
            })
        });
        
        // Remove typing loader
        removeMessage(loaderId);
        
        if (resp.ok) {
            const data = await resp.json();
            
            // Format answer with styled interactive citation links [N]
            const formattedAnswer = parseIntextCitations(data.answer);
            
            // Render bot answer
            appendMessage("assistant", formattedAnswer, true);
            
            // Show latency metric
            latencyVal.innerText = `${data.elapsed_ms ? Math.round(data.elapsed_ms) : 0}ms`;
            latencyBadge.classList.remove("hidden");
            
            // Render expanded query rewrites
            if (data.query_variants && data.query_variants.length > 0) {
                renderQueryVariants(data.query_variants);
            }
            
            // Render citation cards
            currentCitations = data.citations || [];
            renderCitationCards(currentCitations);
            
            // Wire dynamic hover highlights & clicks
            wireCitationEventHandlers();
            
        } else {
            appendMessage("assistant", "Sorry, the server returned an error while processing your request.");
        }
    } catch (e) {
        removeMessage(loaderId);
        appendMessage("assistant", "Failed to connect to the backend server. Make sure uvicorn is running.");
    }
}

// Append Chat bubble
function appendMessage(sender, htmlContent, isHtml = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}-message`;
    msgDiv.id = `msg-${Date.now()}`;
    
    const icon = sender === "user" ? "fa-user" : "fa-robot";
    
    msgDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid ${icon}"></i></div>
        <div class="message-content">
            ${isHtml ? htmlContent : `<p>${escapeHtml(htmlContent)}</p>`}
        </div>
    `;
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv.id;
}

// Append typing dot animations
function appendTypingLoader() {
    const loaderDiv = document.createElement("div");
    loaderDiv.className = "message assistant-message loader-message";
    loaderDiv.id = `loader-${Date.now()}`;
    
    loaderDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;
    
    chatMessages.appendChild(loaderDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return loaderDiv.id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// Render query expanded accordion list
function renderQueryVariants(variants) {
    rewritesBody.innerHTML = "";
    variants.forEach(variant => {
        const item = document.createElement("div");
        item.className = "rewrite-item";
        item.innerHTML = `<i class="fa-solid fa-circle"></i> <span>"${escapeHtml(variant)}"</span>`;
        rewritesBody.appendChild(item);
    });
    rewritesContainer.classList.remove("hidden");
}

// Render right side panel source cards
function renderCitationCards(citations) {
    citationsList.innerHTML = "";
    
    if (citations.length === 0) {
        citationsList.innerHTML = `
            <div class="empty-citations">
                <i class="fa-solid fa-folder-open"></i>
                <p>No sources referenced for the current answer.</p>
            </div>
        `;
        return;
    }
    
    citations.forEach(cit => {
        const card = document.createElement("div");
        card.className = "citation-card";
        card.id = `cit-card-${cit.index}`;
        card.setAttribute("data-index", cit.index);
        
        // Truncate path
        const pathText = cit.heading_path ? cit.heading_path : `${cit.title} doc`;
        
        card.innerHTML = `
            <div class="citation-card-header">
                <div class="citation-source">
                    <span class="icon">${cit.icon || "📎"}</span>
                    <span>${escapeHtml(cit.title)}</span>
                </div>
                <div class="citation-badge">[${cit.index}]</div>
            </div>
            <div class="citation-path" title="${escapeHtml(pathText)}">${escapeHtml(pathText)}</div>
            <div class="citation-snippet">"${escapeHtml(cit.content_snippet)}"</div>
            <div class="citation-card-footer">
                <div class="citation-score">
                    <i class="fa-solid fa-square-poll-vertical"></i> 
                    <span>Score: ${cit.score ? cit.score.toFixed(3) : "N/A"}</span>
                </div>
                <div class="citation-acls">
                    ${(cit.acls || []).map(acl => `<span class="citation-acl-badge">${escapeHtml(acl)}</span>`).join("")}
                </div>
            </div>
        `;
        
        citationsList.appendChild(card);
    });
}

// Parse inline bracket tags like [1] or [2] into styled active anchor links
function parseIntextCitations(text) {
    // Regex matches [N] where N is a digit
    const citationRegex = /\[(\d+)\]/g;
    
    // Convert markdown newline characters into HTML paragraph structures first
    let parsedText = text.split("\n\n").map(para => `<p>${escapeHtml(para)}</p>`).join("");
    
    // Replace markdown bold tags too
    parsedText = parsedText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    parsedText = parsedText.replace(/\*(.*?)\*/g, "<em>$1</em>");
    
    // Replace [N] with styled interactive link
    parsedText = parsedText.replace(citationRegex, (match, index) => {
        return `<a class="citation-link" data-index="${index}">[${index}]</a>`;
    });
    
    return parsedText;
}

// Wire cross-hover and cross-click highlighting events
function wireCitationEventHandlers() {
    // 1. In-text citation links
    const links = document.querySelectorAll(".citation-link");
    links.forEach(link => {
        const index = link.getAttribute("data-index");
        const matchingCard = document.getElementById(`cit-card-${index}`);
        
        if (matchingCard) {
            // Hover link -> Highlight Card
            link.addEventListener("mouseenter", () => {
                matchingCard.classList.add("highlighted");
            });
            link.addEventListener("mouseleave", () => {
                matchingCard.classList.remove("highlighted");
            });
            
            // Click link -> Scroll & Flash Card
            link.addEventListener("click", () => {
                matchingCard.scrollIntoView({ behavior: "smooth", block: "center" });
                flashElement(matchingCard);
            });
        }
    });

    // 2. Sidebar citation cards
    const cards = document.querySelectorAll(".citation-card");
    cards.forEach(card => {
        const index = card.getAttribute("data-index");
        const matchingLinks = document.querySelectorAll(`.citation-link[data-index="${index}"]`);
        
        // Hover Card -> Highlight matching links in chat
        card.addEventListener("mouseenter", () => {
            matchingLinks.forEach(lnk => lnk.classList.add("highlighted"));
        });
        card.addEventListener("mouseleave", () => {
            matchingLinks.forEach(lnk => lnk.classList.remove("highlighted"));
        });
        
        // Click Card -> Flash matching links in chat
        card.addEventListener("click", () => {
            matchingLinks.forEach(lnk => {
                lnk.scrollIntoView({ behavior: "smooth", block: "center" });
                flashElement(lnk);
            });
        });
    });
}

// Simple CSS flash helper
function flashElement(el) {
    el.style.transition = "none";
    el.style.backgroundColor = "rgba(139, 92, 246, 0.4)";
    setTimeout(() => {
        el.style.transition = "all 0.6s ease";
        el.style.backgroundColor = "";
    }, 150);
}

// Helper to escape HTML tags to prevent XSS injection
function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
