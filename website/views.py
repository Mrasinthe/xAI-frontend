# Make sure to import these from your app

from flask import request, render_template, session, flash, Response
from datetime import datetime
from .models import User
from . import db
import aiohttp
import asyncio
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from flask_login import login_required, current_user
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from aiohttp import FormData
from aiohttp import ClientSession
from flask_login import UserMixin
from functools import wraps
from django.shortcuts import render
import time
from math import ceil
import base64


views = Blueprint('views', __name__)

# To check the user role

###################### START DEFUALT ############################


def user_role_required(required_role):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            # Get the user's role from the session
            user_role = session.get('user_role')
            user = User.query.filter_by(
                first_name=current_user.first_name).first()
            user_role = user.user_role

            if user_role == required_role:
                return func(*args, **kwargs)
            else:
                # Redirect to an unauthorized page or take other action
                return redirect(url_for('views.unauthorized'))

        return decorated_function

    return decorator


@views.route('/')
def home():
    if current_user.is_authenticated:
        # If user is already logged in, redirect to a different page
        return redirect(url_for('views.select_role'))

    return render_template("home.html", user=current_user)


@views.route('/unauthorized', methods=['GET'])
def unauthorized():
    user_role = request.args.get('user_role')
    print("unauthorized",  user_role)
    session['user_role'] = user_role

    return render_template("unauthorized.html", user=current_user, user_role=user_role)


