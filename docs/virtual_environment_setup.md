# Virtual Environment Setup

To start a Python virtual environment, follow these steps. This isolates your project's dependencies from other Python projects and your system-wide Python installation.

**1. Create the Virtual Environment:**

Open your terminal or command prompt in the root directory of your project (`C:\Users\grunt\sunroom_dev`).

```bash
python -m venv venv
```
This command creates a new directory named `venv` (you can choose any name) in your project folder, which will contain the Python interpreter and a `pip` installation specific to this environment.

**2. Activate the Virtual Environment:**

After creating it, you need to activate it. The command differs slightly between Windows and macOS/Linux:

*   **On Windows:**
    ```bash
    .\venv\Scripts\Activate
    ```
    You should see `(venv)` appear at the beginning of your terminal prompt, indicating that the virtual environment is active.

*   **On macOS / Linux:**
    ```bash
    source venv/bin/activate
    ```
    You should see `(venv)` appear at the beginning of your terminal prompt, indicating that the virtual environment is active.

**3. Install Dependencies:**

Once activated, you can install your project's Python dependencies into this isolated environment:

```bash
pip install -r requirements.txt
```

**4. Deactivate the Virtual Environment:**

When you're done working on the project and want to return to your system's default Python environment, simply type:

```bash
deactivate
```
The `(venv)` prefix will disappear from your prompt.
