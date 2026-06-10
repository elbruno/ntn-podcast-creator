# Template Feature Documentation

## Overview
The template feature allows users to save and quickly load podcast settings configurations. This includes all audio files (intro, outro, background music) and processing options (denoising, enhancement, normalization, transcription).

## Features

### Save Template
- Saves all current settings as a named template
- Includes:
  - Intro audio file path
  - Outro audio file path
  - Background music tracks (multiple files)
  - Background volume settings
  - Per-track volume settings
  - Noise reduction settings (enabled/disabled and method)
  - Adobe enhancement setting
  - LUFS normalization settings
  - Transcript generation settings
  - Whisper model selection

### Load Template
- Loads previously saved template
- Applies all settings to the current configuration
- Marks template as active
- Settings are immediately available in the UI

### Delete Template
- Removes template from storage
- Clears active template if the deleted template was active
- Updates template list immediately

### List Templates
- Shows all available templates in a dropdown
- Sorted alphabetically
- Displays current active template

## Storage

Templates are stored in `core/templates/` directory as JSON files:
- Each template is a separate file: `<template_name>.json`
- File names are sanitized (alphanumeric, spaces, hyphens, underscores only)
- Includes metadata: template name, creation timestamp

## Template File Structure

```json
{
  "name": "My Weekly Podcast",
  "created_at": "2026-01-12T20:37:22.213385",
  "settings": {
    "intro_file": "audios/intro_audio/intro.mp3",
    "outro_file": "audios/outro_audio/outro.mp3",
    "background_tracks": ["track1.mp3", "track2.mp3"],
    "background_volume": 15,
    "track_volumes": {
      "track1.mp3": 10,
      "track2.mp3": 20
    },
    "denoise_audio": true,
    "denoise_method": "audio_denoiser",
    "enhance_audio": false,
    "normalize_lufs": true,
    "target_lufs": -16.0,
    "generate_transcript": false,
    "whisper_model": "base"
  }
}
```

## UI Components

### Location
The template management UI is located in the main "🎙️ Podcast Creator" tab, within an accordion section labeled "📋 Templates".

### UI Elements
1. **Template Dropdown**: Select from existing templates
2. **Load Template Button**: Apply selected template to current settings
3. **Delete Template Button**: Remove selected template
4. **Template Name Input**: Text field to name new template
5. **Save Template Button**: Save current settings as new template
6. **Template Status**: Display area showing operation results

## User Workflow

### Saving a Template
1. Configure all desired settings (intro, outro, background, processing options)
2. Open "📋 Templates" accordion
3. Enter a name for the template in the "Template Name" field
4. Click "💾 Save Template"
5. Status message confirms successful save
6. Template appears in dropdown list

### Loading a Template
1. Open "📋 Templates" accordion
2. Select template from dropdown
3. Click "📂 Load Template"
4. All settings are immediately applied
5. Status message confirms successful load

### Deleting a Template
1. Open "📋 Templates" accordion
2. Select template from dropdown
3. Click "🗑️ Delete Template"
4. Confirm deletion
5. Template is removed from list
6. Status message confirms successful deletion

## Implementation Details

### Backend Modules

#### `features/template_manager.py`
- `TemplateManager` class handles all template operations
- Methods:
  - `save_template(name, settings)`: Save template
  - `load_template(name)`: Load template
  - `delete_template(name)`: Delete template
  - `list_templates()`: Get all template names
  - `get_template_info(name)`: Get template metadata

#### `features/config_manager.py` Extensions
- Added methods:
  - `get_template_settings()`: Extract all template-saveable settings
  - `apply_template_settings(settings)`: Apply template to config
  - `get_active_template()`: Get current active template
  - `set_active_template(name)`: Set active template
- Added config key: `active_template`

### Frontend Integration

#### Event Handlers (`app.py`)
- `save_template_handler()`: Handles save button click
- `load_template_handler()`: Handles load button click
- `delete_template_handler()`: Handles delete button click
- All handlers update the template dropdown and status display

## Testing

### Unit Tests
Test script: `tests/test_template_feature.py`

Tests include:
- ✅ Save template functionality
- ✅ Load template functionality
- ✅ Delete template functionality
- ✅ List templates functionality
- ✅ Template info retrieval
- ✅ Multiple template management
- ✅ Config manager integration
- ✅ Template settings extraction
- ✅ Template settings application
- ✅ Active template tracking

All tests passed successfully.

## Benefits

1. **Time Saving**: Quickly switch between different podcast configurations
2. **Consistency**: Ensure same settings across episodes
3. **Flexibility**: Maintain different templates for different podcast types
4. **Ease of Use**: One-click loading of complete configurations
5. **Non-Destructive**: Templates don't affect original audio files

## Error Handling

The template feature includes robust error handling:
- Invalid template names are rejected
- Missing files are handled gracefully (ignored on load)
- File I/O errors are caught and reported to user
- Template operations never crash the application
- User-friendly error messages in status display

## Security Considerations

- Template names are sanitized to prevent path traversal attacks
- File size limits prevent abuse (handled by JSON parser)
- Template files are stored in dedicated directory
- No executable code stored in templates (pure JSON data)

## Future Enhancements

Potential future improvements:
- Template export/import (share templates between installations)
- Template preview before loading
- Template categories or tags
- Template search/filter
- Template cloning (save as copy)
- Template comparison tool
- Default template setting

## Compatibility

- Works with Gradio 6.0+
- Compatible with all existing podcast creator features
- Does not require additional dependencies
- Backward compatible (doesn't break existing configs)

## Maintenance

Template files can be:
- Manually edited (JSON format)
- Backed up (copy files from `core/templates/`)
- Shared (copy template files between installations)
- Version controlled (can be committed to git)

## Support

If templates are not working:
1. Check `core/templates/` directory exists and is writable
2. Verify template files are valid JSON
3. Check application logs for error messages
4. Ensure settings being saved are valid
5. Try creating a new template with minimal settings
