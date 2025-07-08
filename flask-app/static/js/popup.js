function showPopup(message) {
    document.getElementById('popupMessage').textContent = message;
    document.getElementById('popupOverlay').style.display = 'flex';
}

function closePopup() {
    document.getElementById('popupOverlay').style.display = 'none';
}