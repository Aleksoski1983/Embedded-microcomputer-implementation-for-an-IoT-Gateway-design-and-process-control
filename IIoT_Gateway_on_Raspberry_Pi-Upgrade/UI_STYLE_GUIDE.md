# UI Style Guide - IIoT Gateway

## Design Philosophy

The IIoT Gateway web interface follows a clean, industrial design aesthetic with consistent styling across all pages. The design prioritizes:
- **Clarity**: Clear visual hierarchy and intuitive navigation
- **Consistency**: Unified colors, spacing, and component styling
- **Responsiveness**: Adaptive layouts for different screen sizes
- **Accessibility**: High contrast and readable typography
- **Professional**: Industrial-grade appearance suitable for manufacturing environments

## Color Palette

### Primary Colors
```css
--primary: #3498db      /* Blue - Primary actions, links, highlights */
--success: #27ae60      /* Green - Success states, connected status */
--warning: #f39c12      /* Orange - Warnings, caution states */
--danger: #e74c3c       /* Red - Errors, disconnected, delete actions */
--info: #17a2b8         /* Teal - Information, test actions */
--secondary: #95a5a6    /* Gray - Secondary actions, disabled states */
```

### Neutral Colors
```css
--dark: #2c3e50         /* Navigation, headers, primary text */
--dark-secondary: #34495e /* Table headers, card titles */
--gray: #7f8c8d         /* Secondary text, hints */
--light-gray: #ecf0f1   /* Borders, dividers */
--background: #f5f5f5   /* Page background */
--white: #ffffff        /* Card backgrounds, light text */
```

### Status Colors
```css
--online: #27ae60       /* Connected, active, online */
--offline: #e74c3c      /* Disconnected, inactive, offline */
```

## Typography

### Font Family
```css
font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
```

### Font Sizes
- **Page Headers (h2)**: 1.8rem (28.8px)
- **Section Headers (h3)**: 1.3rem (20.8px)
- **Body Text**: 1rem (16px)
- **Small Text**: 0.9rem (14.4px)
- **Table Headers**: 0.9rem (14.4px) uppercase

### Font Weights
- **Headers**: 600 (semi-bold)
- **Buttons**: 500 (medium)
- **Table Headers**: 600 (semi-bold)
- **Body Text**: 400 (normal)

## Layout Components

### Page Structure

All pages should follow this structure:
```html
<div class="page-wrapper [page-specific-class]">
    <div class="page-header">
        <h2>[emoji] Page Title</h2>
    </div>
    
    <!-- Page content -->
    <div class="card">
        <!-- Card content -->
    </div>
</div>
```

### Page Wrapper
```css
.page-wrapper {
    max-width: 100%;
}

.page-header {
    margin-bottom: 25px;
    padding-bottom: 15px;
    border-bottom: 3px solid #3498db;
}

.page-header h2 {
    color: #2c3e50;
    font-size: 1.8rem;
    font-weight: 600;
    margin: 0;
}
```

## UI Components

### Buttons

#### Button Classes
```html
<!-- Primary action -->
<button class="btn btn-primary">Save</button>

<!-- Success/Confirm action -->
<button class="btn btn-success">Connect</button>

<!-- Warning/Caution action -->
<button class="btn btn-warning">Disconnect</button>

<!-- Danger/Delete action -->
<button class="btn btn-danger">Delete</button>

<!-- Info/Test action -->
<button class="btn btn-info">Test Connection</button>

<!-- Secondary/Cancel action -->
<button class="btn btn-secondary">Cancel</button>

<!-- Small button -->
<button class="btn btn-sm btn-primary">🔄 Refresh</button>
```

#### Button Styling
```css
.btn {
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.3s ease;
    font-weight: 500;
}

.btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
```

### Cards

#### Card Structure
```html
<div class="card">
    <h3>Card Title</h3>
    <!-- Card content -->
</div>
```

#### Card Styling
```css
.card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: box-shadow 0.3s ease;
}

.card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.card h3 {
    color: #2c3e50;
    margin-top: 0;
    margin-bottom: 15px;
    font-size: 1.3rem;
    font-weight: 600;
}
```

### Tables

#### Table Structure
```html
<table>
    <thead>
        <tr>
            <th>Column 1</th>
            <th>Column 2</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Data 1</td>
            <td>Data 2</td>
            <td><button class="btn btn-sm btn-primary">Edit</button></td>
        </tr>
    </tbody>
</table>
```

#### Table Styling
```css
table {
    width: 100%;
    border-collapse: collapse;
    background: white;
}

table th {
    background-color: #34495e;
    color: white;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.9rem;
    letter-spacing: 0.5px;
    padding: 12px;
    text-align: left;
}

table td {
    padding: 12px;
    border-bottom: 1px solid #ecf0f1;
}

table tbody tr {
    transition: background-color 0.2s ease;
}

table tbody tr:hover {
    background-color: #f8f9fa;
}
```

### Status Indicators

#### Status Dots
```html
<div class="status-indicator">
    <span class="status-dot online"></span>
    <span class="status-text">Connected</span>
</div>
```

```css
.status-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-dot.online {
    background-color: #27ae60;
    box-shadow: 0 0 5px #27ae60;
}

.status-dot.offline {
    background-color: #e74c3c;
}
```

#### Badge Indicators
```html
<span class="badge badge-success">Connected</span>
<span class="badge badge-danger">Error</span>
<span class="badge badge-warning">Warning</span>
<span class="badge badge-info">Testing</span>
<span class="badge badge-secondary">Disabled</span>
```

