# Changelog - IIoT Gateway

## Version 2.1.0 (2026-01-21)

### Major UI/UX Improvements

#### Dashboard Redesign
- **Removed**: Temperature (Live) chart from main dashboard
  - Simplified dashboard layout for better focus on system status
  - Removed Chart.js dependencies from dashboard page
  - Cleaned up unused JavaScript functions (updateTemperatureChart)
  
- **Enhanced Status Display**: 
  - Improved real-time connection status monitoring
  - Added comprehensive error handling and debug logging
  - Dashboard now properly reflects actual connection states from Configuration page
  - Fixed synchronization between Configuration and Dashboard status indicators

#### Navigation Menu Update
- **Renamed**: "Variables" → "OPC-UA Variables"
  - Provides clearer indication of functionality
  - Distinguishes OPC-UA variables from MQTT variables
  - Better aligns with industrial automation terminology

#### Unified Page Styling
All pages now share consistent design language:
- **Page Headers**: 
  - Consistent `.page-wrapper` and `.page-header` classes
  - Uniform emoji icons for quick visual identification
  - Blue bottom border (3px solid #3498db) across all pages
  
- **Buttons**: 
  - Enhanced with smooth hover effects (translateY, box-shadow)
  - Consistent color scheme across all button types:
    - Primary: #3498db (blue)
    - Success: #27ae60 (green)
    - Warning: #f39c12 (orange)
    - Danger: #e74c3c (red)
    - Info: #17a2b8 (teal)
    - Secondary: #95a5a6 (gray)
  - All buttons now have 0.3s transition animations
  - Proper disabled state styling (opacity: 0.6)
  
- **Cards**: 
  - Consistent shadow (0 2px 8px rgba(0,0,0,0.1))
  - Hover effect (0 4px 12px rgba(0,0,0,0.15))
  - Unified padding (20px) and border-radius (8px)
  - Card headers (h3) with consistent styling
  
- **Tables**: 
  - Dark header background (#34495e) with white text
  - Uppercase header text with letter-spacing
  - Smooth row hover transitions
  - Consistent padding and borders
  
- **Control Sections**: 
  - Flexbox layout with proper spacing (gap: 10-15px)
  - Wrap-friendly for responsive design
  - Consistent across Dashboard, Variables, MQTT Monitor, Configuration, and Logs pages

### Critical Bug Fixes

#### Unicode Encoding Error (Windows Console)
- **Problem**: Application crashed with `UnicodeEncodeError` when logging messages containing Unicode characters (→, ←, emojis)
- **Root Cause**: Windows console uses cp1252 encoding by default, which doesn't support Unicode
- **Solution Applied**:
  ```python
  # In run.py
  if sys.platform == 'win32':
      try:
          import codecs
          sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
          sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')
      except Exception:
          pass
  ```
- **Files Modified**:
  - `run.py` - Main application logging
  - `test_opcua_connection.py` - Test script logging
  - `test_opcua_connection_simple.py` - Simple test script logging
- **Result**: 
  - All Unicode characters now display correctly on Windows
  - No more encoding crashes
  - Error handling with 'replace' mode prevents future issues
  - Cross-platform compatibility (Windows, Linux, Raspberry Pi)

#### Dashboard Status Synchronization
- **Problem**: Dashboard showed all services as "Disconnected" (red) even when Configuration page showed them as connected
- **Root Cause**: 
  - Potential null checks missing in system info endpoint
  - JavaScript error handling not providing feedback
  - Chart.js initialization failing due to removed temperature chart
- **Solution Applied**:
  - Added null safety checks in `/api/system/info` endpoint
  - Enhanced error handling with debug logging on both server and client
  - Added console.log statements for troubleshooting
  - Removed temperature chart initialization code
  - Improved error responses with success flags
- **Files Modified**:
  - `app/api/data_routes.py` - Enhanced system_info endpoint
  - `app/static/js/dashboard.js` - Improved error handling and logging

### Technical Improvements

#### Code Quality
- **Removed Duplicate Code**: Eliminated duplicate button style definitions in CSS
- **Better Error Handling**: Added try-catch blocks with detailed logging
- **Debug Logging**: Server-side logging for connection states
- **Console Logging**: Client-side debugging for API responses

#### Performance
- **Reduced Dependencies**: Removed unused Chart.js functionality
- **Optimized CSS**: Consolidated duplicate styles
- **Cleaner JavaScript**: Removed unused functions and event handlers

#### Maintainability
- **Consistent Code Style**: Unified formatting across all templates
- **Better Documentation**: Added inline comments for complex logic
- **Clear Separation**: Page-specific styles vs. global styles

### Files Changed

#### Templates
- `app/templates/base.html` - Updated navigation menu
- `app/templates/index.html` - Removed temperature chart, added page wrapper
- `app/templates/variables.html` - Added consistent page styling
- `app/templates/configuration.html` - Added page wrapper and header
- `app/templates/mqtt_monitor.html` - Moved inline styles to CSS, added wrapper
- `app/templates/logs.html` - Added consistent page styling

#### Static Assets
- `app/static/css/style.css` - Major styling overhaul:
  - Added `.page-wrapper` and `.page-header` classes
  - Enhanced button styles with animations
  - Improved card and table styling
  - Added MQTT monitor specific styles
  - Removed duplicate definitions
  - Added consistent control section styling

- `app/static/js/dashboard.js` - Bug fixes and improvements:
  - Removed temperature chart code
  - Added debug logging
  - Enhanced error handling
  - Fixed status update logic

#### Backend
- `app/api/data_routes.py` - Enhanced system_info endpoint:
  - Added null safety checks
  - Debug logging for connection states
  - Better error responses
  - Consistent return format

- `run.py` - UTF-8 encoding fix:
  - Windows console encoding configuration
  - UTF-8 file handlers
  - Proper error handling

#### Tests
- `test_opcua_connection.py` - UTF-8 encoding support
- `test_opcua_connection_simple.py` - UTF-8 encoding support

### Migration Notes

#### For Existing Installations
1. **No Database Changes**: No schema updates required
2. **No Configuration Changes**: Existing `.env` files work as-is
3. **Browser Cache**: Users may need to clear browser cache to see CSS changes
4. **Restart Required**: Application restart needed for encoding fixes

#### For Developers
1. **CSS Classes**: Use `.page-wrapper` and `.page-header` for new pages
2. **Buttons**: Use existing `.btn-*` classes, no custom styles needed
3. **Logging**: All logging now supports Unicode characters
4. **Error Handling**: Follow new pattern in dashboard.js for API calls

### Breaking Changes
- **None**: All changes are backward compatible

### Known Issues
- None reported

### Upgrade Instructions

```bash
# Pull latest changes
git pull

# Restart the application
sudo systemctl restart iiot-gateway

# Or if running manually:
pkill -f run.py
python run.py
```

### Testing Checklist
- [x] Dashboard displays correct connection statuses
- [x] All buttons have consistent styling
- [x] Page headers are uniform across all pages
- [x] Unicode characters display correctly in logs
- [x] No console errors on page load
- [x] Status updates every 5 seconds on dashboard
- [x] MQTT Monitor styling matches other pages
- [x] Configuration page styling consistent
- [x] Variables page renamed to "OPC-UA Variables"
- [x] Temperature chart removed from dashboard
- [x] All tables have consistent styling
- [x] Hover effects work on all interactive elements

### Future Improvements
- Consider adding system health metrics to dashboard
- Add user preferences for theme/styling
- Implement dashboard widgets system
- Add export functionality for logs and data
- Create mobile-responsive views
