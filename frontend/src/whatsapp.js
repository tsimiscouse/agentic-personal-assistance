/**
 * WhatsApp Client Manager
 * Handles WhatsApp Web.js client initialization and message handling
 */

import pkg from 'whatsapp-web.js';
const { Client, LocalAuth } = pkg;
import qrcode from 'qrcode-terminal';
import config from '../config/config.js';

/**
 * Create and configure WhatsApp client
 *
 * @returns {Client} - Configured WhatsApp client
 */
export function createWhatsAppClient() {
  console.log('[WhatsApp] Creating client...');

  const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
  });

  return client;
}

/**
 * Setup WhatsApp client event listeners
 *
 * @param {Client} client - WhatsApp client instance
 * @param {Function} onMessage - Message handler callback
 */
export function setupClientListeners(client, onMessage) {
  let qrCount = 0;

  // QR Code generation
  client.on('qr', (qr) => {
    qrCount++;
    console.clear();
    console.log('\n╔═════════════════════════════════════════════════╗');
    console.log('║                                                 ║');
    console.log('║        SCAN THIS QR CODE WITH WHATSAPP          ║');
    console.log('║                                                 ║');
    console.log('║     (Attempt #' + qrCount + ')                                  ║');
    console.log('║                                                 ║');
    console.log('╚═════════════════════════════════════════════════╝\n');
    
    // Generate QR code - small: true makes it fit in terminal
    qrcode.generate(qr, { small: true, width: 40 });
    
    console.log('\n╔═════════════════════════════════════════════════╗');
    console.log('║     Waiting for QR code scan...                 ║');
    console.log('║     Make sure your WhatsApp is open!            ║');
    console.log('╚═════════════════════════════════════════════════╝\n');
  });

  // Loading authentication
  client.on('loading_screen', (percent, message) => {
    console.log(`[WhatsApp] Loading: ${percent}% - ${message}`);
  });

  // Authenticated successfully
  client.on('authenticated', () => {
    console.log('[WhatsApp] ✓ Authenticated successfully!');
  });

  // Authentication failure
  client.on('auth_failure', (msg) => {
    console.error('[WhatsApp] ✗ Authentication failure:', msg);
    console.log('[WhatsApp] Deleting session and retrying...');
    
    // Remove session on auth failure
    try {
      require('fs').rmSync('.wwebjs_auth', { recursive: true });
      console.log('[WhatsApp] Session deleted. Please restart the application.');
    } catch (e) {
      console.error('[WhatsApp] Could not delete session:', e.message);
    }
  });

  // Client ready
  client.on('ready', async () => {
    console.clear();
    console.log('\n╔═════════════════════════════════════════════════╗');
    console.log('║      ✓ WhatsApp Client is Ready!               ║');
    console.log('╚═════════════════════════════════════════════════╝\n');

    const info = client.info;
    console.log(`📱 Connected as: ${info.pushname}`);
    console.log(`📞 Phone: ${info.wid.user}`);
    console.log(`🖥️  Platform: ${info.platform}`);
    console.log('╚═════════════════════════════════════════════════╝\n');
  });

  // Message received
  client.on('message', async (message) => {
    try {
      const contact = await message.getContact();
      const chat = await message.getChat();

      console.log(`\n[${new Date().toLocaleTimeString()}] 💬 Message from ${contact.pushname || contact.number}`);
      console.log(`   Message: "${message.body}"`);

      await onMessage(message, contact, chat);
    } catch (error) {
      console.error('[WhatsApp] Error handling message:', error);
    }
  });

  // Message acknowledgment
  client.on('message_ack', (msg, ack) => {
    if (config.debug) {
      const ackLabels = ['ERROR', 'PENDING', 'SERVER', 'DEVICE', 'READ', 'PLAYED'];
      console.log(`[WhatsApp] Message ack: ${ackLabels[ack] || ack}`);
    }
  });

  // Disconnected
  client.on('disconnected', (reason) => {
    console.log(`\n[WhatsApp] ✗ Client disconnected: ${reason}`);
    console.log('[WhatsApp] Attempting to restart...\n');
  });

  // Error handler
  client.on('error', (error) => {
    console.error('[WhatsApp] Client error:', error.message);
  });
}

/**
 * Initialize WhatsApp client
 *
 * @param {Function} onMessage - Message handler callback
 * @returns {Promise<Client>} - Initialized client
 */
export async function initializeWhatsAppClient(onMessage) {
  console.log('[WhatsApp] Initializing WhatsApp client...');

  try {
    const client = createWhatsAppClient();
    setupClientListeners(client, onMessage);

    console.log('[WhatsApp] Starting initialization...\n');

    await client.initialize();

    console.log('[WhatsApp] Client initialized successfully');
    return client;

  } catch (error) {
    console.error('[WhatsApp] Initialization error:', error.message);
    console.error('[WhatsApp] Full error:', error);
    throw error;
  }
}

export default {
  createWhatsAppClient,
  setupClientListeners,
  initializeWhatsAppClient,
};