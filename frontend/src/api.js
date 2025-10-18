/**
 * Backend API Client
 * Handles communication with Python FastAPI backend
 */

import axios from 'axios';
import config from '../config/config.js';

/**
 * Create axios instance with base configuration
 */
const apiClient = axios.create({
  baseURL: config.backendApiUrl,
  timeout: config.whatsappTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Send message to backend agent
 *
 * @param {string} userId - WhatsApp user ID (phone@c.us)
 * @param {string} message - User's message
 * @param {Object} fileData - Optional file data {data: base64, name: filename, mime: mimetype}
 * @returns {Promise<Object>} - Agent's response
 */
export async function sendMessageToAgent(userId, message, fileData = null) {
  try {
    console.log(`[API] Sending message to backend for user ${userId}`);

    const payload = {
      user_id: userId,
      message: message,
    };

    // Add file data if present
    if (fileData) {
      payload.file_data = fileData.data;
      payload.file_name = fileData.name;
      payload.file_mime = fileData.mime;
      console.log(`[API] Including file attachment: ${fileData.name}`);
    }

    // Use longer timeout for file uploads (5 minutes instead of 1 minute)
    const requestTimeout = fileData ? 300000 : 180000; // 5 min for files, 1 min for text

    const response = await apiClient.post('/chat', payload, {
      timeout: requestTimeout
    });

    console.log(`[API] Received response from backend`);

    return {
      success: true,
      response: response.data.response,
      toolUsed: response.data.tool_used,
      conversationId: response.data.conversation_id,
    };
  } catch (error) {
    console.error(`[API] Error communicating with backend:`, error.message);

    // Return user-friendly error message
    return {
      success: false,
      response: "I'm having trouble connecting to my brain right now. Please try again in a moment.",
      error: error.message,
    };
  }
}

/**
 * Check backend health
 *
 * @returns {Promise<Object>} - Health status
 */
export async function checkBackendHealth() {
  try {
    const response = await apiClient.get('/health');
    return {
      healthy: true,
      ...response.data,
    };
  } catch (error) {
    console.error(`[API] Backend health check failed:`, error.message);
    return {
      healthy: false,
      error: error.message,
    };
  }
}

/**
 * Get conversation history for a user
 *
 * @param {string} userId - WhatsApp user ID
 * @param {number} limit - Number of conversations to retrieve
 * @returns {Promise<Object>} - Conversation history
 */
export async function getConversationHistory(userId, limit = 10) {
  try {
    const response = await apiClient.get(`/history/${userId}`, {
      params: { limit },
    });

    return {
      success: true,
      ...response.data,
    };
  } catch (error) {
    console.error(`[API] Error fetching history:`, error.message);
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * Clear user session (short-term memory)
 *
 * @param {string} userId - WhatsApp user ID
 * @returns {Promise<Object>} - Operation result
 */
export async function clearUserSession(userId) {
  try {
    const response = await apiClient.delete(`/session/${userId}`);

    return {
      success: true,
      ...response.data,
    };
  } catch (error) {
    console.error(`[API] Error clearing session:`, error.message);
    return {
      success: false,
      error: error.message,
    };
  }
}

export default {
  sendMessageToAgent,
  checkBackendHealth,
  getConversationHistory,
  clearUserSession,
};
