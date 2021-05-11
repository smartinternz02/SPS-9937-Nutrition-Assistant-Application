from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import json
import requests
from ibm_watson import VisualRecognitionV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'remotemysql.com'
app.config['MYSQL_USER'] = 'kFODHuq1oX'
app.config['MYSQL_PASSWORD'] = 'dsc8nkk0S8'
app.config['MYSQL_DB'] = 'kFODHuq1oX'
mysql = MySQL(app)
app.secret_key = 'a'


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/uploaddata', methods=['GET', 'POST'])
def uploaddata():
    msg = ''
    if request.method == 'POST':
        name = request.form['username']
        email = request.form['emailaddress']
        pword = request.form['pword']
        cpword = request.form['confirmPassword']
        if pword == cpword:
            session["username"] = name
            cursor = mysql.connection.cursor()
            cursor.execute(
                'INSERT INTO userdetails VALUES (% s, % s, % s)', (name, email, pword))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
    return render_template('register.html', msg=msg)


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/authenticate', methods=['GET', 'POST'])
def authenticate():
    if request.method == 'POST':
        email = request.form['emailaddress']
        pword = request.form['pword']

        cursor = mysql.connection.cursor()
        cursor.execute(
            'SELECT * FROM userdetails WHERE email= % s and pword = % s', (email, pword))
        mysql.connection.commit()
        data = cursor.fetchone()
        if data == None:
            data = 'INCORRECT DETAILS'
            return render_template('login.html', msg=data)
        else:
            session["email"] = email
        print("data", data)
    return render_template('index.html')


@app.route('/trackfood')
def trackfood():
    return render_template('trackfood.html')


@app.route('/logout')
def logout():
    session.clear()
    return render_template('index.html')


@app.route('/upload_img', methods=['GET', 'POST'])
def upload_img():
    if request.method == 'POST':
        img = request.files['foodimg']
        pathname = './static/'+session['email']+'.jpg'
        img.save(pathname)
        # using ibm watson visualrecognition api to identify the fooditem
        authenticator = IAMAuthenticator(
            'P4KdTbcPJhm8pxf2_JQHclANOs-7Inhu8hMenVX88t_M')
        visual_recognition = VisualRecognitionV3(
            version='2018-03-19',
            authenticator=authenticator
        )
        try:
            visual_recognition.set_service_url(
                'https://api.us-south.visual-recognition.watson.cloud.ibm.com/instances/341d2fd2-3d4b-4a9f-a216-f413be52fc73')
            with open(pathname, 'rb') as images_file:
                classes = visual_recognition.classify(
                    images_file=images_file,
                    classifier_ids=["food"]).get_result()
            fooditem = classes['images'][0]['classifiers'][0]['classes'][0]['class']
        except:
            return render_template('trackfood.html', msg=0)

        # using usda api to get the nutrients of the food item

        nutrients = requests.get('https://api.nal.usda.gov/fdc/v1/foods/search?query={}&pageSize={}&api_key={}'.format(
            fooditem, '2', 'wNxP2RfBXrx3amU5HypuuEWUtSSgeRErZMcU5LFA'))
        data = json.loads(nutrients.text)
        print(json.dumps(data, indent=2))
        allnutrients = []
        n = len(data['foods'][0]['foodNutrients'])
        allnutrients.append(fooditem.upper())
        allnutrients.append(n*2)
        for i in range(0, n):
            allnutrients.append(
                data['foods'][0]['foodNutrients'][i]['nutrientName'])
            allnutrients.append(data['foods'][0]['foodNutrients'][i]['nutrientNumber'] +
                                " "+data['foods'][0]['foodNutrients'][i]['unitName'])
        return render_template('trackfood.html', msg=allnutrients)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)
