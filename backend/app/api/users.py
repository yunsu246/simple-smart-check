from app.api import apiRestful
from app.api.security import require_auth
from app.config import Config
from app.extensions import db
from app.ormmodels import UsersModel, RevokedTokenModel
from app.ormmodels import UsersModelSchema, RevokedTokenModelSchema
from datetime import timedelta
from flask import request
from flask_restplus import Resource
from flask_jwt_extended import create_access_token, jwt_required, get_raw_jwt
from passlib.hash import django_pbkdf2_sha256


# # ---------------------------[ SecureResource ]----------------------------------
# # Calls require_auth decorator on all requests
# class SecureResource(Resource):
#     method_decorators = [require_auth]
# # -------------------------------------------------------------------------------


# # ----------------[ API SAMPLE with Applying SecureResources ]-------------------
# @apiRestful.route('/users/secret')
# class SecretResource(SecureResource):
#     @jwt_required
#     def get(self):
#         return {
#             'answer': 42
#         }
# # -------------------------------------------------------------------------------


# --------------------[ API to System Users/Admin and Auth ]-----------------------
class Users:

    # ----------------[ Register a New User ]--------------------------------------
    @apiRestful.route('/users/new')
    @apiRestful.doc(params= {
                    'username': {'in': 'formData', 'description': 'application/json, body required'},
                    'password': {'in': 'formData', 'description': 'application/json, body required'},
    })
    class post_Users_New(Resource):       # Before applying SecureResource

        def post(self):
            # if key doesn't exist, returns a 400, bad request error("message": "The browser (or proxy) sent a request that this server could not understand.")
            # Reference : https://scotch.io/bar-talk/processing-incoming-request-data-in-flask
            infoFromClient = request.form
            usernameFromClient = infoFromClient['username']
            passwordFromClient = infoFromClient['password']
            
            if UsersModel.query.filter_by(username= usernameFromClient).first():
                return {'message': f'User {usernameFromClient} already exists'}
            
            pbkdf2_sha256 = django_pbkdf2_sha256.using(salt= Config.SALT_KEYWORD, salt_size= Config.SALT_SIZE, rounds= Config.SALT_ROUNDS)
            newUserInfoFromClient = UsersModel(
                username= usernameFromClient,
                password= pbkdf2_sha256.hash(passwordFromClient)    #Crypt the password with pbkdf2
            )

            # [!] Transaction Issue when DB insert fails
            try:
                db.session.add(newUserInfoFromClient)
                accessToken = create_access_token(identity= usernameFromClient)
                db.session.commit()
                return {'return': {
                            'message': f'User {usernameFromClient} was created',
                            'access_token': accessToken,
                        }}
            except:
                db.session.rollback()
                return {'return': {'message': 'Something went wrong'}}, 500
    # -----------------------------------------------------------------------------


    # ----------------[ Login ]----------------------------------------------------
    @apiRestful.route('/users/login')
    @apiRestful.doc(params= {
                    'username': {'in': 'formData', 'description': 'application/json, body required'},
                    'password': {'in': 'formData', 'description': 'application/json, body required'},
    })
    class post_Users_Login(Resource):      # Before applying SecureResource

        def post(self):
            # if key doesn't exist, returns a 400, bad request error("message": "The browser (or proxy) sent a request that this server could not understand.")
            # Reference : https://scotch.io/bar-talk/processing-incoming-request-data-in-flask
            infoFromClient = request.form
            usernameFromClient = infoFromClient['username']
            passwordFromClient = infoFromClient['password']
            # passwordFromClient = django_pbkdf2_sha256.using(salt= Config.SALT_KEYWORD, salt_size= Config.SALT_SIZE, rounds= Config.SALT_ROUNDS).hash(infoFromClient['password']).split('$')[-1]

            UserInfoFromDB = UsersModel.query.filter_by(username= usernameFromClient).first()

            if passwordFromClient == UserInfoFromDB.password.split('$')[-1]:        # Successfully Login, return 201
                accessToken = create_access_token(identity= usernameFromClient)
                return {'return': {
                            'message': f'Logged in as {UserInfoFromDB.username}',
                            'access_token': accessToken,
                        }}, 201
            elif not UserInfoFromDB:                                                # if User is not registered, return 500
                return {'return': {'message': f'User {usernameFromClient} doesn\'t exist'}}, 500
            else:
                return {'return': {'message': 'Wrong credentials'}}, 500            # Something wrong, return 500
    # -----------------------------------------------------------------------------


    # ----------------[ Logout ]---------------------------------------------------
    @apiRestful.route('/users/logout')
    class post_Users_Logout(Resource):       # Before applying SecureResource

        @jwt_required
        def post(self):
            jti = get_raw_jwt()['jti']
            try:
                db.session.add(RevokedTokenModel(jti= jti))
                db.session.commit()
                return {'return': {'message': 'Successfully Logout, Access token has been revoked'}}
            except:
                db.session.rollback()
                return {'return': {'message': 'Something went wrong'}}, 500
    # -----------------------------------------------------------------------------


    # ----------------[ Get Users ]------------------------------------------------
    @apiRestful.route('/users/filter')
    @apiRestful.doc(params= {
                    'username': {'in': 'query', 'description': 'URL parameter, optional'},
    })
    class get_Users_Filter(Resource):       # Before applying SecureResource
        def get(self):
            queryFilter = request.args
            users = UsersModel.query.filter_by(**queryFilter).all()
            usersSchema = UsersModelSchema(many= True)
            output = usersSchema.dump(users)
            return {'return': output}
    # -----------------------------------------------------------------------------
# ---------------------------------------------------------------------------------