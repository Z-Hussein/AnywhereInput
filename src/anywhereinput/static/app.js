/*
 * AnywhereInput Client - Entry Point
 */

import { AnywhereInputClient } from './core/AnywhereInputClient.js';

const client = new AnywhereInputClient();

// Expose to window for debugging (optional, remove in production)
if (typeof window !== 'undefined') {
    window.aiClient = client;
}
