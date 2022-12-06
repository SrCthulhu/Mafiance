from flask import Flask, render_template, redirect, session, request, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import random
import os
from twilio.rest import Client
import api.keys as keys


app = Flask(__name__, static_url_path='', static_folder='public',)
app.secret_key = ".."
uri = os.environ.get('MONGO_DB_URI', "mongodb://127.0.0.1")
print(uri)
client = MongoClient(uri)
db = client.mafiance
account_sid = 'AC7c85cd42c3cff44b7edaa85b60352e89'
auth_token = '9bcf0c1f65cbc68699b937b5624ba752'
clientTwilio = Client(account_sid, auth_token)


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
        'user': new_user_name,
        'completed_orders': 0
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
    mensaje = request.args.get('mensaje')

    userId = session.get('user_id')
    order = db.orders.find_one({'advertiser_id': userId})
####### Forma de agregar un dato nuevo a la lista de la coleccion ads. para type error de listas por indices etc. #######
# Vease la vista P2PBuyer.html donde ajustamos el dato de nombre. Acá buscamos con el id en otra colección
    for ad in ads:
        user = db.users.find_one({'_id': ObjectId(ad['user_id'])})
        method = db.banks.find_one({'_id': ObjectId(ad['payment_method'])})
        ad['user'] = user
        ad['method'] = method

    return render_template("p2pBuyer.html", ads=ads, banks=banks, order=order, userId=userId, mensaje=mensaje)


@ app.route("/p2pSeller")
def p2pSeller_view():

    if not session.get('user_id'):
        return redirect('/')

    ads = list(db.advertisements.find({'type': 'Venta'}))
    banks = list(db.banks.find({}))

    userId = session.get('user_id')
    order = db.orders.find_one({'advertiser_id': userId})
    mensaje = request.args.get('mensaje')
    for ad in ads:
        user = db.users.find_one({'_id': ObjectId(ad['user_id'])})
        method = db.banks.find_one({'_id': ObjectId(ad['payment_method'])})
        ad['user'] = user
        ad['method'] = method

    return render_template("p2pSeller.html", ads=ads, banks=banks, order=order, userId=userId, mensaje=mensaje)
################################### Borramos un anuncio #######################################


@app.route("/remove_buyer_selected_ad/<id>")
def remove_buyer_ad(id):
    db.advertisements.delete_one({'_id': ObjectId(id)})
    return redirect('/p2pBuyer')


@app.route("/remove_seller_selected_ad/<id>")
def remove_seller_ad(id):
    db.advertisements.delete_one({'_id': ObjectId(id)})
    return redirect('/p2pSeller')

################################### Creación de Órdenes al comprar anuncio #######################################


@app.route("/buy_selected_ad/<id>")
def buy_selected(id):
    if not session.get('user_id'):
        return redirect('/')

    ad = db.advertisements.find_one({'_id': ObjectId(id)})
    user = db.users.find_one({'_id': ObjectId(ad['user_id'])})
    method = db.banks.find_one({'_id': ObjectId(ad['payment_method'])})
    banks = list(db.banks.find({}))
    mensaje = request.args.get('mensaje')

    advertiser_wallet = db.wallets.find_one(
        {'user_id': ad['user_id'], 'currency': ad['currency']})

    if float(advertiser_wallet['balance']) < float(ad['amount']):
        return redirect('/p2pBuyer?mensaje=El Anuncio está desactualizado, por favor elija otro')

    return render_template("buy_selected_ad.html", ad=ad, user=user, method=method, mensaje=mensaje, banks=banks)


@app.route("/orders")
def orders_view():
    if not session.get('user_id'):
        return redirect('/')

    userId = session.get('user_id')
    orders = list(db.orders.find({'user_id': userId}))
    return render_template("orders.html", orders=orders)


