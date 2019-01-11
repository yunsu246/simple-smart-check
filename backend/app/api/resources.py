from app.api import apiRestful
from app.api.modules import requireAuth, convertDataframeToDictsList
from app.config import Config
from app.extensions import db
from app.ormmodels import AttendanceLogsModel, ApplicantsModel, CurriculumsModel, MembersModel
from app.ormmodels import AttendanceLogsModelSchema, ApplicantsModelSchema, CurriculumsModelSchema, MembersModelSchema
from datetime import datetime, timedelta
from flask import request
from flask_restplus import Resource     # Reference : http://flask-restplus.readthedocs.io
from json import loads
from sqlalchemy import and_, func
import pandas as pd


# # ---------------------------[ SecureResource ]----------------------------------
# # Calls requireAuth decorator on all requests
# class SecureResource(Resource):
#     method_decorators = [requireAuth]
# # -------------------------------------------------------------------------------


# # ----------------[ API SAMPLE with Applying SecureResources ]-------------------
# @apiRestful.route('/secure-resource/<string:resource_id>')
# @apiRestful.param('resource_id', 'Class-wide description')
# class SecureResourceOne(SecureResource):    # Secure Resource Class: Inherit from Resource

#     @apiRestful.doc(params= {'resource_id': 'An ID'})
#     def get(self, resource_id):
#         timestamp = datetime.utcnow().isoformat()
#         return {'timestamp': timestamp}
# # -------------------------------------------------------------------------------


# ------------------------[ API to manage Curriculums ]-------------------------
class Curriculums:

    # ----------------[ Get Curriculums ]---------------------------------------
    @apiRestful.route('/resource/curriculums/filter')
    @apiRestful.doc(params= {
            'curriculumCategory': {'in': 'query', 'description': 'URL parameter, optional'},
            'curriculumType': {'in': 'query', 'description': 'URL parameter, optional'},
            # You can add query filter columns if needed.
    })
    class get_Curriculums_Filter(Resource):

        def get(self):
            queryParams = request.args
            filtersFromClient = loads(queryParams['filters'])
            filters = [getattr(CurriculumsModel, column).like(f'%{keyword}%') for column, keyword in filtersFromClient.items()]
            sort = loads(queryParams['sort'])
            column, option = sort['column'], sort['option']
            order = getattr(getattr(CurriculumsModel, column), option)()
            page = int(queryParams['page'])
            limit = int(queryParams['limit'])
            start, stop = (page-1)*limit, page*limit

            query = CurriculumsModel.query.filter(and_(*filters))
            curriculums = query.order_by(order).slice(start, stop).all()
            curriculumsSchema = CurriculumsModelSchema(many= True)
            output = curriculumsSchema.dump(curriculums)
            total = query.count()
            return {'return': {'items': output, 'total': total}}, 200
    # ---------------------------------------------------------------------------


    # ----------------[ Get Curriculums, joined to Members counts ]--------------
    @apiRestful.route('/resource/curriculums/withmembercount')
    class get_Curriculums_WithMemberCount(Resource):

        def get(self):
            curriculumList = CurriculumsModel.query.with_entities(CurriculumsModel.curriculumNo, CurriculumsModel.curriculumCategory, CurriculumsModel.ordinalNo, CurriculumsModel.curriculumName, func.concat(CurriculumsModel.startDate, '~', CurriculumsModel.endDate).label('curriculumPeriod'), CurriculumsModel.curriculumType).subquery()
            applicantCount = ApplicantsModel.query.with_entities(ApplicantsModel.curriculumNo, func.count(ApplicantsModel.phoneNo).label('ApplicantCount')).group_by(ApplicantsModel.curriculumNo).subquery()
            memberCount = MembersModel.query.with_entities(MembersModel.curriculumNo, func.count(MembersModel.phoneNo).label('MemberCount')).filter(MembersModel.attendanceCheck == 'Y').group_by(MembersModel.curriculumNo).subquery()
            memberCompleteCount = MembersModel.query.with_entities(MembersModel.curriculumNo, func.count(MembersModel.phoneNo).label('MemberCompleteCount')).filter(MembersModel.curriculumComplete == 'Y').group_by(MembersModel.curriculumNo).subquery()
            memberEmploymentCount = MembersModel.query.with_entities(MembersModel.curriculumNo, func.count(MembersModel.phoneNo).label('MemberEmploymentCount')).filter(MembersModel.employment == 'Y').group_by(MembersModel.curriculumNo).subquery()
            query = db.session.query(curriculumList).with_entities(curriculumList, func.ifnull(applicantCount.c.ApplicantCount, 0).label('ApplicantCount'), func.ifnull(memberCount.c.MemberCount, 0).label('MemberCount'), func.ifnull(memberCompleteCount.c.MemberCompleteCount, 0).label('MemberCompleteCount'), func.ifnull(memberEmploymentCount.c.MemberEmploymentCount, 0).label('MemberEmploymentCount')).outerjoin(applicantCount, curriculumList.c.curriculumNo == applicantCount.c.curriculumNo).outerjoin(memberCount, curriculumList.c.curriculumNo == memberCount.c.curriculumNo).outerjoin(memberCompleteCount, curriculumList.c.curriculumNo == memberCompleteCount.c.curriculumNo).outerjoin(memberEmploymentCount, curriculumList.c.curriculumNo == memberEmploymentCount.c.curriculumNo)

            df = pd.read_sql(query.statement, db.get_engine(bind= 'mysql'))
            output = convertDataframeToDictsList(df)
            total = query.count()

            return {'return': {'items': output, 'total': total}}, 200
    # ---------------------------------------------------------------------------
