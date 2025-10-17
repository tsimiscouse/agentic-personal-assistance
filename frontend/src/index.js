/**
 * Personal Assistant WhatsApp Bot - Frontend Entry Point
 * Node.js application that bridges WhatsApp with Python LangChain backend
 */

import { initializeWhatsAppClient } from './whatsapp.js';
import { sendMessageToAgent, checkBackendHealth } from './api.js';
import config from '../config/config.js';

/**
 * Handle incoming WhatsApp messages
 *
 * @param {Message} message - WhatsApp message object
 * @param {Contact} contact - Contact who sent the message
 * @param {Chat} chat - Chat where message was sent
 */
async function handleMessage(message, contact, chat) {
  try {
    // Ignore group messages
    if (chat.isGroup) {
      console.log('[Handler] Ignoring group message');
      return;
    }

    // Ignore status/broadcast/community messages
    if (message.from === 'status@broadcast' || message.broadcast) {
      console.log('[Handler] Ignoring broadcast/status message');
      return;
    }

    // Ignore own messages
    if (message.fromMe) {
      console.log('[Handler] Ignoring own message');
      return;
    }

    // Get user ID (WhatsApp chat ID)
    const userId = message.from;

    // Check if access is restricted to specific numbers
    if (config.allowedNumbers.length > 0) {
      // Extract phone number from userId (format: 1234567890@c.us)
      const phoneNumber = userId.split('@')[0];

      // Check if this number is allowed
      if (!config.allowedNumbers.includes(phoneNumber)) {
        console.log(`[Handler] ⛔ Access denied for ${phoneNumber} - silently ignoring`);
        // Don't reply to unauthorized users - just ignore silently
        return;
      }

      console.log(`[Handler] ✓ Access granted for ${phoneNumber}`);
    }

    // Handle document/file attachments
    let fileData = null;
    let messageText = message.body || '';

    // Check if message has media
    if (message.hasMedia) {
      try {
        console.log(`[Handler] Message contains media attachment`);

        // Download media
        const media = await message.downloadMedia();

        if (media) {
          console.log(`[Handler] Media downloaded - Type: ${media.mimetype}, Size: ${media.data.length} chars`);

          // Check if it's a supported document type
          const supportedTypes = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // DOCX
            'application/vnd.openxmlformats-officedocument.presentationml.presentation', // PPTX
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // XLSX
            'application/vnd.ms-excel', // XLS
            'text/csv',
            'text/plain',
            'application/msword' // DOC
          ];

          if (supportedTypes.includes(media.mimetype)) {
            // Get filename from message or create one
            const filename = media.filename || `document.${getExtensionFromMimetype(media.mimetype)}`;

            fileData = {
              data: media.data, // Already base64
              name: filename,
              mime: media.mimetype
            };

            console.log(`[Handler] ✓ Document will be processed: ${filename}`);

            // If no text message, add a default one
            if (!messageText || messageText.trim() === '') {
              messageText = 'Please summarize this document.';
            }
          } else {
            console.log(`[Handler] Unsupported media type: ${media.mimetype}`);
            // For images, audio, video - just process the text
            if (!messageText || messageText.trim() === '') {
              console.log('[Handler] Ignoring media-only message (unsupported type)');
              return;
            }
          }
        }
      } catch (mediaError) {
        console.error('[Handler] Error downloading media:', mediaError);
        // Continue processing text message even if media download fails
      }
    }

    // Check if we have any text to process
    if (!messageText || messageText.trim() === '') {
      console.log('[Handler] Ignoring empty message');
      return;
    }

    console.log(`[Handler] Processing message from ${userId}`);

    // Show typing indicator
    chat.sendStateTyping();

    // Send message to backend agent (with file data if present)
    const result = await sendMessageToAgent(userId, messageText, fileData);

    // Stop typing indicator
    chat.clearState();

    // Send response back to user
    if (result.success) {
      await message.reply(result.response);
      console.log(`[Handler] ✓ Response sent successfully`);

      // Log tool usage
      if (result.toolUsed) {
        console.log(`[Handler] Tool used: ${result.toolUsed}`);
      }
    } else {
      // Send error message
      await message.reply(result.response);
      console.log(`[Handler] ✗ Error response sent`);
    }
  } catch (error) {
    console.error('[Handler] Error processing message:', error);

    try {
      // Send fallback error message to user
      await message.reply(
        "I apologize, but I'm having technical difficulties right now. Please try again in a moment."
      );
    } catch (replyError) {
      console.error('[Handler] Failed to send error message:', replyError);
    }
  }
}

/**
 * Get file extension from MIME type
 * @param {string} mimetype - MIME type
 * @returns {string} - File extension
 */
function getExtensionFromMimetype(mimetype) {
  const mimeMap = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.ms-excel': 'xls',
    'text/csv': 'csv',
    'text/plain': 'txt',
    'application/msword': 'doc'
  };

  return mimeMap[mimetype] || 'bin';
}

/**
 * Main application entry point
 */
async function main() {
  console.log('\n=================================================');
  console.log('Personal Assistant WhatsApp Bot - Frontend');
  console.log('=================================================');
  console.log(`Environment: ${config.environment}`);
  console.log(`Backend API: ${config.backendApiUrl}`);
  console.log('=================================================\n');

  try {
    // Check backend health before starting
    console.log('[Main] Checking backend health...');
    const health = await checkBackendHealth();

    if (!health.healthy) {
      console.error('[Main] ✗ Backend is not healthy!');
      console.error(`[Main] Error: ${health.error}`);
      console.error('[Main] Please ensure the backend is running:');
      console.error('[Main]   cd backend');
      console.error('[Main]   uvicorn app.main:app --reload');
      process.exit(1);
    }

    console.log('[Main] ✓ Backend is healthy');
    console.log(`[Main] Backend version: ${health.version}`);
    console.log(`[Main] Backend environment: ${health.environment}\n`);

    // Initialize WhatsApp client
    const client = await initializeWhatsAppClient(handleMessage);

    console.log('[Main] ✓ WhatsApp client initialized successfully');
    console.log('[Main] Bot is now running and ready to receive messages!\n');

    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      console.log('\n[Main] Shutting down gracefully...');
      await client.destroy();
      console.log('[Main] ✓ Client destroyed');
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      console.log('\n[Main] Received SIGTERM, shutting down...');
      await client.destroy();
      console.log('[Main] ✓ Client destroyed');
      process.exit(0);
    });

    // Keep process alive
    process.stdin.resume();
  } catch (error) {
    console.error('[Main] Fatal error:', error);
    process.exit(1);
  }
}

// Run the application
main().catch((error) => {
  console.error('[Main] Unhandled error:', error);
  process.exit(1);
});
