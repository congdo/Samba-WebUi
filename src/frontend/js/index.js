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
        
        // Create user info section
        const userInfoSection = document.createElement('div');
        userInfoSection.className = 'mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200 shadow-sm';
        
        // Create user info container
        const userInfo = document.createElement('div');
        userInfo.className = 'space-y-3';
        
        // Add username with icon
        const usernameInfo = document.createElement('p');
        usernameInfo.className = 'flex items-center text-blue-900';
        usernameInfo.innerHTML = `
            <span class="text-xl mr-3">👤</span>
            <span class="flex-1">
                <span class="text-blue-600 font-medium">Username:</span>
                <span class="ml-2 font-bold">${profileData.username}</span>
            </span>
        `;
        userInfo.appendChild(usernameInfo);
        
        // Add groups with icon
        const groupsData = await groupsResponse.json();
        if (groupsData.groups && groupsData.groups.length > 0) {
            const groupsInfo = document.createElement('p');
            groupsInfo.className = 'flex items-center text-blue-900';
            groupsInfo.innerHTML = `
                <span class="text-xl mr-3">👥</span>
                <span class="flex-1">
                    <span class="text-blue-600 font-medium">Groups:</span>
                    <span class="ml-2 font-bold">${groupsData.groups.join(', ')}</span>
                </span>
            `;
            userInfo.appendChild(groupsInfo);
        }
        
        userInfoSection.appendChild(userInfo);
        document.getElementById('welcome-message').parentNode.insertBefore(
            userInfoSection,
            document.getElementById('welcome-message').nextSibling
        );

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