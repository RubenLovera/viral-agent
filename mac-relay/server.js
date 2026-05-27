#!/usr/bin/env node
/**
 * mac-relay — HTTP server that bridges VPS → iMessage via osascript.
 * Runs on Mac at port 3737, called by viral_bot on the VPS.
 *
 * Start: node server.js
 * Persist: launchd (com.culveros.mac-relay.plist)
 */
const express = require('express');
const { execSync } = require('child_process');

const app  = express();
const PORT = parseInt(process.env.PORT || '3737', 10);
const RELAY_KEY = process.env.MAC_RELAY_KEY || process.env.RELAY_KEY;

if (!RELAY_KEY) {
  console.error('MAC_RELAY_KEY env var required');
  process.exit(1);
}

app.use(express.json());

function auth(req, res, next) {
  if (req.headers['x-relay-key'] !== RELAY_KEY) {
    return res.status(401).json({ ok: false, error: 'Unauthorized' });
  }
  next();
}

// Sanitize message for osascript — escape backslashes, quotes, newlines.
function escapeForAppleScript(s) {
  return s
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '');
}

// ── POST /imessage — send a single iMessage ────────────────────────────────

app.post('/imessage', auth, (req, res) => {
  const { to, message } = req.body;
  if (!to || !message) {
    return res.status(400).json({ ok: false, error: 'Missing to or message' });
  }

  const safeMsg = escapeForAppleScript(message);
  const script = `
tell application "Messages"
  set targetService to 1st service whose service type = iMessage
  set targetBuddy to buddy "${to}" of targetService
  send "${safeMsg}" to targetBuddy
end tell
  `.trim();

  try {
    execSync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 10000 });
    res.json({ ok: true });
  } catch (err) {
    console.error('osascript error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ── POST /create-group — create iMessage group + send first message ────────

app.post('/create-group', auth, (req, res) => {
  const { participants, name, initial_message } = req.body;
  if (!participants || !Array.isArray(participants) || participants.length === 0) {
    return res.status(400).json({ ok: false, error: 'Missing participants array' });
  }

  const buddyLines = participants
    .map(p => `buddy "${p}" of targetService`)
    .join(', ');
  const safeMsg = initial_message ? escapeForAppleScript(initial_message) : '';

  const script = `
tell application "Messages"
  set targetService to 1st service whose service type = iMessage
  set theChat to make new chat with properties {participants: {${buddyLines}}}
  ${name ? `set name of theChat to "${escapeForAppleScript(name)}"` : ''}
  ${safeMsg ? `send "${safeMsg}" to theChat` : ''}
end tell
  `.trim();

  try {
    execSync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 15000 });
    res.json({ ok: true });
  } catch (err) {
    console.error('create-group error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ── POST /send-group — send message to an existing iMessage group chat ────

app.post('/send-group', auth, (req, res) => {
  const { chat_identifier, message } = req.body;
  if (!chat_identifier || !message) {
    return res.status(400).json({ ok: false, error: 'Missing chat_identifier or message' });
  }

  const safeMsg  = escapeForAppleScript(message);
  // AppleScript chat id format for group chats is "any;+;{uuid}"
  const fullId   = `any;+;${chat_identifier}`;
  const safeId   = fullId.replace(/'/g, "\\'");

  const script = `
tell application "Messages"
  set theChat to a reference to chat id "${safeId}"
  send "${safeMsg}" to theChat
end tell
  `.trim();

  try {
    execSync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 10000 });
    res.json({ ok: true });
  } catch (err) {
    console.error('send-group error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ── Health check ───────────────────────────────────────────────────────────

app.get('/health', (req, res) => {
  res.json({ ok: true, ts: new Date().toISOString() });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`mac-relay listening on port ${PORT}`);
});
