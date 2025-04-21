function goTocastevotepage() {
    window.location.href = `{{ url_for('caste-vote') }}`; // Flask will replace this with '/caste-vote'
}

function showVoterView() {
    document.getElementById('voterView').style.display = 'block';
    document.getElementById('adminView').style.display = 'none';
    document.getElementById('adminLogin').style.display = 'none';
}

function showAdminLogin() {
    document.getElementById('adminLogin').style.display = 'block';
    document.getElementById('voterView').style.display = 'none';
    document.getElementById('adminView').style.display = 'none';
}

function login(event) {
    event.preventDefault(); // Prevent the form from submitting

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    // For demonstration, use hardcoded credentials
    if (username === 'admin' && password === 'password123') {
        document.getElementById('adminView').style.display = 'block';
        document.getElementById('adminLogin').style.display = 'none';
    } else {
        alert('Invalid credentials! Please try again.')
    }
    function login(event) {
        event.preventDefault(); // Prevent the form from submitting
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        // Check credentials
        if (username === adminCredentials.username && password === adminCredentials.password) {
            alert("Login successful!");
            // Redirect to the admin dashboard
            window.location.href = "admin_dashboard.html"; // Adjust this path as necessary
        } else {
            alert("Invalid username or password. Please try again.");
        }
    }
}

