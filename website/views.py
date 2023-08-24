from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_login import login_required, current_user
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

views = Blueprint('views', __name__)

@views.route('/')
def home():
    return render_template("home.html",user=current_user)


@views.route('/userRole', methods=['GET', 'POST'])
@login_required
def select_role():
    if request.method == 'POST':
        user_role = request.form.get('user_role')
        print("Selected role:", user_role)  
        session['user_role'] = user_role # Store the selected role in a session variable
        return redirect(url_for('views.mainPage',user_role=user_role))   # Redirect to the main page with the selected role as a query parameter
        
    return render_template('userRole.html',user=current_user)

    
@views.route('/MainPage',methods=['GET', 'POST'])
@login_required
def mainPage():
    user_role = request.args.get('user_role')
    print("mainPage",  user_role)
    session['user_role'] = user_role

    return render_template("mainPage.html",user=current_user,user_role=user_role)


# Simulated data for the APIs based on user roles  , 'http://172.17.88.154:8080/explain_occlusion/image'
API_URLS = {
    'User': ['http://172.17.91.246:8050/explain_lime/image'],
    'Developer':  ['http://172.17.91.246:8050/explain_lime/image','http://172.17.91.246:8050/explain_occlusion/image','http://172.17.91.246:8050/explain_shap/image'],
    'Auditor': ['http://172.17.88.154:8080/explain_lime/image', 'http://172.17.88.154:8080/explain_shap/image', 'http://172.17.88.154:8080/explain_occlusion/image'],
    'Business': ['http://172.17.88.154:8080/explain_lime/image']
}


@views.route('/explain', methods=['GET', 'POST'])
@login_required
async def explain():
    user_role = session.get('user_role', None)
    print("explain",  user_role)
    if not user_role:
        return "User role not found in the session. Please select a role first."

    # Get class label and image from the form
    ClassLabel = request.form['ClassLabel']
    ImageFile = request.files['ImageFile']
    mlModel = request.files['mlModel']
    ImageFileBytes =   request.files['ImageFile'].read()

    api_urls = API_URLS.get(user_role, None)

    if not api_urls:
        return "Invalid user role."


    results = []

    with ThreadPoolExecutor(10) as executor:
        futures = []
        for api_url in api_urls:
            try:

                api_url = f"{api_url}?imagetype={ClassLabel}"
                files = {'file': (ImageFile.filename, ImageFile.stream, ImageFile.content_type), 'mlModel': (mlModel.filename, mlModel.stream, mlModel.content_type)
                  ,'ImageFileBytes': ImageFileBytes
                 }
                future = executor.submit(requests.post, api_url, files=files)
                futures.append(future)
            except Exception as e:
                print(f"API call to {api_url} failed with exception: {e}")

        for future in as_completed(futures):
    
            try:
                response = future.result()
                if response.status_code == 200:
                    results.append(response.json())
                else:
                    print(f"API call returned status code: {response.status_code}")
            except Exception as e:
                print(f"API call failed with exception: {e}")

    user_role = session.get('user_role', None)


    merged_dict = {}

# Iterate through the JSON objects and merge their contents into the merged_dict
    for json_obj in results:
        merged_dict.update(json_obj)

# Convert the merged dictionary back to JSON format
    merged_json = json.dumps(merged_dict, indent=4)
    data_dict = json.loads(merged_json)

    # Redirect to the results page
    return render_template('results.html', results=data_dict, user=current_user, user_role=user_role)






