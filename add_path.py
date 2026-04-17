from modules.colors import RESET, BOLD, RED, GREEN, YELLOW, BLUE
from pathlib import Path
import json


def add_path():
    """Configure or display the download directory path"""
    parent_folder = Path(__file__).parent
    config_file = parent_folder / "config.json"

    try:
        user_input = input(f"{BOLD}\tEnter your path: {RESET}").strip()

        # Setter mode - user provided a path
        if user_input:
            input_path = Path(user_input).expanduser().resolve()

            # Save path to config file
            config = {"path": str(input_path)}
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            print(f"{GREEN}Configuration saved successfully!{RESET}")
            print(f"{YELLOW}\tPath: {RESET}{input_path}")
            print(f"{BLUE}\tConfig file: {RESET}{config_file}")

        # Getter mode - no input provided, show current config
        else:
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        saved_path_str = data.get("path")

                        if saved_path_str:
                            saved_path = Path(saved_path_str)

                            # Verify the saved path still exists
                            if saved_path.exists():
                                print(
                                    f"{GREEN}Current download directory: {RESET}{saved_path}"
                                )
                                print(
                                    f"{GREEN}Configuration file: {RESET}{config_file}"
                                )
                            else:
                                print(
                                    f"{RED}\nConfig file exists but the saved path is invalid!{RESET}"
                                )
                                print(f"{RED}Path: {RESET}{saved_path}")
                                exit(1)
                        else:
                            print(
                                f"{RED}\nConfig file exists but 'path' key is missing!{RESET}"
                            )
                            exit(1)

                    except json.JSONDecodeError:
                        print(
                            f"{RED}\nConfig file is corrupted! Please reconfigure.{RESET}"
                        )
                        exit(1)
            else:
                print(
                    f"{RED}\nConfig file not found! Please set a download path first.{RESET}"
                )
                exit(1)

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print(f"\r\033[K{GREEN}Goodbye!{RESET}")
        exit(0)

    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        exit(1)


if __name__ == "__main__":
    add_path()
