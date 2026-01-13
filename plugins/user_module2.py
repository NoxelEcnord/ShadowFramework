class Module:
    MODULE_INFO = {
        'name': 'plugins/user_module2',
        'description': 'A user-defined plugin that demonstrates custom integration.',
        'options': {
            'MESSAGE': 'Hello from Shadow Plugin!'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        msg = self.framework.options.get('MESSAGE')
        self.framework.print_status(f"Plugin executing with message: {msg}")
        self.framework.print_success("Plugin task completed successfully.")
