function showPopup(message, withYes = false) {
    return new Promise((resolve) => {
        const popupOverlay = document.getElementById('popupOverlay');
        const popupMessage = document.getElementById('popupMessage');
        const yesButton = document.getElementById('yesButton');

        popupMessage.textContent = message;

        yesButton.style.display = 'none';
        yesButton.onclick = null;

        if (withYes) {
            yesButton.style.display = 'inline-block';
            yesButton.onclick = () => {
                closePopup();
                resolve(true);
            };
        }

        const escHandler = (e) => {
            if (e.key === "Escape") {
                closePopup();
                resolve(false);
                document.removeEventListener("keydown", escHandler);
            }
        };
        document.addEventListener("keydown", escHandler);

        popupOverlay.style.display = 'flex';
    });
}

function closePopup() {
    document.getElementById('yesButton').style.display = 'none';
    document.getElementById('popupOverlay').style.display = 'none';
}
