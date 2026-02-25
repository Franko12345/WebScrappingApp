// Max News switch functionality
const switchEl = document.getElementById("max_news_switch");
const maxNewsInput = document.getElementById("max_news");
const maxNewsAsterisk = document.getElementById("max_news_asterisk");

// Function to update asterisk color
function updateAsteriskColor() {
    if (maxNewsAsterisk) {
        if (switchEl.checked) {
            maxNewsAsterisk.classList.add("active");
        } else {
            maxNewsAsterisk.classList.remove("active");
        }
    }
}

// initialize state
maxNewsInput.disabled = !switchEl.checked;
updateAsteriskColor();

switchEl.addEventListener("change", () => {
    maxNewsInput.disabled = !switchEl.checked;

    if (maxNewsInput.disabled) {
        maxNewsInput.value = "50"; // clear when disabled (optional)
    }
    
    updateAsteriskColor();
});


