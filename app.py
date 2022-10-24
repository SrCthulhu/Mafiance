from email import message
from types import NoneType
from flask import Flask, render_template, redirect, session, request, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import random

app = Flask(__name__)
app.secret_key = ".."
uri = os.environ.get('MONGO_DB_URI', "mongodb://127.0.0.1")
print(uri)
client = MongoClient(uri)
db = client.mafiance


@app.route("/")
def home_view():
    return render_template("home.html")


@app.route("/login")
def login_view():
    mensaje = request.args.get('mensaje')
    return render_template("login.html", mensaje=mensaje)


@app.route("/login/users")
def login_users():
    userEmail = request.args.get('email')
    userPassword = request.args.get('password')

    if userEmail == "":
        return redirect('/login?mensaje=Ingresa el Email o Nombre de usuario')
    if userPassword == "":
        return redirect('/login?mensaje=Ingresa la contraseña')

    # Forma fácil para buscar por email y tambien por el user registrado:
    userDocument = db.users.find_one({'email': userEmail})

    if not userDocument:
        userDocument = db.users.find_one({'user': userEmail})

    # userDocument = db.users.find_one({ '$or': [{'email': userEmail}, {'user': userEmail}]})

    if not userDocument:
        return redirect('/login?mensaje=El usuario no existe')
    # ----------------------------------
    if userDocument['password'] != userPassword:
        return redirect('/login?mensaje=La contraseña inválida')

    session['user_id'] = str(userDocument['_id'])

    return redirect('/index')


@app.route("/signin")
def signin_view():
    mensaje3 = request.args.get('mensaje3')
    return render_template("signin.html", mensaje3=mensaje3)


@app.route("/signin/new_user")
def signin_user():
    newEmail = request.args.get('email')
    newPassword = request.args.get('password')
    new_user_name = request.args.get('user')

    if newEmail == "":
        return redirect('/signin?mensaje3=Ingresa el Email')

    if newPassword == "":
        return redirect('/signin?mensaje3=Ingresa una Contraseña')

    if len(newPassword) < 8:
        return redirect('/signin?mensaje3=La contraseña debe contener 8 o más carácteres')

    if new_user_name == "":
        return redirect('/signin?mensaje3=Ingresa un nombre de Usuario')

    emailSplitted = newEmail.split('@')

    if len(emailSplitted) != 2 or emailSplitted[1] != 'gmail.com' != 'hotmail.com':

        return redirect('/signin?mensaje3=la dirección de correo no es válida, debe contener @gmail.com ó @hotmail.com')

    newUser = {
        'email': newEmail,
        'password': newPassword,
        'user': new_user_name
    }
    # Creamos documentos en la base de datos.
    newUserId = str(db.users.insert_one(newUser).inserted_id)
    # inserta el documento y devuelve el id del documento insertado con .inserted_id por eso se escribe abajo newUserId
    newWallet = {
        'name': "Mafiance Coin",
        'currency': "MFC",
        'balance': 0.0,
        'user_id': newUserId,
    }
    db.wallets.insert_one(newWallet)

    session.pop('user_id', None)
    return redirect('/finished')

    # Tarea! Hacer que al iniciar sesión identifique al nuevo usuario.


@app.route("/finished")
def registration_view():
    return render_template("finished.html")


@app.route("/index")
def index_view():

    if not session.get('user_id'):
        return redirect('/')

    userId = session.get('user_id')

    actualBalance = db.wallets.find_one({'user_id': userId})
    criptoactives = list(db.wallets.find({'user_id': userId}))
    return render_template("index.html", actualBalance=actualBalance, criptoactives=criptoactives)


@app.route("/profile")
def profile_view():

    if not session.get('user_id'):
        return redirect('/')

    userId = session.get('user_id')

    user = db.users.find_one({'_id': ObjectId(userId)})
    if not user:
        return abort(404)
    return render_template("profile.html", user=user)


