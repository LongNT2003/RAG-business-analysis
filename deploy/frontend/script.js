// frontend/script.js

const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');

let conversationId = "";

import { getConfig } from './config.js';
const envConfig = getConfig();
const BACKEND_URL = envConfig.backendUrl;

function displayMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerText = text;
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(message) {
    if (!message) return;
    displayMessage(message, 'user');

    try {
        // const response = await fetch(`${BACKEND_URL}/send_message`, {
        const response = await fetch(`http://localhost:3000/send_message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: message
            })
        });

        const data = await response.json();
        displayMessage(data.response, 'bot');
    } catch (error) {
        console.error('Error:', error);
        displayMessage('Xin lỗi, có lỗi xảy ra', 'bot');
    }
}


// Xử lý tin nhắn từ parent window
window.addEventListener('message', (event) => {
    if (event.data?.type === 'showChatbot') {
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            chatContainer.style.display = 'flex';  // Đảm bảo hiển thị lại đúng layout
        }
    }
    if (event.data?.type === 'sendMessage') {
        const message = event.data.message;
        // Đảm bảo container được hiển thị trước khi gửi tin nhắn
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            chatContainer.style.display = 'flex';
        }
        sendMessage(message);
    }
});

// Xử lý input từ người dùng
sendButton.addEventListener('click', () => {
    const message = userInput.value.trim();
    if (message) {
        sendMessage(message);
        userInput.value = '';
    }
});

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const message = userInput.value.trim();
        if (message) {
            sendMessage(message);
            userInput.value = '';
        }
    }
});


// Lắng nghe sự kiện click để đóng chatbot
document.getElementById('close-chatbot').addEventListener('click', () => {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.style.display = 'none';
    } else {
        console.error('Chat container not found!');
    }

    window.parent.postMessage({ type: 'closeChatbot' }, '*');
});

async function getCollections() {
    try {
        const response = await fetch('http://localhost:3000/get_collections', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const collections = await response.json();
        console.log('Available Collections:', collections['collections']);
        const dropdown = document.getElementById('collection-dropdown');
        dropdown.innerHTML = collections['collections'].map(col => `<option>${col}</option>`).join('');
    } catch (error) {
        console.error('Error fetching collections:', error);
    }
}
document.getElementById('show-collections-button').addEventListener('click', () => {
    getCollections();
});