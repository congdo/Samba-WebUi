// Check authentication and load user data
async function initApp() {
    try {
        const response = await fetch('/api/user/profile');
        const data = await response.json();
        
        if (response.status === 401) {
            window.location.href = '/unauthorized';
            return;
        }

        if (response.status === 403) {
            document.getElementById('message').textContent = 'Account is disabled';
            return;
        }

        document.getElementById('welcome-message').textContent = `Welcome, ${data.username}`;
        if (data.is_admin) {
            document.getElementById('admin-link').classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('message').textContent = 'Error loading profile';
    }
}

// Handle password form submission
document.getElementById('password-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = e.target.password.value;
    
    try {
        const response = await fetch('/api/user/password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ password }),
        });

        const data = await response.json();
        document.getElementById('message').textContent = data.message;
        
        if (response.ok) {
            e.target.reset();
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('message').textContent = 'Error updating password';
    }
});

// Initialize the application
initApp();