@views.route('/userRole', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def select_role():
    if request.method == 'POST':
        user_role = request.form.get('user_role')
        print("Selected role:", user_role)
        # Store the selected role in a session variable
        session['user_role'] = user_role
        # Redirect to the main page with the selected role as a query parameter
        return redirect(url_for('views.dashboard', user_role=user_role))

    return render_template('userRole.html', user=current_user)


@views.route('/admin', methods=['GET', 'POST'])
@login_required
@user_role_required('admin')
def admin_page():
    if request.method == 'POST':
        user_role = request.form.get('user_role')
        print("Selected role:", user_role)
        # Store the selected role in a session variable
        session['user_role'] = user_role
        # Redirect to the main page with the selected role as a query parameter
        return redirect(url_for('views.dashboard', user_role=user_role))

    return render_template('admin_page.html', user=current_user)


@views.route('/dashboard', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def dashboard():
    user_role = request.args.get('user_role')
    print("Dashboard",  user_role)
    session['user_role'] = user_role

    return render_template("dashboard.html", user=current_user, user_role=user_role)


@views.route('/about', methods=['GET'])
def about():
    user_role = request.args.get('user_role')
    print("about",  user_role)
    session['user_role'] = user_role

    return render_template("about.html", user=current_user, user_role=user_role)


@views.route('/contact', methods=['GET', 'POST'])
def contact():
    user_role = request.args.get('user_role')
    print("contact",  user_role)
    session['user_role'] = user_role

    return render_template("contact.html", user=current_user, user_role=user_role)


@views.route('/profile', methods=['GET'])
def profile():
    print(current_user.first_name)
    user = User.query.filter_by(first_name=current_user.first_name).first()
    user_role = request.args.get('user_role')
    print("profile",  user_role)
    session['user_role'] = user_role
    if user:
        id = user.id

        user_detail = User.query.get(id)
        print("user_detail",  user_detail)

        user_data = {
            "id": user_detail.id,
            "name": user_detail.first_name,
            "email": user_detail.email
        }

        return render_template("profile.html", results=user_data, user=current_user, user_role=user_role)
    else:

        return render_template("profile.html", results='Wrong User', user=current_user, user_role=user_role)

###################### END DEFUALT ############################

###################### START XAI ##############################


@views.route('/XAI', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def mainPage():
    user_role = request.args.get('user_role')
    print("mainPage",  user_role)
    session['user_role'] = user_role

    return render_template("mainPage.html", user=current_user, user_role=user_role)


# Simulated data for the APIs based on user roles

# 193.40.154.160:8090 - LIME
# 193.40.154.87:8090 - SHAP
# 193.40.155.96:8090 - Occlusion ['http://193.40.154.160:8090/explain_lime/image','http://193.40.154.87:8090/explain_shap/image','http://193.40.155.96:8090/explain_occlusion/image'],    , 'http://193.40.154.143:8000/explain_shap/image','http://193.40.154.143:8000/explain_occlusion/image'


XAI_URLS = {
    'User': ['http://193.40.154.143:8000/explain_lime/image'],
    'Developer': ['http://193.40.154.160:8090/explain_lime/image', 'http://193.40.154.143:8000/explain_shap/image', 'http://193.40.154.143:8000/explain_occlusion/image'],
    'Auditor': ['http://193.40.154.143:8000/explain_lime/image', 'http://193.40.154.143:8000/explain_shap/image', 'http://193.40.154.143:8000/explain_occlusion/image'],
    'Business': ['http://193.40.154.143:8000/explain_lime/image']
}


@views.route('/explain', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def explain():
    user_role = session.get('user_role', None)
    print("explain", user_role)
    if not user_role:
        return "User role not found in the session. Please select a role first."

    ClassLabel = request.form['ClassLabel']
    ImageFile = request.files['ImageFile']
    mlModel = request.files['mlModel']
    ImageFileBytes = request.files['ImageFile'].read()
    print("ImageFileBytes")
    # print(ImageFileBytes)

    api_urls = XAI_URLS.get(user_role, None)

    if not api_urls:
        return "Invalid user role."

    try:

        async def make_api_call():
            results = []
            async with ClientSession() as csession:
                async def fetch_data(api_url):
                    try:
                        api_url = f"{api_url}?imagetype={ClassLabel}"
                        form_data = FormData()
                        form_data.add_field('file', ImageFile.stream.read(
                        ), filename=ImageFile.filename, content_type=ImageFile.content_type)
                        form_data.add_field('mlModel', mlModel.stream.read(
                        ), filename=mlModel.filename, content_type=mlModel.content_type)
                        form_data.add_field(
                            'ImageFileBytes', ImageFileBytes, content_type='application/octet-stream')

                        async with csession.post(api_url, data=form_data) as response:
                            if response.status == 200:
                                result = await response.json()
                                return result
                            else:
                                print(
                                    f"API call to {api_url} failed with status {response.status}.")
                                return f"API call to {api_url} failed with status {response.status}.", 500
                    except Exception as e:
                        print(
                            f"API call to {api_url} failed with exception: {e}")
                        return None

                tasks = [fetch_data(api_url) for api_url in api_urls]
                results = await asyncio.gather(*tasks)

                merged_dict = {}

                for json_obj in results:
                    if isinstance(json_obj, dict):
                        merged_dict.update(json_obj)

                merged_json = json.dumps(merged_dict, indent=4)
                data_dict = json.loads(merged_json)
                return data_dict

        loop = asyncio.new_event_loop()
        data_dict = loop.run_until_complete(make_api_call())

    except Exception as e:
        print(f"API call to {api_urls} failed with exception: {e}")
        return f"API call failed with exception: {e}", 500

    user_role = session.get('user_role', None)

    return render_template('results.html', results=data_dict, user=current_user, user_role=user_role)


###################### END XAI ##############################

###################### START FAIRNESS #################################


@views.route('/fairness', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def fairness():
    user_role = request.args.get('user_role')
    print("fairness",  user_role)
    session['user_role'] = user_role

    return render_template("Fairness/fairness.html", user=current_user, user_role=user_role)


# 193.40.154.161:31057 - Fairness
FAIR_URL = 'http://193.40.154.143:8000/explain_fairness/file'


@views.route('/explainFair', methods=['POST'])
@login_required
@user_role_required('user')
def explainFair():
    user_role = session.get('user_role', None)

    try:
        ImageFile = request.files['ImageFile']
    except KeyError as e:
        return f"Missing required field: {str(e)}", 400

    api_url = FAIR_URL

    try:
        async def make_api_call():
            async with ClientSession() as csession:
                form_data = FormData()
                form_data.add_field('file', ImageFile.stream.read(),
                                    filename=ImageFile.filename, content_type=ImageFile.content_type)

                async with csession.post(api_url, data=form_data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(
                            f"API call to {api_url} failed with status {response.status}.")
                        return f"API call to {api_url} failed with status {response.status}.", 500

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(make_api_call())

    except Exception as e:
        print(f"API call to {api_url} failed with exception: {e}")
        return f"API call failed with exception: {e}", 500

    return render_template('Fairness/fairResults.html', results=result, user=current_user, user_role=user_role)


###################### END FAIRNESS #################################


####################### START PRIVACY ##################################

@views.route('/privacy', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def privacy():
    user_role = request.args.get('user_role')
    print("privacy",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            clientSamplingRate = float(request.form['clientSamplingRate'])
            clippingValue = float(request.form['clippingValue'])
            delta = float(request.form['delta'])
            epsilon = float(request.form['epsilon'])
            modelParameters1 = float(request.form['modelParameters1'])
            modelParameters2 = float(request.form['modelParameters2'])
            noiseType = int(request.form['noiseType'])
            sigma = float(request.form['sigma'])
            totalFLRounds = int(request.form['totalFLRounds'])
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        payload = {
            "clientSamplingRate": clientSamplingRate,
            "clippingValue": clippingValue,  # Assuming you want the file name here
            "delta": delta,
            "epsilon": epsilon,
            "modelParameters": [
                [
                    [
                        [
                            modelParameters1,
                            modelParameters2
                        ]
                    ]
                ]
            ],
            "noiseType": noiseType,
            "sigma": sigma,
            "totalFLRounds": totalFLRounds
        }
        print("Before Submit", payload)

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the asynchronous task and retrieve the result
            results = loop.run_until_complete(
                post_privacy(payload))
            print(results)
            return render_template("Privacy/privacy_MS.html", results=results,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("Privacy/privacy_MS.html", results=None, user=current_user, user_role=user_role)


Privacy_URL = 'http://193.40.154.143:8000/api/v3/differential_privacy/execute'


async def post_privacy(payload):
    api_url = f"{Privacy_URL}"
    try:
        async with ClientSession() as csession:

            async with csession.post(api_url, data=json.dumps(
                    payload), headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    print(
                        f"Check API call to {api_url} failed with status {response.status}.")
                    return f"API call to {api_url} failed with status {response.status}.", 500
    except aiohttp.ClientError as e:
        return []

###################### END PRIVACY  ##############################


####################### START MEDICAL ANALYSIS ##################################
MAS_DetectURL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/emergency_detection/mi_detection/predict'


@views.route('/medical', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def medical():
    user_role = request.args.get('user_role')
    print("medical",  user_role)
    session['user_role'] = user_role

    return render_template("MAS/medicalService.html", user=current_user, user_role=user_role)


@views.route('/emergencyDetection', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def emergencyDetection():
    user_role = request.args.get('user_role')
    print("emergencyDetection",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            dat = request.form['dat']
            hea = request.form['hea']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the asynchronous task and retrieve the result
            results = loop.run_until_complete(
                post_emergency(payload))
            print(results)
            return render_template("MAS/emergencyDetection.html", results=results,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/emergencyDetection.html", results=None, user=current_user, user_role=user_role)


async def post_emergency(payload):
    api_url = f"{MAS_DetectURL}"
    try:
        async with ClientSession() as csession:

            async with csession.post(api_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    response_text = await response.text()
                    return f"API call to {api_url} failed with status {response_text} .",  {response.status}
    except aiohttp.ClientError as e:
        return []


MAS_ExplainURL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/emergency_detection/mi_detection/explain'


@views.route('/emergencyExplain', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def emergencyExplain():
    user_role = request.args.get('user_role')
    print("emergencyExplain",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            dat = request.form['dat2']
            hea = request.form['hea2']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the asynchronous task and retrieve the result
            results2 = loop.run_until_complete(
                post_emergencyExplain(payload))

            if isinstance(results2, bytes):
                base64_image = base64.b64encode(results2).decode("utf-8")

            return render_template("MAS/emergencyDetection.html", results2=base64_image,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/emergencyDetection.html", results2=None, user=current_user, user_role=user_role)


async def post_emergencyExplain(payload):
    api_url = f"{MAS_ExplainURL}"
    print(api_url)
    try:
        async with ClientSession() as csession:

            async with csession.post(api_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        result = await response.json()
                        print(result)
                        return result
                    else:
                        # Handle non-JSON response here
                        # response_text = await response.text()
                        # print(response_text)
                        binary_data = await response.read()
                        # You can save binary_data to a file or handle it as needed
                        # For example, if it's an image, you can save it or display it
                        # If it's some other binary data, process it as required
                        return binary_data
                        # return f"API call succeeded with unexpected content type: {content_type}"
                else:
                    response_text = await response.text()
                    print(response)
                    return f"API call to {api_url} failed with status {response_text} .",  {response.status}
    except aiohttp.ClientError as e:
        return f"API call to {api_url} failed with status {e} .",  {response.status}


MAS_DemoURL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/emergency_detection/mi_detection/enhanced_interpretability_module_link_demo'


@views.route('/emergencyDemo', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def emergencyDemo():
    user_role = request.args.get('user_role')
    print("emergencyDemo",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            dat = request.form['dat3']
            hea = request.form['hea3']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the asynchronous task and retrieve the result
            results3 = loop.run_until_complete(
                post_emergencyDemo(payload))

            if isinstance(results3, bytes):
                base64_image = base64.b64encode(results3).decode("utf-8")
            # if isinstance(results3, bytes):
            #     return Response(results3, content_type="image/png")

            return render_template("MAS/emergencyDetection.html", results3=base64_image,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/emergencyDetection.html", results3=None, user=current_user, user_role=user_role)


async def post_emergencyDemo(payload):
    api_url = f"{MAS_DemoURL}"
    print(api_url)
    try:
        async with ClientSession() as csession:

            async with csession.get(api_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        result = await response.json()
                        print(result)
                        return result
                    else:
                        # Handle non-JSON response here
                        # response_text = await response.text()
                        # print(response_text)
                        binary_data = await response.read()
                        # You can save binary_data to a file or handle it as needed
                        # For example, if it's an image, you can save it or display it
                        # If it's some other binary data, process it as required
                        return binary_data
                        # return f"API call succeeded with unexpected content type: {content_type}"

                else:
                    response_text = await response.text()
                    print(response)
                    return f"API call to {api_url} failed with status {response_text} .",  {response.status}
    except aiohttp.ClientError as e:
        return f"API call to {api_url} failed with status {e} .",  {response.status}


# medicalAnalysis


@views.route('/medicalAnalysis', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def medicalAnalysis():
    user_role = request.args.get('user_role')
    print("medicalAnalysis",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            dat = request.form['dat']
            hea = request.form['hea']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the asynchronous task and retrieve the result
            results = loop.run_until_complete(
                post_MASECG(payload))

            if isinstance(results, bytes):
                base64_image2 = base64.b64encode(results).decode("utf-8")

            return render_template("MAS/MedicalAnalysis.html", results=base64_image2,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/MedicalAnalysis.html", results=None, user=current_user, user_role=user_role)


MedAnalysisECG_URL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/medical_analysis/ecg_analysis/visualize_ecg'


async def post_MASECG(payload):
    api_url = f"{MedAnalysisECG_URL}"
    try:
        async with ClientSession() as csession:

            async with csession.post(api_url, data=json.dumps(
                    payload), headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        result = await response.json()
                        print(result)
                        return result
                    else:
                        # Handle non-JSON response here
                        # response_text = await response.text()
                        # print(response_text)
                        binary_data = await response.read()
                        # You can save binary_data to a file or handle it as needed
                        # For example, if it's an image, you can save it or display it
                        # If it's some other binary data, process it as required
                        return binary_data
                        # return f"API call succeeded with unexpected content type: {content_type}"

                else:
                    print(
                        f"Check API call to {api_url} failed with status {response.status}.")
                    return f"API call to {api_url} failed with status {response.status}.", 500
    except aiohttp.ClientError as e:
        return []


# identifySegments

@views.route('/identifySegments', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def identifySegments():
    user_role = request.args.get('user_role')
    print("identifySegments",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            dat = request.form['dat']
            hea = request.form['hea']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the asynchronous task and retrieve the result
            results = loop.run_until_complete(
                post_identifySegments(payload))

            if isinstance(results, bytes):
                base64_image2 = base64.b64encode(results).decode("utf-8")

            return render_template("MAS/identifySegments.html", results=base64_image2,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/identifySegments.html", results=None, user=current_user, user_role=user_role)


MedSegment_URL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/medical_analysis/ecg_analysis/identify_segments'


async def post_identifySegments(payload):
    api_url = f"{MedSegment_URL}"
    try:
        async with ClientSession() as csession:

            async with csession.post(api_url, data=json.dumps(
                    payload), headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        result = await response.json()
                        print(result)
                        return result
                    else:
                        # Handle non-JSON response here
                        # response_text = await response.text()
                        # print(response_text)
                        binary_data = await response.read()
                        # You can save binary_data to a file or handle it as needed
                        # For example, if it's an image, you can save it or display it
                        # If it's some other binary data, process it as required
                        return binary_data
                        # return f"API call succeeded with unexpected content type: {content_type}"

                else:
                    print(
                        f"Check API call to {api_url} failed with status {response.status}.")
                    return f"API call to {api_url} failed with status {response.status}.", 500
    except aiohttp.ClientError as e:
        return []

# tickImportance


@views.route('/tickImportance', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def tickImportance():
    user_role = request.args.get('user_role')
    print("tickImportance",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            xai_method = request.form['xai_method']
            model_id = request.form['model_id']
            dat = request.form['dat']
            hea = request.form['hea']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        tickImportance_URL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/medical_analysis/ecg_analysis/explain/'

        api_url = f"{tickImportance_URL}{xai_method}/tick_importance?model_id={model_id}"
        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the asynchronous task and retrieve the result
            results = loop.run_until_complete(
                post_tickImportance(payload, api_url))

            if isinstance(results, bytes):
                base64_image2 = base64.b64encode(results).decode("utf-8")

            return render_template("MAS/tickImportance.html", results=base64_image2,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/tickImportance.html", results=None, user=current_user, user_role=user_role)


async def post_tickImportance(payload, api_url):

    try:
        async with ClientSession() as csession:

            async with csession.post(api_url, data=json.dumps(
                    payload), headers={"Content-Type": "application/json"}) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        result = await response.json()
                        print(result)
                        return result
                    else:
                        # Handle non-JSON response here
                        # response_text = await response.text()
                        # print(response_text)
                        binary_data = await response.read()
                        # You can save binary_data to a file or handle it as needed
                        # For example, if it's an image, you can save it or display it
                        # If it's some other binary data, process it as required
                        return binary_data
                        # return f"API call succeeded with unexpected content type: {content_type}"

                else:
                    print(
                        f"Check API call to {api_url} failed with status {response.status}.")
                    return f"API call to {api_url} failed with status {response.status}.", 500
    except aiohttp.ClientError as e:
        return []

# timeImportance


@views.route('/timeImportance', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def timeImportance():
    user_role = request.args.get('user_role')
    print("timeImportance",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            xai_method = request.form['xai_method']
            model_id = request.form['model_id']
            dat = request.form['dat']
            hea = request.form['hea']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        tickImportance_URL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/medical_analysis/ecg_analysis/explain/'

        api_url = f"{tickImportance_URL}{xai_method}/time_importance?model_id={model_id}"
        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the asynchronous task and retrieve the result
            results = loop.run_until_complete(
                post_tickImportance(payload, api_url))

            if isinstance(results, bytes):
                base64_image2 = base64.b64encode(results).decode("utf-8")

            return render_template("MAS/timeImportance.html", results=base64_image2,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/timeImportance.html", results=None, user=current_user, user_role=user_role)


# leadImportance
@views.route('/leadImportance', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def leadImportance():
    user_role = request.args.get('user_role')
    print("leadImportance",  user_role)
    session['user_role'] = user_role

    if request.method == 'POST':
        try:
            xai_method = request.form['xai_method']
            model_id = request.form['model_id']
            dat = request.form['dat']
            hea = request.form['hea']
        except KeyError as e:
            return f"Missing required field: {str(e)}", 400

        tickImportance_URL = 'https://medical-analysis-service.apps.osc.fokus.fraunhofer.de/medical_analysis/ecg_analysis/explain/'

        api_url = f"{tickImportance_URL}{xai_method}/lead_importance?model_id={model_id}"
        payload = {
            "dat": dat,
            "hea": hea
        }

        try:
            # Create and run a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the asynchronous task and retrieve the result
            results = loop.run_until_complete(
                post_tickImportance(payload, api_url))

            if isinstance(results, bytes):
                base64_image2 = base64.b64encode(results).decode("utf-8")

            return render_template("MAS/leadImportance.html", results=base64_image2,  user=current_user, user_role=user_role)

        except Exception as e:
            return f"API call failed with exception: {e}", 500

    return render_template("MAS/leadImportance.html", results=None, user=current_user, user_role=user_role)

###################### END MEDICAL ANALYSIS  ##############################

###################### START MONTIMAGE ##############################


# @views.route('/networkTraffic', methods=['GET', 'POST'])
# @login_required
# @user_role_required('user')
# def networkTraffic():
#     user_role = request.args.get('user_role')
#     print("networkTraffic",  user_role)
#     session['user_role'] = user_role
#     timestamp = 1696846901651 / 1000  # Convert from milliseconds to seconds
#     dt = datetime.fromtimestamp(timestamp)
#     print(dt)

#     api_url = 'http://193.40.154.52:31057/api/models'

#     try:
#         response = requests.get(api_url)
#         models = response.json()
#         print('models', models)
#     except requests.exceptions.RequestException as e:
#         models = []

#     return render_template("NT/networkTraffic.html", models=models, user=current_user, user_role=user_role)

MODELS_URL = 'http://193.40.154.52:31057/api/models'

# Define an asynchronous function to fetch models


async def fetch_models():
    api_url = f"{MODELS_URL}"
    async with ClientSession() as csession:
        try:
            async with csession.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return []
        except aiohttp.ClientError as e:
            return []


@ views.route('/networkTraffic', methods=['GET', 'POST'])
@ login_required
@ user_role_required('user')
def networkTraffic():
    user_role = request.args.get('user_role')
    print("networkTraffic", user_role)
    session['user_role'] = user_role

    # Create and run a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run the asynchronous task and retrieve the result
    models = loop.run_until_complete(fetch_models())

    return render_template('NT/networkTraffic.html', models=models, user=current_user, user_role=user_role)


@ views.route('/models/all', methods=['GET', 'POST'])
@ login_required
@ user_role_required('user')
def show_all_models():
    user_role = request.args.get('user_role')
    print("show_all_models", user_role)
    session['user_role'] = user_role

    # Create and run a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run the asynchronous task and retrieve the result
    models = loop.run_until_complete(fetch_models())

    return render_template('NT/modelsList.html', models=models, user=current_user, user_role=user_role)


ACBuild_URL = 'http://193.40.154.52:31057/api/ac/build'


@ views.route('/ac/build', methods=['GET', 'POST'])
@ login_required
@ user_role_required('user')
def ac_build():
    user_role = request.args.get('user_role')
    print("ac_build",  user_role)
    session['user_role'] = user_role

    # if request.method == 'POST':
    #     api_url = f"{ACBuild_URL}"
    #     try:
    #         modelType = request.files['modelType']
    #         ImageFile = request.files['ImageFile']
    #         trainingRatio = request.files['trainingRatio']

    #     except KeyError as e:
    #         return f"Missing required field: {str(e)}", 400

    #     try:
    #         async with ClientSession() as csession:
    #             form_data = FormData()
    #             form_data.add_field('modelType', modelType.stream.read(
    #             ), filename=modelType.filename, content_type=modelType.content_type)
    #             form_data.add_field('ImageFile', ImageFile.stream.read(
    #             ), filename=ImageFile.filename, content_type=ImageFile.content_type)
    #             form_data.add_field('trainingRatio', trainingRatio.stream.read(
    #             ), filename=trainingRatio.filename, content_type=trainingRatio.content_type)

    #             async with csession.post(api_url, data=form_data) as response:
    #                 if response.status == 200:
    #                     result = await response.json()
    #                     flash('The model {{ result }} was built successfully!',
    #                           category='success')
    #                     redirect(url_for('views.ac_build'),
    #                              user=current_user, user_role=user_role)
    #                 else:
    #                     print(
    #                         f"API call to {api_url} failed with status {response.status}.")
    #                     return f"API call to {api_url} failed with status {response.status}.", 500
    #     except Exception as e:
    #         print(f"API call to {api_url} failed with exception: {e}")
    #         return f"API call failed with exception: {e}", 500

    # return redirect(url_for('views.ac_build'), user=current_user, user_role=user_role)

    return render_template("NT/ac_build.html", user=current_user, user_role=user_role)


@ views.route('/ac/build/p', methods=['POST'])
@ login_required
@ user_role_required('user')
def ac_build_p():
    user_role = session.get('user_role', None)

    api_url = f"{ACBuild_URL}"
    try:
        modelType = request.form['modelType']
        ImageFile = request.files['ImageFile']
        featureList = request.form['featureList']
        trainingRatio = request.form['trainingRatio']

    except KeyError as e:
        return f"Missing required field: {str(e)}", 400

    try:
        # Create and run a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the asynchronous task and retrieve the result
        models = loop.run_until_complete(
            post_acmodels(modelType, ImageFile, featureList, trainingRatio))
        print(models)
        flash('The model {{ result }} was built successfully!',
              category='success')
        return render_template('NT/ac_build.html',  user=current_user, user_role=user_role)
    #                     redirect(url_for('views.ac_build'),
    #                              user=current_user, user_role=user_role)

    except Exception as e:
        print(f"API call to {api_url} failed with exception: {e}")
        return f"API call failed with exception: {e}", 500

    return render_template('NT/ac_build.html',  user=current_user, user_role=user_role)


async def post_acmodels(modelType, ImageFile, featureList, trainingRatio):
    api_url = f"{ACBuild_URL}"
    try:
        # Create the JSON payload
        payload = {
            "buildACConfig": {
                "modelType": modelType,
                "dataset": ImageFile,  # Assuming you want the file name here
                "trainingRatio": trainingRatio
            }
        }
        print(payload)
        async with ClientSession() as csession:

            form_data = FormData()
            form_data.add_field('json', json.dumps(
                payload),  content_type='application/json')

            # Send the POST request with the JSON payload
            # Use data instead of json
            async with csession.post(api_url, data=form_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    print(
                        f"Check API call to {api_url} failed with status {response.status}.")
                    return f"API call to {api_url} failed with status {response.status}.", 500
    except aiohttp.ClientError as e:
        return []


@views.route('/ad/build', methods=['GET', 'POST'])
@login_required
@user_role_required('user')
def ad_build():
    user_role = request.args.get('user_role')
    print("ad_build",  user_role)
    session['user_role'] = user_role

    return render_template("NT/ad_build.html", user=current_user, user_role=user_role)


# @views.route('/submit_form', methods=['POST'])
# def submit_form():
#     # Get the values from the form
#     modelType = request.form['modelType']
#     dataset = request.files['ImageFile']
#     trainingRatio = request.form['trainingRatio']

#     user_role = session.get('user_role', None)
#     print("submit_form",  user_role)
#     session['user_role'] = user_role
#     # Construct the JSON data
#     data = {
#         "buildACConfig": {
#             "modelType": modelType,
#             "dataset": dataset.filename,
#             "trainingRatio": float(trainingRatio)
#         }
#     }

#     try:
#         # Make the POST request with JSON data
#         response = requests.post(ACBuild_URL, json=data)

#         # Check the response status code
#         response.raise_for_status()

#         # Check if the response is in JSON format
#         if response.headers.get('content-type') == 'application/json':
#             response_data = response.json()
#             print(response_data)
#             flash('The model {{ result }} was built successfully!',
#                   category='success')
#             return render_template('NT/ac_build.html', user=current_user, user_role=user_role)
#             # return "POST request was successful!<br>" + str(response_data)
#         else:
#             return "POST request was successful, but the response is not in JSON format."

#     except requests.exceptions.RequestException as e:
#         return f"POST request failed with the following error: {e}"

#     except ValueError as e:
#         return f"Failed to parse the response JSON: {e}"


# @views.route('/submit_form', methods=['POST'])
# def submit_form():
#     # Get the values from the form
#     modelType = request.form['modelType']
#     dataset = request.files['ImageFile']
#     featureList = request.form['featureList']
#     trainingRatio = request.form['trainingRatio']

#     user_role = session.get('user_role', None)
#     session['user_role'] = user_role

#     # Construct the JSON data
#     data = {
#         "buildACConfig": {
#             "modelType": modelType,
#             "dataset": dataset.filename,
#             "trainingRatio": float(trainingRatio)
#         }
#     }

#     # Make the POST request with JSON data
#     response = requests.post(ACBuild_URL, json=data)

#     # Check the response status code
#     if response.status_code == 200:
#         response_json = response.json()
#         while True:
#             status_response = requests.get(url_for('check_model_status'))
#             if status_response.status_code == 200:
#                 status_json = status_response.json()
#                 is_running = status_json.get("isRunning", True)
#                 if not is_running:

#                     flash('Error fetching model status from the other API.',
#                           category='error')
#                     break  # Exit the loop once isRunning is False
#                 else:
#                     # Wait for 5 seconds before checking again
#                     time.sleep(5)
#         else:
#             flash(
#                 f'The model with id {response_json["lastBuildId"]} was built successfully!',
#                 category='success'
#             )

#     else:
#         flash('The model build request failed with a status code: ' +
#               str(response.status_code), category='error')

#     return render_template('NT/ac_build.html', user=current_user, user_role=user_role)

@views.route('/submit_form', methods=['POST'])
async def submit_form():
    # Get the values from the form
    modelType = request.form['modelType']
    dataset = request.files['ImageFile']
    featureList = request.form['featureList']
    trainingRatio = request.form['trainingRatio']

    user_role = session.get('user_role', None)
    session['user_role'] = user_role

    # Construct the JSON data
    data = {
        "buildACConfig": {
            "modelType": modelType,
            "dataset": dataset.filename,
            "trainingRatio": float(trainingRatio)
        }
    }

    # Make the POST request with JSON data
    response = requests.post(ACBuild_URL, json=data)

    # Check the response status code
    if response.status_code == 200:
        response_json = response.json()
        while True:
            status_response = requests.get(ACStatus_URL)
            if status_response.status_code == 200:
                status_json = status_response.json()
                print('status_json', status_json)
                is_running = status_json.get("isRunning", True)
                if not is_running:
                    flash(
                        f'The model with id {response_json["lastBuildId"]} was built successfully!',
                        category='success'
                    )
                    break
                    # return render_template('NT/ac_build.html', user=current_user, user_role=user_role)
                  # Exit the loop once isRunning is False
                else:
                    # Wait for 5 seconds before checking again
                    time.sleep(5)
            else:
                flash('Error fetching model status from the other API.',
                      category='error')
            break

        flash(
            f'The model with id {response_json["lastBuildId"]} was built successfully!',
            category='success'
        )

    else:
        flash('The model build request failed with a status code: ' +
              str(response.status_code), category='error')

    return render_template('NT/ac_build.html', user=current_user, user_role=user_role)


ACStatus_URL = 'http://193.40.154.52:31057/api/ac/build'


@views.route('/check_model_status', methods=['GET'])
def check_model_status():
    # Replace with your actual API URL
    api_url = f"{ACStatus_URL}"
    status_response = requests.get(api_url)

    if status_response.status_code == 200:
        status_json = status_response.json()
        # is_running = status_json.get("isRunning", False)
        return jsonify({"status_json": status_json})
    else:
        return jsonify({"error": "Error fetching model status from the other API"}), 500


Delete_Models = 'http://193.40.154.52:31057/api/models/app/ac'


@views.route('/delete_models', methods=['POST'])
def delete_models():
    user_role = session.get('user_role', None)
    session['user_role'] = user_role
    print("user_role", user_role)

    try:
        response = requests.delete(Delete_Models)
        print(response)
        if response.status_code == 200:
            flash('All models have been deleted successfully.',
                  category='success')
            return redirect(url_for('views.show_all_models'))

        else:
            flash('Failed to delete models. Status Code: {response.status_code}',
                  category='error')
            return redirect(url_for('views.show_all_models'))

    except ValueError as e:
        # return f"Failed with the following error:  {e}"
        flash('Failed with the following error:  {e}',
              category='error')
        return redirect(url_for('views.show_all_models'))


ModelsDataUrl = 'http://193.40.154.52:31057'


@views.route('/model_dataset_view', methods=['GET'])
@login_required
@user_role_required('user')
def model_dataset_view():
    datasetType = 'train'
    modelId = request.args.get('modelId')
    print("modelId", modelId)
    user_role = request.args.get('user_role')
    print("model_dataset_view", user_role)
    session['user_role'] = user_role

    # Create and run a new event loop
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)

    # Run the asynchronous task and retrieve the result
    # models = loop.run_until_complete(
    #     fetch_modelsDataset(modelId, datasetType))

    api_url = f"{ModelsDataUrl}/api/models/{modelId}/datasets/{datasetType}/view"
    print(api_url)

    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            #         csv_data = response.text
            #         csv_rows = csv_data.split('\n')
            #         header = csv_rows[0].split(';')
            #         data = [row.split(';') for row in csv_rows[1:]]

            #         page = request.args.get('page', default=1, type=int)
            #         rows_per_page = 10
            #         start_index = (page - 1) * rows_per_page
            #         end_index = start_index + rows_per_page

            # # Slice the data to get the rows for the current page
            #         current_page_data = data[start_index:end_index]

            csv_data = response.text
            csv_rows = csv_data.split('\n')
            header = csv_rows[0].split(';')
            data = [row.split(';') for row in csv_rows[1:]]

            page = request.args.get('page', default=1, type=int)
            rows_per_page = 10
            total_rows = len(data)
            total_pages = int(ceil(total_rows / rows_per_page))

            start_index = (page - 1) * rows_per_page
            end_index = min(start_index + rows_per_page, total_rows)

            current_page_data = data[start_index:end_index]

            # flash('All models have been deleted successfully.',
            #       category='success')

            return render_template('NT/modelDatasetView.html', models=current_page_data, modelId=modelId, header=header, user=current_user, user_role=user_role, page=page, total_pages=total_pages)

            # return render_template('NT/modelDatasetView.html', models=csv_data, user=current_user, user_role=user_role)

        else:
            flash('Failed to delete models. Status Code: {response.status_code}',
                  category='error')
            return render_template('NT/modelDatasetView.html', models=csv_data, user=current_user, user_role=user_role)
    except ValueError as e:
        # return f"Failed with the following error:  {e}"
        flash(f'Failed with the following error: {e}', category='error')
        print(e)

        return render_template('NT/modelDatasetView.html', models=csv_data, user=current_user, user_role=user_role)


async def fetch_modelsDataset(modelId, datasetType):
    api_url = f"{ModelsDataUrl}/api/models/{modelId}/datasets/{datasetType}/view"
    async with ClientSession() as csession:
        try:
            async with csession.get(api_url) as response:
                if response.status == 200:
                    status_json = response.json()
                    print('status_json', status_json)
                    data = await response.json()
                    return data
                else:
                    return []
        except aiohttp.ClientError as e:
            return []
