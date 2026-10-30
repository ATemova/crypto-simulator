const $ = (id) => document.getElementById(id);
const short = (s, n = 10) => (s && s.length > 2 * n ? `${s.slice(0, n)}…${s.slice(-n)}` : s || "");
let address = "";
let reconnectDelay = 1000;

function toast(message, isError = false) {
    const el = $("toast");
    el.textContent = message;
    el.className = `toast${isError ? " error" : ""}`;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => el.classList.add("hidden"), 4000);
}

async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
        const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join(", ") : body.detail;
        throw new Error(detail || `HTTP ${res.status}`);
    }
    return body;
}

function setConnected(online) {
    $("conn-dot").className = `dot ${online ? "online" : "offline"}`;
    $("conn-text").textContent = online ? "Live" : "Disconnected — retrying…";
}

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function renderState(state) {
    address = state.address;
    $("address").textContent = short(state.address, 12);
    $("address").title = state.address;
    $("height").textContent = state.height;
    $("balance").textContent = state.balance.confirmed;
    $("available").textContent = state.balance.available;
    $("pending").textContent = state.pending;
    $("peers").textContent = state.peers;
    $("difficulty").textContent = state.difficulty;
    $("valid").textContent = state.valid ? "✔" : "✖";
    const btn = $("mine-btn");
    btn.disabled = state.mining;
    btn.textContent = state.mining ? "⛏ Mining…" : "⛏ Mine Block";
}

function renderPeers(peers) {
    const list = $("peer-list");
    list.replaceChildren(...peers.map((p) => el("li", "", `${p.address} (${p.direction})`)));
}

function renderMempool(pending) {
    const box = $("mempool");
    if (!pending.length) {
        box.replaceChildren(document.createTextNode("Empty"));
        return;
    }
    box.replaceChildren(
        ...pending.map((tx) => {
            const row = el("div", "tx", `${short(tx.sender, 6)} → ${short(tx.recipient, 6)} · ${tx.amount}`);
            row.addEventListener("click", () => openModal(JSON.stringify(tx, null, 2)));
            return row;
        })
    );
}

function renderBlocks(blocks) {
    const container = $("blocks");
    container.replaceChildren(
        ...blocks
            .slice()
            .reverse()
            .map((block) => {
                const div = el("div", "block");
                div.append(
                    el("strong", "", `Block #${block.index}`),
                    el("div", "mono", `Hash: ${short(block.hash, 16)}`),
                    el("div", "", `Transactions: ${block.transactions.length} · Nonce: ${block.nonce}`),
                    el("div", "muted", block.timestamp ? new Date(block.timestamp * 1000).toLocaleString() : "Genesis")
                );
                div.addEventListener("click", () => openModal(JSON.stringify(block, null, 2)));
                return div;
            })
    );
}

function renderEvents(events) {
    const box = $("events");
    box.replaceChildren(
        ...events
            .slice()
            .reverse()
            .map((e) => el("div", "", `${new Date(e.time * 1000).toLocaleTimeString()}  ${e.message}`))
    );
}

function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => {
        reconnectDelay = 1000;
        setConnected(true);
    };
    ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data);
        renderState(data.state);
        renderPeers(data.peers);
        renderMempool(data.pending);
        renderEvents(data.events);
        if (data.blocks) renderBlocks(data.blocks);
    };
    ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 10000);
    };
}

$("mine-btn").addEventListener("click", async () => {
    $("mine-btn").disabled = true;
    try {
        const res = await api("/mine", { method: "POST" });
        toast(`Mined block #${res.block.index}`);
    } catch (err) {
        toast(err.message, true);
    }
});

$("copy-address").addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(address);
        toast("Address copied");
    } catch {
        openModal(address);
    }
});

$("send-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
        const res = await api("/transactions", {
            method: "POST",
            body: JSON.stringify({ recipient: $("recipient").value.trim(), amount: Number($("amount").value) }),
        });
        toast(`Transaction ${res.transaction.id.slice(0, 12)} pending`);
        e.target.reset();
    } catch (err) {
        toast(err.message, true);
    }
});

$("peer-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = $("peer-addr").value.trim();
    const [host, port] = raw.includes(":") ? raw.split(":") : ["127.0.0.1", raw];
    try {
        await api("/peers", { method: "POST", body: JSON.stringify({ host, port: Number(port) }) });
        toast(`Connected to ${host}:${port}`);
        e.target.reset();
    } catch (err) {
        toast(err.message, true);
    }
});

connect();