@app.route("/p2pBuyer")
def p2pBuyer_view():

    if not session.get('user_id'):
        return redirect('/')

    ads = list(db.advertisements.find({'type': 'Compra'}))
    banks = list(db.banks.find({}))
####### Forma de agregar un dato nuevo a la lista de la coleccion ads. para type error de listas por indices etc. #######
# Vease la vista P2PBuyer.html donde ajustamos el dato de nombre. Acá buscamos con el id en otra colección
    for ad in ads:
        user = db.users.find_one({'_id': ObjectId(ad['user_id'])})
        method = db.banks.find_one({'_id': ObjectId(ad['payment_method'])})
        ad['user'] = user
        ad['method'] = method

    return render_template("p2pBuyer.html", ads=ads, banks=banks)


@ app.route("/p2pSeller")
def p2pSeller_view():

    if not session.get('user_id'):
        return redirect('/')

    ads = list(db.advertisements.find({'type': 'Venta'}))
    banks = list(db.banks.find({}))

    for ad in ads:
        user = db.users.find_one({'_id': ObjectId(ad['user_id'])})
        method = db.banks.find_one({'_id': ObjectId(ad['payment_method'])})
        ad['user'] = user
        ad['method'] = method

    return render_template("p2pSeller.html", ads=ads, banks=banks)


@app.route("/buy_selected_ad/<id>")
def buy_selected(id):
    if not session.get('user_id'):
        return redirect('/')

    ad = db.advertisements.find_one({'_id': ObjectId(id)})
    user = db.users.find_one({'_id': ObjectId(ad['user_id'])})
    method = db.banks.find_one({'_id': ObjectId(ad['payment_method'])})
    banks = list(db.banks.find({}))
    mensaje = request.args.get('mensaje')

    return render_template("buy_selected_ad.html", ad=ad, user=user, method=method, mensaje=mensaje, banks=banks)


@app.route("/create/order/<id>")
def orders_creation(id):

    if not session.get('user_id'):
        return redirect('/')

    ad = db.advertisements.find_one({'_id': ObjectId(id)})
    user = db.users.find_one({'_id': ObjectId(ad['user_id'])})

    if not ad:
        return abort(404)

    quantity = request.args.get('client_quantity')
    client_selected_method = request.args.get('method')

    if not quantity:
        return redirect('/buy_selected_ad/?mensaje=Ingresa una cantidad')

    if client_selected_method == "":
        return redirect('/buy_selected_ad/<id>?mensaje=Selecciona un método de pago')

    order_type = ad['type']
    order_currency = ad['currency']
    order_fiat = ad['fiat']
    advertiser_amount = ad['amount']
    user_name = user['user']
    order_exchange_type = ad['exchange_type']
    order_fixed_price = ad['fixed_price']
    order_float_price = ad['float_price']
    color = ad['color']
    userId = session.get('user_id')

    user_order = db.orders.find_one(
        {'user_id': userId, 'currency': order_currency, 'client_quantity': quantity})  # Acá verficamos si la orden ya existe redirecciona. ########

    # Si no tiene order, se crea. y si tiene order, va a ir a index y no creara otra.
    if not user_order:
        new_order = {
            'status': "Pendiente",
            'type': order_type,
            'client_quantity': float(quantity),
            'currency': order_currency,
            'fiat': order_fiat,
            'advertiser_amount': advertiser_amount,
            'exchange_type': order_exchange_type,
            'fixed_price': order_fixed_price,
            'float_price': order_float_price,
            'valor_al_cambio': "por definir",
            'client_payment_method': client_selected_method,
            'advertiser_name': user_name,
            'created_at': datetime.now(),
            'color': color,
            'user_id': userId,
        }
    last_order_id = db.orders.insert_one(new_order).inserted_id

    return redirect('/chat/' + str(last_order_id))


