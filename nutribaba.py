from flask import Flask, render_template, request, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import json
import requests
from ibm_watson import VisualRecognitionV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import hashlib
import plotly
import plotly.graph_objs as go


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
            pword = hashlib.md5(pword.encode())
            pword = pword.hexdigest()
            
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM userdetails WHERE email= % s', (email,))
            mysql.connection.commit()
            userexist = cursor.fetchone()
            if userexist != None:
                msg = 'User with this Email already exist. Please Login'
                return render_template('register.html', msg=msg)

                
            else:
                cursor = mysql.connection.cursor()
                cursor.execute(
                    'INSERT INTO userdetails VALUES (% s, % s, % s)', (name, email, pword))
                mysql.connection.commit()
                msg = 'You have successfully registered !'
                return render_template('login.html', msg=msg)


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/authenticate', methods=['GET', 'POST'])
def authenticate():
    if request.method == 'POST':
        email = request.form['emailaddress']
        pword = request.form['pword']
        pword = hashlib.md5(pword.encode())
        pword = pword.hexdigest()

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM userdetails WHERE email= % s', (email,))
        mysql.connection.commit()
        userexist = cursor.fetchone()
        if userexist == None:
            msg = 'User with this Email doesn\'t exist. Please Sign-up before Login'
            return render_template('login.html', msg=msg)
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


