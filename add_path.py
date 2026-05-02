from json import JSONDecodeError, dump, load
from pathlib import Path

from modules.colors import BLUE, BOLD, GREEN, RED, RESET, YELLOW


def add_path():
    """Configure or display the download directory path"""
    config_file = Path(__file__).parent / "config.json"

    try:
        user_input = input(f"{BOLD}\tEnter your path: {RESET}").strip()

        # Setter mode - user provided a path
        if user_input:
            input_path = Path(user_input).expanduser().resolve()

            # Save path to config file
            config = {"path": str(input_path)}
            with open(config_file, "w", encoding="utf-8") as f:
                dump(config, f, ensure_ascii=False, indent=4)

            return (
                f"{GREEN}Configuration saved successfully!{RESET}"
                f"{YELLOW}    Path: {RESET}{input_path}"
                f"{BLUE}    Config file: {RESET}{config_file}"
            )

        # Getter mode - no input provided, show current config
        else:
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    try:
                        data = load(f)
                        saved_path_str = data.get("path")

                        if saved_path_str:
                            saved_path = Path(saved_path_str)

                            # Verify the saved path still exists
                            if saved_path.exists():
                                return (
                                    f"{GREEN}Current download directory: {RESET}{saved_path}"
                                    f"{GREEN}Configuration file: {RESET}{config_file}"
                                )
                            else:
                                return (
                                    f"{RED}\nConfig file exists but the saved path is invalid!{RESET}"
                                    f"{RED}Path: {RESET}{saved_path}"
                                )
                        else:
                            return f"{RED}\nConfig file exists but 'path' key is missing!{RESET}"

                    except JSONDecodeError:
                        return f"{RED}\nConfig file is corrupted! Please reconfigure.{RESET}"
            else:
                return f"{RED}\nConfig file not found! Please set a download path first.{RESET}"

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        return f"\r\033[K\n{GREEN}Goodbye!{RESET}"

    except Exception as e:
        return f"{RED}Error: {e}{RESET}"


if __name__ == "__main__":
    add_path()
