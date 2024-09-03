import hashlib
import os 
import psycopg2
import re
import base64
import pandas as pd
from flask import Flask, request, render_template, redirect, session,url_for,abort

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Connection
def get_db_connection():
    return psycopg2.connect(
        database="deepika",
        user="postgres",
        password="Deepika@123sainju",
        host="127.0.0.1",
        port=5432
    )

# Regular expressions
regex_email = re.compile(r'^[a-zA-Z0-9._%+-]+@gmail\.com$')
regex_pass = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')

# Hashing of password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)

@app.route("/")
def root():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS LOGIN(
                USER_ID SERIAL PRIMARY KEY NOT NULL,
                USERNAME VARCHAR(20) NOT NULL,
                EMAIL VARCHAR(20) NOT NULL,
                PASSWORD VARCHAR(64) NOT NULL
                )
                """) 
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS birthcertificate(
                Id_no SERIAL PRIMARY KEY NOT NULL,
                Certificate_no varchar(20) not null,
                fullname VARCHAR(60) NOT NULL,
                mothername VARCHAR(60) NOT NULL,
                fathername VARCHAR(60) NOT NULL,
                grandfathername VARCHAR(60) NOT NULL,
                dob varchar(20) not null,
                gender varchar(10) not null,
                zone varchar(15) not null,
                district varchar(30) not null,
                muni_vdc varchar(30) not null,
                muni_vdc_name varchar(50) not null,
                wardno integer not null,
                marriage_certificate bytea,
                registrarname varchar(60) not null,
                issueddate varchar(20) not null
                )
                """)
            conn.commit()
    except Exception as e:
        return render_template('error.html', error=str(e))
    return render_template("signin.html")


def generate_certificate_number(prefix="BRC-"):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT MAX(Certificate_no) FROM birthcertificate")
                max_certificate_no = cursor.fetchone()[0]
                if max_certificate_no is None:
                    return prefix + "1"
                else:
                    # Extracting numeric part and incrementing
                    numeric_part = int(max_certificate_no.split("-")[-1])
                    new_certificate_no = numeric_part + 1
                    return f"{prefix}{new_certificate_no}"
    except Exception as e:
        raise e

   
  
    
    
@app.route('/signup', methods=['POST'])
def register():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confpass = request.form.get('confirm_password')

        if not (username and email and password and confpass):
            raise ValueError("All fields are required")

        if not re.match(regex_email, email):
            raise ValueError("Invalid email address")

        if not re.match(regex_pass, password):
            raise ValueError("Password must contain at least 1 uppercase, 1 lowercase, 1 digit, 1 special character, and be at least 8 characters long")

        if password != confpass:
            raise ValueError("Password and confirm password don't match")
                
        hashed_password = hash_password(password)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM LOGIN WHERE EMAIL = %s", (email,))
                if cursor.fetchone():
                    raise ValueError("Email already registered")
                cursor.execute("INSERT INTO LOGIN(USERNAME, EMAIL, PASSWORD) VALUES (%s, %s, %s)", (username, email, hashed_password))
                conn.commit()
        return render_template('signin.html')
        
    except Exception as e:
        return render_template('signin.html', info=str(e))     

@app.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    
    try:
        query = request.args.get('query')
        if query is None:
            return render_template("error.html", info="No search query provided.")

        wildcard_query = f"%{query.lower()}%"

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Corrected SQL query with matching parameter count
                cursor.execute("""
                    SELECT id_no, fullname, gender, issueddate, fathername, mothername, dob
                    FROM birthcertificate
                    WHERE lower(fullname) LIKE %s
                       OR issueddate LIKE %s
                       OR lower(fathername) LIKE %s
                       OR dob = %s
                       OR lower(gender) = %s
                """, (wildcard_query, query, wildcard_query, query, query.lower()))
                
                data = cursor.fetchall()

                # Corrected count query to match the search criteria
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM birthcertificate
                    WHERE lower(fullname) LIKE %s
                       OR issueddate LIKE %s
                       OR lower(fathername) LIKE %s
                       OR dob = %s
                       OR lower(gender) = %s
                """, (wildcard_query, query, wildcard_query, query, query.lower()))
                
                total = cursor.fetchone()[0]
                return render_template('hompage.html', items=data, total=total)

    except Exception as e:
        return render_template('error.html', info=str(e))

   
    

@app.route('/home')
def home():
    if 'user_id' in session:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id_no,fullname,gender,issueddate,fathername,mothername,dob  FROM birthcertificate order by id_no desc")
                    items=cursor.fetchall()
                    cursor.execute("SELECT COUNT(id_no) from birthcertificate")
                    total=cursor.fetchone()[0]
            return render_template('hompage.html', items=items,total=total)
        except Exception as e:
            return render_template('error.html',info= f"An error occurred: {str(e)}")
    else:
        return redirect('/')

@app.route('/signin', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM LOGIN WHERE EMAIL = %s", (email,))
                user = cursor.fetchone()

                if user and verify_password(user[3], password):
                    session['user_id'] = user[0]
                    return redirect('/home')
    except Exception as e:
        return render_template('signin.html', info="Error occurred during login process")

    return render_template('signin.html', info="Invalid email or password")

@app.route('/users')
def users():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id,username,email FROM login order by user_id desc")
                items=cursor.fetchall()
                cursor.execute("SELECT COUNT(user_id) from login")
                total=cursor.fetchone()[0]
        return render_template('Userlist.html', items=items,total=total)
    except Exception as e:
            return render_template('error.html',info= f"An error occurred: {str(e)}")

    

@app.route("/birthcertificate")
def birthcertificate():
    return render_template("birth_certificate.html")

@app.route("/registerbirthcertificate" , methods=['POST'])
def registerbirthcertificate():
    try:    
        name=request.form.get('name')
        fathername=request.form.get('fathername')
        mothername=request.form.get('mothername')
        grandfathername=request.form.get('grandfathername')
        gender=request.form.get('gender')
        dob=request.form.get('dob')
        zone=request.form.get('zone')
        district=request.form.get('district')
        muni_vdc=request.form.get('muni_vdc')
        muni_vdcn_name=request.form.get('muni_vdc_name')
        ward_no=request.form.get('ward_no')
        registrarname=request.form.get('registrarname')
        issueddate=request.form.get('issueddate')

        # Generate a unique certificate number
        certificate_no = generate_certificate_number()

        # Insert data into the birthcertificate table along with the generated certificate number
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO birthcertificate(
                            Certificate_no,
                            fullname, 
                            fathername, 
                            mothername, 
                            grandfathername, 
                            dob, 
                            gender, 
                            zone, 
                            district, 
                            muni_vdc, 
                            muni_vdc_name, 
                            wardno, 
                            registrarname,
                            issueddate
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    """, (
                        certificate_no,
                        name, fathername, mothername, grandfathername, dob, gender, zone, district,
                        muni_vdc, muni_vdcn_name, ward_no, registrarname,issueddate
                    ))
                    conn.commit()
                    return redirect('/home')
        except Exception as e:
            conn.rollback()
            return str(e)
                    
    except Exception as e:
        return str(e)
    
