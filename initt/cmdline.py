import os
import sys
import subprocess
from typing import Dict, List, Any, Union
import venv
import click
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import getpass


import questionary

__VERSION__ = "0.0.9"


def hook_setup_virtualenv(base_path: str, context: dict):
    Logger.info("VEnv", f"Setting up virtual environment at {base_path}")

    venv_path = os.path.join(base_path, ".venv")
    if os.path.exists(venv_path):
        Logger.info("VEnv", f"Virtual environment already exists at {venv_path}")
        return True

    try:
        Logger.info("VEnv", f"Creating virtual environment at {venv_path}")
        venv_builder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
        venv_builder.create(venv_path)
        Logger.success("VEnv", f"Successfully created virtual environment at {venv_path}")

        if context.get("use_install", False):
            req_path = os.path.join(base_path, "requirements.txt")
            if not os.path.exists(req_path):
                Logger.warning("VEnv", f"requirements.txt not found at {req_path}, skipping install.")
                return True

            pip_executable = (
                os.path.join(venv_path, "Scripts", "pip.exe")
                if sys.platform == "win32"
                else os.path.join(venv_path, "bin", "pip")
            )

            Logger.info("VEnv", f"Installing dependencies from {req_path}...")
            subprocess.check_call([pip_executable, "install", "-r", req_path])
            Logger.success("VEnv", f"Dependencies installed from {req_path}")

        return True

    except Exception as e:
        Logger.error("VEnv", f"Failed to create virtual environment: {str(e)}")
        return False