@app.route('/termsconditions')
def termsconditions():
    return render_template('TermsConditions.html')


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
        if fooditem.lower() == 'non-food':
            allnutrients = {'meta': {}, 'Essentials': {}, 'Minerals': {
            }, 'Vitamins': {}, 'Fattyacids': {}, 'Carotenoids': {}}
            allnutrients['meta']['fooditem'] = fooditem.upper()
            allnutrients['meta']['nutrients'] = 0
            return render_template('trackfood.html', msg=allnutrients)
        else:
            # using usda api to get the nutrients of the food item
            nutrients = requests.get('https://api.nal.usda.gov/fdc/v1/foods/search?query={}&pageSize={}&api_key={}'.format(
                fooditem, '1', 'wNxP2RfBXrx3amU5HypuuEWUtSSgeRErZMcU5LFA'))
            data = json.loads(nutrients.text)
            allnutrients = {'meta': {}, 'Essentials': {}, 'Minerals': {
            }, 'Vitamins': {}, 'Fattyacids': {}, 'Carotenoids': {}}
            label = []
            value = []
            # print(json.dumps(data, indent=2))
            n = len(data['foods'][0]['foodNutrients'])
            allnutrients['meta']['fooditem'] = fooditem.upper()
            allnutrients['meta']['nutrients'] = n
            fattyacids = ['SFA', 'MUFA', 'PUFA']
            allnutrients['Minerals']['total'] = 0
            allnutrients['Vitamins']['total'] = 0
            allnutrients['Fattyacids']['total'] = 0
            allnutrients['Carotenoids']['total'] = 0
            for i in range(0, n):
                if(any([substring in (data['foods'][0]['foodNutrients'][i]['nutrientName']) for substring in fattyacids])):
                    allnutrients['meta']['nutrients'] -= 1
                    continue
                no=int(data['foods'][0]['foodNutrients'][i]['nutrientNumber'])
                if(no < 292 or no == 421 or no == 601):
                    allnutrients['Essentials'][(data['foods'][0]['foodNutrients'][i]['nutrientName'])] = str(
                        (data['foods'][0]['foodNutrients'][i]['value']))+" "+(data['foods'][0]['foodNutrients'][i]['unitName'])
                    if (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'g':
                        label.append(data['foods'][0]
                                 ['foodNutrients'][i]['nutrientName'])
                        value.append(data['foods'][0]['foodNutrients'][i]['value'])
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'mg':
                        label.append(data['foods'][0]
                                 ['foodNutrients'][i]['nutrientName'])
                        value.append(
                        (data['foods'][0]['foodNutrients'][i]['value'])*0.001)
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'ug':
                        label.append(data['foods'][0]
                                 ['foodNutrients'][i]['nutrientName'])
                        value.append(
                        (data['foods'][0]['foodNutrients'][i]['value'])*0.000001)
                elif(no > 300 and no < 317):
                    allnutrients['Minerals'][(data['foods'][0]['foodNutrients'][i]['nutrientName'])] = str(
                        (data['foods'][0]['foodNutrients'][i]['value']))+" "+(data['foods'][0]['foodNutrients'][i]['unitName'])

                    if (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'g':
                        allnutrients['Minerals']['total'] = (allnutrients['Minerals']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'mg':
                        allnutrients['Minerals']['total'] = (allnutrients['Minerals']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])*0.001
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'ug':
                        allnutrients['Minerals']['total'] = (allnutrients['Minerals']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])*0.000001

                elif(no >= 318 and no < 578 and no not in [321,322,334,337,338]):
                    allnutrients['Vitamins'][(data['foods'][0]['foodNutrients'][i]['nutrientName'])] = str(
                        (data['foods'][0]['foodNutrients'][i]['value']))+" "+(data['foods'][0]['foodNutrients'][i]['unitName'])

                    if (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'g':
                        allnutrients['Vitamins']['total'] = (allnutrients['Vitamins']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'mg':
                        allnutrients['Vitamins']['total'] = (allnutrients['Vitamins']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])*0.001
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'ug':
                        allnutrients['Vitamins']['total'] = (allnutrients['Vitamins']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])*0.000001

                elif(no in [321,322,334,337,338]):
                    allnutrients['Carotenoids'][(data['foods'][0]['foodNutrients'][i]['nutrientName'])] = str(
                        (data['foods'][0]['foodNutrients'][i]['value']))+" "+(data['foods'][0]['foodNutrients'][i]['unitName'])
                    
                    if (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'g':
                        allnutrients['Carotenoids']['total'] = (allnutrients['Carotenoids']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'mg':
                        allnutrients['Carotenoids']['total'] = (allnutrients['Carotenoids']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])*0.001
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'ug':
                        allnutrients['Carotenoids']['total'] = (allnutrients['Carotenoids']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])*0.000001

                elif(no >= 602):
                    allnutrients['Fattyacids'][(data['foods'][0]['foodNutrients'][i]['nutrientName'])] = str(
                        (data['foods'][0]['foodNutrients'][i]['value']))+" "+(data['foods'][0]['foodNutrients'][i]['unitName'])
                    if (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'g':
                        allnutrients['Fattyacids']['total'] = (allnutrients['Fattyacids']['total'])+(data['foods'][0]['foodNutrients'][i]['value'])
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'mg':
                        allnutrients['Fattyacids']['total'] = (allnutrients['Fattyacids']['total'])+((data['foods'][0]['foodNutrients'][i]['value'])*0.001)
                    elif (data['foods'][0]['foodNutrients'][i]['unitName']).lower() == 'ug':
                        allnutrients['Fattyacids']['total'] = (allnutrients['Fattyacids']['total'])+((data['foods'][0]['foodNutrients'][i]['value'])*0.000001)
                    
# the below code is to enter the sub groups of nutrients created above, into the pie chart label and values and also into the allnutrients dictionary 

            label.append('Minerals')
            label.append('Vitamins')
            label.append('Carotenoids')
            label.append('Fattyacids')
            value.append(allnutrients['Minerals']['total'])
            value.append(allnutrients['Vitamins']['total'])
            value.append(allnutrients['Carotenoids']['total'])
            value.append(allnutrients['Fattyacids']['total'])
            allnutrients['Minerals']['total'] = str(round(((allnutrients['Minerals']['total'])*1000),1))+" "+"MG"
            allnutrients['Vitamins']['total'] = str(round(((allnutrients['Vitamins']['total'])*1000),1))+" "+"MG"
            allnutrients['Carotenoids']['total'] = str(round(((allnutrients['Carotenoids']['total'])*1000),1))+" "+"MG"
            allnutrients['Fattyacids']['total'] = str(round(((allnutrients['Fattyacids']['total'])*1000),1))+" "+"MG"

# cretion of the piechart using plotly go
            data = [
                go.Pie(
                    labels=label,
                    values=value
                )
            ]
            graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
            return render_template('trackfood.html', msg=allnutrients, plot=graphJSON)


@app.route('/mybmi')
def mybmi():
    return render_template('mybmi.html')


@app.route('/nutrition')
def nutrition():
    return render_template('nutrition.html')


@app.route('/getchart')
def getchart():
    pie = create_plot()
    return render_template('demo.html', plot=pie)





if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)
