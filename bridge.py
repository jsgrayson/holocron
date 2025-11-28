import time
import os
import json
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# CONFIGURATION
# TODO: User needs to set the correct Account Name
WOW_SAVED_VARIABLES_PATH = "/Applications/World of Warcraft/_retail_/WTF/Account/YOUR_ACCOUNT_NAME_HERE/SavedVariables"
SERVER_URL = "http://localhost:5000/upload"

class SavedVariablesHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        
        # Phase 1-5: DataStore
        if filename.startswith("DataStore") and filename.endswith(".lua"):
            print(f"Detected change in {filename}. Processing...")
            self.process_lua_file(event.src_path, filename)
            
        # Phase 6: SavedInstances (Pathfinder)
        elif filename == "SavedInstances.lua":
            print(f"Detected change in {filename}. Processing...")
            self.process_lua_file(event.src_path, filename)

        # Phase 8: DataStore_Reputations (Diplomat)
        elif filename == "DataStore_Reputations.lua":
            print(f"Detected change in {filename}. Processing...")
            self.process_lua_file(event.src_path, filename)

    def process_lua_file(self, filepath, filename):
        """
        Reads the Lua file, attempts to parse it (naive parsing or using a library),
        and sends it to the server.
        """
        try:
            # TODO: Implement robust Lua to JSON parsing. 
            # For now, we will just read the raw content and send it wrapped.
            # In a real scenario, we'd use slpp or similar to parse Lua tables to Python dicts.
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            payload = {
                "source": filename.replace(".lua", ""),
                "data": content # Sending raw content for server to parse for now
            }

            response = requests.post(SERVER_URL, json=payload)
            if response.status_code == 200:
                print(f"Successfully uploaded {filename}")
            else:
                print(f"Failed to upload {filename}: {response.text}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    print(f"Starting Holocron Bridge...")
    print(f"Watching: {WOW_SAVED_VARIABLES_PATH}")
    
    event_handler = SavedVariablesHandler()
    observer = Observer()
    
    # Check if path exists to avoid immediate crash
    if not os.path.exists(WOW_SAVED_VARIABLES_PATH):
        print(f"WARNING: Path not found: {WOW_SAVED_VARIABLES_PATH}")
        print("Please edit bridge.py to set the correct WOW_SAVED_VARIABLES_PATH.")
    else:
        observer.schedule(event_handler, WOW_SAVED_VARIABLES_PATH, recursive=False)
        observer.start()
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
