console.log("JS подключен успешно!");

const dark_theme_checkbox = document.getElementById('dark_theme_checkbox');
const theme_switch = document.getElementById('dark_theme_checkbox');

// On page load, check saved theme
if (localStorage.getItem('dark_mode') === 'on') {
    theme_switch.checked = true;
    document.body.classList.add('dark');
}

// Toggle theme on checkbox change
theme_switch.addEventListener('change', function() {
    if (this.checked) {
        localStorage.setItem('dark_mode', 'on');
        document.body.classList.add('dark');
    } else {
        localStorage.setItem('dark_mode', 'off');
        document.body.classList.remove('dark');
    }
});
