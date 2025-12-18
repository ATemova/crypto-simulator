let ws = new WebSocket("ws://127.0.0.1:5000/ws");

ws.onmessage = (msg) => {
    const data = JSON.parse(msg.data);

    document.getElementById("height").innerText = data.chain_length;
    document.getElementById("balance").innerText = data.balance;
    document.getElementById("pending").innerText = data.pending;
    document.getElementById("peers").innerText = data.peers.length;

    renderBlocks(data.chain);
};

function renderBlocks(chain) {
    const container = document.getElementById("blocks");
    container.innerHTML = "";

    chain.forEach((block, i) => {
        let div = document.createElement("div");
        div.className = "block";
        div.innerHTML = `
            <strong>Block #${block.index}</strong><br>
            Hash: ${block.hash.substring(0, 25)}...<br>
            TX Count: ${block.transactions.length}
        `;
        div.onclick = () => openModal(JSON.stringify(block, null, 2));
        container.appendChild(div);
    });
}

async function mineBlock() {
    if (!confirm("Mine a new block?")) return;
    await fetch("http://127.0.0.1:5000/mine", { method: "POST" });
}

async function refreshChain() {
    const res = await fetch("http://127.0.0.1:5000/chain");
    const data = await res.json();
    renderBlocks(data.chain);
}