@app.route("/viewbirthcertificate/<int:item_id>", methods=['GET', 'POST'])
def viewbirthcertificate(item_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM birthcertificate where id_no={item_id} ORDER BY Certificate_no DESC LIMIT 1")
                certificate = cursor.fetchone()
                if certificate:
                    certificate_data = {
                        'certificate_no': certificate[1],
                        'issue_date': certificate[-1],
                        'registrar': certificate[-2],
                        'gender': certificate[7],
                        'grandfather': certificate[5],
                        'father': certificate[4],
                        'mother': certificate[3],
                        'fullname': certificate[2],
                        'district': certificate[9],
                        'muni_vdc': certificate[10],
                        'wardno': certificate[12],
                        'date': certificate[6],
                        'muni_vdc_name': certificate[11]  # Assuming this should be the same as 'muni_vdc_name'
                    }
                    return render_template("view.html", **certificate_data)
                else:
                    return render_template("hompage.html",message="Birth certificatenot found!!")
    except Exception as e:
        return str(e)
    
    
    
    
    
@app.route('/update/<int:item_id>', methods=['GET', 'POST'])
def update(item_id):
    # Ensure the user is authenticated and has a valid role in the session
    if 'user_id' not in session:
        return redirect(url_for('/'))

    if request.method == 'POST':
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    name=request.form.get('name')
                    fathername=request.form.get('fathername')
                    mothername=request.form.get('mothername')
                    grandfathername=request.form.get('grandfathername')
                    gender=request.form.get('gender')
                    dob=request.form.get('dob')
                    zone=request.form.get('zone')
                    district=request.form.get('district')
                    muni_vdc=request.form.get('muni_vdc')
                    muni_vdcn_name=request.form.get('muni_vdc_name')
                    ward_no=request.form.get('ward_no')
                    # Construct and execute the SQL update query
                    cursor.execute("""
                        UPDATE birthcertificate SET 
                            fullname=%s, 
                            fathername=%s, 
                            mothername=%s, 
                            grandfathername=%s, 
                            dob=%s, 
                            gender=%s, 
                            zone=%s, 
                            district=%s, 
                            muni_vdc=%s, 
                            muni_vdc_name=%s, 
                            wardno=%s 
                            WHERE id_no=%s""", (name,fathername,mothername,grandfathername,dob,gender,zone,district,muni_vdc,muni_vdcn_name,ward_no,item_id))
                    conn.commit()
                return redirect(url_for('home'))
        except Exception as e:
            # Render error template with relevant error message
            return render_template('error.html', info=f"Update error: {e}")
    else:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Fetch item birthcertificates from database
                    cursor.execute("SELECT * FROM birthcertificate WHERE id_no = %s", (item_id,))
                    birth_certificate = cursor.fetchone()
                    certificate_data = {
                        'certificate_no':birth_certificate[1],
                        'name': birth_certificate[2],
                        'fathername': birth_certificate[4],
                        'mothername': birth_certificate[3],
                        'grandfathername': birth_certificate[5],
                        'gender': birth_certificate[7],
                        'dob': birth_certificate[6],
                        'zone': birth_certificate[8],
                        'district': birth_certificate[9],
                        'muni_vdc_name': birth_certificate[11],
                        'ward_no': birth_certificate[12],
                        'muni_vdc':birth_certificate[10]
                            }
                    return render_template("updatebirthcertificate.html", **certificate_data)
        except Exception as e:
            # Render error template with relevant error message
            return render_template('error.html', info=f"Update page loading error: {e}")


@app.route('/delete/<int:item_id>', methods=['GET'])
def delete(item_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM birthcertificate WHERE id_no = %s', (item_id,))
            conn.commit()
            conn.close()
            return redirect(url_for('home'))
        except Exception as e:
            return render_template('error,html',info=f"An error occurred: {str(e)}")
        

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True , host='0.0.0.0')