# -------------------------------------------------------------------------------


# ------------------------[ API to manage AttendanceLogs ]-----------------------
class AttendanceLogs:
    
    # ----------------[ Get new Attendance logs ]--------------------------------
    @apiRestful.route('/resource/attendancelogs/filter')
    @apiRestful.doc(params= {
            'phoneNo': {'in': 'query', 'description': 'URL parameter, optional'},
            'curriculumNo': {'in': 'query', 'description': 'URL parameter, optional'},
            'checkInOut': {'in': 'query', 'description': 'URL parameter, optional'},
            'attendanceDate': {'in': 'query', 'description': 'URL parameter, optional'},
            # You can add query filter columns if needed.
    })
    class get_AttendanceLogs_Filter(Resource):

        def get(self):
            queryFilter = request.args
            attendanceLogs = AttendanceLogsModel.query.filter_by(**queryFilter)
            attendanceLogsSchema = AttendanceLogsModelSchema(many= True)
            output = attendanceLogsSchema.dump(attendanceLogs.all())
            total = attendanceLogs.count()

            return {'return': {'items': output, 'total': total}}, 200
    # ---------------------------------------------------------------------------


    # ----------------[ Get attendance list of a specific curriculum ]-----------
    @apiRestful.route('/resource/attendancelogs/list')
    @apiRestful.doc(params= {
            'curriculumNo': {'in': 'query', 'description': 'URL parameter, reqired'},
    })
    class get_AttendanceLogs_List(Resource):

        def get(self):
            queryFilter = request.args
            
            attendanceLogs = AttendanceLogsModel.query.filter_by(**queryFilter)
            curriculumDuration = CurriculumsModel.query.with_entities(CurriculumsModel.startDate, CurriculumsModel.endDate).filter_by(**queryFilter).all()
            curriculumDuration = [date.strftime('%Y-%m-%d') for date in curriculumDuration[0]]
            membersPhoneNoList = MembersModelSchema(many= True).dump( MembersModel.query.with_entities(MembersModel.phoneNo).filter_by(**queryFilter).all() )
            membersPhoneNoList = [phoneNoDict['phoneNo'] for phoneNoDict in membersPhoneNoList]

            attendanceLogsDf = pd.read_sql(attendanceLogs.statement, db.get_engine(bind= 'mysql'))
            attendanceLogsDf['attendanceDate'] = attendanceLogsDf['attendanceDate'].astype(str)
            pivot = attendanceLogsDf.set_index(['phoneNo', 'checkInOut', 'attendanceDate'])[['signature', 'insertedTimestamp']]
            pivot['signatureTimestamp'] = pivot['signature'] + '\n' + pivot['insertedTimestamp'].dt.strftime('%Y-%m-%dT%H:%M:%SZ').astype(str)
            pivot = pivot.drop(columns= ['signature', 'insertedTimestamp']).unstack(level= [2, 1]).sort_index(axis= 'columns', level= 1)

            curriculumDates = [date.strftime('%Y-%m-%d') for date in pd.date_range(start= curriculumDuration[0], end= curriculumDuration[1], freq= 'B')]

            def convertDataframeToVueElementUiJsonFormat(dataframe):

                target = dataframe
                vueElementUiListJson = []

                recordIdx_name = target.index.name
                columnLevel0_name = target.columns.get_level_values(0)[0]
                columnLevel1_name = target.columns.get_level_values(1).name
                columnLevel3_1st = target.columns.get_level_values(2)[0]
                columnLevel3_2st = target.columns.get_level_values(2)[1]

                for recordIdxOrder in range(len(target.index)):
                    recordJson = {}
                    recordJson[recordIdx_name] = target.index[recordIdxOrder]
                    recordJson[columnLevel0_name] = []

                    for columnLevel2Order in range( len(set(target.columns.get_level_values(1))) ):
                        columnLevel2Idx = columnLevel2Order * 2
                        columnLevel3_1stRecordValue = target[ columnLevel0_name ][ target.columns.get_level_values(1)[columnLevel2Idx] ][ columnLevel3_1st ].values[recordIdxOrder]
                        columnLevel3_2ndRecordValue = target[ columnLevel0_name ][ target.columns.get_level_values(1)[columnLevel2Idx] ][ columnLevel3_2st ].values[recordIdxOrder]
                        columnLevel2Segment = {
                            columnLevel1_name: target.columns.get_level_values(1)[columnLevel2Idx],
                            columnLevel3_1st: columnLevel3_1stRecordValue,
                            columnLevel3_2st: columnLevel3_2ndRecordValue
                        }
                        recordJson[columnLevel0_name].append(columnLevel2Segment)
                    vueElementUiListJson.append(recordJson)

                return vueElementUiListJson

            output = convertDataframeToVueElementUiJsonFormat(pivot)
            total = attendanceLogs.count()

            return {'return': {'items': output, 'total': total}}, 200
    # ---------------------------------------------------------------------------


    # ----------------[ Create a new Attendance log ]----------------------------
    @apiRestful.route('/resource/attendancelogs/new')
    @apiRestful.doc(params= {
            'phoneNo': {'in': 'formData', 'description': 'application/json, body required'},
            'curriculumNo': {'in': 'formData', 'description': 'application/json, body required'},
            'checkInOut': {'in': 'formData', 'description': 'application/json, body required'},
            'signature': {'in': 'formData', 'description': 'application/json, body required'},
            # You can add formData columns if needed.
    })
    class post_AttendanceLogs_New(Resource):

        def post(self):
            infoFromClient = request.form
            phoneNoFromClient = infoFromClient['phoneNo']               # if key doesn't exist, returns a 400, bad request error("message": "The browser (or proxy) sent a request that this server could not understand."), https://scotch.io/bar-talk/processing-incoming-request-data-in-flask
            curriculumNoFromClient = infoFromClient['curriculumNo']
            checkInOutFromClient = infoFromClient['checkInOut']
            signatureFromClient = infoFromClient['signature'].split(',')[-1].strip()
            attendanceDate = (datetime.utcnow() + timedelta(hours= 9)).strftime('%Y-%m-%d')     # Calculate Korea Standard Time(KST), date only

            requestedBody = {
                "phoneNo": phoneNoFromClient,
                "curriculumNo": curriculumNoFromClient,
                "checkInOut": checkInOutFromClient,
                "signature": signatureFromClient,
                "attendanceDate": attendanceDate,
            }
            
            newAttendanceLog = AttendanceLogsModel(**requestedBody)

            try:
                db.session.add(newAttendanceLog)
                db.session.commit()
                return {'return': {'message': f'New AttendanceLog created : {requestedBody}'}}, 201
            except:
                db.session.rollback()
                return {'return': {'message': 'Something went wrong'}}, 500
    # ---------------------------------------------------------------------------
