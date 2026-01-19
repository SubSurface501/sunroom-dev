import os

# ---------------------------------------------------------
# CONFIGURATION: Folders and Files to Ignore
# ---------------------------------------------------------
IGNORE_DIRS = {
    'node_modules', '.git', '.next', '__pycache__', 'dist', 'build', 
    'venv', 'env', 'Lib', 'Scripts', 'share', 'include', 'site-packages',
    '.firebase', '.vite', 'coverage', 'migrations', '.idea', '.vscode'
}

IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', '.DS_Store', 'poetry.lock', 
    'pnpm-lock.yaml', 'LICENSE', 'README.md'
}

def list_files(startpath):
    output_file = "clean_structure.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Project Structure for: {os.path.basename(os.getcwd())}\n")
        f.write("="*50 + "\n")
        
        for root, dirs, files in os.walk(startpath):
            # MODIFY dirs IN-PLACE to prevent walking into ignored folders
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            level = root.replace(startpath, '').count(os.sep)
            indent = '│   ' * (level)
            
            # Don't print the root dot "."
            if level > 0:
                f.write('{}{}/\n'.format(indent, os.path.basename(root)))
            
            subindent = '│   ' * (level + 1)
            for file in files:
                if file not in IGNORE_FILES and not file.endswith('.pyc') and not file.endswith('.pyo'):
                    f.write('{}{}\n'.format(subindent, file))
                    
    print(f"✅ Success! File structure saved to: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    list_files(".")