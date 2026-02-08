// Notification functionality
function showNotification() {
    const notif = document.getElementById("notification");
    notif.classList.add("show");

    setTimeout(() => {
        notif.classList.remove("show");
    }, 2000); // disappears after 2 seconds
}