@app.route("/sell_selected_ad/<id>")
def sell_selected(id):
    if not session.get('user_id'):
        return redirect('/')

    ad = db.advertisements.find_one({'_id': ObjectId(id)})
    user = db.users.find_one({'_id': ObjectId(ad['user_id'])})
    method = db.banks.find_one({'_id': ObjectId(ad['payment_method'])})
    banks = list(db.banks.find({}))
    mensaje = request.args.get('mensaje')
    return render_template("sell_selected_ad.html", ad=ad, user=user, method=method, banks=banks, mensaje=mensaje)


@app.route("/chat/<id>")
def chat_view(id):
    if not session.get('user_id'):
        return redirect('/')

    order = db.orders.find_one({'_id': ObjectId(id)})
    message = list(db.messages.find({}))
    userId = session.get('user_id')
    return render_template("client_chat.html", order=order, message=message, userId=userId)


@app.route("/message/create")
def comment_create():
    if not session.get('user_id'):
        return redirect('/')

    messageText = request.args.get('message')
    orderId = request.args.get('order_id')
    userId = session.get('user_id')
    user_name = db.users.find_one({'_id': ObjectId(userId)})

    message = {}
    message['message'] = messageText
    message['order_id'] = orderId
    message['user_id'] = userId
    message['user'] = user_name

    db.messages.insert_one(message)

    return redirect('/chat/' + str(orderId))


@ app.route("/orders")
def orders_view():
    if not session.get('user_id'):
        return redirect('/')

    userId = session.get('user_id')
    orders = list(db.orders.find({'user_id': userId}))
    if not orders:
        return abort(404)
    return render_template("orders.html", orders=orders)


@ app.route("/divisa")
def divisa_view():

    if not session.get('user_id'):
        return redirect('/')
    return render_template("divisa.html")


@ app.route("/comercio/<id>")
def trade_view(id):
    if not session.get('user_id'):
        return redirect('/')

    coin = db.coins.find_one({'_id': ObjectId(id)})
    if not coin:
        return abort(404)

    return render_template("comercio_cripto.html", coin=coin)

# flask necesita a la ruta (/add/MFC/<id>) para despues def add(id):


@ app.route("/add/<acronym>")
def add(acronym):
    if not session.get('user_id'):
        return redirect('/')
    # Cuando traemos un numero del formulario debemos convertirlo a numero porque viene como un string y no se
    # puede sumar con int() o float().
    amount = float(request.args.get('quantity'))
    userId = session.get('user_id')

    wallet = db.wallets.find_one({'user_id': userId, 'currency': acronym})
    if not wallet:
        return abort(404)

    newTransaction = {
        'wallet_sender_id': 0,
        'wallet_receiver_id': str(wallet['_id']),
        'amount': amount,
        'currency': acronym,
        'created_at': datetime.now()
    }
    db.transactions.insert_one(newTransaction)
    # Agregar y aumentar el balance.

    print({'user_id': userId})

    if wallet:
        db.wallets.update_one(
            {'user_id': userId, 'currency': acronym},
            {
                '$set': {'balance': wallet['balance'] + amount}
            }
        )
    else:
        return abort(404)

    return redirect("/index")


@ app.route("/send")
def send_view():
    if not session.get('user_id'):
        return redirect('/')
    mensaje = request.args.get('mensaje')
    return render_template("send.html", mensaje=mensaje)


@ app.route("/send/wallet")
def sendtoWallet():
    if not session.get('user_id'):
        return redirect('/')

    wallet_id = request.args.get('wallet_id')
    amount = float(request.args.get('quantity'))
    # se valida antes
    if wallet_id == "":
        return redirect('/send?mensaje=Ingresa el ID de la billetera')
    if amount == "":
        return redirect('/send?mensaje=Ingresa una cantidad')

    if len(wallet_id) < 24:
        return redirect('/send?mensaje=La billetera no existe')

    userId = session.get('user_id')

    # Definimos las variables para buscar cada wallet y se hizo un filtro con currency para que especificar el tipo
    # de moneda que ambas wallet sean POR EJEMPLO USDT. y en el diccionario con str(senderWallet)
    # evitamos traer un object Id y nos traemos por si acaso un string.
    receiverWallet = db.wallets.find_one({'_id': ObjectId(wallet_id)})
    senderWallet = db.wallets.find_one(
        {'user_id': userId, 'currency': receiverWallet['currency']})

    if not senderWallet:
        return redirect('/send?mensaje=No tienes una billetera con esta moneda')

    newTransaction = {
        'wallet_sender_id': str(senderWallet['_id']),
        'wallet_receiver_id': wallet_id,
        'amount': amount,
        'currency': receiverWallet['currency'],
        'created_at': datetime.now()
    }
    lastTransactionId = db.transactions.insert_one(newTransaction).inserted_id
    return redirect('/send_confirm/' + str(lastTransactionId))


