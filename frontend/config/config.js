/**
 * Frontend Configuration
 * Manages environment variables and settings
 */

import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables from root .env file
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const config = {
  // Backend API Configuration
  backendApiUrl: process.env.BACKEND_API_URL || 'http://localhost:8000',

  // WhatsApp Configuration
  whatsappSessionName: process.env.WHATSAPP_SESSION_NAME || 'whatsapp-assistant-session',
  whatsappTimeout: parseInt(process.env.WHATSAPP_TIMEOUT) || 60000,

  // Access Control
  allowedNumbers: process.env.ALLOWED_WHATSAPP_NUMBERS
    ? process.env.ALLOWED_WHATSAPP_NUMBERS.split(',').map(n => n.trim())
    : [], // Empty array = allow all

  // Environment
  environment: process.env.ENVIRONMENT || 'development',
  debug: process.env.DEBUG === 'true',
};

// Validate required configuration
if (!config.backendApiUrl) {
  throw new Error('BACKEND_API_URL is required in .env file');
}

// Log access control status
if (config.allowedNumbers.length > 0) {
  console.log(`[Config] Access restricted to ${config.allowedNumbers.length} number(s)`);
} else {
  console.log('[Config] Access control: OPEN (all numbers allowed)');
}

export default config;
