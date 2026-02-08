// Max News switch functionality
const switchEl = document.getElementById("max_news_switch");
const maxNewsInput = document.getElementById("max_news");

// initialize state
maxNewsInput.disabled = !switchEl.checked;

switchEl.addEventListener("change", () => {
    maxNewsInput.disabled = !switchEl.checked;

    if (maxNewsInput.disabled) {
        maxNewsInput.value = "50"; // clear when disabled (optional)
    }
});


