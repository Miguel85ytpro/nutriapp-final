from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests

db_usuarios = [] 

app = Flask(__name__, template_folder='templates')
app.secret_key = 'vladimirxd' 

USDA_API_KEY = "5dY0aFv08WlWgdaACefuNRvJdeADZdCqNcmXQ45P"
USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

def calcular_imc(peso, altura_cm):
    altura_m = altura_cm / 100
    imc = peso / (altura_m ** 2)
    if imc < 18.5:
        interpretacion = "Bajo peso"
    elif 18.5 <= imc < 24.9:
        interpretacion = "Peso normal"
    elif 25 <= imc < 29.9:
        interpretacion = "Sobrepeso"
    else:
        interpretacion = "Obesidad"
    return round(imc, 2), interpretacion

def calcular_tmb(peso, altura_cm, edad, sexo):
    if sexo == "male":
        tmb = (10 * peso) + (6.25 * altura_cm) - (5 * edad) + 5
    else:
        tmb = (10 * peso) + (6.25 * altura_cm) - (5 * edad) - 161
    return round(tmb, 2)

def calcular_gct(tmb, nivel_actividad):
    factores = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "activo": 1.725,
        "muy_activo": 1.9
    }
    factor = factores.get(nivel_actividad, 1.2)
    gct = tmb * factor
    return round(gct, 2)

def calcular_peso_ideal(altura_cm, sexo):
    altura_m = altura_cm / 100
    if sexo == "male":
        peso_ideal = 22 * (altura_m ** 2)
    else:
        peso_ideal = 21 * (altura_m ** 2)
    return round(peso_ideal, 2)

def calcular_macros(tdee, carb_perc, prot_perc, fat_perc):
    if abs((carb_perc + prot_perc + fat_perc) - 100) > 0.01:
        return None
    kcal_carb_g = 4
    kcal_prot_g = 4
    kcal_fat_g = 9
    carb_kcal = tdee * (carb_perc / 100)
    prot_kcal = tdee * (prot_perc / 100)
    fat_kcal = tdee * (fat_perc / 100)
    carbohidratos_g = round(carb_kcal / kcal_carb_g, 2)
    proteinas_g = round(prot_kcal / kcal_prot_g, 2)
    grasas_g = round(fat_kcal / kcal_fat_g, 2)
    return {
        "carbohidratos_g": carbohidratos_g,
        "proteinas_g": proteinas_g,
        "grasas_g": grasas_g
    }

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        for u in db_usuarios:
            if u['email'] == email:
                flash("El correo ya está registrado.", 'danger')
                return redirect(url_for('register'))

        nuevo_usuario = {
            "nombre": request.form.get('nombre'),
            "apellidos": request.form.get('apellidos'),
            "email": email,
            "password": password, 
            "edad": request.form.get('edad', type=int),
            "sexo": request.form.get('sexo'),
            "peso": request.form.get('peso', type=float),
            "altura": request.form.get('altura', type=float),
            "nivel_actividad": request.form.get('nivel_actividad'),
            "objetivo": request.form.get('objetivo'),
            "alergias": request.form.get('alergias'),
            "dieta_especifica": request.form.get('dieta_especifica'),
            "nivel_experiencia": request.form.get('nivel_experiencia')
        }
        
        db_usuarios.append(nuevo_usuario)
        
        flash("Registro exitoso. Ahora puedes iniciar sesión.", 'success')
        return redirect(url_for('login'))
        
    usuario = session.get('usuario')
    return render_template('register.html', usuario=usuario)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        for u in db_usuarios:
            if u['email'] == email and u['password'] == password:
                session['usuario'] = u['nombre'] 
                flash(f"¡Bienvenido de nuevo, {u['nombre']}!", 'success')
                return redirect(url_for('home'))

        flash("Correo o contraseña incorrectos.", 'danger')
        return render_template('login.html')

    usuario = session.get('usuario')
    return render_template('login.html', usuario=usuario)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash("Has cerrado sesión correctamente.", 'info')
    return redirect(url_for('home'))

@app.route('/')
def home():
    usuario = session.get('usuario')
    return render_template('home.html', usuario=usuario)

@app.route('/calculadoras')
def calculadoras():
    usuario = session.get('usuario')
    return render_template('calculadoras_dashboard.html', usuario=usuario)

@app.route('/recetas', methods=['GET', 'POST'])
def formulario():
    usuario = session.get('usuario')
    return render_template('recetas.html', usuario=usuario)

