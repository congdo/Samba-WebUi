// Utility function to show messages
function showMessage(message, category) {
    const container = document.getElementById('message-container');
    const div = document.createElement('div');
    const bgColor = {
        'success': 'bg-green-100 text-green-800',
        'error': 'bg-red-100 text-red-800',
        'info': 'bg-blue-100 text-blue-800',
        'warning': 'bg-yellow-100 text-yellow-800'
    }[category] || 'bg-gray-100 text-gray-800';
    
    div.className = `flash p-3 rounded-md text-sm ${bgColor}`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 5000);
}

// Load and display all users
async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        const data = await response.json();
        
        if (!response.ok) {
            if (response.status === 403) {
                window.location.href = '/frontend/index.html';
                return;
            }
            throw new Error(data.message || 'Failed to load users');
        }

        const tbody = document.getElementById('user-table-body');
        tbody.innerHTML = '';

        data.users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="py-3 px-4 border-b border-gray-200 text-gray-700">${user.username}</td>
                <td class="py-3 px-4 border-b border-gray-200 text-gray-700">
                    <button onclick="toggleAdmin('${user.username}')"
                            class="toggle-btn text-blue-600 hover:text-blue-800 underline font-medium">
                        ${user.role}
                    </button>
                </td>
                <td class="py-3 px-4 border-b border-gray-200 text-gray-700">
                    <button onclick="toggleDisable('${user.username}')"
                            class="toggle-btn ${user.status === 'Enabled' ? 'text-green-600 hover:text-green-800' : 'text-red-600 hover:text-red-800'} underline font-medium">
                        ${user.status}
                    </button>
                </td>
                <td class="py-3 px-4 border-b border-gray-200 text-gray-700">
                    ${renderUserGroups(user)}
                </td>
                <td class="py-3 px-4 border-b border-gray-200 text-gray-700">
                    <button onclick="deleteUser('${user.username}')"
                            class="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-md text-sm transition-colors duration-200">
                        Delete User
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

// Load and display all groups
async function loadGroups() {
    try {
        const response = await fetch('/api/admin/groups');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to load groups');
        }

        const groupList = document.getElementById('group-list');
        groupList.innerHTML = data.groups.length ? '' : 
            '<li class="text-gray-500 italic p-3">No groups managed yet. Create one above.</li>';

        data.groups.forEach(group => {
            const li = document.createElement('li');
            li.className = 'group-management-item flex justify-between items-center bg-gray-100 p-3 rounded-md shadow-sm';
            li.innerHTML = `
                <span class="font-medium text-gray-800">${group}</span>
                <button onclick="removeGroup('${group}')" 
                        class="remove-managed-group-btn bg-red-600 hover:bg-red-700 text-white text-sm px-3 py-1 rounded-md transition-colors duration-200">
                    Remove Group
                </button>
            `;
            groupList.appendChild(li);
        });
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

// Render user groups and dropdown
function renderUserGroups(user) {
    let html = '<ul class="group-list">';
    
    user.groups.forEach(group => {
        html += `
            <li class="group-item bg-gray-200 text-gray-800 px-3 py-1 rounded-full text-sm flex items-center">
                <button onclick="removeUserFromGroup('${user.username}', '${group}')"
                        class="remove-group-from-user-btn text-gray-700 hover:text-red-600 underline">
                    ${group}
                </button>
            </li>
        `;
    });
    html += '</ul>';

    if (user.available_groups.length) {
        html += `
            <select onchange="addUserToGroup('${user.username}', this)" 
                    class="group-add-select mt-2 w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm">
                <option value="">-- Add to Group --</option>
                ${user.available_groups.map(g => `<option value="${g}">${g}</option>`).join('')}
            </select>
        `;
    } else {
        html += '<p class="text-xs text-gray-500 italic mt-2">No more groups to add.</p>';
    }

    return html;
}

// User management functions
async function toggleAdmin(username) {
    if (!confirm(`Change role for user ${username}?`)) return;
    
    try {
        const response = await fetch('/api/admin/users/toggle-admin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to toggle admin status');
        
        showMessage(data.message, 'success');
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

async function toggleDisable(username) {
    if (!confirm(`Toggle disable status for user ${username}?`)) return;
    
    try {
        const response = await fetch('/api/admin/users/toggle-disable', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to toggle disable status');
        
        showMessage(data.message, 'success');
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

async function deleteUser(username) {
    if (!confirm(`Permanently delete user ${username} and all their data?`)) return;
    
    try {
        const response = await fetch('/api/admin/users/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to delete user');
        
        showMessage(data.message, 'success');
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

// Group management functions
async function createGroup(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const groupName = formData.get('new_group_name').trim().toLowerCase();
    
    try {
        const response = await fetch('/api/admin/groups/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ group_name: groupName })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to create group');
        
        showMessage(data.message, 'success');
        event.target.reset();
        loadGroups();
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

async function removeGroup(groupName) {
    if (!confirm(`Permanently delete the group ${groupName}, remove its share, and remove all users from this group?`)) return;
    
    try {
        const response = await fetch('/api/admin/groups/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ group_name: groupName })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to remove group');
        
        showMessage(data.message, 'success');
        loadGroups();
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

// User-group management functions
async function addUserToGroup(username, selectElement) {
    const groupName = selectElement.value;
    if (!groupName) return;
    
    try {
        const response = await fetch('/api/admin/users/add-to-group', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, group_name: groupName })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to add user to group');
        
        showMessage(data.message, 'success');
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

async function removeUserFromGroup(username, groupName) {
    if (!confirm(`Remove user ${username} from group ${groupName}?`)) return;
    
    try {
        const response = await fetch('/api/admin/users/remove-from-group', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, group_name: groupName })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to remove user from group');
        
        showMessage(data.message, 'success');
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

// Bulk user import
async function importUsers(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const importData = formData.get('import_data').trim();
    
    try {
        const response = await fetch('/api/admin/users/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ import_data: importData })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.message || 'Failed to import users');
        
        showMessage(data.message, 'success');
        event.target.reset();
        loadUsers();
    } catch (error) {
        console.error('Error:', error);
        showMessage(error.message, 'error');
    }
}

// Event listeners
document.getElementById('import-form').addEventListener('submit', importUsers);
document.getElementById('create-group-form').addEventListener('submit', createGroup);

// Initialize the admin panel
loadUsers();
loadGroups();