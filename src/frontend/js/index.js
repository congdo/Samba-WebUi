// Fetch and display server IP
async function loadServerIP() {
    try {
        const response = await fetch('/api/server-ip');
        const data = await response.json();
        if (data.ip) {
            document.getElementById('server-ip-windows').textContent = `\\\\${data.ip}`;
            document.getElementById('server-ip-unix').textContent = `smb://${data.ip}`;
        }
    } catch (error) {
        console.error('Error fetching server IP:', error);
        document.getElementById('server-ip-windows').textContent = 'Could not load server IP';
        document.getElementById('server-ip-unix').textContent = 'Could not load server IP';
    }
}

// Check authentication and load user data
async function initApp() {
    try {
        const [profileResponse, groupsResponse] = await Promise.all([
            fetch('/api/user/profile'),
            fetch('/api/user/groups')
        ]);
        
        const profileData = await profileResponse.json();
        
        if (profileResponse.status === 401) {
            window.location.href = '/unauthorized';
            return;
        }

        if (profileResponse.status === 403) {
            document.getElementById('message').textContent = 'Account is disabled';
            return;
        }

        // Extract first name from username or use username as fallback
        let greeting = `Welcome, ${profileData.username}`;
        const email = profileData.email;
        
        // Extract name from email (format: cong.do@mozox.com)
        if (email && email.includes('@')) {
            const [localPart] = email.split('@');
            if (localPart.includes('.')) {
                const [firstName] = localPart.split('.');
                const capitalizedName = firstName.charAt(0).toUpperCase() + firstName.slice(1);
                greeting = `Welcome, ${capitalizedName}`;
            }
        }
        document.getElementById('welcome-message').textContent = greeting;
        
        // Show username hint
        const usernameHint = document.createElement('p');
        usernameHint.className = 'text-sm text-gray-500 mt-1';
        usernameHint.textContent = `Your username is: ${profileData.username}`;
        document.getElementById('welcome-message').parentNode.insertBefore(usernameHint, document.getElementById('welcome-message').nextSibling);

        // Show user groups
        const groupsData = await groupsResponse.json();
        if (groupsData.groups && groupsData.groups.length > 0) {
            const groupsInfo = document.createElement('p');
            groupsInfo.className = 'text-sm text-gray-600 mt-2';
            groupsInfo.textContent = `Your groups: ${groupsData.groups.join(', ')}`;
            document.getElementById('welcome-message').parentNode.insertBefore(groupsInfo, usernameHint.nextSibling);
        }

        if (profileData.is_admin) {
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
        const messageElement = document.querySelector('#password-form #message');
        messageElement.textContent = data.message;
        
        if (response.ok) {
            e.target.reset();
        }
    } catch (error) {
        console.error('Error:', error);
        const messageElement = document.querySelector('#password-form #message');
        messageElement.textContent = 'Error updating password';
    }
});

// Initialize the application
initApp();
loadServerIP();