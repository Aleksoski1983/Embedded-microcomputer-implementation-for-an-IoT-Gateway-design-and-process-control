# Configuration Page Testing Guide

## 🎯 Quick Test Scenarios

### ✅ Scenario 1: Test Connection with Current Settings
**Steps:**
1. Open http://127.0.0.1:5001/configuration
2. Verify endpoint shows: `opc.tcp://10.210.76.161:4840`
3. Verify security shows: `None` / `None`
4. Click **🔍 Test Connection** button
5. **Expected:** 
   - Button shows "🔍 Testing..."
   - Status badge changes to "Testing..." (blue)
   - After ~2-3 seconds, result dialog appears
   - If successful: "✓ Connection Test Successful!" with namespace count
   - If failed: "✗ Connection Test Failed!" with specific error
   - Status badge resets after 3 seconds

**What This Tests:**
- Test endpoint using asyncua library
- Security policy handling (None/None)
- Error message clarity
- UI feedback during operation

---

### ✅ Scenario 2: Save Configuration and Reconnect
**Steps:**
1. Keep current settings (or modify endpoint/timeout)
2. Click **💾 Save & Reconnect** button
3. **Expected:**
   - Confirmation dialog appears with settings summary
   - Click "OK" to confirm
   - Button shows "Saving..."
   - Success notification: "✓ OPC UA configuration saved successfully!"
   - Configuration reloads
   - Status updates automatically
   - Connection attempt with new settings

**What This Tests:**
- Configuration persistence to .env file
- Runtime config update
- Automatic reconnection
- Status synchronization

---

### ✅ Scenario 3: Manual Disconnect/Connect
**Steps:**

**Part A - Disconnect:**
1. If status shows "✓ Connected", click **🔌 Disconnect**
2. **Expected:**
   - Confirmation dialog: "Disconnect from OPC UA server?"
   - Click "OK"
   - Button shows "🔌 Disconnecting..."
   - Status badge changes to "Disconnecting..." (yellow)
   - Success notification: "✓ Disconnected from OPC UA server successfully"
   - Status updates to "✗ Disconnected" (gray)
   - Disconnect button hides
   - Connect button appears

**Part B - Reconnect:**
1. Click **🔌 Connect** button
2. **Expected:**
   - Button shows "🔌 Connecting..."
   - Status badge changes to "Connecting..." (blue)
   - After connection: "✓ Connected to OPC UA server successfully"
   - Status updates to "✓ Connected" (green)
   - Connect button hides
   - Disconnect button appears

**What This Tests:**
- Manual connection control
- Button state management
- Status badge transitions
- Smooth UI feedback

---

### ✅ Scenario 4: Test Different Security Settings
**Steps:**
1. Change Security Policy to: `Basic256Sha256`
2. Change Security Mode to: `Sign`
3. Click **🔍 Test Connection** button
4. **Expected:**
   - Test attempts connection with new security
   - If server supports: Success message
   - If server doesn't support: Clear error about security mismatch
   - Settings NOT saved (test only)

**Repeat for:**
- None/None (anonymous)
- Basic256Sha256/Sign
- Basic256Sha256/SignAndEncrypt
- Basic256/SignAndEncrypt
- Basic128Rsa15/Sign

**What This Tests:**
- All security configuration support
- Security policy mapping
- Security mode handling
- Error messages for unsupported security

---

### ✅ Scenario 5: Test Invalid Endpoint
**Steps:**
1. Enter invalid endpoint: `opc.tcp://192.168.99.99:4840`
2. Set timeout to: `5` seconds
3. Click **🔍 Test Connection**
4. **Expected:**
   - Test runs for ~5 seconds
   - Error dialog: "✗ Connection Test Failed!"
   - Message: "Connection timeout after 5s. Server may be unreachable or slow to respond."
   - Clear troubleshooting tips displayed
   - Status badge shows "✗ Test Failed" (red)
   - Resets after 3 seconds

**What This Tests:**
- Timeout handling
- Connection error detection
- User-friendly error messages
- Graceful failure handling

---

### ✅ Scenario 6: Status Synchronization
**Steps:**
1. Open http://127.0.0.1:5001/ (dashboard) in another tab
2. Keep configuration page open in first tab
3. On configuration page, click **🔌 Disconnect**
4. **Expected:**
   - Configuration page updates immediately
   - Dashboard page updates within 5 seconds
   - Both show "Disconnected" status
5. Click **🔌 Connect** on configuration page
6. **Expected:**
   - Both pages update to "Connected"
   - Status stays synchronized

