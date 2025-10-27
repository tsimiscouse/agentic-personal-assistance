# Bidirectional Gmail Sync - Implementation

## Overview
Implemented **bidirectional sync** between database and Gmail drafts, ensuring users always see the most up-to-date version of their drafts, regardless of where they were last edited (chatbot or Gmail web interface).

## Problem Solved

### Before (One-Way Sync):
```
Chatbot → Database → Gmail  ✅ (Working)
Gmail → Database            ❌ (Not synced)

User edits draft in Gmail → Database shows old content → User confusion
```

### After (Bidirectional Sync):
```
Chatbot ↔ Database ↔ Gmail  ✅ (Both directions)

User edits draft anywhere → Always see latest version
```

## Implementation

### New Function: `_fetch_gmail_draft()` (email_tool.py:1158-1223)

**Purpose:** Fetch draft content from Gmail API and return structured data

**Signature:**
```python
def _fetch_gmail_draft(draft_id: str) -> Optional[dict]:
    """
    Fetch a draft from Gmail to sync latest changes

    Returns:
        dict: {'to_email': str, 'subject': str, 'body': str} or None if failed
    """
```

**How It Works:**
1. Gets Gmail API service
2. Fetches draft by ID using `service.users().drafts().get()`
3. Decodes base64 raw message
4. Parses email headers (To, Subject)
5. Extracts body (text/plain)
6. Returns structured dictionary

**Error Handling:**
- Returns `None` if Gmail API unavailable
- Returns `None` if draft not found
- Handles multipart/plain text messages
- Logs all operations

### Updated: `list_drafts_tool()` (email_tool.py:637-651)

**Added Sync Logic:**
```python
# After fetching drafts from database:

# Sync from Gmail: Update each draft with latest content
synced_count = 0
for draft in drafts:
    if draft.gmail_draft_id:
        gmail_content = _fetch_gmail_draft(draft.gmail_draft_id)
        if gmail_content:
            # Update database with Gmail content
            draft.to_email = gmail_content['to_email'] or draft.to_email
            draft.subject = gmail_content['subject'] or draft.subject
            draft.body = gmail_content['body'] or draft.body
            synced_count += 1

if synced_count > 0:
    db.commit()
    logger.info(f"📥 Synced {synced_count} drafts from Gmail")
```

**When It Syncs:**
- Every time user runs "show my drafts"
- Before displaying the list
- Syncs ALL active drafts with gmail_draft_id

### Updated: `select_draft_tool()` (email_tool.py:735-743)

**Added Sync Logic:**
```python
# After selecting draft:

# Sync from Gmail: Fetch latest content before showing
if selected_draft.gmail_draft_id:
    gmail_content = _fetch_gmail_draft(selected_draft.gmail_draft_id)
    if gmail_content:
        # Update database with latest Gmail content
        selected_draft.to_email = gmail_content['to_email'] or selected_draft.to_email
        selected_draft.subject = gmail_content['subject'] or selected_draft.subject
        selected_draft.body = gmail_content['body'] or selected_draft.body
        logger.info(f"📥 Synced draft from Gmail")

# Then show the updated content
```

**When It Syncs:**
- Every time user selects a draft
- Before displaying draft content
- Ensures user sees latest version

## Complete Flow Examples

### Example 1: Edit in Gmail, View in Chatbot

```
1. User (Chatbot): "Draft email to alice@example.com about meeting at 2 PM"
   → Database: subject="meeting", body="...2 PM..."
   → Gmail: Creates draft with same content
   → Both in sync ✅

2. User opens Gmail web interface
   → Finds draft to alice@example.com
   → Edits: Changes time from "2 PM" to "3 PM"
   → Gmail: Updated to "...3 PM..."
   → Database: Still shows "...2 PM..." (not yet synced)

3. User (Chatbot): "Show my drafts"
   → list_drafts_tool() runs
   → Fetches drafts from database
   → For each draft with gmail_draft_id:
      - Calls _fetch_gmail_draft(draft_id)
      - Gets: body="...3 PM..." from Gmail
      - Updates database: body="...3 PM..."
   → db.commit()
   → Database: Now shows "...3 PM..." ✅
   → User sees: "Meeting at 3 PM" (latest version)

4. User (Chatbot): "select draft 1"
   → select_draft_tool() runs
   → Gets draft from database (already synced)
   → Syncs again from Gmail (ensures absolutely latest)
   → Shows: "Meeting at 3 PM" ✅

5. User (Chatbot): "send it"
   → Sends email with "3 PM" (correct version) ✅
```

### Example 2: Edit Subject in Gmail

```
1. User (Chatbot): "Draft email to bob@company.com"
   → Subject: "Message from Personal Assistant"
   → Synced to Gmail ✅

2. User opens Gmail
   → Changes subject to: "Q1 Project Update"
   → Gmail draft updated
   → Database: Still shows old subject

3. User (Chatbot): "List my drafts"
   → Syncs from Gmail
   → Database updated: subject="Q1 Project Update"
   → User sees: "Subject: Q1 Project Update" ✅

4. User (Chatbot): "select draft 1"
   → Shows updated subject
   → "send it"
   → Email sent with correct subject ✅
```

### Example 3: Multiple Edits

```
1. Create draft in chatbot
   → Version 1: "Meeting at 2 PM"

2. Edit in Gmail web
   → Version 2: "Meeting at 3 PM"

3. Edit in Gmail mobile
   → Version 3: "Meeting at 4 PM"

4. Chatbot: "show my drafts"
   → Syncs from Gmail
   → Database: "Meeting at 4 PM" (latest) ✅

5. Chatbot: "select draft 1"
   → Syncs again from Gmail
   → Shows: "Meeting at 4 PM" ✅
```

