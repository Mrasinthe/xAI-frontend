import aiohttp
import asyncio
from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_login import login_required, current_user
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from aiohttp import FormData
from aiohttp import ClientSession


views = Blueprint('views', __name__)


@views.route('/')
def home():
    if current_user.is_authenticated:
        # If user is already logged in, redirect to a different page
        return redirect(url_for('views.select_role'))

    return render_template("home.html", user=current_user)


@views.route('/userRole', methods=['GET', 'POST'])
@login_required
def select_role():
    if request.method == 'POST':
        user_role = request.form.get('user_role')
        print("Selected role:", user_role)
        # Store the selected role in a session variable
        session['user_role'] = user_role
        # Redirect to the main page with the selected role as a query parameter
        return redirect(url_for('views.mainPage', user_role=user_role))

    return render_template('userRole.html', user=current_user)


@views.route('/about', methods=['GET', 'POST'])
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


@views.route('/XAI', methods=['GET', 'POST'])
@login_required
def mainPage():
    user_role = request.args.get('user_role')
    print("mainPage",  user_role)
    session['user_role'] = user_role

    return render_template("mainPage.html", user=current_user, user_role=user_role)


# Simulated data for the APIs based on user roles

# 193.40.154.160:8090 - LIME
# 193.40.154.87:8090 - SHAP
# 193.40.155.96:8090 - Occlusion ['http://193.40.154.160:8090/explain_lime/image','http://193.40.154.87:8090/explain_shap/image','http://193.40.155.96:8090/explain_occlusion/image'],   


API_URLS = {
    'User': ['http://193.40.154.143:8000/explain_lime/image'],
    'Developer': ['http://193.40.154.143:8000/explain_lime/image', 'http://193.40.154.143:8000/explain_shap/image','http://193.40.154.143:8000/explain_occlusion/image'],
    'Auditor': ['http://193.40.154.143:8000/explain_lime/image', 'http://193.40.154.143:8000/explain_shap/image', 'http://193.40.154.143:8000/explain_occlusion/image'],
    'Business': ['http://193.40.154.143:8000/explain_lime/image']
}




@views.route('/explain', methods=['GET', 'POST'])
@login_required
async def explain():
    user_role = session.get('user_role', None)
    print("explain",  user_role)
    if not user_role:
        return "User role not found in the session. Please select a role first."

    ClassLabel = request.form['ClassLabel']
    ImageFile = request.files['ImageFile']
    mlModel = request.files['mlModel']
    ImageFileBytes = request.files['ImageFile'].read()

    api_urls = API_URLS.get(user_role, None)

    if not api_urls:
        return "Invalid user role."

    results = []

    async with ClientSession() as csession:
        async def fetch_data(api_url):
            try:
                api_url = f"{api_url}?imagetype={ClassLabel}"
                form_data = FormData()
                form_data.add_field('file', ImageFile.stream.read(), filename=ImageFile.filename, content_type=ImageFile.content_type)
                form_data.add_field('mlModel', mlModel.stream.read(), filename=mlModel.filename, content_type=mlModel.content_type)
                form_data.add_field('ImageFileBytes', ImageFileBytes, content_type='application/octet-stream')
                
                async with csession.post(api_url, data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        print(f"API call to {api_url} failed with status {response.status}.")
                        return None
            except Exception as e:
                print(f"API call to {api_url} failed with exception: {e}")
                return None

        tasks = [fetch_data(api_url) for api_url in api_urls]
        results = await asyncio.gather(*tasks)

    merged_dict = {}

    for json_obj in results:
        if isinstance(json_obj, dict):
            merged_dict.update(json_obj)

    merged_json = json.dumps(merged_dict, indent=4)
    data_dict = json.loads(merged_json)

    user_role = session.get('user_role', None)

    return render_template('results.html', results=data_dict, user=current_user, user_role=user_role)