@ app.route("/send_confirm/<id>")
def send_confirm_view(id):
    if not session.get('user_id'):
        return redirect('/')
    # FORMA DE ACCEDER AL ID DE UN DOCUMENTO CREADO A TRAVES DE UNA COLECCION A OTRA QUE COINCIDA CON EL ID.
    # (Imprimimos al final en la vista: send_confirm.html el nombre del usuario a traves de la variable user_name)
    transactionDocument = db.transactions.find_one({'_id': ObjectId(id)})
    if not(transactionDocument):
        return abort(404)

    receiverWallet = db.wallets.find_one(
        {'_id': ObjectId(transactionDocument['wallet_receiver_id'])})

    receiver_id = receiverWallet['user_id']

    user_name = db.users.find_one({'_id': ObjectId(receiver_id)})

    return render_template("send_confirm.html", transactionDocument=transactionDocument, user_name=user_name)


@ app.route("/update_wallet_receiver/<id>")
def update_wallet_receiver(id):
    if not session.get('user_id'):
        return redirect('/')

    transactionDocument = db.transactions.find_one({'_id': ObjectId(id)})

    senderWallet = db.wallets.find_one(
        {'_id': ObjectId(transactionDocument['wallet_sender_id'])})
    receiverWallet = db.wallets.find_one(
        {'_id': ObjectId(transactionDocument['wallet_receiver_id'])})

    if not senderWallet or not receiverWallet:
        return abort(404)

    # tiene es que tener el saldo que va a mandar
    if senderWallet['balance'] < float(transactionDocument['amount']):
        return redirect('/send?mensaje=Saldo insuficiente')

    db.wallets.update_one(
        {'_id': ObjectId(transactionDocument['wallet_sender_id'])},
        {
            '$set': {'balance': senderWallet['balance'] - transactionDocument['amount']}
        }
    )
    db.wallets.update_one(
        {'_id': ObjectId(transactionDocument['wallet_receiver_id'])},
        {
            '$set': {'balance': receiverWallet['balance'] + transactionDocument['amount']}
        }
    )

    return redirect('/completed/' + str(transactionDocument['_id']))


@ app.route("/completed/<id>")
def completed_view(id):
    if not session.get('user_id'):
        return redirect('/')
    transactionDocument = db.transactions.find_one({'_id': ObjectId(id)})
    return render_template("completed.html", transactionDocument=transactionDocument)


@ app.route("/criptos")
def criptos_view():
    if not session.get('user_id'):
        return redirect('/')
    mensaje = request.args.get('mensaje')
    # En la vista hicimos que muestre el id al pasar el cursor.
    coins = list(db.coins.find())
    return render_template("criptos.html", mensaje=mensaje, coins=coins)


@ app.route("/addCripto/<id>")
def addCripto(id):
    coin = db.coins.find_one({'_id': ObjectId(id)})
    if not coin:
        return abort(404)

    coin_acronym = coin['acronym']
    coin_img = coin['img']
    coin_name = coin['name']
    userId = session.get('user_id')

    user_wallet = db.wallets.find_one(
        {'user_id': userId, 'currency': coin_acronym})  # Acá verficamos si la wallet ya existe redirecciona. ########

    if not user_wallet:  # Si no tiene wallet, se crea. y si tiene wallet, va a ir a comercio con la wallet y no creara otra
        newWallet = {
            'currency': str(coin_acronym),
            'balance': 0.0,
            'img': coin_img,
            'name': coin_name,
            'user_id': userId,
        }
        db.wallets.insert_one(newWallet)

    return redirect('/comercio/' + id)