# -------------------------------------------------------------------------------


# ------------------------[ API to manage Members ]------------------------------
class Members:

    # ----------------[ Get members ]--------------------------------------------
    @apiRestful.route('/resource/members/filter')
    @apiRestful.doc(params= {
            'phoneNo': {'in': 'query', 'description': 'URL parameter, optional'},
            'curriculumNo': {'in': 'query', 'description': 'URL parameter, optional'},
            'attendancePass': {'in': 'query', 'description': 'URL parameter, optional'},
            'attendanceCheck': {'in': 'query', 'description': 'URL parameter, optional'},
            'curriculumComplete': {'in': 'query', 'description': 'URL parameter, optional'},
            'employment': {'in': 'query', 'description': 'URL parameter, optional'},
            # You can add query filter columns if needed.
    })
    class get_Members_Filter(Resource):

        def get(self):
            queryFilter = request.args
            members = MembersModel.query.filter_by(**queryFilter)
            membersSchema = MembersModelSchema(many= True)
            output = membersSchema.dump(members.all())
            total = members.count()

            return {'return': {'items': output, 'total': total}}, 200
    # -----------------------------------------------------------------------------


    # ----------------[ Update members' Info ]-------------------------------------
    @apiRestful.route('/resource/members')
    @apiRestful.doc(params= {
            'phoneNo': {'in': 'formData', 'description': 'application/json, body required'},
            'curriculumNo': {'in': 'formData', 'description': 'application/json, body required'},
            'attendancePass': {'in': 'formData', 'description': 'application/json, body required'},
            'attendanceCheck': {'in': 'formData', 'description': 'application/json, body required'},
            'curriculumComplete': {'in': 'formData', 'description': 'application/json, body required'},
            'employment': {'in': 'formData', 'description': 'application/json, body required'},
            # You can add formData columns if needed.
    })
    class put_Members_Info(Resource):

        def put(self):
            infoFromClient = request.form
            requestedBody = {
                'phoneNo': infoFromClient['phoneNo'],                   # if key doesn't exist, returns a 400, bad request error("message": "The browser (or proxy) sent a request that this server could not understand."), https://scotch.io/bar-talk/processing-incoming-request-data-in-flask
                'curriculumNo': infoFromClient['curriculumNo'],
                'attendancePass': infoFromClient['attendancePass'],
                'attendanceCheck': infoFromClient['attendanceCheck'],
                'curriculumComplete': infoFromClient['curriculumComplete'],
                'employment': infoFromClient['employment'],
            }

            memberInfo = MembersModel(**requestedBody)

            try:
                db.session.merge(memberInfo)    # session.merge() : A kind of UPSERT, https://docs.sqlalchemy.org/en/latest/orm/session_state_management.html#merging
                db.session.commit()
                return {'return': {'message': f'MemberInfo updated : {requestedBody}'}}, 201
            except:
                db.session.rollback()
                return {'return': {'message': 'Something went wrong'}}, 500
    # -----------------------------------------------------------------------------
