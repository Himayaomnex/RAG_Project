document.addEventListener("DOMContentLoaded", () => {
    let activeUserID = "USR-OWNER-01";
    let activeRole = "owner";
    let activeName = "System Owner";
    let currentTheme = "light";

    const htmlRoot = document.documentElement;
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const themeIcon = document.getElementById("themeIcon");
    const themeText = document.getElementById("themeText");

    const loginModal = document.getElementById("loginModal");
    const loginUserSelect = document.getElementById("loginUserSelect");
    const loginBtn = document.getElementById("loginBtn");
    const switchUserBtn = document.getElementById("switchUserBtn");
    
    const previewBadge = document.getElementById("previewBadge");
    const previewName = document.getElementById("previewName");
    const previewScope = document.getElementById("previewScope");
    
    const authenticatedRoleText = document.getElementById("authenticatedRoleText");
    const workspaceSubtitle = document.getElementById("workspaceSubtitle");

    const agentCards = document.querySelectorAll(".agent-card");
    const promptInput = document.getElementById("promptInput");
    const submitBtn = document.getElementById("submitBtn");
    const targetMemberSelect = document.getElementById("targetMemberSelect");
    const chipBtns = document.querySelectorAll(".chip-btn");

    const responseSection = document.getElementById("responseSection");
    const resUserID = document.getElementById("resUserID");
    const resAgentName = document.getElementById("resAgentName");
    const resLatency = document.getElementById("resLatency");
    const responseBody = document.getElementById("responseBody");

    const historyList = document.getElementById("historyList");
    const historyCountBadge = document.getElementById("historyCountBadge");

    const roleDetailsMap = {
        "owner": {
            badge: "Role: System Owner",
            scope: "Full Access: Live Demo Mode • Manager, Mentor & Teammates Agents Unlocked",
            displayName: "System Owner Mode"
        },
        "manager": {
            badge: "Role: Executive Manager",
            scope: "Access Scope: Executive Review • Accomplishments, Blockers, Risks & Required Decisions",
            displayName: "Manager Agent (Iyappan Sir)"
        },
        "siddharth": {
            badge: "Role: Technical Mentor",
            scope: "Access Scope: Mentee Evaluation • Technical Strengths, Misconceptions, Scorecards & Quizzes",
            displayName: "Mentor Agent (Siddharth Saminathan)"
        },
        "himaya": {
            badge: "Role: Teammate (Himaya)",
            scope: "Access Scope: Teammate Workspace • Codebase Architecture & Spoken Meeting Excerpts",
            displayName: "Teammates Agent (Himaya Perumal)"
        },
        "ganesh": {
            badge: "Role: Teammate (Ganesh)",
            scope: "Access Scope: Teammate Workspace • Schema Generation & Vector Pipeline Guidance",
            displayName: "Teammates Agent (Ganesh Krishna)"
        },
        "dakshinya": {
            badge: "Role: Teammate (Dakshinya)",
            scope: "Access Scope: Teammate Workspace • MCP Server & Scoping Guidance",
            displayName: "Teammates Agent (Dakshinya Nachimuthu)"
        }
    };

    // Theme Switcher Logic
    themeToggleBtn.addEventListener("click", () => {
        if (currentTheme === "light") {
            currentTheme = "dark";
            htmlRoot.setAttribute("data-theme", "dark");
            themeIcon.textContent = "🌙";
            themeText.textContent = "Dark Mode";
        } else {
            currentTheme = "light";
            htmlRoot.setAttribute("data-theme", "light");
            themeIcon.textContent = "☀️";
            themeText.textContent = "Light Mode";
        }
    });

    // Modal Selector Live Update
    loginUserSelect.addEventListener("change", () => {
        const [userID, role, name] = loginUserSelect.value.split("|");
        const details = roleDetailsMap[role] || {};
        
        previewBadge.textContent = details.badge || `Role: ${role}`;
        previewName.textContent = `${name} (${userID})`;
        previewScope.textContent = details.scope || "Access Scope: General Workspace";
    });

    // Authenticate Button
    loginBtn.addEventListener("click", () => {
        const [userID, role, name] = loginUserSelect.value.split("|");
        activeUserID = userID;
        activeRole = role;
        activeName = name;

        if (role === "owner") {
            authenticatedRoleText.textContent = `👑 Owner Mode (All Agents Unlocked)`;
            workspaceSubtitle.textContent = `System Owner Mode: All 3 Agents Unlocked for Presentation Demo`;
        } else {
            authenticatedRoleText.textContent = `ID: ${activeUserID} • ${activeName} (${role.toUpperCase()})`;
            workspaceSubtitle.textContent = `Workspace locked to ${activeUserID} (${activeName}) access scope.`;
        }

        applyRoleScoping(activeRole);
        loginModal.style.display = "none";
        fetchAgentHistory();
    });

    // Switch User Button
    switchUserBtn.addEventListener("click", () => {
        loginModal.style.display = "flex";
    });

    let selectedAgentRole = "manager";

    agentCards.forEach(card => {
        card.addEventListener("click", () => {
            if (card.classList.contains("disabled")) return;
            agentCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            selectedAgentRole = card.getAttribute("data-role");
            fetchAgentHistory();
        });
    });

    function applyRoleScoping(role) {
        agentCards.forEach(c => {
            c.classList.remove("active", "disabled");
        });

        if (role === "owner") {
            document.getElementById("cardManager").classList.add("active");
            selectedAgentRole = "manager";
        } else if (role === "manager") {
            document.getElementById("cardManager").classList.add("active");
            document.getElementById("cardMentor").classList.add("disabled");
            document.getElementById("cardTeammate").classList.add("disabled");
            selectedAgentRole = "manager";
        } else if (role === "siddharth") {
            document.getElementById("cardMentor").classList.add("active");
            document.getElementById("cardManager").classList.add("disabled");
            document.getElementById("cardTeammate").classList.add("disabled");
            selectedAgentRole = "siddharth";
        } else {
            document.getElementById("cardTeammate").classList.add("active");
            document.getElementById("cardManager").classList.add("disabled");
            document.getElementById("cardMentor").classList.add("disabled");
            selectedAgentRole = "himaya";
        }
    }

    // Benchmark Chips Click — also auto-selects the correct agent card
    chipBtns.forEach(chip => {
        chip.addEventListener("click", () => {
            promptInput.value = chip.getAttribute("data-prompt");

            const agentKey = chip.getAttribute("data-agent");
            if (agentKey) {
                agentCards.forEach(c => c.classList.remove("active"));
                const cardMap = {
                    "manager":   "cardManager",
                    "siddharth": "cardMentor",
                    "himaya":    "cardTeammate",
                    "ganesh":    "cardTeammate",
                    "dakshinya": "cardTeammate",
                    "auto":      "cardAuto"
                };
                const targetCard = document.getElementById(cardMap[agentKey]);
                if (targetCard && !targetCard.classList.contains("disabled")) {
                    targetCard.classList.add("active");
                    selectedAgentRole = agentKey;
                    fetchAgentHistory();
                }
            }
        });
    });

    // Fetch Agent History Logs
    async function fetchAgentHistory() {
        try {
            const roleKey = (activeRole === "owner") ? selectedAgentRole : activeRole;
            const normRole = (roleKey === "siddharth") ? "mentor" : ((roleKey === "himaya" || roleKey === "ganesh" || roleKey === "dakshinya") ? "teammate" : "manager");
            
            const res = await fetch(`/api/v1/history?role=${normRole}`);
            if (!res.ok) return;

            const data = await res.json();
            const logs = data[normRole] || [];

            historyCountBadge.textContent = `${logs.length} Session Logs`;

            if (logs.length === 0) {
                historyList.innerHTML = `<p style="color: var(--text-muted); font-size: 13px;">No history recorded yet for ${normRole.toUpperCase()} agent. Execute a query to save history logs!</p>`;
                return;
            }

            historyList.innerHTML = logs.slice().reverse().map(item => `
                <div class="history-item">
                    <div class="history-meta">
                        <span>🕒 ${item.timestamp} • User: ${item.user_id}</span>
                        <span>⚡ ${item.latency}s</span>
                    </div>
                    <div class="history-prompt">❓ ${escapeHtml(item.prompt)}</div>
                </div>
            `).join("");

        } catch (err) {
            console.error("Error fetching history:", err);
        }
    }

    function escapeHtml(text) {
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function detectIntentRole(text) {
        const lower = text.toLowerCase();
        const mentorKeywords = [
            "evaluate", "mentor", "weakness", "strength", "quiz", "mentee", "score",
            "misconception", "methodology", "problem-solving", "next task", "grading",
            "next tasks", "learning topic", "feedback", "guidance", "diagnosis", "grade",
            "diagnose", "learning gap", "technical gap", "understanding", "coaching"
        ];
        const teammateKeywords = [
            "code", "pipeline", "qdrant", "how works", "explain", "architecture",
            "semantic", "chunking", "embedding", "cachedembedding",
            "semantictranscriptparser", "vector", "retriever", "reranker",
            "transcript parser", "dense", "collection"
        ];
        if (mentorKeywords.some(w => lower.includes(w))) return "siddharth";
        if (teammateKeywords.some(w => lower.includes(w))) return "himaya";
        return "manager";
    }

    function highlightCard(role) {
        agentCards.forEach(c => c.classList.remove("active"));
        const cardMap = {
            "manager": "cardManager",
            "siddharth": "cardMentor",
            "mentor": "cardMentor",
            "himaya": "cardTeammate",
            "ganesh": "cardTeammate",
            "dakshinya": "cardTeammate",
            "teammate": "cardTeammate",
            "auto": "cardAuto"
        };
        const target = document.getElementById(cardMap[role] || "cardManager");
        if (target && !target.classList.contains("disabled")) {
            target.classList.add("active");
        }
    }

    // Auto-detect agent card when user types in Owner mode
    promptInput.addEventListener("input", () => {
        if (activeRole === "owner") {
            const prompt = promptInput.value.trim();
            if (prompt.length > 5) {
                const autoRole = detectIntentRole(prompt);
                highlightCard(autoRole);
                selectedAgentRole = autoRole;
            }
        }
    });

    // Submit on Enter Key Press (Shift+Enter inserts new line)
    promptInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault(); // Prevent default newline character insertion
            submitBtn.click();  // Trigger submit execution
        }
    });

    // Submit Prompt Execution
    submitBtn.addEventListener("click", async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert("Please enter a prompt or select a benchmark prompt chip.");
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>⏳ Executing as ${activeUserID}...</span>`;
        responseSection.style.display = "block";
        responseBody.innerHTML = `<div style="padding: 20px; color: var(--text-secondary);">⚡ Retrieving dense vector chunks & generating Google Gemini LLM grounded response...</div>`;

        const targetMember = targetMemberSelect.value;
        let targetRole = activeRole;
        if (activeRole === "owner") {
            targetRole = selectedAgentRole || detectIntentRole(prompt);
        }
        const endpoint = getEndpointForRole(targetRole);

        try {
            const startTime = performance.now();
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": activeUserID,
                    "X-User-Role": targetRole,
                    "X-User-Name": activeName
                },
                body: JSON.stringify({
                    prompt: prompt,
                    // For owner mode, send empty string so agents auto-resolve mentee from prompt text.
                    // For role-scoped sessions, send the authenticated user's name.
                    target_member: targetMember || (activeRole === "owner" ? "" : activeName)
                })
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `HTTP Error ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const duration = ((performance.now() - startTime) / 1000).toFixed(3);
            const resolvedRole = data.agent_role || targetRole;

            resUserID.textContent = activeUserID;
            resAgentName.textContent = getAgentDisplayName(resolvedRole);
            resLatency.textContent = `${data.latency_seconds || duration}s`;
            if (data.llm_provider) {
                resLLM.textContent = data.llm_provider;
            }

            highlightCard(resolvedRole);

            if (typeof marked !== "undefined") {
                responseBody.innerHTML = marked.parse(data.response);
            } else {
                responseBody.innerHTML = `<pre>${data.response}</pre>`;
            }

            // Update history drawer
            fetchAgentHistory();

        } catch (err) {
            console.error("FastAPI Execution Error:", err);
            responseBody.innerHTML = `
                <div style="color: #e11d48; padding: 16px; background: rgba(225,29,72,0.1); border-radius: 8px;">
                    <h4>⚠️ API Connection Warning</h4>
                    <p>${err.message}</p>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">Ensure FastAPI server is running via <code>python api_server.py</code></p>
                </div>
            `;
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>🚀 Execute Agent Request</span>`;
        }
    });

    function getEndpointForRole(role) {
        if (role === "manager") return "/api/v1/manager";
        if (role === "siddharth" || role === "mentor") return "/api/v1/mentor";
        if (role === "himaya" || role === "ganesh" || role === "dakshinya" || role === "teammate") return "/api/v1/teammate";
        return "/api/v1/query";
    }

    function getAgentDisplayName(role) {
        if (role === "manager") return "Manager Agent (Iyappan Sir)";
        if (role === "siddharth" || role === "mentor") return "Mentor Agent (Siddharth Saminathan)";
        if (role === "himaya" || role === "ganesh" || role === "dakshinya" || role === "teammate") return "Teammates Agent";
        return "Central Intent Router";
    }

    // Initial history fetch
    fetchAgentHistory();
});
