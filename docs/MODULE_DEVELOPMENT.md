# 🛠️ Module Development Guide

ShadowFramework is designed to be easily extensible. This guide outlines the criteria and steps for building your own functional modules.

---

## 🏗️ Module Structure

All modules must reside in the `modules/` directory, categorized logically (e.g., `modules/auxiliary/`, `modules/exploit/`, `modules/post/`).

### File Naming
- Use lowercase with underscores: `my_new_module.py`.
- The filename determines the module name used in the framework (e.g., `use auxiliary/my_new_module`).

### The Module Class
Every module MUST contain a class named `Module`. This class should handle the initialization and execution logic.

---

## 📝 Criteria for a Working Module

To be considered a valid, working module in ShadowFramework, your code must satisfy these requirements:

1.  **`MODULE_INFO` Dictionary**: A class attribute containing metadata.
    - `name`: Full path of the module.
    - `description`: A brief summary of what the module does.
    - `options`: A dictionary of configurable parameters where the key is the option name and the value is a description or default value.

2.  **`__init__(self, framework)`**: The constructor must accept the framework instance.
    - Store the framework: `self.framework = framework`.

3.  **`run(self)`**: The main execution method called when the user types `run`.
    - Access options via `self.framework.options`.
    - Use `self.framework.print_status`, `self.framework.print_error`, and `self.framework.print_success` for consistent UI output.

---

## 💻 Template Example

```python
class Module:
    MODULE_INFO = {
        'name': 'auxiliary/example_scanner',
        'description': 'An example scanner module that checks for a specific port.',
        'options': {
            'RHOST': 'The target host IP',
            'RPORT': '80'  # Default value
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        target = self.framework.options.get('RHOST')
        port = self.framework.options.get('RPORT')

        if not target:
            self.framework.print_error("RHOST is not set!")
            return

        self.framework.print_status(f"Scanning {target}:{port}...")
        
        # --- Logic goes here ---
        # success = do_something(target, port)
        # -----------------------

        self.framework.print_success("Module execution finished.")
```

---

## 🧪 Best Practices

- **Error Handling**: Always wrap network operations or external tool calls in `try-except` blocks.
- **Dependencies**: If your module requires a library not in `requirements.txt`, document it in the module's description or handle the `ImportError` gracefully.
- **Rich Integration**: Leverage the framework's print methods to ensure your output matches the premium "Shadow" aesthetic.
- **External Tools**: Use `subprocess` to call external binaries like `nmap` or `adb` when necessary, but ensure they are available in the system PATH.
