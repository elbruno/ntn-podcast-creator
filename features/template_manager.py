"""Template management for podcast creator application.

This module provides functionality to save, load, and manage podcast settings templates.
Templates allow users to quickly switch between different podcast configurations.
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime


class TemplateManager:
    """Manages podcast settings templates with persistent storage."""

    def __init__(self, templates_dir: str = "core/templates"):
        """Initialize template manager.

        Args:
            templates_dir: Directory to store template files
        """
        self.templates_dir = templates_dir
        os.makedirs(self.templates_dir, exist_ok=True)

    def _get_template_path(self, template_name: str) -> str:
        """Get full path for a template file.

        Args:
            template_name: Name of the template

        Returns:
            Full path to template file
        """
        # Sanitize template name to prevent path traversal
        safe_name = "".join(c for c in template_name if c.isalnum() or c in (' ', '-', '_')).strip()
        return os.path.join(self.templates_dir, f"{safe_name}.json")

    def save_template(self, template_name: str, settings: Dict[str, Any]) -> tuple[bool, str]:
        """Save current settings as a named template.

        Args:
            template_name: Name for the template
            settings: Dictionary of settings to save

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not template_name or not template_name.strip():
            return False, "Template name cannot be empty"

        try:
            template_path = self._get_template_path(template_name)
            
            # Add metadata
            template_data = {
                "name": template_name,
                "created_at": datetime.now().isoformat(),
                "settings": settings
            }

            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2)

            return True, f"Template '{template_name}' saved successfully"
        except Exception as e:
            return False, f"Error saving template: {str(e)}"

    def load_template(self, template_name: str) -> tuple[Optional[Dict[str, Any]], str]:
        """Load settings from a named template.

        Args:
            template_name: Name of the template to load

        Returns:
            Tuple of (settings: Dict or None, message: str)
        """
        if not template_name or not template_name.strip():
            return None, "Template name cannot be empty"

        try:
            template_path = self._get_template_path(template_name)
            
            if not os.path.exists(template_path):
                return None, f"Template '{template_name}' not found"

            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            settings = template_data.get("settings", {})
            return settings, f"Template '{template_name}' loaded successfully"
        except json.JSONDecodeError as e:
            return None, f"Error: Invalid template format - {str(e)}"
        except Exception as e:
            return None, f"Error loading template: {str(e)}"

    def delete_template(self, template_name: str) -> tuple[bool, str]:
        """Delete a named template.

        Args:
            template_name: Name of the template to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not template_name or not template_name.strip():
            return False, "Template name cannot be empty"

        try:
            template_path = self._get_template_path(template_name)
            
            if not os.path.exists(template_path):
                return False, f"Template '{template_name}' not found"

            os.remove(template_path)
            return True, f"Template '{template_name}' deleted successfully"
        except Exception as e:
            return False, f"Error deleting template: {str(e)}"

    def list_templates(self) -> List[str]:
        """List all available templates.

        Returns:
            List of template names
        """
        try:
            if not os.path.exists(self.templates_dir):
                return []

            templates = []
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.json'):
                    # Remove .json extension
                    template_name = filename[:-5]
                    templates.append(template_name)

            return sorted(templates)
        except Exception as e:
            print(f"Error listing templates: {e}")
            return []

    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a template.

        Args:
            template_name: Name of the template

        Returns:
            Dictionary with template metadata or None if not found
        """
        try:
            template_path = self._get_template_path(template_name)
            
            if not os.path.exists(template_path):
                return None

            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            return {
                "name": template_data.get("name", template_name),
                "created_at": template_data.get("created_at", "Unknown"),
                "has_intro": bool(template_data.get("settings", {}).get("intro_file")),
                "has_outro": bool(template_data.get("settings", {}).get("outro_file")),
                "background_tracks_count": len(template_data.get("settings", {}).get("background_tracks", []))
            }
        except Exception as e:
            print(f"Error getting template info: {e}")
            return None
