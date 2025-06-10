from app import create_app

application = create_app()
app = application  # for Gunicorn

if __name__ == '__main__':
    application.run() 