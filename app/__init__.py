from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_pymongo import PyMongo
import os
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt

mongo = PyMongo()
jwt = JWTManager()
bcrypt = Bcrypt()


def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    
    load_dotenv()
    app.config['MONGO_URI'] = os.getenv(
        'MONGO_URI',
        'mongodb+srv://group_payroll_sysdb:ICTGroupProject@cluster1.eeqaf7t.mongodb.net/?appName=Cluster1'
    )
    app.config['MONGO_DB'] = os.getenv('MONGO_DB', 'payroll_db')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'ia41sId6LOTehoP0XR8VZ_e96_G4n4-IqZ2FI9XsJRw')
    app.config['CORS_ORIGIN'] = os.getenv('CORS_ORIGIN', 'http://localhost:5173')

    # Initialize MongoDB and JWT
    mongo.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # Test Mongo Connection
    try:
        with app.app_context():
            mongo.db.command('ping')
            print("\n✅ MongoDB connected successfully!\n")
    except Exception as e:
        print(f"\n❌ MongoDB connection failed: {e}\n")

    # Enable CORS
    # CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGIN']}}, supports_credentials=True)
    # CORS(app, resources={r"/api/*": {"origins": "*"}})
    CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    supports_credentials=True,
)


    # ✅ Import and register blueprints *AFTER* initializing extensions
    from .auth import auth_bp
    from routes.personnel import personnel_bp
    from routes.payroll import payroll_bp

    
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(personnel_bp, url_prefix="/api/personnel")
    app.register_blueprint(payroll_bp)
    # app.register_blueprint(personnel_bp, )


    
    
    print("✅ Auth blueprint imported successfully")
    print("✅ Auth blueprint registered at /api/auth")
    
    
    # This to show all registered routes
    # print("\n📜 Registered routes:")
    # for rule in app.url_map.iter_rules():
    #  print(rule)
    #  print()


    @app.after_request
    def after_request(response):
        print("CORS headers:", response.headers)
        return response
    
    @app.route('/')
    def home():
        return "MongoDB connected successfully", 200

    return app