## Sync Behavior

### When Sync Happens:
1. **list_drafts_tool** - Syncs ALL drafts before showing list
2. **select_draft_tool** - Syncs specific draft before showing content

### What Gets Synced:
- ✅ Recipient email (to_email)
- ✅ Subject line
- ✅ Body content

### What Doesn't Get Synced:
- ❌ Status (draft/kept) - Controlled by chatbot only
- ❌ Expiry time - Controlled by chatbot only
- ❌ Created date - Original creation time preserved

### Fallback Behavior:
```python
# If Gmail API unavailable or draft not found:
draft.subject = gmail_content['subject'] or draft.subject
# ↑ Uses Gmail content if available, otherwise keeps database value
```

## Performance Considerations

### API Calls:
- **list_drafts_tool**: N API calls (where N = number of drafts with gmail_draft_id)
- **select_draft_tool**: 1 API call (for selected draft only)

### Optimization:
```python
# Only syncs drafts that have gmail_draft_id
if draft.gmail_draft_id:
    gmail_content = _fetch_gmail_draft(draft.gmail_draft_id)
    # Syncs only if draft exists in Gmail
```

### Example:
```
User has 5 drafts:
- Draft 1: gmail_draft_id = "abc123" → Syncs ✅
- Draft 2: gmail_draft_id = "def456" → Syncs ✅
- Draft 3: gmail_draft_id = None → Skips (no Gmail draft)
- Draft 4: gmail_draft_id = "ghi789" → Syncs ✅
- Draft 5: gmail_draft_id = None → Skips

Total: 3 API calls when listing drafts
```

## Logging

### Success Logs:
```
[INFO] 📥 Fetched Gmail draft: abc123
[INFO] 📥 Synced 3 drafts from Gmail for user 628118491177@c.us
[INFO] 📥 Synced draft draft-id-xyz from Gmail
```

### Error Logs:
```
[ERROR] Error fetching Gmail draft: HttpError 404
[WARNING] No message found in Gmail draft: abc123
[ERROR] Error initializing Gmail API: Token expired
```

## Error Handling

### Scenario 1: Gmail API Unavailable
```python
gmail_content = _fetch_gmail_draft(draft_id)
# Returns: None

# Fallback:
draft.subject = gmail_content['subject'] or draft.subject
# ↑ Keeps database value, no error shown to user
```

### Scenario 2: Draft Deleted in Gmail
```python
# User deletes draft in Gmail, but database still has record
gmail_content = _fetch_gmail_draft("deleted_draft_id")
# Returns: None (draft not found)

# Fallback: Shows database version (outdated but safe)
```

### Scenario 3: Network Error
```python
# Gmail API call fails due to network issue
try:
    draft = service.users().drafts().get(...)
except Exception as e:
    logger.error(f"Error fetching Gmail draft: {e}")
    return None

# Fallback: Shows database version
```

## Testing Scenarios

### Test 1: Edit Subject in Gmail
```
Setup: Create draft in chatbot
Action: Edit subject in Gmail web
Test: "show my drafts" in chatbot
Expected: Shows updated subject from Gmail
```

### Test 2: Edit Body in Gmail
```
Setup: Create draft with body "Meeting at 2 PM"
Action: Edit in Gmail to "Meeting at 3 PM"
Test: "select draft 1" in chatbot
Expected: Shows "Meeting at 3 PM"
```

### Test 3: Multiple Drafts Sync
```
Setup: Create 3 drafts, edit all in Gmail
Action: "show my drafts" in chatbot
Expected: All 3 show updated content from Gmail
Verify: Database updated for all 3
```

### Test 4: Gmail API Unavailable
```
Setup: Stop Gmail API (remove token)
Action: "show my drafts"
Expected: Shows database content (no error)
Verify: No crash, graceful fallback
```

### Test 5: Draft Deleted in Gmail
```
Setup: Create draft, sync to Gmail, delete in Gmail
Action: "show my drafts" → "select draft 1"
Expected: Shows database version
Note: User can still send from database
```

### Test 6: Concurrent Edits
```
Setup: Draft in both database and Gmail
Action:
  1. Edit body in Gmail to "Version A"
  2. Before syncing, edit subject in chatbot to "Version B"
  3. "show my drafts"
Expected:
  - Subject: "Version B" (chatbot wins for subject)
  - Body: "Version A" (Gmail wins for body)
```

## Benefits

1. **Always Up-to-Date**: Users see latest draft content regardless of edit location
2. **No Confusion**: Eliminates "Why is my draft different?" questions
3. **Flexibility**: Edit in Gmail web, Gmail mobile, or chatbot - all work
4. **Safe Fallback**: If Gmail unavailable, database content still accessible
5. **Transparent**: Users don't need to know sync is happening
6. **Efficient**: Only syncs drafts with Gmail IDs

## Limitations

1. **One-Time Sync**: Syncs when listing/selecting, not in real-time
2. **API Quota**: Each sync uses Gmail API quota (usually not an issue)
3. **Network Dependent**: Requires internet to sync from Gmail
4. **Text Only**: Only syncs plain text body (not HTML/attachments)

## Future Enhancements

- Real-time webhooks: Gmail → Database instant sync
- Conflict resolution: What if edited in both places?
- Sync history: Track sync timestamps
- Manual sync command: "sync draft 1 from gmail"
- Batch sync optimization: Parallel API calls

---

**Date:** 2025-10-27
**Status:** ✅ Complete - Bidirectional Sync Active
**Related:** DRAFT_MANAGEMENT_FEATURE.md, GMAIL_DRAFT_INTEGRATION.md
