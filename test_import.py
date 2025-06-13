try:
    import main
    print("Successfully imported main.py")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Other error during import: {e}")
