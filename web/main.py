from main_app import create_app
from flask_mail import Mail

app = create_app()
mail = Mail(app)

if __name__ == "__main__":
    app.run(debug=True)
