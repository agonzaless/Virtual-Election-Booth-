
function showVoterView() {
    document.getElementById('voterView').style.display = 'block';
    // Add smooth fade-in animation
    document.getElementById('voterView').classList.add('fade-in');
}

// Show admin login modal
function showAdminLogin() {
    const adminModal = new bootstrap.Modal(document.getElementById('adminLoginModal'));
    adminModal.show();
}

// Navigate to cast vote page
function goTocastevotepage() {
    window.location.href = '/castevote';
}

// Initialize Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});