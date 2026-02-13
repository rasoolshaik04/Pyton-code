# Examples showing how to use `app.py` from other modules.

# 1) Import the module-level `app` (keeps old behavior)
from app import app

def example_using_module_app():
    with app.test_client() as client:
        # Try /qr if qrcode is available, otherwise skip it
        try:
            resp = client.get("/qr")
            print('module app ->', resp.status_code, resp.content_type)
        except Exception as e:
            print('module app -> skipped /qr test:', e)


# 2) Use the factory `create_app()` to create an app instance (recommended for tests)
from app import create_app

def example_using_factory():
    app_instance = create_app()
    with app_instance.test_client() as client:
        try:
            resp = client.get("/qr")
            print('factory app ->', resp.status_code, resp.content_type)
        except Exception as e:
            print('factory app -> skipped /qr test:', e)


if __name__ == "__main__":
    example_using_module_app()
    example_using_factory()