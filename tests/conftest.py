import os

# Provide a fake key so startup validation doesn't block tests
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-sk-fake')