@ app.route("/new_cripto_completed/<id>")
def newCripto(id):
    if not session.get('user_id'):
        return redirect('/')

    new_wallet_cripto = db.wallets.find_one({'_id': ObjectId(id)})
    if not(new_wallet_cripto):
        return abort(404)

    return render_template("new_cripto_completed.html", new_wallet_cripto=new_wallet_cripto)

######################### Acá creamos los anuncios ########################


@ app.route("/anuncios")
def anuncios_view():
    if not session.get('user_id'):
        return redirect('/')

    userId = session.get('user_id')
    ads = list(db.advertisements.find({'user_id': userId}))

    for bank in ads:
        method = db.banks.find_one({'_id': ObjectId(bank['payment_method'])})
        bank['method'] = method
    return render_template("anuncios.html", ads=ads)


@ app.route("/publish_buyer")
def publishBuyer_view():
    if not session.get('user_id'):
        return redirect('/')

    mensaje = request.args.get('mensaje')
    userId = session.get('user_id')
    criptoactives = list(db.wallets.find({'user_id': userId}))
    banks = list(db.banks.find({}))
    return render_template("publish_buyer.html", mensaje=mensaje, criptoactives=criptoactives, banks=banks)


@ app.route("/publish_seller")
def publishSeller_view():
    if not session.get('user_id'):
        return redirect('/')

    mensaje = request.args.get('mensaje')
    userId = session.get('user_id')
    criptoactives = list(db.wallets.find({'user_id': userId}))
    banks = list(db.banks.find({}))
    return render_template("publish_seller.html", mensaje=mensaje, criptoactives=criptoactives, banks=banks)


@ app.route("/publish_buyer/create_ad")
def create_buy_ad():
    if not session.get('user_id'):
        return redirect('/')

    coin = request.args.get('coin')
    fiat = request.args.get('fiat')
    type = request.args.get('type')
    fixed_price = request.args.get('fixed_price')
    quantity = request.args.get('quantity')
    limit_min = request.args.get('limit_min')
    limit_max = request.args.get('limit_max')
    payment_method = request.args.get('method')
    time = request.args.get('time')
    costumer_registred_days = request.args.get('costumer_registred_days')
    costumer_holdings_hystory = request.args.get('costumer_holdings_hystory')
    terms = request.args.get('terms')
    message = request.args.get('message')
    # El estado del anuncio le ponemos el mismo name a los dos radios de la vista publish_buyer.html
    status_online = request.args.get('status_online')
    userId = session.get('user_id')

    if coin == "" or fiat == "" or type == "" or fixed_price == "" or quantity == "" or limit_min == "" or limit_max == "" or payment_method == "" or time == "" or status_online == "":
        return redirect('/publish_buyer?mensaje=Tienes campos vacíos')

    # Filtramos la wallet del usuario para hacer la condicion de si posee el balance que dice tener y con el tipo de moneda que eligió.
    user_wallet = db.wallets.find_one({'user_id': userId, 'currency': coin})

    if float(quantity) > float(user_wallet['balance']):
        return redirect('/publish_buyer?mensaje=La cantidad introducida excede el balance disponible')

    final_limit = 1000000

    if float(limit_max) >= float(final_limit):
        return redirect('/publish_buyer?mensaje=El límite máximo no debe exceder 1000000.00')

    final_limit_min = 0

    if float(limit_min) <= float(final_limit_min):
        return redirect('/publish_buyer?mensaje=El límite mínimo no puede ser 0')

    if len(terms) >= 200:
        return redirect('/publish_buyer?mensaje=Los términos no deben superar los 200 caracteres')

    newAd = {
        'type': "Compra",
        'currency': coin,
        'fiat': fiat,
        'exchange_type': type,
        'fixed_price': float(fixed_price),
        'float_price': 0,
        'high_price': 290,
        'amount': float(quantity),
        'limit_min': float(limit_min),
        'limit_max': float(limit_max),
        'payment_method': payment_method,
        'time': time,
        'costumer_registred_days': costumer_registred_days,
        'costumer_holdings_hystory': costumer_holdings_hystory,
        'terms': terms,
        'message': message,
        'status_online': status_online,
        'color': "rgb(87, 255, 87)",
        'user_id': userId
    }
    db.advertisements.insert_one(newAd).inserted_id

    return redirect('/anuncios')