@app.route('/resultado', methods=['POST'])
def resultado():
    usuario = session.get('usuario')
    ingrediente = request.form.get('ingrediente')
    
    if not ingrediente:
        flash("Por favor, introduce un ingrediente para buscar.", 'warning')
        return redirect(url_for('formulario'))

    params = {
        "api_key": USDA_API_KEY,
        "query": ingrediente,
        "pageSize": 20
    }

    resultados = [] 

    try:
        response = requests.get(USDA_URL, params=params)
        response.raise_for_status()
        data = response.json()
        alimentos = data.get("foods", [])

        for item in alimentos:
            nombre = item.get("description", "Sin nombre")
            nutrientes = item.get("foodNutrients", [])
            kcal = next(
                (n["value"] for n in nutrientes if n.get("nutrientName") == "Energy" and n.get("unitName") == "KCAL"),
                "No disponible"
            )
            resultados.append({
                "label": nombre,
                "calories": kcal,
                "image": "https://via.placeholder.com/150?text=Food",
                "url": f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{item.get('fdcId')}/nutrients"
            })
            
        return render_template("resultado.html", recetas=resultados, ingrediente=ingrediente, usuario=usuario)

    except requests.exceptions.HTTPError as e:
        flash(f"Error HTTP al buscar alimentos en USDA: {e}", 'danger')
    except requests.exceptions.RequestException as e:
        flash(f"Error de conexión al API de USDA: {e}", 'danger')
    except Exception as e:
        flash(f"Ocurrió un error inesperado: {e}", 'danger')
    
    # Renderiza la plantilla con resultados vacíos en caso de error para evitar un error 500
    return render_template("resultado.html", recetas=resultados, ingrediente=ingrediente, usuario=usuario)

@app.route('/imc', methods=['GET', 'POST'])
def imc():
    results = None
    usuario = session.get('usuario')
    if request.method == 'POST':
        try:
            peso = float(request.form.get('weight_imc'))
            altura_cm = float(request.form.get('height_imc'))
            imc_valor, interpretacion = calcular_imc(peso, altura_cm)
            results = {
                "titulo": "Resultado IMC",
                "tipo": "imc",
                "imc": imc_valor,
                "interpretacion": interpretacion
            }
        except ValueError:
            flash("Asegúrate de introducir números válidos para peso y estatura.", 'danger')
    return render_template('imc_calculator.html', results=results, usuario=usuario)

@app.route('/tmb', methods=['GET', 'POST'])
def tmb():
    results = None
    usuario = session.get('usuario')
    if request.method == 'POST':
        try:
            peso = float(request.form.get('weight_tmb'))
            altura_cm = float(request.form.get('height_tmb'))
            edad = int(request.form.get('age_tmb'))
            sexo = request.form.get('gender_tmb')
            tmb_valor = calcular_tmb(peso, altura_cm, edad, sexo)
            results = {
                "titulo": "Resultado TMB",
                "tipo": "tmb",
                "tmb": tmb_valor
            }
        except ValueError:
            flash("Asegúrate de introducir números válidos.", 'danger')
    return render_template('tmb_calculator.html', results=results, usuario=usuario)

@app.route('/gct', methods=['GET', 'POST'])
def gct():
    results = None
    usuario = session.get('usuario')
    if request.method == 'POST':
        try:
            tmb_valor = float(request.form.get('tmb_gct'))
            nivel_actividad = request.form.get('activity_level_gct')
            gct_valor = calcular_gct(tmb_valor, nivel_actividad)
            results = {
                "titulo": "Resultado Gasto Calórico Total",
                "tipo": "gct",
                "gct": gct_valor
            }
        except ValueError:
            flash("Asegúrate de introducir un valor numérico para la TMB.", 'danger')
    return render_template('gct_calculator.html', results=results, usuario=usuario)

@app.route('/peso_ideal', methods=['GET', 'POST'])
def peso_ideal():
    results = None
    usuario = session.get('usuario')
    if request.method == 'POST':
        try:
            altura_cm = float(request.form.get('height_pi'))
            sexo = request.form.get('gender_pi')
            peso_ideal_valor = calcular_peso_ideal(altura_cm, sexo)
            results = {
                "titulo": "Resultado Peso Ideal",
                "tipo": "peso_ideal",
                "peso_ideal": peso_ideal_valor
            }
        except ValueError:
            flash("Asegúrate de introducir números válidos para la estatura.", 'danger')
    return render_template('peso_ideal_calculator.html', results=results, usuario=usuario)

@app.route('/macros', methods=['GET', 'POST'])
def macros():
    results = None
    usuario = session.get('usuario')
    if request.method == 'POST':
        try:
            tdee = float(request.form.get('tdee_macros'))
            carb_perc = float(request.form.get('carb_perc'))
            prot_perc = float(request.form.get('prot_perc'))
            fat_perc = float(request.form.get('fat_perc'))
            macros_g = calcular_macros(tdee, carb_perc, prot_perc, fat_perc)
            if macros_g:
                results = {
                    "titulo": "Resultado de Distribución de Macronutrientes",
                    "tipo": "macros",
                    "macros": macros_g
                }
            else:
                flash("La suma de los porcentajes debe ser igual a 100.", 'danger')
        except ValueError:
            flash("Asegúrate de introducir números válidos.", 'danger')
    return render_template('macros_calculator.html', results=results, usuario=usuario)

if __name__ == '__main__':
    app.run(debug=True)