**What This Tests:**
- Cross-page status synchronization
- Socket event emission
- Polling updates (5-second interval)
- Real-time status propagation

---

## 🔍 Visual Indicators Guide

### Button States
```
Test Connection:
├─ Normal: "🔍 Test Connection" (blue, enabled)
├─ Testing: "🔍 Testing..." (blue, disabled)
└─ Reset: Auto-resets after test completes

Save & Reconnect:
├─ Normal: "💾 Save & Reconnect" (blue, enabled)
├─ Saving: "Saving..." (blue, disabled)
└─ Reset: Auto-resets after save completes

Disconnect (when connected):
├─ Normal: "🔌 Disconnect" (yellow, enabled)
├─ Active: "🔌 Disconnecting..." (yellow, disabled)
└─ Result: Hides after successful disconnect

Connect (when disconnected):
├─ Normal: "🔌 Connect" (green, enabled)
├─ Active: "🔌 Connecting..." (green, disabled)
└─ Result: Hides after successful connect
```

### Status Badge Colors
```
✓ Connected       → Green (badge-success)
✗ Disconnected    → Gray (badge-secondary)
Testing...        → Blue (badge-info)
Connecting...     → Blue (badge-info)
Disconnecting...  → Yellow (badge-warning)
✗ Test Failed     → Red (badge-danger)
⚠ Error          → Red (badge-danger)
```

---

## 🐛 Troubleshooting

### Issue: Test always fails
**Check:**
1. Is the OPC UA server running?
2. Is the endpoint URL correct?
3. Can you ping the server IP?
4. Is firewall blocking port 4840?
5. Do security settings match server requirements?

**Quick Diagnostic:**
```powershell
# Check if server is reachable
Test-NetConnection -ComputerName 10.210.76.161 -Port 4840

# Check if server responds to OPC UA
# (Should see socket connection in logs)
```

### Issue: Configuration not saving
**Check:**
1. Is `.env` file writable?
2. Are there any error messages in browser console (F12)?
3. Is Flask server running?
4. Check server logs for errors

### Issue: Buttons not showing/hiding
**Check:**
1. Open browser console (F12)
2. Look for JavaScript errors
3. Check `updateConnectionStatus()` is running (logs every 5s)
4. Verify status endpoint returns data: `GET /opcua/client/status`

### Issue: Status not synchronizing
**Check:**
1. Is Socket.IO connected? (check browser console)
2. Are both pages loaded completely?
3. Is polling active? (should see status requests every 5s)
4. Check if `status_sync` events are emitted

---

## 📊 Expected Test Results

| Test | Expected Result | Status |
|------|----------------|--------|
| Test with None/None | Should connect if server available | ⏳ Pending |
| Test with Basic256 | Depends on server support | ⏳ Pending |
| Save configuration | Settings persist to .env | ⏳ Pending |
| Manual disconnect | Clean disconnect, button states update | ⏳ Pending |
| Manual connect | Successful reconnect | ⏳ Pending |
| Invalid endpoint | Clear error message within timeout | ⏳ Pending |
| Cross-tab sync | Both tabs show same status | ⏳ Pending |

---

## ✅ Verification Checklist

After testing, verify:

- [ ] Test connection works for all security modes
- [ ] Configuration saves to `.env` file
- [ ] Settings persist after server restart
- [ ] Disconnect button shows when connected
- [ ] Connect button shows when disconnected
- [ ] Test button always available
- [ ] Save button always available
- [ ] Status badge updates correctly
- [ ] Error messages are clear and helpful
- [ ] Notifications appear for all actions
- [ ] Status syncs across browser tabs
- [ ] No JavaScript console errors
- [ ] No Python errors in server logs

---

## 🎯 Current Status

**Server Running:** ✅ Yes
- URL: http://127.0.0.1:5001
- URL: http://10.210.76.156:5001
- Configuration Page: /configuration
- Dashboard: /

**Known Issues:**
- Initial connection to `opc.tcp://10.210.76.161:4840` timing out
- This is expected - test with your actual PLC endpoint

**Next Action:**
1. Open http://127.0.0.1:5001/configuration
2. Try **Test Connection** with your S7-1500 PLC
3. Save configuration if test succeeds
4. Verify all button states work correctly

---

## 📞 Support

If you encounter any issues:
1. Check browser console (F12 → Console tab)
2. Check server logs in terminal
3. Verify network connectivity to PLC
4. Test with different security settings
5. Try manual disconnect/reconnect

**All features are now ready for testing!** 🚀
