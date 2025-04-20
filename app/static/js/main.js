const socket = io({
    transports: ['websocket'],
    upgrade: false,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    forceNew: true
});

let selectedBook = null;
let selectedBookTitle = null;

// Connection handling
socket.on('connect', () => {
    console.log('Connected to server');
    loadExistingMessages();
});

socket.on('connect_error', (error) => {
    console.error('Connection Error:', error);
    showNotification('Connection error. Trying to reconnect...', 'error');
});

socket.on('reconnect', (attemptNumber) => {
    console.log('Reconnected on attempt:', attemptNumber);
    showNotification('Reconnected to server!', 'success');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    showNotification('Disconnected from server. Reconnecting...', 'error');
});

// Message handling
socket.on('status', (data) => {
    console.log('Status message received:', data);
    appendStatusMessage(data);
});

socket.on('new_message', (data) => {
    console.log('New message received:', data);
    if (data.message_type === 'book_qa') {
        appendBookMessage(data);
    } else if (data.message_type === 'ai_help') {
        console.log('Processing AI help message:', data);
        appendRegularMessage(data);
    } else {
        appendRegularMessage(data);
    }
});

socket.on('message', (data) => {
    if (data.message_type === 'book_qa') {
        appendBookMessage(data);
    } else {
        appendRegularMessage(data);
    }
});

socket.on('error', (data) => {
    showNotification(data.message, 'error');
});

// Utility functions
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function loadExistingMessages() {
    const messages = document.querySelectorAll('.message-data');
    messages.forEach(message => {
        const data = JSON.parse(message.textContent);
        if (data.message_type === 'book_qa') {
            appendBookMessage(data);
        } else {
            appendRegularMessage(data);
        }
    });
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;

    if (selectedBook) {
        // If a book is selected, treat it as a book question
        socket.emit('book_question', {
            book_id: selectedBook,
            question: message
        });
    } else {
        // Regular chat message
        socket.emit('message', { message: message });
    }
    
    input.value = '';
}

function askBook() {
    if (!selectedBook) {
        showNotification('Please select a book first!', 'error');
        return;
    }
    
    const input = document.getElementById('bookQuestion');
    const question = input.value.trim();
    
    if (question) {
        socket.emit('book_question', {
            book_id: selectedBook,
            question: question
        });
        input.value = '';
    }
}

function selectBook(bookId, bookTitle) {
    console.log('Selecting book:', bookId, bookTitle);
    selectedBook = bookId;
    selectedBookTitle = bookTitle;
    
    // Update UI
    document.querySelectorAll('.book-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    const selectedElement = document.getElementById(`book-${bookId}`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
        document.getElementById('selectedBook').textContent = `Selected: ${bookTitle}`;
        document.getElementById('deselectBookBtn').style.display = 'block';
        document.getElementById('messageInput').placeholder = `Ask a question about "${bookTitle}"...`;
    } else {
        console.error('Could not find element with id:', `book-${bookId}`);
    }
}

function appendStatusMessage(data) {
    const messages = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message status';
    messageDiv.innerHTML = `
        <span class="timestamp">[${data.timestamp}]</span>
        <span class="status">${data.msg}</span>
    `;
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
}

function getInitials(username) {
    return username
        .split(' ')
        .map(word => word[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
}

function appendRegularMessage(data) {
    console.log('Appending regular message:', data); // Debug log
    const messages = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    if (data.message_type === 'ai_help') {
        messageDiv.innerHTML = `
            <div class="message-avatar initials">AI</div>
            <div class="message-content">
                <div class="message-username">${data.username}</div>
                <div class="message-text">${data.content}</div>
                <div class="message-timestamp">${data.timestamp}</div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-avatar initials">${getInitials(data.username)}</div>
            <div class="message-content">
                <div class="message-username">${data.username}</div>
                <div class="message-text">${data.content}</div>
                <div class="message-timestamp">${data.timestamp}</div>
            </div>
        `;
    }
    
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
}

function appendBookMessage(data) {
    const messages = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'book-qa-message';
    messageDiv.innerHTML = `
        <div class="message-avatar initials">${getInitials(data.username)}</div>
        <div class="message-content">
            <div class="message-username">${data.username}</div>
            <div class="message-text">
                <strong>Question:</strong> ${data.content.question}<br>
                <strong>Answer:</strong> ${data.content.answer}<br>
                <em>From: ${data.content.book_title}</em>
            </div>
            <div class="message-timestamp">${data.timestamp}</div>
        </div>
    `;
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
}

function displayMessage(message) {
    const messagesDiv = document.getElementById('messages');
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    
    // Create message HTML based on type
    if (message.message_type === 'chat') {
        messageElement.innerHTML = `
            <div class="message-avatar initials">${getInitials(message.username)}</div>
            <div class="message-content">
                <div class="message-username">${message.username}</div>
                <div class="message-text">${message.content}</div>
                <div class="message-timestamp">${message.timestamp}</div>
            </div>
        `;
    } else if (message.message_type === 'book_qa') {
        messageElement.innerHTML = `
            <div class="message-avatar initials">${getInitials(message.username)}</div>
            <div class="message-content">
                <div class="message-username">${message.username}</div>
                <div class="message-text">
                    <strong>Question:</strong> ${message.content.question}<br>
                    <strong>Answer:</strong> ${message.content.answer}<br>
                    <em>From: ${message.content.book_title}</em>
                </div>
                <div class="message-timestamp">${message.timestamp}</div>
            </div>
        `;
    }
    
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function getUserAvatar(userId) {
    // Get user info from session or use default avatar
    const userInfo = window.userInfo || {};
    return userInfo.picture || '/static/images/default-avatar.png';
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('messageInput');
    const bookQuestion = document.getElementById('bookQuestion');

    messageInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    bookQuestion?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            askBook();
        }
    });

    // Add click event listeners to all book items
    document.querySelectorAll('.book-item').forEach(item => {
        item.addEventListener('click', function() {
            const bookId = this.id.replace('book-', '');
            const bookTitle = this.querySelector('.book-title').textContent;
            selectBook(bookId, bookTitle);
        });
    });
});

function deselectBook() {
    selectedBook = null;
    selectedBookTitle = null;
    
    // Update UI
    document.querySelectorAll('.book-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // Clear selected book display and hide deselect button
    document.getElementById('selectedBook').textContent = '';
    document.getElementById('deselectBookBtn').style.display = 'none';
    
    // Reset message input placeholder
    document.getElementById('messageInput').placeholder = 'Type your message...';
}

function helpMeAI() {
    console.log('Help me AI button clicked');
    socket.emit('help_me_ai');
}