def get_git_email(default: str = "YOUREMAIL@gmail.com") -> str:
    try:
        value = (
            subprocess.check_output(["git", "config", "--global", "user.email"], stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()
        )
        return value if value else default
    except subprocess.CalledProcessError:
        return default


PROJECT_PARAMS: List[Dict[str, Any]] = [
    {
        "type": "text",
        "name": "project_name",
        "message": "Project name:",
        "default": os.path.basename(os.getcwd()).lower(),
    },
]

VERSION_PARAMS: List[Dict[str, Any]] = [
    {"type": "text", "name": "project_version", "message": "Version number:", "default": "0.0.1"},
]

# Template configuration structured definition
TEMPLATES: Dict[str, Dict[str, Union[List[str], List[Dict[str, Any]]]]] = {
    "python": {
        "project": [
            "{project_name}/__init__.py",
            "{project_name}/cmdline.py",
            "{project_name}/templates",
            ".gitignore",
            "pyproject.toml",
            "README.md",
            "requirements.txt",
            ".vscode/launch.json",
            ".vscode/extensions.json",
            ".vscode/settings.json",
        ],
        "params": [
            *PROJECT_PARAMS,
            {
                "type": "text",
                "name": "project_description",
                "message": "Project description:",
                "default": "A simple Python CLI tool",
            },
            *VERSION_PARAMS,
            {
                "type": "text",
                "name": "authors_name",
                "message": "Author name:",
                "default": getpass.getuser(),
            },
            {
                "type": "text",
                "name": "authors_email",
                "message": "Author email:",
                "default": get_git_email(),
            },
            {"type": "confirm", "name": "use_requests", "message": "Support requests:", "default": False},
            {"type": "confirm", "name": "use_tqdm", "message": "Support tqdm:", "default": False},
            {"type": "confirm", "name": "use_pydantic", "message": "Support pydantic:", "default": False},
            {"type": "confirm", "name": "use_install", "message": "Exec install:", "default": True},
        ],
        "hook": [hook_setup_virtualenv],
    },
    "nodejs": {
        "project": [
            "tsconfig.json",
            "package.json",
            "src/index.ts",
            ".gitignore",
            "README.md",
            ".vscode/extensions.json",
            ".vscode/launch.json",
            ".vscode/settings.json",
        ],
        "params": [
            *PROJECT_PARAMS,
            *VERSION_PARAMS,
        ],
        "hook": ["yarn install", "yarn add typescript tsx @types/node -D", "yarn start"],
    },
    "swift": {
        "project": [
            "Application",
            "Extensions",
            "Helpers",
            "Models",
            "Services",
            "ViewModels",
            "SwiftData/Models",
            "Views",
        ]
    },
    "react": {"project": ["models", "viewmodels", "views", "services", "hooks", "contexts", "types"]},
    "flutter": {"project": ["models", "viewmodels", "views", "services", "repositories", "widgets", "utils"]},
    "android": {
        "project": [
            "data/model",
            "data/remote",
            "data/local",
            "data/repository",
            "ui/screen",
            "ui/component",
            "ui/navigation",
            "di",
        ]
    },
}


class Logger:
    """Logger class for unified log formatting and output"""

    ICONS = {
        "cli": "🖥️",
        "info": "ℹ️",
        "success": "🎉",
        "warning": "⚠️",
        "error": "❌",
        "file": "📝",
        "directory": "📁",
        "start": "🚀",
        "hook": "🔄",
    }

    @staticmethod
    def log(level: str, label: str, message: str) -> None:
        """Output formatted logs"""
        icon = Logger.ICONS.get(level, "•")
        click.echo(f"{icon} [{label}] {message}")

    @classmethod
    def info(cls, label: str, message: str) -> None:
        cls.log("info", label, message)

    @classmethod
    def cli(cls, label: str, message: str) -> None:
        cls.log("cli", label, message)

    @classmethod
    def success(cls, label: str, message: str) -> None:
        cls.log("success", label, message)

    @classmethod
    def warning(cls, label: str, message: str) -> None:
        cls.log("warning", label, message)

    @classmethod
    def error(cls, label: str, message: str) -> None:
        cls.log("error", label, message)

    @classmethod
    def file(cls, path: str) -> None:
        cls.log("file", "File", f"Created: {path}")

    @classmethod
    def directory(cls, path: str) -> None:
        cls.log("directory", "Directory", f"Created: {path}")

    @classmethod
    def hook(cls, command: str) -> None:
        cls.log("hook", "Hook", f"Executing: {command}")


class TemplateRenderer:
    """Template renderer, responsible for template loading and rendering"""

    @staticmethod
    def get_template_env(template: str) -> Environment:
        """Get Jinja2 rendering environment"""
        # First check development environment path
        dev_template_dir = os.path.join(os.path.dirname(__file__), "templates", template)

        if os.path.exists(dev_template_dir):
            template_dir = dev_template_dir
        else:
            raise FileNotFoundError(f"Cannot find template directory: {template}")

        return Environment(loader=FileSystemLoader(template_dir), trim_blocks=False, lstrip_blocks=False)

    @staticmethod
    def render_template(env: Environment, template_name: str, context: dict) -> str:
        """Render template content"""
        try:
            template = env.get_template(template_name)
            return template.render(context)
        except TemplateNotFound:
            Logger.warning("Skip", f"Template file not found: {template_name}")
            return ""
        except Exception as e:
            Logger.error("Render", f"Failed to render template {template_name}: {str(e)}")
            return ""


class ProjectCreator:
    """Project creator class, responsible for generating files and folders"""

    def __init__(self, template_type: str):
        """
        Initialize project creator

        Args:
            template_type: Template type
        """
        self.template_type = template_type.lower()
        if self.template_type not in TEMPLATES:
            raise ValueError(f"Unsupported template type: {self.template_type}")

        self.template_config = TEMPLATES[self.template_type]
        try:
            self.env = TemplateRenderer.get_template_env(self.template_type)
        except FileNotFoundError:
            # Not all template types will have template files
            Logger.info(
                "Templates",
                f"No template files found for {self.template_type}, continuing with directory structure only",
            )
            self.env = None

    def create_file(self, path: str, context: dict) -> bool:
        """Generate a single file

        Args:
            path: File path
            context: Template context

        Returns:
            bool: Whether creation was successful
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # If we don't have a template environment, just create an empty file
            if self.env is None:
                with open(path, "w", encoding="utf-8") as f:
                    pass  # Create empty file
                Logger.file(path)
                return True

            # Try to render template
            template_name = os.path.basename(path) + ".jinja"
            content = TemplateRenderer.render_template(self.env, template_name, context)

            # Write to file if there's content
            if content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                Logger.file(path)
                return True
            return False
        except Exception as e:
            Logger.error("Error", f"Failed to create file: {path} - {str(e)}")
            return False

    def execute_hooks(self, base_path: str, context: dict) -> bool:
        """Execute post-creation hooks

        Args:
            base_path: Project base path
            context: Template context

        Returns:
            bool: Whether all hooks executed successfully
        """
        hooks = self.template_config.get("hook", [])
        if not hooks:
            return True

        Logger.info("Hooks", f"Executing {len(hooks)} post-creation hook(s)")

        success = True
        original_dir = os.getcwd()

        try:
            # Change to project directory to execute hooks
            os.chdir(base_path)

            for hook in hooks:
                try:
                    if callable(hook):
                        func_name = hook.__name__
                        Logger.hook(f"Function: {func_name}")

                        result = hook(base_path, context)

                        if result or result is None:
                            Logger.success("Hook", f"Function executed successfully: {func_name}")
                        else:
                            Logger.error("Hook", f"Function failed: {func_name}")
                            success = False
                    else:
                        command = hook.format(**context) if isinstance(hook, str) else str(hook)
                        Logger.hook(command)

                        # Execute the hook command
                        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)

                        if result.returncode == 0:
                            Logger.success("Hook", f"Command executed successfully: {command}")
                            if result.stdout.strip():
                                click.echo(result.stdout.strip())
                        else:
                            Logger.error("Hook", f"Command failed with exit code {result.returncode}: {command}")
                            if result.stderr.strip():
                                click.echo(result.stderr.strip())
                            success = False

                except KeyError as ke:
                    Logger.error("Hook", f"Missing required parameter {ke} for hook: {hook}")
                    success = False
                except Exception as e:
                    Logger.error("Hook", f"Failed to execute hook: {str(hook)} - {str(e)}")
                    success = False

        finally:
            # Restore original directory
            os.chdir(original_dir)

        return success

    def create_project(self, base_path: str, context: dict) -> bool:
        """Create project structure and files

        Args:
            base_path: Base path
            context: Template context parameters

        Returns:
            bool: Whether the entire project was successfully created
        """
        try:
            project_items = self.template_config.get("project", [])
            success_count = 0

            for item in project_items:
                try:
                    # Format variables in path
                    relative_path = item.format(**context)
                    full_path = os.path.join(base_path, relative_path)

                    # Determine if it's a file or directory
                    if "." in os.path.basename(full_path):  # File
                        if self.create_file(full_path, context):
                            success_count += 1
                    else:  # Directory
                        os.makedirs(full_path, exist_ok=True)
                        Logger.directory(full_path)
                        success_count += 1
                except KeyError as ke:
                    Logger.error("Format", f"Missing required parameter {ke} for path: {item}")
                except Exception as e:
                    Logger.error("Create", f"Error processing project item {item}: {str(e)}")

            # Check project creation success
            project_success = success_count > 0

            # Execute hooks if project was created successfully
            if project_success:
                hooks_success = self.execute_hooks(base_path, context)
                if not hooks_success:
                    Logger.warning("Hooks", "Some hooks failed to execute")

            # Return success if there were any successful project items
            return project_success

        except Exception as e:
            Logger.error("Project", f"Failed to create project: {str(e)}")
            return False


class WizardInterface:
    """Interactive wizard interface, handles user input and selection"""

    @staticmethod
    def collect_params(template_type: str) -> Dict[str, Any]:
        """Collect template parameters

        Args:
            template_type: Template type

        Returns:
            Dict[str, Any]: Dictionary of collected parameters
        """
        template_config = TEMPLATES.get(template_type, {})
        params = template_config.get("params", [])
        context = {}

        for param in params:
            qtype = param.get("type", "text")
            name = param.get("name")
            message = param.get("message", name)
            default = param.get("default", "")

            try:
                if qtype == "text":
                    answer = questionary.text(message, default=default).ask()
                elif qtype == "select":
                    choices = param.get("choices", [])
                    answer = questionary.select(message, choices=choices).ask()
                elif qtype == "confirm":
                    answer = questionary.confirm(message, default=default).ask()
                elif qtype == "path":
                    answer = questionary.path(message, default=default).ask()
                else:
                    Logger.warning("Skip", f"Unsupported question type: {qtype}")
                    continue

                # Handle cancellation
                if answer is None:
                    raise KeyboardInterrupt("User cancelled the operation")

                context[name] = answer
            except Exception as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                Logger.error("Param", f"Error collecting parameter {name}: {str(e)}")
                # Use default value
                context[name] = default

        return context


@click.command()
@click.version_option(__VERSION__)
def wizard():
    """Create project interactively"""
    try:
        # Show version info
        Logger.cli("initt", f"Project Generator v{__VERSION__}")

        # Get project type
        available_templates = list(TEMPLATES.keys())
        template = questionary.select("Select project template type:", choices=available_templates).ask()

        if not template:
            Logger.warning("Cancel", "User cancelled the operation")
            return

        # Get project path
        path = questionary.path("Select project creation path:", default=os.getcwd()).ask()

        if not path:
            Logger.warning("Cancel", "User cancelled the operation")
            return

        # Collect template parameters
        context = WizardInterface.collect_params(template)

        # Display creation info
        click.echo()
        Logger.log("start", "Start", f"Creating {template} project at {path}")

        # Create project
        creator = ProjectCreator(template)
        success = creator.create_project(path, context)

        if success:
            Logger.success("Success", "Project creation completed")
        else:
            Logger.error("Failed", "Errors occurred during project creation")

    except KeyboardInterrupt:
        click.echo("\n")
        Logger.warning("Cancel", "User interrupted the operation")
        sys.exit(1)
    except Exception as e:
        Logger.error("Error", f"Program exception: {str(e)}")
        sys.exit(1)


# Program entry
if __name__ == "__main__":
    wizard()