```css
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
}

.badge-success {
    background-color: #27ae60;
    color: white;
}

.badge-danger {
    background-color: #e74c3c;
    color: white;
}
```

### Form Controls

#### Form Group
```html
<div class="form-group">
    <label>Field Label:</label>
    <input type="text" class="form-control" placeholder="Enter value">
    <small>Helpful hint text</small>
</div>
```

```css
.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 5px;
    color: #34495e;
}

.form-control {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
    width: 100%;
}

.form-control:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}
```

### Control Sections

#### Controls Container
```html
<div class="controls">
    <button class="btn btn-primary">Action 1</button>
    <button class="btn btn-secondary">Action 2</button>
    <span class="status-message">Status text</span>
</div>
```

```css
.controls {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
}
```

## Page-Specific Styling

### Dashboard
- **Status Cards**: Grid layout, 4 columns on desktop
- **Device Table**: Full-width, hover effects
- **Database Status**: Prominent display with color coding

### OPC-UA Variables
- **Tree Browser**: Collapsible navigation tree
- **Variable Table**: Gradient header, hover effects
- **Toggle Indicators**: Database storage visualization

### MQTT Monitor
- **Stats Grid**: 4-column grid for metrics
- **Message Display**: Dark terminal-style display
- **Topic Table**: Live updating statistics

### Configuration
- **Section Cards**: Color-coded left borders
- **Info Boxes**: Context-specific backgrounds
- **Form Sections**: Grouped related settings

### Logs
- **Log Display**: Dark background, monospace font
- **Auto-scroll**: Terminal-style log viewing
- **Controls**: Simple refresh and clear actions

## Icons and Emojis

Emojis are used consistently for quick visual identification:

- 📊 Dashboard
- 🔧 OPC-UA Variables
- 📡 MQTT Monitor
- ⚙️ Configuration
- 📋 Logs
- 🔍 Browse/Search
- ➕ Add
- 🗑️ Delete
- 💾 Save/Database
- 🔄 Refresh
- 🔌 Connect/Disconnect
- ✅ Success
- ❌ Error
- ⚠️ Warning

## Responsive Design

### Breakpoints
```css
/* Mobile: < 768px */
@media (max-width: 768px) {
    .variables-container {
        grid-template-columns: 1fr;
    }
    
    .status-cards {
        grid-template-columns: 1fr;
    }
    
    .navbar .container {
        flex-direction: column;
    }
}
```

### Mobile Considerations
- Navigation menu stacks vertically on mobile
- Card grids collapse to single column
- Tables remain scrollable horizontally
- Buttons remain touch-friendly (min 44px height)

## Animations and Transitions

### Standard Transitions
```css
/* Button hover */
transition: all 0.3s ease;

/* Row hover */
transition: background-color 0.2s ease;

/* Box shadow */
transition: box-shadow 0.3s ease;
```

### Hover Effects
- **Buttons**: Slight lift (translateY) + shadow
- **Cards**: Enhanced shadow
- **Table Rows**: Background color change
- **Links**: Color change

## Best Practices

### Do's ✅
- Use consistent spacing (10px, 15px, 20px increments)
- Apply proper semantic HTML (h2 for page titles, h3 for sections)
- Include hover states for interactive elements
- Use flexbox for control sections
- Add appropriate ARIA labels for accessibility
- Use emoji icons for quick visual identification
- Maintain consistent button sizing within a section

### Don'ts ❌
- Don't use inline styles (use CSS classes)
- Don't mix different button styles in same context
- Don't create custom colors outside the palette
- Don't use absolute positioning unless necessary
- Don't forget mobile responsiveness
- Don't use custom fonts (stick to system fonts)
- Don't create deeply nested CSS selectors

## Implementation Checklist

When creating a new page:
- [ ] Use `.page-wrapper` and `.page-header` classes
- [ ] Add emoji icon to page title
- [ ] Use `.card` class for content sections
- [ ] Apply standard `.btn` classes for buttons
- [ ] Use `.controls` for action groups
- [ ] Implement proper form groups with `.form-group`
- [ ] Add status indicators where appropriate
- [ ] Test responsive behavior
- [ ] Verify hover effects work
- [ ] Check console for errors
- [ ] Test with browser cache cleared

## Code Examples

### Complete Page Template
```html
{% extends "base.html" %}

{% block title %}Page Title - IIoT Gateway{% endblock %}

{% block content %}
<div class="page-wrapper my-page">
    <div class="page-header">
        <h2>🎯 Page Title</h2>
    </div>
    
    <div class="controls">
        <button class="btn btn-primary">Primary Action</button>
        <button class="btn btn-secondary">Secondary Action</button>
        <span class="status-message" id="status"></span>
    </div>
    
    <div class="card">
        <h3>Section Title</h3>
        <p class="help-text">Description of this section</p>
        
        <table>
            <thead>
                <tr>
                    <th>Column 1</th>
                    <th>Column 2</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="table-body">
                <tr>
                    <td>Data</td>
                    <td>
                        <span class="badge badge-success">Active</span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-info">Edit</button>
                        <button class="btn btn-sm btn-danger">Delete</button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script src="{{ url_for('static', filename='js/my-page.js') }}"></script>
{% endblock %}
```

## Resources

- **CSS File**: `app/static/css/style.css`
- **Base Template**: `app/templates/base.html`
- **Example Pages**: All pages in `app/templates/`
- **JavaScript**: `app/static/js/*.js`

## Version History

- **v2.1.0** (2026-01-21): Initial unified style guide, consistent design system implementation