@app.route("/advertisements/<id>/orders")
def advertisements_order_view(id):
    if not session.get('user_id'):
        return redirect('/')

    orders = list(db.orders.find({'advertisement_id': id}))
    return render_template("advertisements_orders.html", orders=orders)


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
        return redirect('/buy_selected_ad/'+str(ad['_id'])+'?mensaje=Ingresa una cantidad')

    if not client_selected_method:
        return redirect('/buy_selected_ad/'+str(ad['_id'])+'?mensaje=Selecciona un método de pago')

    order_type = ad['type']
    order_currency = ad['currency']
    order_fiat = ad['fiat']
    advertiser_amount = ad['amount']
    user_name = user['user']
    order_exchange_type = ad['exchange_type']
    order_fixed_price = ad['fixed_price']
    order_float_price = ad['float_price']
    color = ad['color']
    advertiser_id = ad['user_id']
    advertisement_id = ad['_id']  # id del anunciante.
    userId = session.get('user_id')  # id de sesion del usuario que compra.

    # Acá verficamos si la orden ya existe redirecciona. ########
    user_order = db.orders.find_one(
        {'user_id': userId, 'currency': order_currency, 'client_quantity': quantity, 'client_payment_method': client_selected_method})

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
            'advertiser_id': advertiser_id,  # id del anunciante.
            'advertisement_id': str(advertisement_id),
            'created_at': datetime.now(),
            'color': color,
            'user_id': userId,  # id de sesion del usuario que compra.
        }
    last_order_id = db.orders.insert_one(new_order).inserted_id

    ################### Proceso de retención de cripto #######################
    ##########################################################################
    advertiser_wallet = db.wallets.find_one(
        {'user_id': ad['user_id'], 'currency': ad['currency']})

    # Creamos un nuevo dato en la colección. Preguntar cómo crear un nuevo campo en base de datos  ###############

    advertiser_wallet['temp_balance'] = float(0)

    if advertiser_wallet:

        # Restamos el balance a 0 y sumamos la cantidad al nuevo campo dentro de la misma wallet.
        db.wallets.update_one(
            {'user_id': advertiser_wallet['user_id'],
                'balance': advertiser_wallet['balance']},
            {
                '$set': {'balance': advertiser_wallet['balance'] - ad['amount']}
            }
        )

        db.wallets.update_one(
            {'user_id': advertiser_wallet['user_id'],
                'temp_balance': advertiser_wallet['temp_balance']},
            {
                '$set': {'temp_balance': advertiser_wallet['temp_balance'] + ad['amount']}
            }
        )
        print(advertiser_wallet)
    else:
        return abort(404)

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

    advertiser_wallet = db.wallets.find_one(
        {'user_id': ad['user_id'], 'currency': ad['currency']})

    if float(advertiser_wallet['balance']) < float(ad['amount']):
        return redirect('/p2pSeller?mensaje=El Anuncio está desactualizado, por favor elija otro')

    return render_template("sell_selected_ad.html", ad=ad, user=user, method=method, banks=banks, mensaje=mensaje)

############################################## CHAT Y CREACIÓN DE MENSAJES #############################################


@app.route("/chat/<id>")
def chat_view(id):
    if not session.get('user_id'):
        return redirect('/')

    order = db.orders.find_one({'_id': ObjectId(id)})
    message = list(db.messages.find({'order_id': id}))
    userId = session.get('user_id')
    mensaje = request.args.get('mensaje')

    return render_template("client_chat.html", order=order, message=message, userId=userId, mensaje=mensaje)


@app.route("/message/create")
def comment_create():
    if not session.get('user_id'):
        return redirect('/')

    messageText = request.args.get('message')
    imageUrl = request.args.get('image')
    orderId = request.args.get('order_id')
    userId = session.get('user_id')
    user_name = db.users.find_one({'_id': ObjectId(userId)})

    ad = request.args.get('ad_id')

    ad_id = db.advertisements.find_one({'_id': ObjectId(ad)})

# En esta condición decimos "si el mensaje de texto no esta vacío o el mensaje
# reservado del anunciante existe crea el mensaje".

    if messageText != "" or imageUrl != "":

        message = {}
        message['message'] = messageText
        message['image_url'] = imageUrl
        message['reserved_message'] = ad_id['message']
        message['order_id'] = orderId
        message['user_id'] = userId
        message['user'] = user_name

    else:
        return redirect('/chat/'+str(orderId)+'?mensaje=Introduce un mensaje válido')

    db.messages.insert_one(message)
    return redirect('/chat/' + str(orderId))


############################ Cambiamos estado de la orden ########################################


@app.route("/order/next/status/<id>")
def order_next_status(id):

    order = db.orders.find_one({'_id': ObjectId(id)})
    # status= se refiere al valor de la clave 'status' que tenga el pedido en la actualidad.
    status = order['status']

    if order['status'] == 'Pendiente':
        # se cumple la condicion y se reemplaza el valor del status. de 'Pendiente' a 'liberando' y luego a 'Completado'
        status = 'Liberando'

    elif order['status'] == 'Liberando':
        status = 'Completado'

    else:
        order['status'] == 'Apelando'
        status = 'Completado'

    db.orders.update_one(
        {'_id': ObjectId(id)},
        {'$set': {'status': status}}
    )
    ################ Pasamos el dinero de la wallet temporal a la del cliente  #######################
    if order['status'] == 'Completado' or order['status'] == 'Apelando':

        advertiser_wallet = db.wallets.find_one(  # Wallet anunciante
            {'user_id': order['advertiser_id'], 'currency': order['currency']})

        client_wallet = db.wallets.find_one(      # Wallet cliente.
            {'user_id': order['user_id'], 'currency': order['currency']})

        if advertiser_wallet:

            db.wallets.update_one(
                {'user_id': order['advertiser_id'],
                    'currency': order['currency']},
                {
                    '$set': {'temp_balance': advertiser_wallet['temp_balance'] - order['advertiser_amount']}
                }
            )

            db.wallets.update_one(
                {'user_id': order['user_id'], 'currency': order['currency']},
                {
                    '$set': {'balance': client_wallet['balance'] + order['advertiser_amount']}
                }
            )

            # Si la orden está como Cancelada, al terminar la transacción pasará a estar Completado
            # Eliminamos el anuncio si el estado de la orden es completado

            if order['status'] == 'Apelando':
                status = 'Completado'
            else:
                ad = db.advertisements.find_one(
                    {'_id': ObjectId(order['advertisement_id'])})

                db.advertisements.delete_one(ad)

            # Hacemos el conteo de ordenes completadas para el usuario dentro de la colección users

                if order['status'] == 'Completado':
                    user_id = db.users.find_one(
                        {'_id': ObjectId(order['user_id'])})

                    db.users.update_one(
                        {'_id': user_id['_id']},
                        {'$set':
                         {'completed_orders':  user_id['completed_orders'] + 1}
                         }
                    )
                return redirect('/order_completed/' + str(id))
    # Recargamos el client_chat.html cuando el usuario le da continuar y se actualiza el estado a liberando.
    return redirect('/chat/' + str(id))


