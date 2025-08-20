import os
import glob
import shutil
import json

def move_replays_to_top_level():
    """
    Move all replay JSON files from subdirectories to the main replays folder.
    """
    # Ensure replays directory exists
    os.makedirs('replays', exist_ok=True)
    
    # Find all JSON files in subdirectories
    subdir_files = glob.glob(os.path.join('replays', '**', '*.json'), recursive=True)
    
    # Filter to only include files in subdirectories, not top-level
    subdir_files = [f for f in subdir_files if os.path.dirname(f) != 'replays']
    
    moved_count = 0
    for file_path in subdir_files:
        try:
            # Generate a new filename with directory info to avoid collisions
            orig_filename = os.path.basename(file_path)
            subdir_name = os.path.basename(os.path.dirname(file_path))
            
            # Create a new filename that includes subdir info to avoid collisions
            new_filename = f"{subdir_name}_{orig_filename}"
            new_path = os.path.join('replays', new_filename)
            
            # Copy file to the top-level replays directory
            shutil.copy2(file_path, new_path)
            print(f"Moved: {file_path} -> {new_path}")
            moved_count += 1
            
            # Validate the file was copied correctly
            try:
                with open(new_path, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: File {new_path} is not valid JSON, but was copied anyway.")
                
        except Exception as e:
            print(f"Error moving file {file_path}: {e}")
    
    print(f"Moved {moved_count} replay files to the top-level replays directory.")

if __name__ == "__main__":
    move_replays_to_top_level()
