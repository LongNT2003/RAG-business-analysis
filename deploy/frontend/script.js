// frontend/script.js

const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');

let conversationId = "";

import { getConfig } from './config.js';
const envConfig = getConfig();
const BACKEND_URL = envConfig.backendUrl;

function displayMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    if (typeof content === 'string') {
        // Nếu content là string (message từ user hoặc response đơn thuần)
        messageDiv.innerHTML = marked.parse(content);
    } else if (typeof content === 'object') {
        // Nếu content là object có response và links
        let messageContent = marked.parse(content.response);
        
        // Thêm phần links nếu có
        if (content.links && content.links.length > 0) {
            messageContent += '<div class="message-links">';
            messageContent += '<p><strong>Related Links:</strong></p>';
            messageContent += '<ul>';
            content.links.forEach(link => {
                messageContent += `<li><a href="${link}" target="_blank">${link}</a></li>`;
            });
            messageContent += '</ul>';
            messageContent += '</div>';
        }
        
        // sử dụng 
        messageDiv.innerHTML = messageContent;
    }
    
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
        // Gửi cả object chứa response và links
        displayMessage({
            response: data.response,
            links: data.links
        }, 'bot');
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

async function changeCollection(collectionName) {
    try {
        const response = await fetch('http://localhost:3000/change_collection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ collection_name: collectionName })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to change collection');
        }

        console.log('Collection changed successfully:', data.message);
        alert(`Collection changed to: ${collectionName}`);
    } catch (error) {
        console.error('Error changing collection:', error);
        alert('Error changing collection. Please try again.');
    }
}

document.getElementById('collection-dropdown').addEventListener('change', (event) => {
    const selectedCollection = event.target.value;
    if (selectedCollection) {
        changeCollection(selectedCollection);
    }
});

// Ensure you fetch and populate the dropdown when the button is clicked
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
        changeCollection(collections['collections'][0]);
        const dropdown = document.getElementById('collection-dropdown');
        dropdown.innerHTML = collections['collections']
            .map(col => `<option value="${col}">${col}</option>`)
            .join('');
    } catch (error) {
        console.error('Error fetching collections:', error);
    }
}

document.getElementById('show-collections-button').addEventListener('click', () => {
    getCollections();
});

document.getElementById('extract-content-button').addEventListener('click', async () => {
    
    // Get input values
    const linkInput = document.getElementById('link-input').value.trim();
    const companyNameInput = document.getElementById('company-name-input').value.trim();
    const maxLinksInput = parseInt(document.getElementById('max-link-input').value.trim(), 10);
    // Validate inputs
    if (!linkInput || !companyNameInput || maxLinksInput <= 0) {
        const errorMessage = 'Please enter valid link, company name, and a positive number for max links!';
        displayError(errorMessage);
        return;
    }
    try {
        // Send POST request to the server
        const response = await fetch('http://localhost:3000/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: linkInput,
                company_name: companyNameInput,
                max_links: maxLinksInput
            })
        });

        // Handle response
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to extract content');
        }

        const data = await response.json();
        const contentInfoDiv = document.getElementById('content-info');
        contentInfoDiv.innerHTML = `<pre>${data['message']}</pre>`; // Display extracted content
    } catch (error) {
        console.error('Error extracting content:', error);
        alert('Error extracting content. Please try again.');
    }
});
// Function to display error message on the frontend
function displayError(message) {
    const errorDiv = document.getElementById('error-message');
    if (!errorDiv) {
        const newErrorDiv = document.createElement('div');
        newErrorDiv.id = 'error-message';
        newErrorDiv.style.color = 'red';  // Make error message red
        newErrorDiv.style.marginTop = '10px';
        document.body.appendChild(newErrorDiv);
        newErrorDiv.textContent = message;
    } else {
        errorDiv.textContent = message;  // Update the existing error message
    }
}
document.getElementById('verify-content-button').addEventListener('click', async () => {
    try {
        // Make a GET request to the /status endpoint
        const response = await fetch('http://localhost:3000/crawl_status');
        
        // Check if the response is OK
        if (!response.ok) {
            throw new Error(`Error fetching status: ${response.statusText}`);
        }

        // Read the response as text
        const statusText = await response.text();

        // Display the status in the content-info div
        const contentInfoDiv = document.getElementById('content-info');
        contentInfoDiv.innerHTML = `
            <h3>Crawl Status:</h3>
            <pre>${statusText}</pre>
        `;
    } catch (error) {
        console.error('Error fetching status:', error);
        const contentInfoDiv = document.getElementById('content-info');
        contentInfoDiv.innerHTML = `
            <h3>Error:</h3>
            <p>Unable to fetch crawl status. Please try again later.</p>
        `;
    }
});




// chunking and save data to db
document.getElementById('save-to-database-button').addEventListener('click', function() {
    // Get the company name from the input field
    const companyName = document.getElementById('company-name-input').value;
    
    // Check if the company name is provided
    if (!companyName) {
        alert('Please enter a company name.');
        return;
    }

    // Prepare the request payload
    const requestData = {
        company_name: companyName
    };

    // Send the POST request to the /save_db route
    fetch('http://localhost:3000/save_db', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        // Check if the response has a message and display it
        const saveMessage = document.getElementById('save-message');
        if (data.message) {
            saveMessage.style.color = 'green';
            saveMessage.innerHTML = data.message;
        } else if (data.error) {
            saveMessage.style.color = 'red';
            saveMessage.innerHTML = `Error: ${data.error}`;
        }
        saveMessage.style.display = 'block';
    })
    .catch(error => {
        // Handle network or other errors
        const saveMessage = document.getElementById('save-message');
        saveMessage.style.color = 'red';
        saveMessage.innerHTML = `An error occurred: ${error.message}`;
        saveMessage.style.display = 'block';
    });
});
