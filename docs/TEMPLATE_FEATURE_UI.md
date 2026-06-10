# Template Feature UI Layout

## Location in Application
The template management interface is located in the main **"🎙️ Podcast Creator"** tab, under the **"📋 Templates"** accordion section (collapsed by default).

## UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 📋 Templates                                               [▼]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Save and load your podcast settings as templates for quick       │
│ access. Templates include intro/outro, background music, and     │
│ processing options.                                               │
│                                                                   │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ Select Template                                           │   │
│ │ ┌─────────────────────────────────────────────────────┐   │   │
│ │ │ [Select...                                      ▼]  │   │   │
│ │ └─────────────────────────────────────────────────────┘   │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│ ┌──────────────────────────┐ ┌──────────────────────────────┐   │
│ │  📂 Load Template        │ │  🗑️ Delete Template          │   │
│ └──────────────────────────┘ └──────────────────────────────┘   │
│                                                                   │
│ Save Current Settings as Template                                │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────┐     │
│ │ Template Name                                           │     │
│ │ ┌─────────────────────────────────┐ ┌─────────────────┐ │     │
│ │ │ e.g., My Weekly Podcast         │ │ 💾 Save Template│ │     │
│ │ └─────────────────────────────────┘ └─────────────────┘ │     │
│ └─────────────────────────────────────────────────────────┘     │
│                                                                   │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ Template Status                                           │   │
│ │ ┌─────────────────────────────────────────────────────┐   │   │
│ │ │                                                       │   │   │
│ │ │                                                       │   │   │
│ │ └─────────────────────────────────────────────────────┘   │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### 1. Select Template Dropdown
- **Type**: Dropdown/Select component
- **Purpose**: Display and select from available templates
- **Behavior**: 
  - Shows all saved template names alphabetically
  - Initially shows the active template (if any)
  - Updates after save/delete operations
  - Empty if no templates exist

### 2. Load Template Button
- **Label**: "📂 Load Template"
- **Style**: Secondary button, small size
- **Purpose**: Apply selected template to current settings
- **Behavior**:
  - Requires template selection
  - Loads all settings from template
  - Updates status message
  - Sets template as active

### 3. Delete Template Button
- **Label**: "🗑️ Delete Template"  
- **Style**: Secondary button, small size
- **Purpose**: Remove selected template permanently
- **Behavior**:
  - Requires template selection
  - Deletes template file
  - Updates dropdown list
  - Updates status message
  - Clears active template if deleted

### 4. Template Name Input
- **Type**: Text input field
- **Placeholder**: "e.g., My Weekly Podcast"
- **Purpose**: Name for new template
- **Validation**: 
  - Cannot be empty
  - Sanitized (alphanumeric, spaces, hyphens, underscores)

### 5. Save Template Button
- **Label**: "💾 Save Template"
- **Style**: Primary button, small size
- **Purpose**: Save current settings as new template
- **Behavior**:
  - Requires template name
  - Saves all current settings
  - Updates dropdown list
  - Clears name input
  - Updates status message
  - Sets new template as active

### 6. Template Status
- **Type**: Read-only text area (2 lines)
- **Purpose**: Display operation results and messages
- **Messages**:
  - Success: "✅ Template 'Name' saved successfully"
  - Error: "❌ Please enter a template name"
  - Load: "✅ Template 'Name' loaded successfully"
  - Delete: "✅ Template 'Name' deleted successfully"

## User Interaction Flow

### Scenario 1: Save Current Settings
1. User configures intro, outro, background music, and processing options
2. Opens "📋 Templates" accordion
3. Enters name in "Template Name" field (e.g., "My Weekly Show")
4. Clicks "💾 Save Template" button
5. Status shows: "✅ Template 'My Weekly Show' saved successfully"
6. Dropdown updates to include "My Weekly Show"
7. Template name field clears

### Scenario 2: Load Existing Template
1. Opens "📋 Templates" accordion
2. Selects "My Weekly Show" from dropdown
3. Clicks "📂 Load Template" button
4. All settings update automatically
5. Status shows: "✅ Template 'My Weekly Show' loaded successfully"

### Scenario 3: Delete Template
1. Opens "📋 Templates" accordion
2. Selects "Old Template" from dropdown
3. Clicks "🗑️ Delete Template" button
4. Template is removed
5. Dropdown updates (no longer shows "Old Template")
6. Status shows: "✅ Template 'Old Template' deleted successfully"

## Visual Design

### Colors & Styling
- Accordion header: Standard Gradio accordion style
- Primary button (Save): Blue/primary color
- Secondary buttons (Load/Delete): Gray/secondary color
- Status success (✅): Green text
- Status error (❌): Red text
- Text inputs: Standard Gradio input styling

### Spacing
- Accordion: Standard Gradio spacing
- Buttons in row: Gap of 10px between buttons
- Sections: Consistent vertical spacing
- Status area: 2 lines height

### Responsiveness
- Buttons scale with container
- Dropdown full width
- Text input takes 2/3 width, save button 1/3 width (in row)
- Works on mobile and desktop

## Integration with Existing UI

The template section is positioned:
- **After**: "📥 Download & Import Settings" accordion
- **Before**: Hidden realtime console component
- **Within**: Main settings column (left side of Podcast Creator tab)
- **Near**: Export/Import settings for related functionality

## Accessibility

- All buttons have descriptive labels with emojis
- Status messages are clear and actionable
- Dropdown is keyboard navigable
- Clear visual hierarchy
- No hidden critical information

## Example Screenshots (Description)

### Empty State
When no templates exist:
- Dropdown shows: "[Select..." (grayed out)
- Status area: Empty
- Save button: Enabled
- Load/Delete buttons: Functional but will show error if clicked

### With Templates
When templates exist:
- Dropdown shows: List of template names (e.g., "My Weekly Podcast", "Simple Setup")
- Active template highlighted/selected
- All buttons enabled and functional

### After Save Operation
- Status shows: "✅ Template 'New Name' saved successfully"
- Dropdown includes new template
- Template name field cleared
- New template selected in dropdown

### After Load Operation  
- Status shows: "✅ Template 'Name' loaded successfully"
- All UI settings reflect template values
- Current template remains selected

### Error State
When operation fails:
- Status shows: "❌ [Error message]" in red text
- Previous state unchanged
- User can retry operation
