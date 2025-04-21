document.addEventListener('DOMContentLoaded', function() {
    // Highlight selected candidate
    const candidateOptions = document.querySelectorAll('.candidate-option');
    candidateOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove highlight from other candidates in same election
            const electionCard = this.closest('.election-card');
            electionCard.querySelectorAll('.candidate-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            // Add highlight to selected candidate
            this.classList.add('selected');
        });
    });

    // Form validation
    const votingForms = document.querySelectorAll('.voting-form');
    votingForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const email = this.querySelector('input[name="email"]').value;
            const token = this.querySelector('input[name="token"]').value;
            const selectedCandidate = this.querySelector('input[name="candidate_id"]:checked');

            if (!selectedCandidate) {
                showMessage('Please select a candidate');
                return;
            }

            // Submit vote
            submitVote(this, {
                email: email,
                token: token,
                candidate_id: selectedCandidate.value,
                election_id: this.querySelector('input[name="election_id"]').value
            });
        });
    });
});

function submitVote(form, data) {
    fetch('/castevote', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showMessage('Vote cast successfully!', 'success');
            form.reset();
            setTimeout(() => {
                window.location.href = '/vote_confirmation';
            }, 2000);
        } else {
            showMessage(result.message || 'Error casting vote', 'error');
        }
    })
    .catch(error => {
        showMessage('Error submitting vote. Please try again.', 'error');
    });
}

function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    document.body.appendChild(messageDiv);
    setTimeout(() => messageDiv.remove(), 3000);
}