function openModal(text) {
    document.getElementById("modal-text").innerText = text;
    document.getElementById("modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("modal").classList.add("hidden");
}