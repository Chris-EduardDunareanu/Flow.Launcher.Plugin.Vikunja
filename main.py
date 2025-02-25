import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from flowlauncher import FlowLauncher

# Set plugin directory path
plugindir = Path.absolute(Path(__file__).parent)
sys.path = [str(plugindir / p) for p in (".", "lib", "plugin")] + sys.path

CONFIG_FILE = plugindir / "config.json"
LISTS_CACHE_FILE = plugindir / "vikunja_lists.json"

def load_config():
    """Load Vikunja API settings from config.json."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "vikunja_url": "http://your-vikunja-instance/api/v1",
            "api_token": "",
            "default_list_id": None
        }
    except json.JSONDecodeError:
        return None

def save_config(config):
    """Save user-provided API settings to config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_cached_lists():
    """Load cached Vikunja lists."""
    try:
        with open(LISTS_CACHE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_cached_lists(lists):
    """Save retrieved Vikunja lists to a cache file."""
    with open(LISTS_CACHE_FILE, "w") as f:
        json.dump(lists, f, indent=4)

class VikunjaTaskPlugin(FlowLauncher):
    def query(self, query):
        """Handles user input from Flow Launcher."""
        config = load_config()

        if not config or not config["api_token"] or not config["vikunja_url"]:
            return [{
                "Title": "⚠️ Vikunja API is not configured",
                "SubTitle": "Use 'task configure' to set API settings.",
                "IcoPath": "assets/icon.png",
                "JsonRPCAction": {"method": "set_config", "parameters": []}
            }]

        if query.lower() == "lists":
            return self.fetch_vikunja_lists()

        if not query:
            return [{
                "Title": "Create a task in Vikunja",
                "SubTitle": "Type a task after 'task'",
                "IcoPath": "assets/icon.png"
            }]

        task_title, due_date = self.parse_task_query(query)

        return [{
            "Title": f"Add Task: {task_title}",
            "SubTitle": f"Due Date: {due_date if due_date else 'None'}",
            "IcoPath": "assets/icon.png",
            "JsonRPCAction": {"method": "create_task", "parameters": [task_title, due_date]}
        }]

    def parse_task_query(self, query):
        """Parses the user input and extracts a possible due date."""
        task_title = query
        due_date = None

        date_keywords = {"tomorrow": 1, "next week": 7}
        for key, days in date_keywords.items():
            if key in query.lower():
                due_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                task_title = query.replace(key, "").strip()
                break

        return task_title, due_date

    def create_task(self, task_title, due_date):
        """Sends a request to Vikunja API to create a task."""
        config = load_config()
        if not config or not config["api_token"] or not config["vikunja_url"]:
            return [{
                "Title": "⚠️ Vikunja API is not configured",
                "SubTitle": "Use 'task configure' to set API settings.",
                "IcoPath": "assets/icon.png"
            }]

        headers = {
            "Authorization": f"Bearer {config['api_token']}",
            "Content-Type": "application/json"
        }

        list_id = config.get("default_list_id")
        if list_id is None:
            return [{
                "Title": "⚠️ No Default List Set",
                "SubTitle": "Use 'task lists' to choose a list.",
                "IcoPath": "assets/icon.png"
            }]

        task_data = {
            "title": task_title,
            "list_id": list_id,
            "due_date": due_date if due_date else None
        }

        try:
            response = requests.post(f"{config['vikunja_url']}/tasks", json=task_data, headers=headers)
            if response.status_code == 201:
                return [{
                    "Title": "✅ Task Created Successfully",
                    "SubTitle": task_title,
                    "IcoPath": "assets/icon.png"
                }]
            else:
                return [{
                    "Title": "❌ Failed to create task",
                    "SubTitle": f"Error: {response.status_code} {response.text}",
                    "IcoPath": "assets/icon.png"
                }]
        except Exception as e:
            return [{
                "Title": "❌ Error",
                "SubTitle": str(e),
                "IcoPath": "assets/icon.png"
            }]

    def fetch_vikunja_lists(self):
        """Fetches task lists from Vikunja and allows user to set default."""
        config = load_config()
        if not config or not config["api_token"] or not config["vikunja_url"]:
            return [{
                "Title": "⚠️ Vikunja API is not configured",
                "SubTitle": "Use 'task configure' to set API settings.",
                "IcoPath": "assets/icon.png"
            }]

        headers = {"Authorization": f"Bearer {config['api_token']}"}

        try:
            response = requests.get(f"{config['vikunja_url']}/lists", headers=headers)
            if response.status_code == 200:
                lists = response.json()
                save_cached_lists(lists)

                return [{
                    "Title": list_item["title"],
                    "SubTitle": f"Select this list (ID: {list_item['id']})",
                    "IcoPath": "assets/icon.png",
                    "JsonRPCAction": {"method": "set_default_list", "parameters": [list_item["id"]]}
                } for list_item in lists]
            else:
                return [{
                    "Title": "❌ Failed to fetch lists",
                    "SubTitle": f"Error: {response.status_code} {response.text}",
                    "IcoPath": "assets/icon.png"
                }]
        except Exception as e:
            return [{
                "Title": "❌ Error",
                "SubTitle": str(e),
                "IcoPath": "assets/icon.png"
            }]

    def set_default_list(self, list_id):
        """Sets the default list for task creation."""
        config = load_config()
        if config:
            config["default_list_id"] = list_id
            save_config(config)
            return [{
                "Title": "✅ Default List Updated",
                "SubTitle": f"New Default List ID: {list_id}",
                "IcoPath": "assets/icon.png"
            }]
        return [{
            "Title": "❌ Error: Failed to update list",
            "SubTitle": "Try again.",
            "IcoPath": "assets/icon.png"
        }]

if __name__ == "__main__":
    VikunjaTaskPlugin()