@app.route("/validationCode/<id>")
def validation_code_view(id):
    if not session.get('user_id'):
        return redirect('/')
    order = db.orders.find_one({'_id': ObjectId(id)})
    userId = session.get('user_id')
    mensaje = request.args.get('mensaje')
    ##################### Api Rest Twilio (Mensajes de verificación al teléfono) ##########################
    number = random.randint(1000, 9000)
    textMessage = clientTwilio.messages.create(
        body="Tu código de verificación es: " + str(number),
        from_=keys.twilio_number,
        to=keys.target_number
    )
    print(textMessage.body)

    return render_template("validation_code.html", order=order, userId=userId, mensaje=mensaje, number=number)


@app.route("/submit_code/<id>")
def validation(id):
    if not session.get('user_id'):
        return redirect('/')
    order = db.orders.find_one({'_id': ObjectId(id)})
    phone_code = request.args.get('phone_code')
    code = request.args.get('code')
    if phone_code == code:
        codeMessage = {}
        codeMessage['code'] = code
        codeMessage['orderId'] = order['_id']
    else:
        return redirect('/validationCode/' + str(id)+'?mensaje=El código introducido no es válido, verifique los datos')

    db.codes.insert_one(codeMessage)

    return redirect('/validationCode/' + str(id))


@app.route("/order/apelation/<id>")
def order_apelation(id):

    order = db.orders.find_one({'_id': ObjectId(id)})

    status = order['status']

    if order['status'] == 'Liberando':
        status = 'Apelando'
############ Diferencia de segundos entre dos fechas ##################
    fechaActual = datetime.now()
    fechaMaxima = order['created_at']

    def diferencia_segundos_fechas(fechaActual, fechaMaxima):
        diferencia = fechaMaxima - fechaActual
        resultado = diferencia.days * 24 * 3600 + diferencia.seconds
        return(resultado)
    print('fecha actual:', fechaActual)
    print(diferencia_segundos_fechas(fechaMaxima, fechaActual))

    if diferencia_segundos_fechas(fechaMaxima, fechaActual) < 180:
        return redirect('/chat/' + str(id) + '?mensaje=Falta tiempo, aun no puedes apelar')

    # INVESTIGAR PARA TEMPORIZADORES EN BACKEND DE VERDAD: cron job o cron tab

    db.orders.update_one(
        {'_id': ObjectId(id)},
        {'$set': {'status': status}}
    )

    return redirect('/chat/' + str(id))


@ app.route("/order_completed/<id>")
def order_completed_view(id):

    if not session.get('user_id'):
        return redirect('/')
    order = db.orders.find_one({'_id': ObjectId(id)})
    return render_template("order_completed.html", order=order)


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
            'temp_balance': 0.0,
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

###################################### CREACIÓN DE ANUNCIOS ############################################


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

    if user_wallet == None:
        return redirect('/publish_buyer?mensaje=No posees una billetera con el activo seleccionado, por favor elija uno válido')

    if payment_method == None:
        return redirect('/publish_buyer?mensaje=Selecciona un banco')

    if status_online == None:
        return redirect('/publish_buyer?mensaje=Elije si tu anuncio será publicado en linea ahora mismo ó manualmente luego')

    if user_wallet:
        if float(quantity) > float(user_wallet['balance']):
            return redirect('/publish_buyer?mensaje=Saldo insuficiente')

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
        return redirect('/publish_seller?mensaje=Tienes campos vacíos')

    final_limit = 1000000

    if float(limit_max) >= float(final_limit):
        return redirect('/publish_seller?mensaje=El límite máximo no debe exceder 1000000.00')

    final_limit_min = 0

    if float(limit_min) <= float(final_limit_min):
        return redirect('/publish_seller?mensaje=El límite mínimo no puede ser 0')

    user_wallet = db.wallets.find_one({'user_id': userId, 'currency': coin})

    if user_wallet == None:
        return redirect('/publish_seller?mensaje=No posees una billetera con el activo seleccionado, por favor elija uno válido')

    if payment_method == None:
        return redirect('/publish_seller?mensaje=Selecciona un banco')

    if status_online == None:
        return redirect('/publish_seller?mensaje=Elije si tu anuncio será publicado en linea ahora mismo ó manualmente luego')

    if float(quantity) > float(user_wallet['balance']):
        return redirect('/publish_seller?mensaje=Saldo insuficiente')

    if len(terms) >= 200:
        return redirect('/publish_seller?mensaje=Los términos no deben superar los 200 caracteres')

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
