document.addEventListener('DOMContentLoaded', function() {
    // Gender Distribution Chart
    const genderCtx = document.getElementById('genderChart').getContext('2d');
    new Chart(genderCtx, {
        type: 'pie',
        data: {
            labels: statsData.gender.map(g => g._id),
            datasets: [{
                data: statsData.gender.map(g => g.count),
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56']
            }]
        }
    });

    // Age Distribution Chart
    const ageCtx = document.getElementById('ageChart').getContext('2d');
    new Chart(ageCtx, {
        type: 'bar',
        data: {
            labels: statsData.age.map(a => a._id),
            datasets: [{
                label: 'Voters by Age Group',
                data: statsData.age.map(a => a.count),
                backgroundColor: '#36A2EB'
            }]
        }
    });

    // State Distribution Chart
    const stateCtx = document.getElementById('stateChart').getContext('2d');
    new Chart(stateCtx, {
        type: 'bar',
        data: {
            labels: statsData.state.map(s => s._id),
            datasets: [{
                label: 'Voters by State',
                data: statsData.state.map(s => s.count),
                backgroundColor: '#FFCE56'
            }]
        }
    });

    // Ethnicity Breakdown Chart
    const ethnicityCtx = document.getElementById('ethnicityChart').getContext('2d');
    new Chart(ethnicityCtx, {
        type: 'doughnut',
        data: {
            labels: statsData.ethnicity.map(e => e._id),
            datasets: [{
                data: statsData.ethnicity.map(e => e.count),
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
            }]
        }
    });

    // Party Performance Chart
    const partyCtx = document.getElementById('partyChart').getContext('2d');
    new Chart(partyCtx, {
        type: 'bar',
        data: {
            labels: statsData.party.map(p => p._id),
            datasets: [{
                label: 'Votes by Party',
                data: statsData.party.map(p => p.total_votes),
                backgroundColor: '#4BC0C0'
            }]
        }
    });

    // Hourly Voting Distribution Chart
    const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
    new Chart(hourlyCtx, {
        type: 'line',
        data: {
            labels: statsData.hourly.map(h => `${h._id}:00`),
            datasets: [{
                label: 'Votes per Hour',
                data: statsData.hourly.map(h => h.vote_count),
                borderColor: '#FF6384',
                fill: false
            }]
        }
    });

    // Monthly Registration Trends Chart
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: statsData.trends.map(t => t._id),
            datasets: [{
                label: 'Registrations by Month',
                data: statsData.trends.map(t => t.registration_count),
                borderColor: '#36A2EB',
                fill: false
            }]
        }
    });
});