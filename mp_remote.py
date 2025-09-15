from pathlib import Path
import argparse
import subprocess
import sys
import time

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
TEST_HTTP_SERVER_DIR = SCRIPT_DIR / 'Test-HTTP-Server'
TIMESTAMP_FILE_NAME = 'last_upload_time.txt'
ESP_ROOT = ':/'
IGNORED_SUFFIXES = ['.txt', '.md', '.pyc', '.log', '.bak', '.bat', '.sh',
                    '.ini', '.cfg', '.config', '.DS_Store',
                    '.git', '.gitignore', '.gitattributes',
                    '.pdf', '.docx', '.xlsx', '.pptx',
                    '.zip', '.tar', '.tar.gz', '.rar' ]


def run_mpremote(args_list, capture_output=False, exit_on_error=True):
    """Run an mpremote command with the given arguments list."""
    cmd = ['mpremote'] + args_list
    try:
        if capture_output:
            result = subprocess.run(cmd, check=True, capture_output=True,
                                    stderr=subprocess.DEVNULL if not capture_output else None,
                                    text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           text=True)
            # Run without capturing output

    except subprocess.CalledProcessError as e:
        if exit_on_error:
            print(f"Error: mpremote command failed: {e}")
            sys.exit(1)


def delete_all_files():
    print("Deleting all files on ESP32...")
    try:
        run_mpremote(['fs', 'rm', '-r', ESP_ROOT])
    except subprocess.CalledProcessError as e:
        print(f"Error deleting files on ESP32: {e}")
        sys.exit(1)
    print("All files removed from ESP32.")


def get_last_upload_time(path: Path):
    timestamp_file = path / TIMESTAMP_FILE_NAME
    if not timestamp_file.exists():
        return 0
    return float(timestamp_file.read_text())

def update_upload_time(path: Path):
    timestamp_file = path / TIMESTAMP_FILE_NAME
    timestamp_file.write_text(str(time.time()))

def upload_path(path_str, force=False):
    """Upload updated non-.txt files to ESP32, ensuring folder structure is created first."""
    path = Path(path_str).resolve()
    if not path.is_dir():
        print(f"Error: Directory not found at {path}")
        sys.exit(1)

    last_upload_time = get_last_upload_time(path)
    files_to_upload = []

    print(f"Scanning for modified files in '{path}'...\n")

    # Step 1: Find all modified files to upload
    for file in path.rglob('*'):
        if not file.is_file():
            continue
        if file.suffix in IGNORED_SUFFIXES:
            continue
        if force or file.stat().st_mtime > last_upload_time:
            files_to_upload.append(file)

    if not files_to_upload:
        print("No files were modified since the last upload.")
        return

    # Step 2: Collect and create required folders on ESP32
    folders_to_create = set()
    for file in files_to_upload:
        relative_folder = file.relative_to(path).parent.as_posix()
        if relative_folder:
            folders_to_create.add(relative_folder)

    for folder in sorted(folders_to_create):
        esp_folder = f"{ESP_ROOT.rstrip('/')}/{folder}"
        try:
            run_mpremote(['fs', 'mkdir', esp_folder], exit_on_error=False)
        except subprocess.CalledProcessError:
            pass  # Folder may already exist

    # Step 3: Upload files
    for file in files_to_upload:
        relative_path = file.relative_to(path).as_posix()
        esp_target = f"{ESP_ROOT.rstrip('/')}/{relative_path}"
        run_mpremote(['fs', 'cp', str(file), esp_target])
        print(f"Uploaded: {relative_path}")

    # Step 4: Update timestamp
    update_upload_time(path)
    print("\nUpload complete.")


def soft_reset():
    print("Performing soft reset on ESP32...")
    run_mpremote(['reset'])
    print("Soft reset sent.")

def terminal():
    print("Opening REPL terminal. Press Ctrl-D to exit.")
    run_mpremote(['repl'])


def list_all_files(base_path=":/"):
    """Recursively list all files and directories on the ESP32, grouped per directory,
    with files printed under the previous directory path line."""
    try:
        output = run_mpremote(['fs', 'ls', base_path], capture_output=True)
    except SystemExit:
        return  # skip invalid path

    lines = output.strip().splitlines()
    if not lines or len(lines) < 2:
        return

    entries = lines[1:]  # Skip "Listing directory: ..."
    files = []
    subdirs = []

    # Separate files and subdirectories
    for entry in entries:
        parts = entry.strip().split()
        if not parts:
            continue
        name = parts[-1]
        if name.endswith('/'):
            subdirs.append(name.rstrip('/'))
        else:
            files.append(name)

    # Print current directory with trailing slash
    print(f"\n{base_path.rstrip('/')}/")

    # Print all files with 2-space indent (or more visually distinct if needed)
    for f in files:
        space = ' ' * (len(base_path.rstrip('/')) + 1)# 2 spaces for indent
        print(f"{space}{f}")

    # Recurse into subdirectories
    for subdir in subdirs:
        sub_path = f"{base_path.rstrip('/')}/{subdir}"
        list_all_files(sub_path)

def main():
    parser = argparse.ArgumentParser(description='Manage files and sessions on ESP32 using mpremote.')
    parser.add_argument('command', choices=['delete_all', 'upload_path', 'soft_reset',
                                             'terminal', 'list_files'], help='Command to execute on the ESP32')

    parser.add_argument('--path', type=str, default=None,
                        help='Path to the directory for upload_path')

    parser.add_argument('--force_upload', action='store_true',
                        help='Upload all files regardless of modification time')

    args = parser.parse_args()

    print (f"\n===================================================================\n")

    if args.command == 'delete_all':
        delete_all_files()
    elif args.command == 'upload_path':
        upload_path(args.path, force=args.force_upload)
    elif args.command == 'soft_reset':
        soft_reset()
    elif args.command == 'terminal':
        terminal()
    elif args.command == 'list_files':
        list_all_files()
    else:
        print(f"Unknown command: {args.command}")

    print (f"\n===================================================================\n")

if __name__ == '__main__':
    #list_all_files()
    main()
    #upload_path('./Wagon-Control')