# ---------------------------------------------------------------------------------


# ------------------------[ API to manage Applicants ]-----------------------------
class Applicants:

    # ----------------[ Get Applicants ]-------------------------------------------
    @apiRestful.route('/resource/applicants/filter')
    @apiRestful.doc(params= {
            'phoneNo': {'in': 'query', 'description': 'URL parameter, optional'},
            'curriculumNo': {'in': 'query', 'description': 'URL parameter, optional'},
            'applicantName': {'in': 'query', 'description': 'URL parameter, optional'},
            'email': {'in': 'query', 'description': 'URL parameter, optional'},
            # You can add query filter columns if needed.
    })
    class get_Applicants_Filter(Resource):

        def get(self):
            queryFilter = request.args
            applicants = ApplicantsModel.query.filter_by(**queryFilter)
            applicantsSchema = ApplicantsModelSchema(many= True)
            output = applicantsSchema.dump(applicants.all())
            total = applicants.count()

            return {'return': {'items': output, 'total': total}}, 200
    # -----------------------------------------------------------------------------


    #--------[ POST Raw Excel File(Google Survey) to Applicants and Members ]------
    @apiRestful.route('/resource/applicants/bulk')
    @apiRestful.doc(params= {
            'curriculumNo': {'in': 'formData', 'description': 'application/json, body required'},
            'applicantsBulkXlsxFile': {'in': 'formData', 'type': 'file', 'description': 'application/json, body/xlsx file required'},
            # You can add formData columns if needed.
    })
    class post_Applicants_Bulk(Resource):

        def post(self):
            curriculumNoFromClient = request.form['curriculumNo']               # if key doesn't exist, returns a 400, bad request error("message": "The browser (or proxy) sent a request that this server could not understand."), https://scotch.io/bar-talk/processing-incoming-request-data-in-flask
            applicantsbulkFromClient = request.files['applicantsBulkXlsxFile']

            applicantsDf = pd.read_excel(applicantsbulkFromClient)
            applicantsDf.columns = applicantsDf.columns.map(lambda x: Config.XLSX_COLUMNS_TO_SCHEMA_MAP[ x[:4]+'_'+str(len(x)//19) ])       # Convert column names, Using "x[:4]+'_'+str(len(x)//19)" as a unique key
            applicantsDf['curriculumNo'] = curriculumNoFromClient
            membersDf = applicantsDf[['phoneNo', 'curriculumNo']]

            applicantsDictsList = convertDataframeToDictsList(applicantsDf)
            membersDictsList = convertDataframeToDictsList(membersDf)

            newBulkApplicants = [ApplicantsModel(**applicant) for applicant in applicantsDictsList]
            newBulkMembers = [MembersModel(**member) for member in membersDictsList]

            try:
                db.session.add_all(newBulkApplicants)
                db.session.add_all(newBulkMembers)
                db.session.commit()
                return {'return': {'message': f'Applicants/Members Bulk : curriculumNo {curriculumNoFromClient}, {len(newBulkApplicants)} records are inserted.'}}, 201
            except:
                db.session.rollback()
                return {'return': {'message': 'Something went wrong'}}, 500
    # -----------------------------------------------------------------------------
# ---------------------------------------------------------------------------------