###### Paso a paso cómo hacer que una colección guarde un color y se seleccione más de un elemento: #########
# 1. Creamos la coleccion de bancos por ejemplo: Llamada Banks en Mongo Atlas.
# 2. Le creamos el campo de su name y de color. luego pegamos el numero hexadecimal deseado o de rgb(12,12,12).
# 3. En la vista publish_buyer.html imprimimos  banks = list(db.banks.find({})) cada elemento en un for.
# 5. Usamos vertical-color en Css y forzamos el style con la variable style="background-color:{{bank['color']}};"
# 6. el input de los bancos quedaria asi: (Cada uno tendrá su respectivo _id diferente)
# <input type="radio" class="btn-check" name="method" value="{{bank['_id']}}"
    # id="method_{{bank['_id']}}" autocomplete="off">
# <label class="btn btn-outline-light" for="method_{{bank['_id']}}">{{bank['name']}}</label>
# 7.


@ app.route("/publish_seller/create_ad")
def create_sell_ad():
    if not session.get('user_id'):
        return redirect('/')

    coin = request.args.get('coin')
    fiat = request.args.get('fiat')
    type = request.args.get('type')
    fixed_price = request.args.get('fixed_price')
    quantity = request.args.get('quantity')
    limit_min = request.args.get('limit_min')
    limit_max = request.args.get('limit_max')
    payment_method = request.args.get('method')
    time = request.args.get('time')
    costumer_registred_days = request.args.get('costumer_registred_days')
    costumer_holdings_hystory = request.args.get('costumer_holdings_hystory')
    terms = request.args.get('terms')
    message = request.args.get('message')
    status_online = request.args.get('status_online')
    userId = session.get('user_id')

    if coin == "" or fiat == "" or type == "" or fixed_price == "" or quantity == "" or limit_min == "" or limit_max == "" or payment_method == "" or time == "" or status_online == "":
        return redirect('/publish_buyer?mensaje=Tienes campos vacíos')

    final_limit = 1000000

    if float(limit_max) >= float(final_limit):
        return redirect('/publish_buyer?mensaje=El límite máximo no debe exceder 1000000.00')

    final_limit_min = 0

    if float(limit_min) <= float(final_limit_min):
        return redirect('/publish_buyer?mensaje=El límite mínimo no puede ser 0')

    user_wallet = db.wallets.find_one({'user_id': userId, 'currency': coin})

    if float(quantity) > float(user_wallet['balance']):
        return redirect('/publish_buyer?mensaje=La cantidad introducida excede el balance disponible')

    if len(terms) >= 200:
        return redirect('/publish_buyer?mensaje=Los términos no deben superar los 200 caracteres')

    newAd = {
        'type': "Venta",
        'currency': coin,
        'fiat': fiat,
        'exchange_type': type,
        'fixed_price': float(fixed_price),
        'float_price': 0,
        'high_price': 290,
        'amount': float(quantity),
        'limit_min': float(limit_min),
        'limit_max': float(limit_max),
        'payment_method': payment_method,
        'time': time,
        'costumer_registred_days': costumer_registred_days,
        'costumer_holdings_hystory': costumer_holdings_hystory,
        'terms': terms,
        'message': message,
        'status_online': status_online,
        'color': "rgb(255, 0, 0)",
        'user_id': userId
    }
    db.advertisements.insert_one(newAd).inserted_id

    return redirect('/anuncios')
