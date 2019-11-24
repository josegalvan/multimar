
#-*- encoding: utf-8 -*-

from django.shortcuts import render,redirect,render_to_response
from django.http import HttpResponse,HttpResponseRedirect,Http404
from django.template import RequestContext,loader
from django.core.urlresolvers import reverse
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder # Permite decodificar fecha y hora con formato mysql obtenido con dictfetchall
from django.contrib.auth import authenticate, login, logout,update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm,PasswordChangeForm
from django.contrib.auth.decorators import login_required,permission_required
from django.views.decorators.csrf import ensure_csrf_cookie
from .forms import (AccesoForm,\
					BuscapedidosForm,\
					PedidosForm,\
					RegsocwebForm,\
					Forma_RegistroForm,\
					BuscapedidosporsocioForm,\
					Calzadollego_gralForm,\
					Calzadollego_detalleForm,\
					Consulta_colocacionesForm,\
					Consulta_ventasForm,\
					Consulta_comisionesForm,\
					BuscapedidosposfechaForm,\
					PedidosgeneralForm,\
					Entrada_sistemaForm,\
					CancelaproductoForm,\
					Ingresa_socioForm,\
					ColocacionesForm,\
					ElegirAlmacenaCerrarForm,\
					SeleccionCierreRpteCotejoForm,\
					SeleccionCierreRecepcionForm,\
					DocumentosForm,\
					DetalleDocumentoForm,\
					CreaDocumentoForm,\
					CierresForm,\
					Crea_devolucionForm,)

from pedidos.models import Asociado,Articulo,Proveedor,Configuracion
from django.db import connection,DatabaseError,Error,transaction,IntegrityError,OperationalError,InternalError,ProgrammingError,NotSupportedError

from datetime import datetime,date,time,timedelta
import calendar
from django.conf import settings
import pdb
import unicodedata
import json
from collections import namedtuple
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
import csv
from decimal import Decimal,getcontext
getcontext().prec = 6# esta linea establece la precision de decimales para numeros decimales,
					  # leer la funcion getcontext de decimales.

#from reportlab.lib.pagesizes import inch

# PARA REPORTLABS (usar un font FreeSans, pero no cambiaba mucho, asi que no se uso)

#from reportlab.pdfbase import pdfmetrics
#from reportlab.pdfbase.ttfonts import TTFont

#pdfmetrics.registerFont(TTFont('FreeSans', '/usr/share/fonts/truetype/freefont/FreeSans.ttf'))




# Las siguiente 3 lineas son para que se indicar a python que hagas las conversiones
# de unicode a utf-8 en lugar de hacerlas a ascii.
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


# Para serializar objetos decimales con json, porque si se serializan directamente no funciona.
# ahorita no se utiliza..pero hay que ver como utilizarla, tambien hay que probar si json puede serializar fechas 
# y otros tipos de objeto.

'''
class DecimalEncoder(json.JSONEncoder):
    def _iterencode(self, o, markers=None):
        if isinstance(o, decimal.Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(o) for o in [o])
        return super(DecimalEncoder, self)._iterencode(o, markers)
'''

'''
def falselogin(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            # Redirect to a success page.
           	redirect('pedidos/autenticacion_exitosa.html')
        else:
            # Return a 'disabled account' error message
            redirect('pedidos/cuenta_desactivada.html')
    else:
        # Return an 'invalid login' error message.
        	redirect('pedidos/autenticacion_fallida.html')
'''
''' VISTA_1 INICIA ACCESO A SISTEMA '''

def index(request):

	request.session.set_test_cookie()

	return render(request,'pedidos/index.html')

'''VISTA_2 SALIDA DEL SISTEMA '''
def logout_view(request):
   	
   	logout(request)

   	return redirect('pedidos:index')# Redirect to a success page.


''' La siguiente variable global se utiliza para guardar el numero de socio en zapcat se actualiza en la rutina "acceso", 
este valor sera utilizado por  la rutina busca_pedidos  para las consultas sql.'''

#g_numero_socio_zapcat = 0



'''VISTA_3 TRAE FECHA_HORA ACTUAL EN FORMATO ADECUADO'''
def trae_fecha_hora_actual(fecha_hoy,hora_hoy):
	hoy = datetime.now()
	fecha_hoy = hoy.strftime("%Y-%m-%d")
	hora_hoy = hoy.strftime("%H:%M:%S") 
	return (fecha_hoy,hora_hoy)

def days_between(d1, d2):

    return abs(d2 - d1).days



'''VISTA_4 CONTINUA ACCESO AL SISTEMA'''
def acceso(request):

	#pdb.set_trace() 
	global g_numero_socio_zapcat
	
	
	mensaje=""
	if request.session.test_cookie_worked():
		request.session.delete_test_cookie()
		
	else:
		
		if request.session.session_key is None:
			return HttpResponse("Por favor active cookies en su navegador e intente nuevamente.")

	# Se trae la session
	session_id = request.session.session_key

	print "SESION:"
	print session_id

	print "USUARIO:"
	print request.user
	usuario_en_session = request.user
	request.session['sucursal_activa'] = 0
	request.session['sucursal_nombre'] = ''
	request.session['is_staff'] = request.user.is_staff

	
	# elimina registros de tabla temporal de pedidos.
	cursor = connection.cursor()
	cursor.execute("DELETE FROM pedidos_pedidos_tmp WHERE session_key=%s;",[session_id])
	

	
	if request.method =='POST':
		
		form = AccesoForm(request.POST)
		if form.is_valid():
			
						

			username = request.POST.get('username')
			password = request.POST.get('password')
			
						
			user = authenticate(username=username, password=password)
			
			if user is not None:
			
				if user.is_active:
					login(request, user)
					mensaje = 'Bienvenido a su sistema de pedidos !'
					cursor.execute("SELECT asociadono,EsSocio FROM asociado where num_web=%s;",[request.user.id])
					socio_datos = dictfetchall(cursor)

					cursor.execute("SELECT * FROM configuracion WHERE empresano = 1;")
					configuracion = cursor.fetchone()

					# Asignacion de otras variables de entorno 

					request.session['cnf_ejercicio_vigente'] = configuracion[1]
					request.session['cnf_periodo_vigente'] = configuracion[2]
					request.session['cnf_razon_social'] = configuracion[3]
					request.session['cnf_direccion'] = configuracion[4]
					request.session['cnf_colonia'] = configuracion[5]
					request.session['cnf_ciudad'] = configuracion[6]
					request.session['cnf_estado'] = configuracion[7]	
					request.session['cnf_codigo_postal'] = configuracion[9]
					request.session['cnf_telefono'] = configuracion[10]
					request.session['cnf_rfc'] = configuracion[11]
					request.session['cnf_iva'] = configuracion[13]
					request.session['cnf_porcentaje_anticipo'] = configuracion[14]
					request.session['cnf_max_dias_extemp'] = configuracion[19]
					request.session['cnf_cuota_dias_extemp'] = configuracion[20]	
					request.session['cnf_dias_vigencia_credito'] = configuracion[21]
					request.session['cnf_comision_por_calzado_no_recogido'] = configuracion[22]
					request.session['cnf_dias_plazo_vmvto_aqui_socio_credito'] = configuracion[23]
					request.session['cnf_dias_plazo_vmto_aqui_socio_sincredito'] = configuracion[24]	
					request.session['cnf_mostrar_socio_en_ticket'] = configuracion[25]
					
					
					if not socio_datos:
						return HttpResponse("Ud. no tiene asignado un numero de socio, por favor consulte al administrador el sistema")					
					else:
						for r in socio_datos:
							g_numero_socio_zapcat = r['asociadono']

							request.session['socio_zapcat'] = r['asociadono']

							request.session['EsSocio'] = r['EsSocio']

					request.session['is_staff']	= user.is_staff			
					# Con la siguiente linea cierra la session al cerrar el navegador.		
					request.session.set_expiry(0)
					
					if user.is_staff:
						form = Entrada_sistemaForm()
						return render(request,'pedidos/entrada_sistema.html',{'form':form,'usuario':request.user,'is_staff':True},)
					else:
						form = BuscapedidosForm()
						return render(request,'pedidos/busca_pedidos.html',{'form':form,'usuario':request.user,'is_staff':request.session['is_staff']},)
	
				else:
					# Return a 'disabled account' error message
					mensaje = 'Usuario y contraseña correctos pero su cuenta está desactivada, comuniquese por favor con el equipo de ES Shoes Multimarcas. !'
					
			else:
				# Return an 'invalid login' error message.
				mensaje = 'Usuario y/o contraseña incorrectos, intente de nuevo !'
		else:			 
			return render(request,'pedidos/acceso.html',{'form':form,'is_staff':False,})
	
	request.session.set_test_cookie()
	form=AccesoForm()
	return render(request,'pedidos/acceso.html',{'form':form,'mensaje':mensaje,'is_staff':False,})

'''VISTA_5 DICCIONARIO DE DATOS '''


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    	]



def namedtuplefetchall(cursor):
    "Return all rows from a cursor as a namedtuple"
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]


def traePrimerUltimoDiasMesAnterior():
	
	#pdb.set_trace() 

	# La rutina calcula la fecha del primero y el ultimo dia del mes anterior
	# al actual y las devuelve como strings en el formato
	# '20190501' y '20190531', (por ejemplo para el mes de Mayo del 2019)



	

	hoy = datetime.now()  # se obtiene la fecha de hoy como tupla
	anio = hoy.year                # se obtiene el anio actuales
	mes = hoy.month                # se obtiene el mes actuales
	dia = hoy.day                  # se obtiene el dia actueles

	anio_anterior = anio-1 if mes==1 else anio # se obtiene el anio anterior
	mes_anterior = 12 if mes ==1 else ( mes -1) # se obtiene el mes anterior

						   


	num_days = calendar.monthrange(anio_anterior, mes_anterior)  # trae una tupla con el rango
	                                                             # de dias del mes
	                                                             # del mes, ejemplo (1,31), si es Enero.

	primer_dia = date(anio_anterior, mes_anterior, 1)   # trae el valor del primer dia
	ultimo_dia = date(anio_anterior, mes_anterior, num_days[1]) # trae el valor del ultimo dia (31, para el ejemplo)
	fecha_inicial = primer_dia.strftime('%Y%m%d') # se convierte a formato 'YYYYmmdd'
	fecha_final = ultimo_dia.strftime('%Y%m%d')   # Se convierte a formato 'YYYYmmdd'
	return(fecha_inicial,fecha_final)







def crea_tabla_pedidos_temporal():

	try:

		cursor = connection.cursor()
		cursor.execute('CREATE TEMPORARY TABLE IF NOT EXISTS pedidos_tmp (id int AUTO_INCREMENT,idproducto char(16),idprovedor int, catalogo char(12),precio decimal(8,2),nolinea int, PRIMARY KEY(id));')
		print "Entro a crear tabla temporal de pedidos"

	except Error as e:	
		print "NO creo tabla de pedidos %s" %e
		

	return()

def lista_asociados(request):
	cursor=connection.cursor()
	cursor.execute('SELECT asociadono,nombre,appaterno,apmaterno,telefono1 from Asociado limit 20;')
	asociados = dictfetchall(cursor)
	for a in asociados:
		print a
	context = {'asociados': asociados}
	return render(request, 'pedidos/asociados.html', context)	
		
def ok(request):
	
	return render(request, 'pedidos/autencitacion_exitosa.html')	


def busca_pedidos(request):
	#pdb.set_trace() 


	try:
		g_numero_socio_zapcat = request.session['socio_zapcat']	
		is_staff = request.user.is_staff

	except KeyError :
		
		#print "llave:",request.session['socio_zapcat']
		return	HttpResponse("Ocurrió un error de conexión con el servidor, Por favor salgase completamente y vuelva a entrar a la página !")

	if request.user.is_authenticated():		
		
		if request.method == 'POST':
			form = BuscapedidosForm(request.POST)
			'''
			Si la forma es valida se normalizan los campos numpedido, status y fecha,
			de otra manera se envia la forma con su contenido erroreo para que el validador
			de errores muestre los mansajes correspondientes '''

			if form.is_valid():
			
				# limpia datos 
				numpedido = form.cleaned_data['numpedido']
				status = form.cleaned_data['status']
				fecha = form.cleaned_data['fecha']
				print "fecha es"
				print fecha
				# Convierte el string '1901-01-01' a una fecha valida en python
				# para ser comparada con la fecha ingresada 

				fecha_1901 =datetime.strptime('1901-01-01', '%Y-%m-%d').date()
				hoy = date.today()
				print "hoy es "
				print hoy

				# Establece conexion con la base de datos
				cursor=connection.cursor()
				
				# Comienza a hacer selects en base a criterios 


				if numpedido != 0:
					cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) where h.asociadono=%s and h.pedidono=%s;", (g_numero_socio_zapcat,numpedido))
					
				else :
					if  status == 'Todos' and fecha != fecha_1901:
						cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) where h.asociadono=%s and h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (g_numero_socio_zapcat,fecha-timedelta(days=60),fecha))
						print "Entro en status=Todos y fecha != 19010101"
					else:
						if status !='Todos' and fecha == fecha_1901:
							cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) where h.asociadono=%s and l.status=%s and h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (g_numero_socio_zapcat,status,hoy-timedelta(days=60),hoy))
							print "Entro en status != Todos y fecha=1901/01/01"
						else:
	 						if status != 'Todos' and fecha != fecha_1901:
								cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) where h.asociadono=%s and l.status=%s and h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (g_numero_socio_zapcat,status,fecha-timedelta(days=60),fecha))			
								print "Entro en status != Todos y fecha != 1901/01/01"
							else:
								mensaje ='No se encontraron registros !'
				
				# El contenido del cursor se convierte a diccionario para poder
				# ser enviado como parte del contexto y sea manipulable.				
				pedidos = dictfetchall(cursor)
				for pun in pedidos:
					print pun

				elementos = len(pedidos)
				

				if not pedidos:
					mensaje = 'No se encontraron registros !'
				else:
					mensaje ='Registros encontrados:'
				
				context = {'pedidos':pedidos,'mensaje':mensaje,'elementos':elementos,'is_staff':is_staff,}

				# Cierra la conexion a la base de datos
				cursor.close()
				
				return render(request,'pedidos/lista_pedidos.html',context)
			
		else:
			form = BuscapedidosForm()
			#cursor.close()
			
		return render(request,'pedidos/busca_pedidos.html',{'form':form,'is_staff':is_staff})
	else:
		redirect('/pedidos/acceso/') 


def lista_pedidos(request):
	context = {'asociados': asociados,'form':form}
	return render(request, 'pedidos/asociados.html', context,{'form':form})


# La siguiente funcion es utilizada para seleccionar 
# los proveedores y que se puedan mostrar en el combo de proveedor al hacer un
# pedido, dicho combo debe tener como valor inicial esta lista para que de ahi
# se pueda hacer la seleccion.

def lista_Proveedores():
	cursor=connection.cursor()
	cursor.execute('SELECT proveedorno,razonsocial from Proveedor where trim(razonsocial)<>"";')
	
	pr=() # Inicializa una tupla para llenar combo de Proveedores
	
	for row in cursor:
		elemento = tuple(row)
		pr=pr+elemento
	x=[]
	y=[]
	
	for i in range(0,len(pr)):
		if i % 2 != 0:
			x.append(pr[i])
			x.append(pr[i])
			y.append(x)
			x=[]
	
	# tuple_of_tuples = tuple(tuple(x) for x in list_of_lists)
	lsuc = tuple(tuple(x) for x in y)
	
	return (lsuc)

def lista_Sucursales():
	cursor=connection.cursor()
	cursor.execute("SELECT nombre from sucursal where SucursalNo >= %s;",[0])
	lsuc = ()
	for row in cursor:
		elemento = tuple(row)
		lsuc=lsuc+elemento
	#lsuc=('SELECCIONE...',)+lsuc
	
	return (lsuc)	
	


@login_required(login_url = "/pedidos/acceso/")
def crea_pedidos(request):
	#import pdb; pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..
	
	mensaje = " "
	tipo = 'P'
	# elimina cualquier registro de la session.
	session_id = request.session.session_key
	# Asigna is_staff para validacines
	is_staff = request.session['is_staff']

	cursor = connection.cursor()
	cursor.execute("DELETE FROM pedidos_pedidos_tmp where session_key= %s;",[session_id])	
	cursor.close()


	#for key,value in pr_dict.items():
	#	print key,value 
	
	 
	if request.method =='POST':
		
		form = PedidosForm(request.POST)
		
		if form.is_valid():
			
			
			proveedor = form.cleaned_data['proveedor']
			temporada =  form.cleaned_data['temporada']
			catalogo = form.cleaned_data['catalogo']
			pagina = form.cleaned_data['pagina']
			estilo = form.cleaned_data['estilo']
			marca = form.cleaned_data['marca']
			color = form.cleaned_data['color']
			talla = form.cleaned_data['talla']	



			#cursor=connection.cursor()
			#registro_encontrado = 0
			#cursor.execute("SELECT a.codigoarticulo from articulo a where a.proveedor=%s and a.temporada=%s and a.catalogo=%s and a.pagina=%s and a.estilo=%s and a.marca=%s and a.color=%s and a.talla=%s", (proveedor,temporada,catalogo,pagina,estilo,marca,color,talla))
			#articulo=dictfetchall(cursor);
			mensaje = "El articulo encontrado fue:abcd " #+ articulo.codigoarticulo
			return render(request,'pedidos/crea_pedido.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})
		else:	
			
			mensaje = "Error en la forma"
			return render(request,'pedidos/crea_pedidos.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})

	form = PedidosForm(request)
	mensaje = "Entrando de nuevo a la forma"
	return render(request,'pedidos/crea_pedidos.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,'tipo':tipo,})	

#  LOGICA PARA COMBO DE TEMPORADAS

def lista_Temporadas(id_prov):
	
	cursor=connection.cursor()
	cursor.execute("SELECT clasearticulo from Catalogostemporada where proveedorno=%s and anio=%s;",[id_prov,id_temp])
	
	listacat=() # Inicializa una tupla para llenar combo de Proveedores
			
	# Convierte el diccionario en tupla
	for row in cursor:
		elemento = tuple(row)
		listacat=listacat+elemento
	listacat=('SELECCIONE...',)+listacat
	
	return (listacat)	

def combo_temporadas(request,*args,**kwargs):
	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		
		
		
		# Trae la lista de catalogos con los parametros indicados:
		l = (('0','SELECCIONE...'),('1','Primavera/Verano'),('2','Otoño/Invierno'))
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		
		data = {'Mensaje':"El id proveedor recibido fue %s" % request.POST.get['id_prov']}
		#data = json.dumps(l)
		
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

		return HttpResponse(data)
	else:
		raise Http404
		print "No hallo pagina para combo temporada"







#  LOGICA PARA COMBO DE CATALOGOS

def lista_Catalogos(id_prov,id_temp,g_numero_socio_zapcat,is_staff):

	#pdb.set_trace()
	#print "g_numero_socio_zapcat trae",g_numero_socio_zapcat
	
	# Si el socio activo es de staff entonces se debe buscar por
	# los catalogos del socio_pidiendo, de otra manera significa que
	# no hay ningun socio pidiendo calzado y quien esta firmado es 
	# quien pide g_numero_socio_zapcat

	# Esto hara que la busqueda se haga por la variable socio_que_pide

	adquirio_catalogo = 1

	cursor=connection.cursor()
	#cursor.execute("SELECT clasearticulo from catalogostemporada where proveedorno=%s and anio=%s;",(id_prov,id_temp))
	
	# Hace un primer select de catalogos considerando al socio y si esta activo para estos catalogos
	cursor.execute("SELECT s.clasearticulo from sociocatalogostemporada s inner join catalogostemporada c on (s.ProveedorNo=c.ProveedorNo and s.Periodo=c.Periodo and s.Anio=c.Anio and s.ClaseArticulo=c.ClaseArticulo)  where s.proveedorno=%s and s.anio=%s and s.AsociadoNo=%s and s.Activo and c.Activo;",[id_prov,id_temp,g_numero_socio_zapcat,])
	registros = cursor.fetchall()


	listacat=() # Inicializa una tupla para llenar combo de Proveedores
	
	
	# Si el primer select no arroja registros, hace un segundo select sin considerar al socio
	# solo para que se traiga la lista de catalogos del proveedor
	# y la bandera de adquirio_catalogo la hace falsa ( le pone cero )
	

	if not registros or is_staff:
		try:

			cursor.execute("SELECT c.clasearticulo from catalogostemporada c  where c.proveedorno=%s and c.anio=%s  and c.Activo=1 group by c.proveedorno,c.anio,c.clasearticulo  ;",[id_prov,id_temp,])
					
			
			adquirio_catalogo = 0
		
		except Error as e:
			print e
	


	# Convierte el diccionario en tupla
	for row in cursor:
		elemento = tuple(row)
		listacat=listacat+elemento
	listacat=('SELECCIONE...',)+listacat

	return (listacat,adquirio_catalogo)	

def combo_catalogos(request,*args,**kwargs):
	#pdb.set_trace()

	g_numero_socio_zapcat = request.session['socio_zapcat']
	print "el socio es ", g_numero_socio_zapcat

	is_staff = request.session['is_staff']

	adquirio_catalogo = 1


	if request.session['is_staff']:


		socio_a_validar = request.session['socio_pidiendo']

		print "Socio staff pidiendo",socio_a_validar
		
	else:
		socio_a_validar = g_numero_socio_zapcat

		print "Socio no staff pidiendo",socio_a_validar


	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		id_temp = request.GET['id_temp']
		
		
		print "llego hasta antes de l"
		print "socio a validar:",socio_a_validar
		# Trae la lista de catalogos con los parametros indicados:
		
		l,adquirio_catalogo = lista_Catalogos(id_prov,id_temp,socio_a_validar,is_staff)
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		h = {'l':l,'adquirio_catalogo':adquirio_catalogo,'is_staff':is_staff}

		data = json.dumps(h)
		
		#data = {'Mensaje':"El id proveedor recibido fue %s" % request.GET['id_prov']}
				
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404
		

#  LOGICA PARA COMBO DE ESTILO

def lista_Estilos(id_prov,id_temp,id_pag,id_cat):
	
	cursor=connection.cursor()
	cursor.execute("SELECT estilo from preciobase where empresano=1 and proveedorid=%s and temporada=%s and pagina=%s and catalogo=%s GROUP BY estilo;",[id_prov,id_temp,id_pag,id_cat])
	
	listaest=() # Inicializa una tupla para llenar combo de Estilos
			
	# Convierte el diccionario en tupla
	for row in cursor:
		elemento = tuple(row)
		listaest=listaest+elemento
	listaest=('SELECCIONE...',)+listaest
	
	return (listaest)	

def combo_estilos(request,*args,**kwargs):
	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		id_temp = request.GET['id_temp']
		id_pag = request.GET['id_pag']
		id_cat = request.GET['id_cat']
		
		# Trae la lista de catalogos con los parametros indicados:
		l = lista_Estilos(id_prov,id_temp,id_pag,id_cat)
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		data = json.dumps(l)
		#data = {'Mensaje':"El id proveedor recibido fue %s" % request.GET['id_prov']}
				
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404
		
#  LOGICA PARA COMBO DE MARCAS

def lista_Marcas(id_prov,id_temp,id_pag,id_cat,id_est):
	
	cursor=connection.cursor()
	cursor.execute("SELECT idmarca from preciobase where empresano=1 and proveedorid=%s and temporada=%s and pagina=%s and catalogo=%s and estilo=%s GROUP BY idmarca;",[id_prov,id_temp,id_pag,id_cat,id_est])
	
	listamar=() # Inicializa una tupla para llenar combo de Estilos
			
	# Convierte el diccionario en tupla
	for row in cursor:
		elemento = tuple(row)
		listamar=listamar+elemento
	listamar=('SELECCIONE...',)+listamar
	
	return (listamar)	



def combo_marcas(request,*args,**kwargs):
	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		id_temp = request.GET['id_temp']
		id_pag = request.GET['id_pag']
		id_cat = request.GET['id_cat']
		id_est = request.GET['id_est']

			
		# Trae la lista de catalogos con los parametros indicados:
		l = lista_Marcas(id_prov,id_temp,id_pag,id_cat,id_est)
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		data = json.dumps(l)
		#data = {'Mensaje':"El id proveedor recibido fue %s" % request.GET['id_prov']}
				
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404
		
#  LOGICA PARA COMBO DE COLOR

def lista_Colores(id_prov,id_temp,id_pag,id_cat,id_est,id_mar):
	
	
	
	cursor=connection.cursor()
	cursor.execute("SELECT idcolor from preciobase where empresano=1 and proveedorid=%s and temporada=%s and pagina=%s and catalogo=%s and estilo=%s and idmarca=%s GROUP BY idcolor;",[id_prov,id_temp,id_pag,id_cat,id_est,id_mar])
	
	listacol=() # Inicializa una tupla para llenar combo de Estilos
			
	# Convierte el diccionario en tupla
	for row in cursor:
		elemento = tuple(row)
		listacol=listacol+elemento
	listacol=('SELECCIONE...',)+listacol
	
	return (listacol)	



def combo_colores(request,*args,**kwargs):
	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		id_temp = request.GET['id_temp']
		id_pag = request.GET['id_pag']
		id_cat = request.GET['id_cat']
		id_est = request.GET['id_est']
		id_mar = request.GET['id_mar']

		
		
		# Trae la lista de catalogos con los parametros indicados:
		l = lista_Colores(id_prov,id_temp,id_pag,id_cat,id_est,id_mar)
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		data = json.dumps(l)
		#data = {'Mensaje':"El id proveedor recibido fue %s" % request.GET['id_prov']}
				
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404
		#print "pagina no encontrada"



#  LOGICA PARA COMBO DE TALLAS

def lista_Tallas(id_prov,id_temp,id_pag,id_cat,id_est,id_mar,id_col):
	
	
	
	cursor=connection.cursor()
	cursor.execute("SELECT talla from preciobase where empresano=1 and proveedorid=%s and temporada=%s and pagina=%s and catalogo=%s and estilo=%s and idmarca=%s and idcolor=%s;",[id_prov,id_temp,id_pag,id_cat,id_est,id_mar,id_col])
	listatall=() # Inicializa una tupla para llenar combo de Estilos
			
	# Convierte el diccionario en tupla
	for row in cursor:
		elemento = tuple(row)
		listatall=listatall+elemento
	listatall=('SELECCIONE...',)+listatall
	
	return (listatall)	



def combo_tallas(request,*args,**kwargs):
	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		id_temp = request.GET['id_temp']
		id_pag = request.GET['id_pag']
		id_cat = request.GET['id_cat']
		id_est = request.GET['id_est']
		id_mar = request.GET['id_mar']
		id_col = request.GET['id_col']
		
		
		# Trae la lista de tallas con los parametros indicados:
		l = lista_Tallas(id_prov,id_temp,id_pag,id_cat,id_est,id_mar,id_col)
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		data = json.dumps(l)
		#data = {'Mensaje':"El id proveedor recibido fue %s" % request.GET['id_prov']}
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404
		#print "pagina no encontrada"


# LOGICA PARA COMBO DE ALMACENES


def lista_almacenes(id_prov):
	
	cursor=connection.cursor()
	cursor.execute("SELECT almacen,razonsocial from almacen where empresano=1 and proveedorno=%s;",[id_prov,])
	
	listaalm=() # Inicializa una tupla para llenar combo de Estilos
			
	# Convierte el diccionario en tupla
	for row in cursor:
		elemento = tuple(row)
		listaalm=listaalm+elemento
	listaalm=('SELECCIONE...',)+listaalm
	
	return (listaalm)	

"""def lista_almacenes(id_prov):
		cursor=connection.cursor()
		cursor.execute("SELECT almacen,razonsocial from almacen where empresano=1 and proveedorno=%s;",[id_prov,])
		pr=() # Inicializa una tupla para llenar combo de Proveedores
		
		# Convierte el diccionario en tupla
		for row in cursor:
			elemento = tuple(row)
			pr=pr+elemento
		pr = (0L,u'Seleccione ') + pr
		

		# Inicializa dos listas para calculos intermedios
		x=[]
		y=[]	

		# Forma una lista unicamente con valores
		# significativos (nombres de proveedores y su numero)

		for i in range(0,len(pr)):
			if i % 2 != 0:
				x.append(pr[i-1])
				x.append(pr[i])
				y.append(x)
				x=[]


		# tuple_of_tuples = tuple(tuple(x) for x in list_of_lists)
		lprov = tuple(tuple(x) for x in y)

		
		
		return (lprov)"""


def combo_almacenes(request,*args,**kwargs):
	#pdb.set_trace()

	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		
		
		# Trae la lista de catalogos con los parametros indicados:
		l = lista_almacenes(id_prov)
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		data = json.dumps(l)
		#data = {'Mensaje':"El id proveedor recibido fue %s" % request.GET['id_prov']}
				
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404





def llena_combo_sucursal(request,*args,**kwargs):

	#print "Entra a llena combo sucursal"
	if request.is_ajax() and request.method == 'GET':
		#print "llena combo suc, es ajax y get"		
		lsuc = lista_Sucursales()
		#print "Las sucursales son:"
		#for j in lsuc:
		#	print j
		
		data = json.dumps(lsuc)
		
		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404
		#print "pagina no encontrada"

# Graba en tabla temporal cada articulo seleccionando

def grabar_pedidos(request):
	#pdb.set_trace()
	# Guarda la llave de la session para su posterior manipulacion.
	session_id = request.session.session_key
	socio_zapcat =  request.session['socio_zapcat']
	EsSocio = request.session['EsSocio']


	if request.is_ajax() and request.method == 'POST':

		

		id_prov = request.POST.get('id_prov')
		id_temp = request.POST.get('id_temp')
		id_pag = request.POST.get('id_pag')
		id_cat = request.POST.get('id_cat')
		id_est = request.POST.get('id_est')
		id_mar = request.POST.get('id_mar')
		id_col = request.POST.get('id_col')
		id_talla = request.POST.get('id_talla')
		id_tallaalt = request.POST.get('id_tallaalt')
		descontiunado =  request.POST.get('descontinuado')
		opcioncompra = request.POST.get('opcioncompra')
		plazoentrega = request.POST.get('plazoentrega')
		fechamaximaentrega = request.POST.get('fechamaximaentrega')
		precio_cliente = request.POST.get('precio_cliente')

		# convierte la fecha a formato adecuado para poder ser grabada en base de datos		
		if fechamaximaentrega is not None:
			f_convertida = datetime.strptime(fechamaximaentrega, "%d/%m/%Y").date()
 		else:
 			f_convertida = '1901/01/01'
		
			

		# inicializa data unicamente con la talla, esto permitira verificar 
		# con jquery que hayan ingresado un valor valido para todos los campos,
		# dado que si la talla tiene un valor distinto de blanco es porque ya 
		# el resto de los campos tiene un valor valido.
		# Si el usuario da click al boton 'elegir' y la talla es cero, el registro no 
		# se grabara, y jquery mandara el mensaje correspondiente.

		data = {'id_talla':id_talla,}

		if id_prov == '0' or  id_temp == '0':
			mensaje = "Error en proveedor o temporada !"
			
		else:
			 
			if (id_cat == 'SELECCIONE...' or id_est == 'SELECCIONE...' or id_mar == 'SELECCIONE...' or id_col == 'SELECCIONE...' or id_talla == 'SELECCIONE...'):
				data = {'id_talla':id_talla,}
				
			else:
				
				# Realiza la busqueda del codigo de producto y lo guarda 
				# tabla temporal.

				cursor = connection.cursor()
				registro_encontrado = 0

				#El select con la tabla 'articulo' 



				cursor.execute("SELECT b.codigoarticulo, b.precio,if(a.descontinuado,'1','0') as descont From preciobase b inner join articulo a  on ( b.empresano=a.empresano and b.codigoarticulo=a.codigoarticulo and b.catalogo=a.catalogo) where b.proveedorid=%s and b.temporada =%s and b.catalogo=%s and b.pagina=%s and b.estilo=%s and b.idmarca=%s and b.idcolor=%s and b.talla=%s limit 1;", [id_prov,id_temp,id_cat,id_pag,id_est,id_mar,id_col,id_talla])
				num_art = cursor.fetchone()

			
				
				
				'''cursor.execute("SELECT b.precio From preciosopcionales b where b.Empresano=1 and b.articuloid=%s and  b.proveedor=%s and b.temporada =%s and b.catalogo=%s and b.tipoprecio='Cliente' limit 1;", [num_art[0],id_prov,id_temp,id_cat,])
				precio_cliente = cursor.fetchone()'''

				#Selecciona el precio dependiendo de si se es socio o cliente:

				precio_final = num_art[1] if EsSocio else precio_cliente
	
				try:
					#pdb.set_trace()

														
					cursor.execute("INSERT INTO pedidos_pedidos_tmp (session_key,idproveedor,idproducto,catalogo,precio,temporada,tallaalt,opcioncompra,plazoentrega,fechamaximaentrega) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (session_id,id_prov,num_art[0],id_cat,precio_final,id_temp,id_tallaalt,opcioncompra,plazoentrega,f_convertida))
					
					cursor.execute("SELECT id FROM pedidos_pedidos_tmp ORDER BY id DESC LIMIT 1")
					id_rec = cursor.fetchone()
					
					# recoge el id del producto insertado y retorna nuevamente los datos recibidos
					# tanto el precio son decimales y se convierten a string para que puedan ser serializados por json.dump, de lo contrario
					# se genera un error de serializacion.

					data = {'id':id_rec[0],'id_prov':id_prov,'id_temp':id_temp,'id_cat':id_cat,'id_pag':id_pag,'id_est':id_est,'id_mar':id_mar,'id_col':id_col,'id_talla':str(id_talla),'precio': str(precio_final),'id_tallaalt':id_tallaalt,'descontinuado': num_art[2],'is_staff':request.session['is_staff'],}
					
				except Error as e:
					
					data = "Error en la ejecucion de la insercion: "
					print e		
					
				cursor.close()
			
		#pdb.set_trace()	
		return HttpResponse(json.dumps(data),content_type='application/json')

		
	else:
		raise Http404
		

# ELIMINACION DE ARTICULOS DE LA TABLA TEMPORAL DE PEDIDOS.

def eli_reg_tmp(request):

	session_id = request.session.session_key

	if request.is_ajax() and request.method =='POST':

		id_item = request.POST.get('id_art')

		cursor = connection.cursor()
		
		cursor.execute("delete from pedidos_pedidos_tmp where id = %s and session_key = %s;",[id_item,session_id])

		cursor.close()
		data = "ok"

		return HttpResponse(json.dumps(data),content_type='application/json')	



	else:

		raise Http404

def fecha_hora_conv(fecha_hoy,hora_hoy):
	# probar esta funcion porque no funciona,
	# no devuelve parametros.	

	hoy = datetime.now()
	fecha_hoy = hoy.strftime("%Y-%m-%d")
	hora_hoy = hoy.strftime("%H:%M:%S") 
	return 

def genera_documento(cursor,
	p_tipodedocumento,
	p_tipodeventa,
	p_asociado,
	p_fechacreacion,
	p_horacreacion,
	p_usuarioquecreodcto,
	p_fechaultimamodificacion,
	p_horaultimamodificacion,
	p_usuariomodifico,
	p_concepto,
	p_monto,
	p_saldo,
	p_descuentoaplicado,
	p_vtadecatalogo,
	p_cancelado,
	p_comisiones,
	p_pagoaplicadoaremisionno,
	p_lo_recibido,
	p_venta,
	p_idsucursal,
	p_bloquearnotacredito):
	#pdb.set_trace()
	# Trae el ultimo documento
	cursor.execute("SELECT nodocto from documentos WHERE empresano=1 ORDER BY nodocto DESC LIMIT 1;")
	ultimo_docto = cursor.fetchone()
	nuevo_docto = ultimo_docto[0]+1

	# Trae el ultimo documento
	cursor.execute("SELECT consecutivo from documentos WHERE empresano=1 and tipodedocumento=%s  ORDER BY consecutivo DESC LIMIT 1;",(p_tipodedocumento,))
	ultimo_consec = cursor.fetchone()
	Nuevo_consec = ultimo_consec[0]+1


	# Genera el documento.
	# Ojo: observar que el campo `UsuarioQueCreoDcto.` se coloco entre apostrofes inversos y el nombre del campo tal y como esta definido en la tabla (casesensitive) dado que si
	# se pone sin apostrofes marca error!
	cursor.execute("INSERT INTO documentos (`EmpresaNo`,`NoDocto`,`Consecutivo`,`TipoDeDocumento`,`TipoDeVenta`,`Asociado`,`FechaCreacion`,`HoraCreacion`,`UsuarioQueCreoDcto.`,`FechaUltimaModificacion`,`HoraUltimaModificacion`,`UsuarioModifico`,`Concepto`,`monto`,`saldo`,`DescuentoAplicado`,`VtaDeCatalogo`,`Cancelado`,`comisiones`,`PagoAplicadoARemisionNo`,`Lo_recibido`,`venta`,`idsucursal`,`BloquearNotaCredito`) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",(1,nuevo_docto,Nuevo_consec,p_tipodedocumento,p_tipodeventa,p_asociado,p_fechacreacion,p_horacreacion,p_usuarioquecreodcto,p_fechaultimamodificacion,p_horaultimamodificacion,p_usuariomodifico,p_concepto,float(p_monto),float(p_saldo),float(p_descuentoaplicado),p_vtadecatalogo,p_cancelado,float(p_comisiones),p_pagoaplicadoaremisionno,float(p_lo_recibido),float(p_venta),p_idsucursal,p_bloquearnotacredito,))
	return nuevo_docto


	''' ********** DOCUMENTOS ****************'''
def documentos(request):
	#pdb.set_trace()
	documentos = {}
	tipo='D'
	if request.method == 'POST':
		
		form = DocumentosForm(request.POST)
		
		if form.is_valid():

			'''documento_num = request.POST.get('documento_num').encode('latin_1')
			tipo_movimiento = request.POST.get('tipo_movimiento').encode('latin_1')
			fechainicial = request.POST.get('fechainicial').encode('latin_1')
			fechafinal = request.POST.get('fechafinal').encode('latin_1')
			socio_num = request.POST.get('socio_num').encode('latin_1')

			fechainicial = fechainicial.strftime("%Y-%m-%d")
			fechafinal = fechafinal.strftime("%Y-%m-%d")'''
			documento_num = form.cleaned_data['documento_num']
			tipo_movimiento = form.cleaned_data['tipo_movimiento']
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']
			socio_num = form.cleaned_data['socio_num']
			



			if documento_num != 0 :
				
				consulta = """SELECT d.NoDocto,
									d.TipoDeDocumento,
									d.FechaCreacion,
									d.asociado,
									CONCAT(trim(s.nombre),' ',
									trim(s.appaterno),' ',
									trim(s.apmaterno)) as nombre_socio,
									d.concepto,
									d.monto,
									d.venta,
									d.saldo,
									d.comisiones,
									d.DescuentoAplicado,
									d.Cancelado FROM documentos d
									INNER JOIN asociado s
									on d.empresano=s.empresano
									and d.asociado=s.asociadono
									WHERE d.empresano=1
									and d.nodocto =%s;"""
				parms = [documento_num]

			elif documento_num == 0 and tipo_movimiento == 'Todos':
				
				consulta = """SELECT d.NoDocto,
									d.TipoDeDocumento,
									d.FechaCreacion,
									d.asociado,
									CONCAT(trim(s.nombre),' ',
									trim(s.appaterno),' ',
									trim(s.apmaterno)) as nombre_socio,
									d.concepto,
									d.monto,
									d.venta,
									d.saldo,
									d.comisiones,
									d.DescuentoAplicado,
									d.Cancelado FROM documentos d
									INNER JOIN asociado s
									on d.empresano=s.empresano
									and d.asociado=s.asociadono
									WHERE d.empresano=1
									and d.asociado =%s and fechacreacion >= %s and fechacreacion<=%s;"""
				parms =[socio_num,fechainicial,fechafinal]
			else :
				
				consulta = """SELECT d.NoDocto,
									d.TipoDeDocumento,
									d.FechaCreacion,
									d.asociado,
									CONCAT(trim(s.nombre),' ',
									trim(s.appaterno),' ',
									trim(s.apmaterno)) as nombre_socio,
									d.concepto,
									d.monto,
									d.venta,
									d.saldo,
									d.comisiones,
									d.DescuentoAplicado,
									d.Cancelado FROM documentos d
									INNER JOIN asociado s
									on d.empresano=s.empresano
									and d.asociado=s.asociadono
									WHERE d.empresano=1
									and d.asociado =%s and fechacreacion >= %s and fechacreacion<=%s and d.TipoDeDocumento=%s;"""
				parms = [socio_num,fechainicial,fechafinal,tipo_movimiento]
			try:
				cursor = connection.cursor()
		
				cursor.execute(consulta,parms) # observar que se uso parms como parte de una lista en lugar de una tupla, si se usa una tupla marca error

				documentos = dictfetchall(cursor)

				if not documentos:
					e = "No se encontraron registros !"
				else:
					e = ''
				context = {'documentos':documentos,'mensaje':e,}
				return render (request,'pedidos/muestra_documentos.html',context)
			
			except DatabaseError as e:
				print e

			
			cursor.close()
		
	else:
		form = DocumentosForm()

	return render (request,'pedidos/documentos.html',{'form':form,'tipo':tipo})
			
		
def muestra_documentos(request):
	return HttpResponse("falta esto")

	

def procesar_pedido(request):

	#pdb.set_trace()
	global g_numero_socio_zapcat
	
	# Se asigna elnumero de socio

	socio_zapcat = request.session['socio_zapcat']

	# se asigna la sesion activa para este socio	
	session_id = request.session.session_key

	if request.is_ajax() and request.method =='POST':


		total = request.POST.get('total')

		if request.session['is_staff']:

			# Toma como socio a validar el socio que pide, no el usuaro que captura.
			# y, lsuc toma el numero de la sucursal_activa en la session.
			
			socio_a_validar = request.session['socio_pidiendo']
			#capturista = request.session['socio_zapcat'] # toma el valor del empleado que captura
			capturista =  request.POST.get('usr_id') # toma el id  de confirmacion del empleado que captura 
			tiposervicio = request.POST.get('tiposervicio')
			
			viasolicitud = request.POST.get('viasolicitud')
			viasolicitud = int(viasolicitud) #  se convierte a entero	
		
			
			usr_id = request.POST.get('usr_id')
			
			if request.POST.get('anticipo') is not None:
				anticipo = int(request.POST.get('anticipo').encode('latin_1'))
			else:
				anticipo = 0	
			
			
			
		else:
			
			# De otra manera toma como socio, el usuario que captura (socio normal).
			# luego busca el numero de sucursal usando el nombre de la sucursal seleccionada 
			
			socio_a_validar = socio_zapcat
			capturista = 99 # toma el valor de capurista en internet
			anticipo = 0
			viasolicitud = 3
			tiposervicio = request.POST.get('tiposervicio')

		
		# trae el numero de sucursal donde se recogera el pedido
		lsuc = request.POST.get('lsuc')

		cursor = connection.cursor()
		cursor.execute("SELECT SucursalNo from sucursal where nombre = %s;",[lsuc])
		sucursal_registro = cursor.fetchone()
		id_suc = sucursal_registro[0]
		cursor.close()

		
		# Inicia la transaccion
		try:
			cursor = connection.cursor()
			cursor.execute("START TRANSACTION;")


			# Se busca el ultimo pedido registrado para hacer y se le suma uno para crear el nuevo
			cursor.execute("SELECT PedidoNo from pedidosheader ORDER BY PedidoNo DESC LIMIT 1;")
			#cursor.callproc('TraeUltimoPedido',)
			
			#pdb.set_trace()
			UltimoPedido = cursor.fetchone()
			
			if UltimoPedido > 0:
				# Si la tabla tiene pedidos registrados incrementa en 1 el PedidoNuevo

				PedidoNuevo = UltimoPedido[0] + 1
			else:

				# Si la tabla esta vacia asigna el numero 1.
				PedidoNuevo = 1
				
		
			# Se convierte la fecha de hoy a formatos manejables para insertarlos en el registro.
			hoy = datetime.now()
			fecha_hoy = hoy.strftime("%Y-%m-%d")
			hora_hoy = hoy.strftime("%H:%M:%S") 
			

				
			#cursor.execute("SET @counter = 0")
			
			# Se actualiza el encabezado del pedido.
			
			cursor.execute("INSERT INTO pedidosheader (EmpresaNo,PedidoNo,FechaPedido,HoraPedido,Saldototal,VtaTotal,UsuarioCrea,FechaUltimaModificacion,FechaCreacion,HoraCreacion,HoraModicacion,UsuarioModifica,idSucursal,AsociadoNo,tiposervicio,viasolicitud) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (1,PedidoNuevo,fecha_hoy,hora_hoy,total,total,capturista,fecha_hoy,fecha_hoy,hora_hoy,hora_hoy,capturista,id_suc,socio_a_validar,tiposervicio,viasolicitud))
			
			# Si hay anticipo, genera el documento correspondiente

			if anticipo > 0:
				print "hay anticipo"	

			#	El sigiuente comentario es para ubicar los parametros con el llamado que viene despues..es solo guia.	
			#	genera_documento(p_tipodedocumento,p_tipodeventa,p_asociado,p_fechacreacion,p_horacreacion,p_usuarioquecreodcto,p_fechaultimamodificacion,p_horaultimamodificacion,p_usuariomodifico,p_concepto,p_monto,p_saldo,p_descuentoaplicado,p_vtadecatalogo,p_cancelado,p_comisiones,p_pagoaplicadoaremisionno,p_lo_recibido,p_venta,p_idsucursal,p_bloquearnotacredito):
			
				nuevo_docto = genera_documento(cursor,"Credito","Contado",socio_a_validar,fecha_hoy,hora_hoy,capturista,fecha_hoy,hora_hoy,capturista,"Anticipo a pedido Num. "+str(PedidoNuevo),anticipo,anticipo,0,False,False,0,0,0,0,id_suc,False)		
			else:
				print "No hay anticipo"
				nuevo_docto = 0

			# Determina la cantidad de registros en temporal para la session en curso.
			cursor.execute("SELECT COUNT(*) FROM pedidos_pedidos_tmp where session_key = %s;",[session_id])
			Tot_reg_tmp = cursor.fetchone()

			print "total registros tmp"
			print Tot_reg_tmp[0]

			#Selecciona registro por registro de la tabla temporal (delimitada por la sesion en curso) y actualiza el detalle del pedido.
			
			cursor.execute("SELECT idproducto,catalogo, precio,temporada,tallaalt,opcioncompra FROM pedidos_pedidos_tmp where session_key= %s;",[session_id])
			datos = namedtuplefetchall(cursor)

			count = 1
			while (count <= Tot_reg_tmp[0]):
				#print datos[count-1].idproducto
				#print datos[count-1].catalogo
				#print datos[count-1].precio
				if datos[count-1].opcioncompra == '1':
					opcioncompra = '1ra.'
				elif datos[count-1].opcioncompra == '2':
					opcioncompra = '2da.'
				else:
					opcioncompra = '3ra'

				cursor.execute("INSERT INTO pedidoslines (EmpresaNo,Pedido,ProductoNo,CantidadSolicitada,precio,subtotal,PrecioOriginal,Status,RemisionNo,NoNotaCreditoPorPedido,NoNotaCreditoPorDevolucion,NoRequisicionAProveedor,NoNotaCreditoPorDiferencia,catalogo,NoLinea,plazoentrega,OpcionCompra,FechaMaximaEntrega,FechaTentativaLLegada,FechaMaximaRecoger,Observaciones,AplicarDcto) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", [1,PedidoNuevo,datos[count-1].idproducto,1,datos[count-1].precio,datos[count-1].precio,datos[count-1].precio,'Por Confirmar',0,nuevo_docto,0,0,0,datos[count-1].catalogo,count,2,opcioncompra,'19010101','19010101','19010101',datos[count-1].tallaalt,0])
				cursor.execute("INSERT INTO pedidoslinestemporada (EmpresaNo,Pedido,ProductoNo,catalogo,NoLinea,Temporada) VALUES(%s,%s,%s,%s,%s,%s)",[1,PedidoNuevo,datos[count-1].idproducto,datos[count-1].catalogo,count,datos[count-1].temporada])
				cursor.execute("INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,ProductoNo,Status,catalogo,NoLinea,FechaMvto,HoraMvto,Usuario) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",[1,PedidoNuevo,datos[count-1].idproducto,'Por Confirmar',datos[count-1].catalogo,count,fecha_hoy,hora_hoy,capturista])
				cursor.execute("INSERT INTO pedidos_encontrados(EmpresaNo,Pedido,ProductoNo,Catalogo,NoLinea,FechaEncontrado,BodegaEncontro,FechaProbable,`2`,`3`,`4`,`5`,`6`,`7`,`8`,`9`,`10`,encontrado,id_cierre,causadevprov,observaciones) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",[1,PedidoNuevo,datos[count-1].idproducto,datos[count-1].catalogo,count,'19010101',0,'19010101','','','','','','','','','','',0,0,''])
				cursor.execute("INSERT INTO pedidos_notas(EmpresaNo,Pedido,ProductoNo,Catalogo,NoLinea,Observaciones) VALUES (%s,%s,%s,%s,%s,%s)",[1,PedidoNuevo,datos[count-1].idproducto,datos[count-1].catalogo,count,''])
				
				count = count + 1


			
			cursor.execute("DELETE FROM pedidos_pedidos_tmp where session_key= %s;",[session_id])	
			
			# Graba cambios.
			cursor.execute("COMMIT;")
			status_operacion = 'ok'

		# Si hay error en base de datos hace rollback:	
		except DatabaseError as e:
			print "el error de base de datos es ",e
			status_operacion = 'fail'
			cursor.execute("ROLLBACK;")

		cursor.close()

		#imprime_ticket(request,PedidoNuevo)
	
		data = {'PedidoNuevo':PedidoNuevo,'status_operacion':status_operacion,}
		return HttpResponse(json.dumps(data),content_type='application/json',)	




	else:

		raise Http404


def verifica_socio(request):


	session_id = request.session.session_key

	if request.is_ajax() and request.method =='POST':

		num_socio = request.POST.get('NoSocio')

		cursor = connection.cursor()
		
		cursor.execute("SELECT nombre,appaterno,apmaterno from Asociado where asociadono=%s;"[num_socio])

		asociado_data = cursor.fetchone()

		cursor.close()
		data = "ok"

		return HttpResponse(json.dumps(data),content_type='application/json')	



	else:

		

		raise Http404


''' La siguiente variable de numero de socio es global y se actualiza en "busca_socio"  para
	despues ser utilizada en la rutina "registra_socio" '''

global_numero_socio_zapcat = 0


@permission_required('auth.add_user',login_url=None,raise_exception=True)
def busca_socio(request):
    # if this is a POST request we need to process the form data
	global global_numero_socio_zapcat
	if request.method == 'POST':
        # create a form instance and populate it with data from the request:
		form = RegsocwebForm(request.POST)
        # check whether it's valid:
		if form.is_valid():

			socio_a_dar_de_alta = request.POST.get('numero')
			request.session['socio_a_dar_de_alta'] = socio_a_dar_de_alta

			cursor = connection.cursor()
		
			cursor.execute("SELECT asociadono,nombre,appaterno,apmaterno,num_web from asociado where asociadono=%s;",[socio_a_dar_de_alta])

			socio_datos = dictfetchall(cursor)
			for r in socio_datos:
				num_web_data = r['num_web']

			if not socio_datos:
					mensaje = 'El número de socio proporcionado no fué encontrado, intente nuevamente !'
					return render(request,'pedidos/error_en_socio.html', {'mensaje':mensaje})
			else:

				if num_web_data != 0:
					mensaje = "Este socio ya está registrado en el sitio Web con el número "+str(num_web_data)+"."
					return render(request,'pedidos/error_en_socio.html',{'mensaje':mensaje})
				# Ojo con la siguite linea, Para que ?	
				global_numero_socio_zapcat = socio_a_dar_de_alta 

				mensaje ='Tenemos a '
				context = {'socio_datos':socio_datos,'mensaje':mensaje}
				return render(request,'pedidos/socio_encontrado.html',context)



			cursor.close()

	else:
		form = RegsocwebForm()

	return render(request,'pedidos/busca_socio.html',{'form':form})


def registro_socio(request):
	
	socio_a_dar_de_alta = request.session['socio_a_dar_de_alta']
	is_staff =  request.session['is_staff']
	if request.method == 'POST':
		form = Forma_RegistroForm(request.POST)
		
		if form.is_valid():
			new_user = form.save()
			nombre_usuario_Web = new_user.username

			''' Graba en la tabla de asociado el id que le correspondio en la Web'''
			cursor = connection.cursor()
			cursor.execute("UPDATE asociado SET num_web = %s where asociadono = %s;",[new_user.id,socio_a_dar_de_alta])
			cursor.close()
			
			para = [request.POST.get('email')]

			email_host_user = getattr(settings, "EMAIL_HOST_USER", None)

			mensaje = """Estimado socio:

			 Ha sido habilitado para usar el sistema de Pedidos por Internet, su usuario es """ + nombre_usuario_Web.encode('utf-8') + """ . Por favor ingrese al sistema
			 con este usuario y la contraseña que eligió y cámbiela para mayor seguridad.

			 De ahora en adelante puede Ud. consultar sus pedidos y realizar nuevos pedidos desde su computadora o celular.

			 
			 Podrá ingresar al sistema en http://www.esshoesmultimarcas.com/pedidos/index/

			 Atentamente.
			 ES Shoes Multimarcas. """
			
			envia_mail(para,email_host_user,'Su registro en ES Shoes mulitimarcas WEB',mensaje)			  

			request.session['socio_a_dar_de_alta']=0

			return render(request,'pedidos/registro_exitoso.html',{'nombre_usuario_Web':nombre_usuario_Web,'is_staff':is_staff})
	else:
		form = Forma_RegistroForm()
	return render(request,'pedidos/registration_form.html',{'form':form,'is_staff':is_staff,})

@login_required
def cambiar_password(request):
    form = PasswordChangeForm(user=request.user)
    nombre_usuario_Web = request.user

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return render(request,'pedidos/cambio_password_exitoso.html',{'nombre_usuario_Web':nombre_usuario_Web,})

    return render(request, 'pedidos/cambio_password_form.html', {
        'form': form,
    })

def envia_mail(v_para,v_de,v_asunto,v_mensaje):
				
	send_mail(v_asunto,v_mensaje,'atencion.clientes@multimarcaslaredo.com',v_para,fail_silently=False,)

	return


#@permission_required('auth.add_user',login_url=None,raise_exception=True)
def empleados(request):

	return render(request,'pedidos/empleados.html')

@login_required
def entrada_sistema(request):
	
	if request.session['is_staff']:

		if request.method == 'POST':


			form = Entrada_sistemaForm(request.POST)
			
			if form.is_valid():
			
				sucursal = form.cleaned_data['sucursal']
			
				# Con la siguientes linea guarda el numero de sucursal  y su nombre en el framework de sesiones 
				# para poder utilizarlos en otros procesos.

				request.session['sucursal_activa'] = sucursal 

				# Se trae el nombre de la sucursal
				cursor=connection.cursor()
				cursor.execute('SELECT SucursalNo,nombre,direccion,colonia,ciudad,estado,pais,telefono1 from sucursal where Sucursalno=%s',(sucursal))
				nombresuc = cursor.fetchone()
				
				request.session['sucursal_nombre']= nombresuc[1]
				request.session['sucursal_direccion']= nombresuc[2]
				request.session['sucursal_colonia']= nombresuc[3]
				request.session['sucursal_ciudad']= nombresuc[4]
				request.session['sucursal_estado']= nombresuc[5]
				request.session['sucursal_telefono']= nombresuc[7]

				return render(request,'pedidos/consulta_menu.html',{'is_staff':request.user.is_staff,})
			else:
				return render(request,'pedidos/entrada_sistema.html',{'form':form,'is_staff':request.session['is_staff'],})
	
		else:
			form=Entrada_sistemaForm()
	
	else:
		return redirect('pedidos:busca_pedidos')

	return render(request,'pedidos/entrada_sistema.html',{'form':form,'is_staff':request.session['is_staff'],})

def consulta_menu(request):

	return render(request,'pedidos/consulta_menu.html')

def con_calzado_que_llego_global(request):
	return render(request,'pedidos/404.html')

def con_calzado_que_llego_detallado(request):
	return render(request,'pedidos/404.html')

def con_colocaciones(request):
	return render(request,'pedidos/404.html')
def con_confirmaciones(request):
	return HttpResponse('Opcion en desarrollo...')


def con_pedidos_por_socio_status(request):

	'''try:
	
		g_numero_socio_zapcat = request.session['socio_zapcat']	
	except KeyError :

		return	HttpResponse("Ocurrió un error de conexión con el servidor, Por favor salgase completamente y vuelva a entrar a la página !")

	if request.user.is_authenticated():'''		
		
	if request.method == 'POST':
		form = BuscapedidosporsocioForm(request.POST)
		'''
		Si la forma es valida se normalizan los campos numpedido, status y fecha,
		de otra manera se envia la forma con su contenido erroreo para que el validador
		de errores muestre los mansajes correspondientes '''

		if form.is_valid():
		
			# limpia datos 
			socio = form.cleaned_data['socio']
			numpedido = form.cleaned_data['numpedido']
			status = form.cleaned_data['status']
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']

			
			# Convierte el string '1901-01-01' a una fecha valida en python
			# para ser comparada con la fecha ingresada 

			fecha_1901 =datetime.strptime('1901-01-01', '%Y-%m-%d').date()
			hoy = date.today()


			# Establece conexion con la base de datos
			cursor=connection.cursor()

		
			# Comienza a hacer selects en base a criterios 


			if numpedido != 0:
				cursor.execute("SELECT l.s,l.productono,l.catalogo,l.precio,l.status,h.asociadono,psf.fechamvto,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) inner join pedidos_status_fechas psf on (psf.empresano=l.empresano and psf.pedido=l.pedido and psf.productono=l.productono and psf.catalogo=l.catalogo and psf.nolinea=l.nolinea and psf.status=l.status) where h.pedidono=%s;",[numpedido])
				socio = 0 # Si acaso el usuario asigno un numero de socio,  este se hace cero para mas delante 
						  # asignar el socio que  nos arroja la consulta por pedido. 
			else :

				if  status == 'Todos':
					cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,h.asociadono,psf.fechamvto,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) inner join pedidos_status_fechas psf on (psf.empresano=l.empresano and psf.pedido=l.pedido and psf.productono=l.productono and psf.catalogo=l.catalogo and psf.nolinea=l.nolinea and psf.status=l.status) where h.asociadono=%s and psf.fechamvto>=%s and psf.fechamvto<=%s ORDER BY h.pedidono DESC;", (socio,fechainicial,fechafinal))
					print "Entro en status=Todos y fecha != 19010101"
				else:
					if status !='Todos':
						cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,h.asociadono,psf.fechamvto,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo)  inner join pedidos_status_fechas psf on (psf.empresano=l.empresano and psf.pedido=l.pedido and psf.productono=l.productono and psf.catalogo=l.catalogo and psf.nolinea=l.nolinea and psf.status=l.status) where h.asociadono=%s and l.status=%s and psf.fechamvto>=%s and psf.fechamvto<=%s ORDER BY h.pedidono DESC;", (socio,status,fechainicial,fechafinal))
						print "Entro en status != Todos y fecha=1901/01/01"
					else:
 						if status != 'Todos':
							cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,h.asociadono,psf.fechamvto,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.Observaciones from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) inner join pedidos_status_fechas psf on (psf.empresano=l.empresano and psf.pedido=l.pedido and psf.productono=l.productono and psf.catalogo=l.catalogo and psf.nolinea=l.nolinea and psf.status=l.status) where h.asociadono=%s and l.status=%s and psf.fechamvto>=%s and psf.fechamvto<=%s ORDER BY h.pedidono DESC;", (socio,status,fechainicial,fechafinal))			
							print "Entro en status != Todos y fecha != 1901/01/01"
						else:
							mensaje ='No se encontraron registros !'
			
			# El contenido del cursor se convierte a diccionario para poder
			# ser enviado como parte del contexto y sea manipulable.				
			pedidos = dictfetchall(cursor)
			for pedido in pedidos:
				print "ASI ESTAN LOS ELEMENTOS DEL DICCIONARIO PEDIDOS:"
				print pedido

			elementos = len(pedidos)

			if socio == 0:
				socio =pedido['asociadono']


				# Comienza por seleccionar el nombre del socio
			cursor.execute("SELECT a.appaterno, a.apmaterno,a.nombre from asociado a where a.asociadono=%s;",[socio])
			
			nombre_socio = cursor.fetchone()

			

			if not pedidos or not socio:# or not nombre_socio[0]:
				mensaje = 'No se encontraron registros !'
				
				return render(request,'pedidos/lista_pedidos_socio_status.html',{'form':form,'mensaje':mensaje,})
			else:
				mensaje ='Registros encontrados:'
				context = {'pedidos':pedidos,'mensaje':mensaje,'elementos':elementos,'socio':socio,'socio_appaterno':nombre_socio[0],'socio_apmaterno':nombre_socio[1],'socio_nombre':nombre_socio[2],}
			

			

			# Cierra la conexion a la base de datos
			cursor.close()
			
			return render(request,'pedidos/lista_pedidos_socio_status.html',context)
		
	else:
		form = BuscapedidosporsocioForm()
		#cursor.close()
		
	return render(request,'pedidos/con_pedidos_por_socio_status.html',{'form':form,})
	'''else:
		redirect('/pedidos/acceso/')''' 


def existe_socio(request):


	if request.is_ajax() and request.method =='POST':
		id_socio = request.POST.get('id_socio')
		cursor = connection.cursor()

		cursor.execute("SELECT nombre,appaterno,apmaterno from asociado where asociadono=%s;",[id_socio])
		asociado_data = cursor.fetchone()
		cursor.close()
		
		if asociado_data is None:
			data = "NO"
		else:
			data = "SI"

		return HttpResponse(json.dumps(data),content_type='application/json')

def trae_nombre_socio(request):


	if request.is_ajax() and request.method =='POST':
		id_socio = request.POST.get('id_socio')
		cursor = connection.cursor()

		cursor.execute("SELECT nombre,appaterno,apmaterno from asociado where asociadono=%s;",[id_socio])
		asociado_data = cursor.fetchone()
		cursor.close()
		
		if asociado_data is None:
			data = "Socio inexistente !"
		else:
			data = asociado_data[0]+' '+ asociado_data[1]+' '+asociado_data[2]

		return HttpResponse(json.dumps(data),content_type='application/json')		



	else:

		

		raise Http404


def picklist_socio(request):	
	string_a_buscar = request.GET.get('string_a_buscar',None)
	
	if request.is_ajax() and request.method == 'GET':
		
		valor ="'%"+string_a_buscar.strip()+"%'"

		id_a_buscar='0'	
		
		if string_a_buscar.isdigit(): # verifica si la cadena a buscar es un digito, de ser asi, usara esa cadana para buscar por id.

			id_a_buscar = string_a_buscar
		

		cursor=connection.cursor()
		
		
		cursor.execute("SELECT o.AsociadoNo,o.ApPaterno,o.ApMaterno,o.Nombre from asociado o WHERE o.AsociadoNo="+id_a_buscar+" or trim(o.Nombre) like "+valor+" or o.ApPaterno like "+valor+" or o.ApMaterno like "+valor+";")
		l = dictfetchall(cursor)
		
		
		data= json.dumps(l)

		
		cursor.close()
				
		return HttpResponse(data,content_type='application/json')


def picklist_estilopagina(request):

	#pdb.set_trace()
	
	string_a_buscar = request.GET.get('estilo_a_buscar',None)
	proveedor = request.GET.get('proveedor',None)
	temporada = request.GET.get('temporada',None)
	catalogo = request.GET.get('catalogo',None)
	
	if request.is_ajax() and request.method == 'GET':
		
		valor =string_a_buscar.strip()
		
		try:

			cursor=connection.cursor()
			
			
			cursor.execute("SELECT a.estilo,a.pagina,max(a.precio) as precio from preciobase a WHERE a.empresano=1 and a.proveedorid=%s and a.temporada=%s  and a.catalogo=%s and  a.Estilo=%s group by a.estilo,a.pagina;",(proveedor,temporada,catalogo,valor,))
			l = dictfetchall(cursor)
			
			
			data= json.dumps(l,cls=DjangoJSONEncoder)

			
			cursor.close()
		except DatabaseError as d:

			print d
			data={'Error':'Error al acceder a base de datos...'}
					
		return HttpResponse(data,content_type='application/json')





def calzadollego_gral(request):

	mensaje =''
	if request.method == 'POST':

		form = Calzadollego_gralForm(request.POST)

		if form.is_valid():

			
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']

			cursor=connection.cursor()

			
			cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,psf.fechatentativallegada AS FTL,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia,k.razonsocial as provnombre FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre)  left join  pedidoslines psf on (p.empresano=psf.empresaNo and p.pedido=psf.pedido and p.productono=psf.productono and p.catalogo=psf.catalogo and p.nolinea=psf.nolinea) inner join proveedor k on (k.proveedorno=c.prov_id and k.empresano=1) left join almacen j on (j.proveedorno=c.prov_id and j.empresano=1 ) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by c.id,psf.fechatentativallegada;",(fechainicial,fechafinal))

			'''cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia,k.razonsocial as provnombre FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre) inner join proveedor k on (k.proveedorno=c.prov_id and k.empresano=1) inner join almacen j on (j.proveedorno=c.prov_id and j.empresano=1) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by psf.fechatentativallegada;",(fechainicial,fechafinal))'''

			pedidos = dictfetchall(cursor)
			
			elementos = len(pedidos)

			


			"""cursor.execute("SELECT p.razonsocial,a.razonsocial from proveedor p inner join almacen a on (p.empresano=a.empresano and p.proveedorno=a.proveedorno) where p.proveedorno=%s;",(ped['prov_id'],))
			
			prov_alm = cursor.fetchone()"""

			if not pedidos:
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_calzadollego_gral.html',{'mensaje':mensaje,})

			else:
				print "lo que hay en pedidos"
				for ped in pedidos:
					print ped
				prov_a_buscar = ped["prov_id"]

				print "proveedor buscado"
				print prov_a_buscar
				mensaje ="Registros encontrados == > "

				context = {'form':form,'mensaje':mensaje,'pedidos':pedidos,'elementos':elementos,}	
			
				return render(request,'pedidos/lista_calzadollego_gral.html',context)

		
	else:

		form = Calzadollego_gralForm()
	return render(request,'pedidos/calzadollego_gral.html',{'form':form,})


	
def calzadoquellego_detalle(request):

	mensaje =''
	if request.method == 'GET':

		

		form = Calzadollego_detalleForm(request.GET)

		if form.is_valid():

			
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']
			op = form.cleaned_data['op']

			cursor=connection.cursor()

			
			"""cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,psf.fechatentativallegada,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre)  left join  pedidoslines psf on (p.empresano=psf.empresaNo and p.pedido=psf.pedido and p.productono=psf.productono and p.catalogo=psf.catalogo and p.nolinea=psf.nolinea) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by c.id,psf.fechatentativallegada;",(fechainicial,fechafinal))"""


			cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.Nolinea,e.BodegaEncontro,e.encontrado,p.fechapedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,if(a.talla='NE',l.observaciones,a.talla) as talla,l.precio,a.idProveedor,e.observaciones,p.idSucursal,e.id_cierre,l.observaciones,pro.razonsocial as provnom,concat(trim(aso.nombre),' ',trim(aso.appaterno),' ',trim(aso.apmaterno)) as nombre,suc.nombre as sucnom,alm.razonsocial as almnom FROM pedidoslines l INNER JOIN   pedidosheader p ON (l.EmpresaNo= p.EmpresaNo and l.Pedido=p.PedidoNo) INNER JOIN articulo a ON (l.EmpresaNo=a.EmpresaNo and l.ProductoNo=a.codigoarticulo and l.Catalogo=a.catalogo)  INNER JOIN pedidos_encontrados e on (l.EmpresaNo=e.empresaNo and l.pedido=e.pedido and e.productono=l.productono and l.catalogo=e.catalogo and e.nolinea=l.nolinea) inner join proveedor pro on (pro.empresano=1 and pro.proveedorno=a.idproveedor) inner join asociado aso on (aso.empresano=1 and aso.asociadono=p.asociadono) inner join sucursal suc on (suc.empresano=1 and suc.sucursalno=p.idsucursal) inner join almacen alm on (alm.empresano=1 and alm.proveedorno=a.idproveedor and e.BodegaEncontro=alm.Almacen) WHERE  l.fechatentativallegada>=%s and l.fechatentativallegada<=%s and e.id_cierre<>0 order by e.id_cierre;",(fechainicial,fechafinal))

			 
			lista_pedidos = dictfetchall(cursor)

			

			elementos = len(lista_pedidos)

			


			"""cursor.execute("SELECT p.razonsocial,a.razonsocial from proveedor p inner join almacen a on (p.empresano=a.empresano and p.proveedorno=a.proveedorno) where p.proveedorno=%s;",(ped['prov_id'],))
			
			prov_alm = cursor.fetchone()"""

			if not lista_pedidos:
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_calzadollego_detalle.html',{'mensaje':mensaje,})

			else:

				if op == 'Pantalla':

					print "lo que hay en pedidos"
					for ped in lista_pedidos:
						print ped

					
					mensaje ="Registros encontrados == > "

					context = {'form':form,'mensaje':mensaje,'elementos':elementos,'lista_pedidos':lista_pedidos,}	
				
					return render(request,'pedidos/lista_calzadollego_detalle.html',context)
				else:

					response = HttpResponse(content_type='text/csv')
					response['Content-Disposition'] = 'attachment; filename="calzadollego_detalle.csv"'

					writer = csv.writer(response)
					writer.writerow(['ID_CIERRE','PEDIDO','FECHA_PEDIDO','PROVEEDOR','MARCA','ESTILO','COLOR','TALLA','PRECIO','SUCURSAL','BODEGA','SOCIO_NUM','SOCIO_NOMBRE'])
					
					for registro in lista_pedidos:
						print registro
						# El registro contiene los elementos a exportar pero no en el orden que se necesita para eso se define la siguiente lista con las llaves en el orden que se desea se exporten	
						llaves_a_mostrar = ['id_cierre','Pedido','fechapedido','provnom','idmarca','idestilo','idcolor','talla','precio','sucnom','almnom','AsociadoNo','nombre'] 
						# Con la siguiente linea se pasan los elementos del diccionario 'registro' a 'lista' de acuerdo al orden mostrado en 'llaves_a_mostrar'
						lista = [registro[x] for x in llaves_a_mostrar]					
						writer.writerow(lista)
					cursor.close()
					return response			















		
	else:

		form = Calzadollego_detalleForm()
	return render(request,'pedidos/calzadollego_detalle.html',{'form':form,})



	return



def consultacolocaciones(request):

	mensaje =''
	if request.method == 'POST':

		form = Consulta_colocacionesForm(request.POST)

		if form.is_valid():

			proveedor = form.cleaned_data['proveedor']
			tipoconsulta = form.cleaned_data['tipoconsulta']
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']

			cursor=connection.cursor()

			
			"""cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,psf.fechatentativallegada,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre)  left join  pedidoslines psf on (p.empresano=psf.empresaNo and p.pedido=psf.pedido and p.productono=psf.productono and p.catalogo=psf.catalogo and p.nolinea=psf.nolinea) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by c.id,psf.fechatentativallegada;",(fechainicial,fechafinal))"""

			if tipoconsulta == '1':
				print "Entro a consulta opcion 1"
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal, l.Observaciones FROM pedidos_encontrados e INNER JOIN pedidoslines l on ( e.EmpresaNo=l.empresano and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p  ON (p.EmpresaNo=l.empresano and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (p.EmpresaNo=e.empresano and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo and a.idProveedor=%s and a.empresano=1) WHERE e.empresano=1 and  e.id_cierre=0 and (e.encontrado='' or  e.encontrado='P')  and  p.FechaPedido>=%s and p.FechaPedido<=%s  and l.Status='Por Confirmar';",(proveedor,fechainicial,fechafinal))
			else:
				print "Entro a consulta opcion 2"
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal, l.Observaciones FROM pedidos_encontrados e INNER JOIN pedidoslines l on ( e.EmpresaNo=l.empresano and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p  ON (p.EmpresaNo=l.empresano and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (p.EmpresaNo=e.empresano and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo and a.idProveedor=%s and a.empresano=1) WHERE e.empresano=1 and  p.FechaPedido>=%s and p.FechaPedido<=%s  and l.Status='Por Confirmar';",(proveedor,fechainicial,fechafinal))

			pedidos = dictfetchall(cursor)

			elementos = len(pedidos)

			


			"""cursor.execute("SELECT p.razonsocial,a.razonsocial from proveedor p inner join almacen a on (p.empresano=a.empresano and p.proveedorno=a.proveedorno) where p.proveedorno=%s;",(ped['prov_id'],))
			
			prov_alm = cursor.fetchone()"""

			if not pedidos:
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_colocaciones.html',{'mensaje':mensaje,'tipoconsulta':tipoconsulta,})

			else:

				
				for ped in pedidos:
					print ped
				
				
				mensaje ="Registros encontrados == > "

				context = {'form':form,'mensaje':mensaje,'pedidos':pedidos,'elementos':elementos,'tipoconsulta':tipoconsulta,}	
			
				return render(request,'pedidos/lista_colocaciones.html',context)

		
	else:

		form = Consulta_colocacionesForm()
	return render(request,'pedidos/consultacolocaciones.html',{'form':form,})


def consultaventas(request):


	#pdb.set_trace()
	''' Inicializa Variables '''

	VentaCalzado = 0.0
	TotalVtaBruta = 0.0
	TotalCargos = 0.0
	TotalCreditos = 0.0
	TotalDescuentos = 0.0
	TotalRegistros = 0.0
	TotalVtaCatalogos = 0.0
	TotalVtaNeta = 0.0



	mensaje =''
	if request.method == 'POST':

		form = Consulta_ventasForm(request.POST)

		if form.is_valid():

			sucursal = form.cleaned_data['sucursal']
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']

			cursor=connection.cursor()

			if sucursal == '0':
				sucursalinicial =1
				sucursalfinal = 9999
				sucursal_nombre ='GENERAL'
			else:
				sucursalinicial =  sucursal
				sucursalfinal =  sucursal
				cursor.execute("SELECT nombre from sucursal WHERE EmpresaNo=1 and SucursalNo=%s;",(sucursal))
				sucursalencontrada = cursor.fetchone()
				sucursal_nombre = sucursalencontrada[0]


			

			
			"""cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,psf.fechatentativallegada,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre)  left join  pedidoslines psf on (p.empresano=psf.empresaNo and p.pedido=psf.pedido and p.productono=psf.productono and p.catalogo=psf.catalogo and p.nolinea=psf.nolinea) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by c.id,psf.fechatentativallegada;",(fechainicial,fechafinal))"""

			
			#cursor.execute("SELECT d.EmpresaNo,d.Consecutivo,d.NoDocto,d.TipoDeDocumento,d.TipoDeVenta,d.Asociado,d.FechaCreacion,d.Concepto,d.Monto,d.Saldo,d.VtaDeCatalogo,d.Cancelado,d.comisiones,d.idsucursal,d.venta,d.descuentoaplicado,a.AsociadoNo,a.Nombre,a.ApPaterno,a.ApMaterno,s.SucursalNo,s.nombre as suc_nom, if(d.venta + d.comisiones > d.Saldo,d.venta+d.comisiones-d.Saldo-d.descuentoaplicado,0) as VtaComisionSaldo FROM documentos d INNER  JOIN  asociado a on ( d.EmpresaNo=a.EmpresaNo and d.Asociado=a.AsociadoNo) INNER JOIN  sucursal s ON (d.EmpresaNo= s.EmpresaNo and d.idsucursal=s.SucursalNo) WHERE d.EmpresaNo=1 and  d.TipoDeDocumento='Remision' and not(d.Cancelado) and d.TipoDeVenta='Contado' and d.FechaCreacion>=%s and d.FechaCreacion<=%s and d.idsucursal>=%s  and d.idsucursal<=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal))
			cursor.execute("SELECT d.EmpresaNo,d.Consecutivo,d.NoDocto,d.TipoDeDocumento,d.TipoDeVenta,d.Asociado,d.FechaCreacion,d.Concepto,d.Monto,d.Saldo,d.VtaDeCatalogo,d.Cancelado,d.comisiones,d.idsucursal,d.venta,d.descuentoaplicado,a.AsociadoNo,a.Nombre,a.ApPaterno,a.ApMaterno,s.SucursalNo,s.nombre as suc_nom, if(d.venta + d.comisiones-d.descuentoaplicado <= d.Saldo,0,d.venta+d.comisiones-d.Saldo-d.descuentoaplicado) as VtaComisionSaldo,if(d.venta + d.comisiones - d.descuentoaplicado <= d.Saldo,d.venta+d.comisiones-d.descuentoaplicado,d.Saldo) as cred_aplicado FROM documentos d INNER  JOIN  asociado a on ( d.EmpresaNo=a.EmpresaNo and d.Asociado=a.AsociadoNo) INNER JOIN  sucursal s ON (d.EmpresaNo= s.EmpresaNo and d.idsucursal=s.SucursalNo) WHERE d.EmpresaNo=1 and  d.TipoDeDocumento='Remision' and not(d.Cancelado) and d.TipoDeVenta='Contado' and d.FechaCreacion>=%s and d.FechaCreacion<=%s and d.idsucursal>=%s  and d.idsucursal<=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal))
			
			

			registros_venta = dictfetchall(cursor)

			elementos = len(registros_venta)

			


			"""cursor.execute("SELECT p.razonsocial,a.razonsocial from proveedor p inner join almacen a on (p.empresano=a.empresano and p.proveedorno=a.proveedorno) where p.proveedorno=%s;",(ped['prov_id'],))
			
			prov_alm = cursor.fetchone()"""

			if not registros_venta:
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_ventas.html',{'mensaje':mensaje,})

			else:

				
				for docto in registros_venta:
										
					if (docto['Cancelado'] == '\x00'):  # pregunta si cancelado es '0' en hex o bien falso
						tipodedocumento = docto['TipoDeDocumento']
						TotalVtaBruta = TotalVtaBruta + float(docto['venta'])
						esvta =docto['Concepto'].strip()
						vtadecatalogo = docto['VtaDeCatalogo']

						# calcula para ventas normales y ventas de catalogo
						if esvta == 'Venta' or vtadecatalogo =='\x01':

						#if tipodedocumento == 'Remision':

							#Excluye las ventas de catalogo para totales de creditos cargos y descuento
							if vtadecatalogo =='\x00':
								TotalCreditos = TotalCreditos + float(docto['cred_aplicado'])															
								TotalCargos = TotalCargos + float(docto['comisiones'])	
								TotalDescuentos =  TotalDescuentos + float(docto['descuentoaplicado'])	
								VentaCalzado = VentaCalzado + float(docto['venta'])
							print float(docto['venta']),float(docto['comisiones']),float(docto['cred_aplicado'])
							print "acumulados:"
							print TotalVtaBruta,TotalCargos,TotalCreditos

						if (TotalVtaBruta + TotalCargos > TotalCreditos):
							print "entro por vtabruta+cargos > creditos"

							TotalVtaNeta = TotalVtaBruta-TotalCreditos+TotalCargos-TotalDescuentos
						else:
							print "entro por el otro lado"
							TotalVtaNeta = 0;

						if vtadecatalogo == '\x01' :
							TotalVtaCatalogos = TotalVtaCatalogos + float(docto['Monto'])
						TotalRegistros = TotalRegistros + 1
						TotalVtaProductos = TotalVtaBruta - TotalVtaCatalogos -TotalDescuentos
				
				mensaje ="Registros encontrados == > "



				context = {'form':form,'mensaje':mensaje,'registros_venta':registros_venta,'TotalRegistros':TotalRegistros,'sucursal_nombre':sucursal_nombre,'TotalCreditos':TotalCreditos,'TotalCargos':TotalCargos,'TotalDescuentos':TotalDescuentos,'VentaCalzado':VentaCalzado,'TotalVtaCatalogos':TotalVtaCatalogos,'TotalVtaBruta':TotalVtaBruta,'TotalVtaNeta':TotalVtaNeta,'TotalVtaProductos':TotalVtaProductos}	
			
				return render(request,'pedidos/lista_ventas.html',context)

		
	else:

		form = Consulta_ventasForm()
	return render(request,'pedidos/consultaventas.html',{'form':form,})



def consultacomisiones(request):
	''' Inicializa Variables '''

	VentaCalzado = 0.0
	TotalVtaBruta = 0.0
	TotalCargos = 0.0
	TotalCreditos = 0.0
	TotalDescuentos = 0.0
	TotalRegistros = 0.0
	TotalVtaCatalogos = 0.0
	TotalVtaNeta = 0.0



	mensaje =''
	if request.method == 'POST':

		form = Consulta_comisionesForm(request.POST)

		if form.is_valid():

			sucursal = form.cleaned_data['sucursal']
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']

			cursor=connection.cursor()

			if sucursal == '0':
				sucursalinicial =1
				sucursalfinal = 9999
				sucursal_nombre ='GENERAL'
			else:
				sucursalinicial =  sucursal
				sucursalfinal =  sucursal
				cursor.execute("SELECT nombre from sucursal WHERE EmpresaNo=1 and SucursalNo=%s;",(sucursal))
				sucursalencontrada = cursor.fetchone()
				sucursal_nombre = sucursalencontrada[0]

			
			"""cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,psf.fechatentativallegada,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre)  left join  pedidoslines psf on (p.empresano=psf.empresaNo and p.pedido=psf.pedido and p.productono=psf.productono and p.catalogo=psf.catalogo and p.nolinea=psf.nolinea) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by c.id,psf.fechatentativallegada;",(fechainicial,fechafinal))"""

			
			cursor.execute("SELECT d.EmpresaNo,d.Consecutivo,d.NoDocto,d.TipoDeDocumento,d.TipoDeVenta,d.Asociado,d.FechaCreacion,d.Concepto,d.Monto,d.Saldo,d.VtaDeCatalogo,d.Cancelado,d.comisiones,d.idsucursal,d.venta,d.descuentoaplicado,a.AsociadoNo,a.Nombre,a.ApPaterno,a.ApMaterno,s.SucursalNo,s.nombre as suc_nom, if(d.venta + d.comisiones > d.Saldo,d.venta+d.comisiones-d.Saldo-d.descuentoaplicado,0) as VtaComisionSaldo FROM documentos d INNER  JOIN  asociado a on ( d.EmpresaNo=a.EmpresaNo and d.Asociado=a.AsociadoNo) INNER JOIN  sucursal s ON (d.EmpresaNo= s.EmpresaNo and d.idsucursal=s.SucursalNo) WHERE d.EmpresaNo=1 and  d.TipoDeDocumento='Cargo' and not(d.Cancelado) and d.FechaUltimaModificacion>=%s and d.FechaUltimaModificacion<=%s and d.idsucursal>=%s  and d.idsucursal<=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal))
			
			

			registros_comisiones = dictfetchall(cursor)

			
			elementos = len(registros_comisiones)

			


			"""cursor.execute("SELECT p.razonsocial,a.razonsocial from proveedor p inner join almacen a on (p.empresano=a.empresano and p.proveedorno=a.proveedorno) where p.proveedorno=%s;",(ped['prov_id'],))
			
			prov_alm = cursor.fetchone()"""

			if not registros_comisiones:
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_comisiones.html',{'mensaje':mensaje,})

			else:

				
				for docto in registros_comisiones:
										
					if (docto['Cancelado'] == '\x00'):  # pregunta si cancelado es '0' en hex o bien falso
						
						TotalVtaBruta = TotalVtaBruta + float(docto['Monto'])
						TotalRegistros = TotalRegistros + 1
						
						mensaje ="Registros encontrados == > "


				
				context = {'form':form,'mensaje':mensaje,'registros_comisiones':registros_comisiones,'TotalRegistros':int(TotalRegistros),'sucursal_nombre':sucursal_nombre,'TotalVtaBruta':TotalVtaBruta,}	
			
				return render(request,'pedidos/lista_comisiones.html',context)

		
	else:

		form = Consulta_comisionesForm()

	return render(request,'pedidos/consultacomisiones.html',{'form':form,})


def buscapedidosposfecha(request):

	mensaje =''
	if request.method == 'GET':

		

		form = BuscapedidosposfechaForm(request.GET)

		if form.is_valid():

			
			socio = form.cleaned_data['socio']
			
			cursor=connection.cursor()

			cursor.execute("SELECT asociadono,nombre,appaterno,apmaterno from asociado WHERE EmpresaNo=1 and asociadono=%s;",(socio,))
			socioencontrado = cursor.fetchone()
			socio_codigo = socioencontrado[0]
			socio_nombre = socioencontrado[1]
			socio_appaterno = socioencontrado[2]
			socio_apmaterno = socioencontrado[3]

			
			"""cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,psf.fechatentativallegada,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre)  left join  pedidoslines psf on (p.empresano=psf.empresaNo and p.pedido=psf.pedido and p.productono=psf.productono and p.catalogo=psf.catalogo and p.nolinea=psf.nolinea) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by c.id,psf.fechatentativallegada;",(fechainicial,fechafinal))"""


			cursor.execute("SELECT l.Pedido,l.ProductoNo,l.Catalogo,l.Nolinea,p.fechapedido,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,l.observaciones,aso.asociadono,aso.nombre,aso.appaterno,aso.apmaterno,pro.razonsocial FROM pedidoslines l INNER JOIN   pedidosheader p ON (l.EmpresaNo= p.EmpresaNo and l.Pedido=p.PedidoNo) INNER JOIN articulo a ON (l.EmpresaNo=a.EmpresaNo and l.ProductoNo=a.codigoarticulo and l.Catalogo=a.catalogo) inner join proveedor pro on (pro.empresano=1 and pro.proveedorno=a.idproveedor) inner join asociado aso on (aso.empresano=1 and aso.asociadono=p.asociadono) WHERE  p.fechapedido>='20180910' and p.asociadono=%s and l.status='Aqui' and a.idproveedor=2;",(socio,))

			 
			lista_pedidos = dictfetchall(cursor)

			

			elementos = len(lista_pedidos)

			


			"""cursor.execute("SELECT p.razonsocial,a.razonsocial from proveedor p inner join almacen a on (p.empresano=a.empresano and p.proveedorno=a.proveedorno) where p.proveedorno=%s;",(ped['prov_id'],))
			
			prov_alm = cursor.fetchone()"""

			if not lista_pedidos:
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_pedidosposfecha.html',{'mensaje':mensaje,})

			else:
				print "lo que hay en pedidos"
				for ped in lista_pedidos:
					print ped

				
				mensaje ="Registros encontrados == > "

				context = {'form':form,'mensaje':mensaje,'elementos':elementos,'lista_pedidos':lista_pedidos,'socio_codigo':socio_codigo,'socio_nombre':socio_nombre,'socio_appaterno':socio_appaterno,}	
			
				return render(request,'pedidos/lista_pedidosposfecha.html',context)

		
	else:

		form = Calzadollego_detalleForm()
	return render(request,'pedidos/buscapedidosposfecha.html',{'form':form,})



	return


@login_required()
@permission_required('auth.add_user',login_url=None,raise_exception=True)
def pedidosgeneral(request):
	tipo='P'
	try:
	
		g_numero_socio_zapcat = request.session['socio_zapcat']	
		sucursal_activa = request.session['sucursal_activa']
		is_staff = request.user.is_staff

		
	except KeyError :

		return	HttpResponse("Ocurrió un error de conexión con el servidor, Por favor salgase completamente y vuelva a entrar a la página !")

	if request.user.is_authenticated():		
		
		if request.method == 'POST':
			form = PedidosgeneralForm(request.POST)
			'''
			Si la forma es valida se normalizan los campos numpedido, status y fecha,
			de otra manera se envia la forma con su contenido erroreo para que el validador
			de errores muestre los mansajes correspondientes '''

			if form.is_valid():
			
				# limpia datos 
				socionum = form.cleaned_data['socionum']
				numpedido = form.cleaned_data['numpedido']
				status = form.cleaned_data['status']
				estiloalt = form.cleaned_data['estiloalt']
				fechainicial = form.cleaned_data['fechainicial']
				fechafinal = form.cleaned_data['fechafinal']
				
				# Convierte el string '1901-01-01' a una fecha valida en python
				# para ser comparada con la fecha ingresada 

				fecha_1901 =datetime.strptime('1901-01-01', '%Y-%m-%d').date()
				hoy = date.today()
				print "hoy es "
				print hoy

				# Establece conexion con la base de datos
				cursor=connection.cursor()
				
				# Comienza a hacer selects en base a criterios 


				if numpedido != 0:
					cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,l.nolinea,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.FechaMaximaEntrega,l.Observaciones,concat(aso.nombre,' ',aso.appaterno,' ',aso.apmaterno) as socionomb from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) INNER JOIN asociado aso on (h.asociadono=aso.asociadono) where h.empresano = 1 and h.idsucursal=%s and  h.pedidono=%s;", (sucursal_activa,numpedido,))
					
				else:
					
					if socionum != 0:

						if  status == 'Todos':
							cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,l.nolinea,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.FechaMaximaEntrega,l.Observaciones,concat(aso.nombre,' ',aso.appaterno,' ',aso.apmaterno) as socionomb from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) INNER JOIN asociado aso on (h.asociadono=aso.asociadono) where h.empresano = 1 and h.idsucursal=%s and h.asociadono=%s and  h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (sucursal_activa,socionum,fechainicial,fechafinal))
							
						else:
							cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,l.nolinea,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.FechaMaximaEntrega,l.Observaciones,concat(aso.nombre,' ',aso.appaterno,' ',aso.apmaterno) as socionomb from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) INNER JOIN asociado aso on (h.asociadono=aso.asociadono) where h.empresano = 1 and h.idsucursal=%s and h.asociadono=%s and l.status=%s and h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (sucursal_activa,socionum,status,fechainicial,fechafinal))

					else:
						if estiloalt.strip() == '':

							cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,l.nolinea,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.FechaMaximaEntrega,l.Observaciones,concat(aso.nombre,' ',aso.appaterno,' ',aso.apmaterno) as socionomb from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo)  INNER JOIN asociado aso on (h.asociadono=aso.asociadono) where h.empresano = 1 and h.idsucursal=%s and l.status=%s and h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (sucursal_activa,status,fechainicial,fechafinal))
						else:
							if status != 'Todos':
								cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,l.nolinea,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.FechaMaximaEntrega,l.Observaciones,concat(aso.nombre,' ',aso.appaterno,' ',aso.apmaterno) as socionomb from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo)  INNER JOIN asociado aso on (h.asociadono=aso.asociadono) where h.empresano = 1 and h.idsucursal=%s and l.status=%s and a.idestilo=%s and h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (sucursal_activa,status,estiloalt,fechainicial,fechafinal))
							else:
								cursor.execute("SELECT l.pedido,l.productono,l.catalogo,l.precio,l.status,l.nolinea,h.asociadono,h.fechapedido,h.pedidono,h.fechaultimamodificacion,a.codigoarticulo,a.catalogo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.FechaTentativallegada,l.FechaMaximaEntrega,l.Observaciones,concat(aso.nombre,' ',aso.appaterno,' ',aso.apmaterno) as socionomb from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo)  INNER JOIN asociado aso on (h.asociadono=aso.asociadono) where h.empresano = 1 and h.idsucursal=%s and a.idestilo=%s and h.fechapedido>=%s and h.fechapedido<=%s ORDER BY h.pedidono DESC;", (sucursal_activa,estiloalt,fechainicial,fechafinal))


									
				# El contenido del cursor se convierte a diccionario para poder
				# ser enviado como parte del contexto y sea manipulable.				
				pedidos = dictfetchall(cursor)
				

				if not pedidos:
					mensaje = 'No se encontraron registros !'
				else:
					
					mensaje ='Registros encontrados:'
				elementos = len(pedidos)
					
				
				context = {'pedidos':pedidos,'mensaje':mensaje,'elementos':elementos,'is_staff':is_staff,}

				# Cierra la conexion a la base de datos
				cursor.close()
				
				return render(request,'pedidos/lista_pedidosgeneral.html',context)
			
		else:
			form = PedidosgeneralForm()
			#cursor.close()
			
		return render(request,'pedidos/pedidosgeneral.html',{'form':form,'is_staff':is_staff,'tipo':tipo,})
	else:
		redirect('/pedidos/acceso/') 


def pedidosgeneraldetalle(request,pedido,productono,catalogo,nolinea):

	pedidono = pedido
	print (pedido,productono,catalogo,nolinea)
	print("la linea es ",nolinea)
	
	cursor=connection.cursor()

	cursor.execute("SELECT h.fechapedido,a.codigoarticulo,pe.fechaencontrado,pe.bodegaencontro,pe.encontrado,pe.id_cierre,pe.causadevprov,pe.observaciones,h.tiposervicio,via.descripcion as via_solicitud from pedidoslines l inner join pedidosheader h inner join articulo a on (l.pedido=h.pedidono and l.productono=a.codigoarticulo and l.catalogo=a.catalogo) INNER JOIN asociado aso on (h.asociadono=aso.asociadono) INNER JOIN pedidos_encontrados pe on (l.empresano=pe.empresano and l.pedido=pe.pedido and l.productono=pe.productono and l.catalogo=pe.catalogo and l.nolinea=pe.nolinea) INNER JOIN viasolicitud via where l.empresano=1 and l.pedido=%s and l.productono=%s and l.catalogo=%s and l.nolinea=%s;", (pedidono,productono,catalogo,nolinea))
	
	# Agregue los siguientes dos if's por si entrega registros en cero, deben ir ???
	if cursor.fetchone():
		print "DATOS CIERRE:"
		datos_cierre = cursor.fetchone()
		for j  in range(0,len(datos_cierre)):
			print datos_cierre[j]
	else:
		datos_cierre = ()
	
	cursor.execute("SELECT proveedorno,almacen,razonsocial from almacen where empresano=1 and almacen =%s;",(datos_cierre[3],))
	if cursor.fetchone():

		datos_almacen = cursor.fetchone()
	else:
		# asigna valores default a la tupla para
		# que pueda hacer joins en los selects y traer informacion
		# pese a que no haya almacen relacionado.
		datos_almacen = ('1','1','1','1','1')

	cursor.execute("SELECT psf.status, psf.fechamvto,psf.horamvto,u.usuario from pedidos_status_fechas psf left join usuarios u on (u.usuariono=psf.usuario) WHERE psf.empresano=1 and psf.pedido=%s and psf.productono=%s and psf.catalogo=%s and psf.nolinea=%s;",(pedidono,productono,catalogo,nolinea) )
	v_PedidosStatusFechas = dictfetchall(cursor)

	if datos_cierre or v_PedidosStatusFechas:

		context={'fechapedido':datos_cierre[0],'productono':datos_cierre[1],'fechaencontrado':datos_cierre[2],'encontrado':datos_cierre[4],'id_cierre':datos_cierre[5],'tiposervicio':datos_cierre[8],'viasolicitud':datos_cierre[9],'almacen':datos_almacen[2],'psf':v_PedidosStatusFechas,}
	else:
		context={'mensaje':"No existe informacion suficiente para la consulta..!"}	
	
	return render(request,'pedidos/lista_pedidosgeneraldetalle.html',context)


################ CANCELACION DE PEDIDOS ###########
"""AHORITA NO ESTA EN USO..QUIZAS SE BORRE """

def cancelarpedidoadvertencia(request,pedido,productono,catalogo,nolinea):
	#no esta en 
	#pdb.set_trace()
	
	status_operation='fail'

	form=CancelaproductoForm()
	context={}
	
	print request.is_ajax()
	if request.method == 'POST'  and not (request.is_ajax()):

			form = CancelaproductoForm(request.POST)
			
			if form.is_valid():
				print " pasa por aqui"
				cursor = connection.cursor()
				# limpia datos 
				motivo_cancelacion = form.cleaned_data['motivo_cancelacion']
				status_operation = cancela_producto(request,pedido,productono,catalogo,nolinea,motivo_cancelacion)			
				cursor.close()
				
	
				return render(request,'pedidos/msj_cancelacion_resultado.html',{'status_operation':status_operation,})
				
			
	elif request.method == 'POST'  and (request.is_ajax()):

		status_operation = cancela_producto(request,pedido,productono,catalogo,nolinea,'CANCELACION')
				
				
	else:			
		
		pass	
	context={'pedido':pedido,'productono':productono,'catalogo':catalogo,'nolinea':nolinea,'status_operation':status_operation,'form':form}
	return render(request,'pedidos/cancelarpedidoadvertencia.html',context,)


# RUTINA PARA CANCELAR UN PRODUCTO

def cancela_producto(request,pedido,productono,catalogo,nolinea,motivo_cancelacion):

	cursor = connection.cursor()

	hoy = datetime.now()
	fecha_hoy = hoy.strftime("%Y-%m-%d")
	hora_hoy = hoy.strftime("%H:%M:%S") 
	error = ''
	 
	try:
		cursor.execute("START TRANSACTION;")
		cursor.execute("UPDATE pedidoslines l set l.status='Cancelado' WHERE l.empresano=1 and  l.pedido=%s and l.productono=%s and l.catalogo=%s and l.nolinea=%s;",(pedido,productono,catalogo,nolinea,))
		cursor.execute("UPDATE pedidos_encontrados set BodegaEncontro=0,encontrado='' WHERE empresano=1 and pedido=%s and productono=%s and catalogo=%s and nolinea=%s;",(pedido,productono,catalogo,nolinea,))
		cursor.execute("INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,ProductoNo,Status,catalogo,NoLinea,FechaMvto,HoraMvto,Usuario) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);",(1,pedido,productono,'Cancelado',catalogo,nolinea,fecha_hoy,hora_hoy,request.session['socio_zapcat']))
		cursor.execute("INSERT INTO pedidoscancelados (Empresano,pedido,productono,catalogo,nolinea,motivo) values(1,%s,%s,%s,%s,%s);",(pedido,productono,catalogo,nolinea,motivo_cancelacion))			
		status_operation='ok'
		cursor.execute("COMMIT;")

	except DatabaseError as err:
		cursor.execute("ROLLBACK;")
		status_operation='fail'
		error=str(err)
	cursor.close()
	return status_operation,error


"""ESTA RUTINA CANCELA UN PEDIDO, ES LLAMADA TANTO DE PEDIDOS GENERAL
COMO DE LA PANTALLA DE VENTAS."""
def cancelar_pedido(request):
	
	#pdb.set_trace()
	
	pedido = request.POST['pedido']
	productono = request.POST['productono']
	catalogo = request.POST['catalogo']
	nolinea = request.POST['nolinea']
	motivo = request.POST['motivo']

	status_operation='fail'
	error = ''
	
	context={}
	
	status_operacion,error = cancela_producto(request,pedido,productono,catalogo,nolinea,motivo)
				
	data = {'status_operacion':status_operacion,'error':error}
	return HttpResponse(json.dumps(data),content_type='application/json',)	

	


def ingresa_socio(request,tipo): # el parametro 'tipo' toma los valores 'P' de pedido o 'D' de documento y se pasa a los templates 
	#pdb.set_trace()

	form = Ingresa_socioForm()
	context ={}	
	asociado_data =()
	existe_socio = True
	is_staff =  request.session['is_staff']
	id_sucursal = 0
	session_id = request.session.session_key

	
	if request.method == 'POST':
		

		form = Ingresa_socioForm(request.POST)

		if form.is_valid():

			
			socio = form.cleaned_data.get('socio')
			
			
			
			cursor = connection.cursor()
			
			cursor.execute("SELECT asociadono,nombre,appaterno,apmaterno,EsSocio,telefono1 from asociado where asociadono=%s;",(socio,))
			
			asociado_data = cursor.fetchone()
						
			print asociado_data	
			print asociado_data		

			
			# Si el asociado no existe...se notifica.
			if asociado_data is None:
				existe_socio = False

			# de otra manera se actualiza 'socio_que_pide' en session
			else:

				request.session['socio_pidiendo'] = asociado_data[0]
				request.session['EsSocio'] = asociado_data[4]
				num_socio = asociado_data[0]
				telefono_socio = asociado_data[5]
				nombre_socio = str(asociado_data[0])+' '+asociado_data[1]+ ' '+asociado_data[2]+' '+asociado_data[3]+'          TELEFONO: '+asociado_data[5]
				
				form=PedidosForm(request)

				
				# trae catalogo de viasolicitud

				cursor.execute("SELECT id,descripcion FROM viasolicitud;")
				vias_solicitud = dictfetchall(cursor)

				# trae catalogo de tipos de servicio

				cursor.execute("SELECT tiposervicio from tiposervicio;")
				tipo_servicio = dictfetchall(cursor)

				cursor.close()

				# Si el tipo recibe una 'P' es un pedido lo que se procesa
				# entonces se invoca el template adecuado
				if tipo == 'P':
					# Elimina los registros de la sesion en curso antes de continuar solicitando pedidos
					# para el nuevo socio
					cursor = connection.cursor()
					cursor.execute("DELETE FROM pedidos_pedidos_tmp where session_key= %s;",[session_id])	
					cursor.close()


					context = {'form':form,'nombre_socio':nombre_socio,'num_socio':num_socio,'tipo_servicio':tipo_servicio,'vias_solicitud':vias_solicitud,'id_sucursal':id_sucursal,'is_staff':is_staff,'tipo':tipo,}
					return render(request,'pedidos/crea_pedidos.html',context,)
				
				# De otra manera se recibe una 'V' es un documento el que se procesa
				# se invoca la forma de documento y se invoca el template adecuado
				elif tipo == 'V':

					# Invoca que traera datos de ventas, comisiones y creditos del socio asi 
					# como porcentajes de descuento, etc.	

					ventas,creditos,cargos,porconfs_confs = trae_inf_venta(request,num_socio)
					context ={'ventas':ventas,'creditos':creditos,'cargos':cargos,'is_staff':is_staff,'num_socio':num_socio,'nombre_socio':nombre_socio,'porconfs_confs':porconfs_confs,}
					return render(request,'pedidos/despliega_venta.html',context)
					
				else:
					form = CreaDocumentoForm()
					context = {'form':form,'nombre_socio':nombre_socio,'num_socio':num_socio,'tipo_servicio':tipo_servicio,'vias_solicitud':vias_solicitud,'id_sucursal':id_sucursal,'is_staff':is_staff,'tipo':tipo,}
					return render(request,'pedidos/crea_documento.html',context,)	
			

			cursor.close()
	context={'existe_socio':existe_socio,'form':form,'is_staff':is_staff,'tipo':tipo,}	
	return render(request,'pedidos/ingresa_socio.html',context,)		
		

		
def imprime_ticket(request):
	#pdb.set_trace()
	
	is_staff = request.session['is_staff']

	if request.method =='GET':
		p_num_pedido = request.GET.get('p_num_pedido')
	else:
		p_num_pedido = request.POST.get('p_num_pedido')

	# se encodifica como 'latin_1' ya que viene como unicode.

	p_num_pedido = p_num_pedido.encode('latin_1')
	
	
	response = HttpResponse(content_type='application/pdf')
	response['Content-Disposition'] = 'inline; filename="mypdf.pdf"'

	#Trae informacion del pedido.
	cursor =  connection.cursor()
	#pdb.set_trace()

	pedido_header,pedido_detalle,usuario,NotaCredito = None,None,None,0

	try:
			
		cursor.execute("SELECT PedidoNo,FechaPedido,HoraPedido,UsuarioCrea,idSucursal,AsociadoNo,vtatotal FROM pedidosheader where EmpresaNo=1 and PedidoNo = %s;",[p_num_pedido])
		pedido_header = cursor.fetchone()
		
		cursor.execute("SELECT appaterno,apmaterno,nombre FROM asociado where asociadono=%s;",(pedido_header[5],))
		datos_socio = cursor.fetchone()

		
		cursor.execute("SELECT l.subtotal,l.NoNotaCreditoPorPedido,l.Observaciones,l.Status,a.pagina,a.idmarca,a.idestilo,a.idcolor,a.talla,a.catalogo,so.nombre,so.appaterno,so.apmaterno,suc.nombre FROM pedidoslines l INNER JOIN articulo a ON (l.empresano = a.empresano and l.productono = a.codigoarticulo and l.catalogo = a.catalogo) INNER JOIN asociado so ON (so.empresano=1 and so.asociadono = %s) INNER JOIN sucursal suc ON (suc.empresano=1 and suc.sucursalno = %s) WHERE l.pedido = %s;",(pedido_header[5],pedido_header[4],p_num_pedido))
		pedido_detalle = dictfetchall(cursor)
		# la siguiente variable  se asigna para ser pasada a la rutina que 
		# imprimira la nota de credito ( en caso de que exista )
		if pedido_detalle is not(None):

			for elem in  pedido_detalle:
				NotaCredito = elem['NoNotaCreditoPorPedido']
				if elem['talla'] != 'NE':
					talla = elem['talla']
				else:
					talla = elem['Observaciones']
		
		cursor.execute("SELECT usuario from usuarios where usuariono=%s;",[pedido_header[3]])
		
		usuario = cursor.fetchone()

		mensaje=""
		
		if usuario is None:
			usuario=['ninguno']
		if (not pedido_header or not pedido_detalle):
			mensaje = "No se encontro informacion del pedido !"

	except DatabaseError as e:
		print "Ocurrio de base datos"
		print e
		
		mensaje = "Ocurrio un error de acceso a la bd. Inf. tecnica: "
	except Exception as e:
		mensaje = "Ocurrio un error desconocido. Inf. tecnica: "
		print "error desconocido: "
		print e
		
	cursor.close()

	linea = 800
	
	
    # Create a file-like buffer to receive PDF data.
	buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
	p = canvas.Canvas(buffer)
	#p.setPageSize("inch")

	p.setFont("Helvetica",10)
	#p.drawString(1,linea,inicializa_imp)
	

    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
	#p.drawString(20,810,mensaje)

	if (pedido_header and pedido_detalle and usuario):
		p.drawString(50,linea, request.session['cnf_razon_social'])
		linea -=20
		p.drawString(60,linea, 'SUC. '+request.session['sucursal_nombre'])
		linea -=20
		p.setFont("Helvetica",12)
		p.drawString(20,linea, "*** PEDIDO NUM."+p_num_pedido+" ***")
		linea -=20
		p.setFont("Helvetica",10)
		p.drawString(20,linea,request.session['sucursal_direccion'])
		linea -= 10
		p.drawString(20,linea,"COL. "+request.session['sucursal_colonia'])
		linea -= 10
		p.drawString(20,linea,request.session['sucursal_ciudad']+", "+request.session['sucursal_estado'])
		linea -= 20
		p.drawString(20,linea,pedido_header[1].strftime("%d-%m-%Y"))
		p.drawString(100,linea,pedido_header[2].strftime("%H:%M:%S"))
		linea -= 10
		p.drawString(20,linea,"CREADO POR: ")
		#p.drawString(100,linea,request.user.username)
		p.drawString(100,linea,usuario[0])
		linea -= 20
		p.drawString(20,linea,"SOCIO NUM: ")
		type(pedido_header[5])
		p.drawString(100,linea,str(pedido_header[5]))
		linea -= 10
		
		var_socio = datos_socio[0]+" "+datos_socio[1]+" "+datos_socio[2]

		p.drawString(20,linea,var_socio[0:28])
		linea -= 10

		p.drawString(20,linea,"--------------------------------------------------")
		
		linea -= 10
		p.drawString(20,linea,"Descrpcion")
		p.drawString(130,linea,"Precio")
		linea -= 10
		p.drawString(20,linea,"--------------------------------------------------")
		linea -= 10
		#p.setFont("Helvetica",8)
		i,paso=1,linea-10
		for elemento in pedido_detalle:

			if elemento['talla'] != 'NE':
				talla = elemento['talla']
			else:
				talla = elemento['Observaciones']
			
			p.drawString(20,paso,elemento['pagina']+' '+elemento['idmarca']+' '+elemento['idestilo']) 
			p.drawString(20,paso-10,elemento['idcolor'][0:7]+' '+talla)
			p.drawString(130,paso-10,'$ '+str(elemento['subtotal']))
			paso -= 30
		p.drawString(20,paso-10,"Total ==>")
		p.drawString(130,paso-10,'$ '+str(pedido_header[6]))
		linea = paso-40
	#pdb.set_trace()	
	if NotaCredito != 0:
		imprime_documento(NotaCredito,'Credito',False,request.session['cnf_razon_social'],request.session['cnf_direccion'],request.session['cnf_colonia'],request.session['cnf_ciudad'],request.session['cnf_estado'],p,buffer,response,True,linea,request)
	else:

	# Close the PDF object cleanly, and we're done.
		p.showPage()
		p.save()


		pdf = buffer.getvalue()
		buffer.close()

		response.write(pdf)

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    #return FileResponse(buffer, as_attachment=True,filename='hello.pdf')
	return response



def imprime_documento(p_num_documento=0,
	p_tipo_documento='',
	p_notacreditopordev=False,
	p_cnf_razon_social='',
	p_cnf_direccion='',
	p_cnf_colonia='',
	p_cnf_ciudad='',
	p_cnf_estado='',
	p=None,
	buffer = None,
	response= None,
	llamada_interna=False,
	linea=800,
	request=None,):
	#inicializa_imp = bytes(b'\x1b\x40')
	#inputHex = binascii.unhexlify("1b\40")
	

	#pdb.set_trace()
	if request is not None:
		cnf_dias_vigencia_credito = request.session['cnf_dias_vigencia_credito']	
		sucursal_activa = request.session['sucursal_activa']
		

		sucursal_nombre = request.session['sucursal_nombre']
		sucursal_direccion = request.session['sucursal_direccion']
		sucursal_colonia =	request.session['sucursal_colonia']
		sucursal_ciudad =	request.session['sucursal_ciudad']
		sucursal_estado = request.session['sucursal_estado']
		sucursal_telefono =	request.session['sucursal_telefono']


		

	#pdb.set_trace()
	
	# se encodifica como 'latin_1' ya que viene como unicode.

	#p_num_documento = p_num_documento.encode('latin_1')
	#p_tipo_documento = p_tipo_documento.encode('latin_1')
	
	if not llamada_interna:
		response = HttpResponse(content_type='application/pdf')
		response['Content-Disposition'] = 'inline; filename="mypdf.pdf"'
	
			
	
	#Trae informacion del pedido.
	cursor =  connection.cursor()
	
	documento,usuario = None,None
	e = None
	mensaje=""
	try:

		# trae documento
		cursor.execute("SELECT asociado,fechacreacion,horacreacion,`UsuarioQueCreoDcto.`,concepto,monto,saldo,descuentoaplicado,vtadecatalogo,cancelado,pagoaplicadoaremisionno,lo_recibido,venta,idsucursal from documentos where empresano=1 and nodocto=%s and tipodedocumento=%s;",[p_num_documento,p_tipo_documento])
		#cursor.execute("SELECT asociado,fechacreacion,horacreacion,`UsuarioQueCreoDcto.`,concepto,monto,saldo,descuentoaplicado,vtadecatalogo,cancelado,pagoaplicadoaremisionno,lo_recibido,venta,idsucursal from documentos where empresano=1 and nodocto=%s;",[p_num_documento,])

		documento = cursor.fetchone()
		
					# trae socio
		cursor.execute("SELECT nombre,appaterno,apmaterno from asociado where asociadono=%s;",[documento[0]])
		socio = cursor.fetchone()
		# trae ped


		#cursor.execute("SELECT PedidoNo,FechaPedido,HoraPedido,UsuarioCrea,idSucursal,AsociadoNo,vtatotal FROM pedidosheader where EmpresaNo=1 and PedidoNo = %s;",[p_num_pedido])
		#pedido_header = cursor.fetchone()
		
		# Si el documento es remision o credito y hay credito por dev busca el detalle
		if p_tipo_documento=='Remision':
			
			cursor.execute("SELECT l.precio,l.NoNotaCreditoPorPedido,l.Observaciones,l.Status,a.pagina,a.idmarca,a.idestilo,a.idcolor,a.talla,a.catalogo,so.nombre,so.appaterno,so.apmaterno,suc.nombre FROM pedidoslines l INNER JOIN articulo a ON (l.empresano = a.empresano and l.productono = a.codigoarticulo and l.catalogo = a.catalogo) INNER JOIN asociado so ON (so.empresano=1 and so.asociadono = %s) INNER JOIN sucursal suc ON (suc.empresano=1 and suc.sucursalno = %s) WHERE l.RemisionNo = %s;",(documento[0],documento[13],p_num_documento))

		else:
			if p_tipo_documento == 'Credito':

				if p_notacreditopordev:
				
					cursor.execute("SELECT l.precio,l.NoNotaCreditoPorPedido,l.Observaciones,l.Status,a.pagina,a.idmarca,a.idestilo,a.idcolor,a.talla,a.catalogo,so.nombre,so.appaterno,so.apmaterno,suc.nombre FROM pedidoslines l INNER JOIN articulo a ON (l.empresano = a.empresano and l.productono = a.codigoarticulo and l.catalogo = a.catalogo) INNER JOIN asociado so ON (so.empresano=1 and so.asociadono = %s) INNER JOIN sucursal suc ON (suc.empresano=1 and suc.sucursalno = %s) WHERE l.NoNotaCreditoPorDevolucion = %s;",(documento[0],documento[13],p_num_documento))
				
				else:

					cursor.execute("SELECT l.precio,l.NoNotaCreditoPorPedido,l.Observaciones,l.Status,a.pagina,a.idmarca,a.idestilo,a.idcolor,a.talla,a.catalogo,so.nombre,so.appaterno,so.apmaterno,suc.nombre FROM pedidoslines l INNER JOIN articulo a ON (l.empresano = a.empresano and l.productono = a.codigoarticulo and l.catalogo = a.catalogo) INNER JOIN asociado so ON (so.empresano=1 and so.asociadono = %s) INNER JOIN sucursal suc ON (suc.empresano=1 and suc.sucursalno = %s) WHERE l.NoNotaCreditoPorPedido = %s;",(documento[0],documento[13],p_num_documento))

			pedido_detalle = dictfetchall(cursor)
		
		cursor.execute("SELECT usuario from usuarios where usuariono=%s;",[documento[3]])
		
		usuario = cursor.fetchone()

		
		
		if usuario is None:
			usuario=['ninguno']
		
		if not documento:
			mensaje = "No se encontro informacion del documento !"
		
	except DatabaseError as e:
		print "Ocurrio de base datos"
		print e
		
		mensaje = "Ocurrio un error de acceso a la bd. Inf. tecnica: "
	except Exception as e:
		print "error desconocido ! ", e
		
	cursor.close()
	
    # Create a file-like buffer to receive PDF data.
	if not llamada_interna:
		buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
		p = canvas.Canvas(buffer)

	
	p.setFont("Helvetica",10)

	
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
	#p.drawString(1,linea,inicializa_imp)
	p.drawString(20,linea,mensaje)

	if (documento and usuario and not e):

		# Convierte la fechacreacion a formato adecuado y le agrega
		# los dias de vigencia de credito
		
		
		fechaFinVigenciaCredito = documento[1] + timedelta(days=cnf_dias_vigencia_credito)
		
		p.drawString(60,linea, p_cnf_razon_social)
		linea -=20
		p.drawString(60,linea," SUC. "+sucursal_nombre)
		linea -=20
		p.setFont("Helvetica",12)
		p.drawString(20,linea,"** Nota de "+p_tipo_documento+" "+str(p_num_documento)+" **")
		p.setFont("Helvetica",8)
		linea -= 20
		p.drawString(20,linea,sucursal_direccion)
		linea -= 10
		p.drawString(20,linea,"COL. "+sucursal_colonia)
		linea -= 10
		p.drawString(20,linea,sucursal_ciudad+", "+sucursal_estado)
		linea -= 15
		#p.setFont("Helvetica",6)
		p.drawString(20,linea,"CREADO POR: ")
		#p.drawString(100,linea,request.user.username)
		p.drawString(100,linea,usuario[0])
		linea -= 15
		p.drawString(20,linea,"SOCIO NUM: ")
		p.drawString(100,linea,str(documento[0]))
		#p.drawString(100,linea,socio[0].strip()+' '+socio[1].strip()+' '+socio[2].strip())
		linea -= 10
		p.drawString(20,linea,documento[1].strftime("%d-%m-%Y"))
		p.drawString(100,linea,documento[2].strftime("%H:%M:%S"))
		linea -= 10
	 	
		p.setFont("Helvetica",8)
		p.drawString(20,linea,"--------------------------------------------------")
		linea -= 10

		p.drawString(20,linea,"Concepto: ")
		linea -= 10
		p.drawString(20,linea,documento[4][slice(0,40,None)])
		linea -= 10

		p.drawString(20,linea,"Monto: $ "+str(documento[5]))
		linea -= 15
		
		if documento[4][slice(0,43,None)]=="Credito generado por concepto de devolucion":
			p.drawString(20,linea,"Productos devueltos:")
			p.drawString(130,linea,"")
			
			linea -=10
			p.drawString(20,linea,"--------------------------------------------------")
			linea -= 10
			
		p.setFont("Helvetica",8)
		i,paso = 1,linea
		if pedido_detalle:

			for elemento in pedido_detalle:
				
				p.drawString(20,paso,(elemento['pagina']+' '+elemento['idmarca']+' '+elemento['idestilo']).lower()) 
				p.drawString(20,paso-10,(elemento['idcolor']+' '+elemento['talla']).lower())
				p.drawString(130,paso-10,('$ '+str(elemento['precio'])).lower())
				paso -= 20
		
		#paso = linea
		paso -= 30
		p.drawString(20,paso,"Valido hasta el "+ fechaFinVigenciaCredito.strftime('%d-%m-%Y'))
		paso -=10
		p.drawString(20,paso,"es INDISPENSABLE presentarlo en su compra.")
		paso -= 10
		p.setFont("Helvetica",8)
		#p.drawString(20,paso-10,"Total ==>")
		#p.drawString(130,paso-10,str(pedido_header[6]))

	# Close the PDF object cleanly, and we're done.
	
	'''if llamada_interna:

		p.showPage()
	
		p.save()

		pdf = buffer.getvalue()
		buffer.close()

		response.write(pdf)
		return response
	else:

		return	'''
	p.showPage()
	
	p.save()

	pdf = buffer.getvalue()
	buffer.close()

	response.write(pdf)
	return response


# **************** COLOCACIONES **********************************

@login_required(login_url = "/pedidos/acceso/")
def colocaciones(request):
	#import pdb; pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..
	
	mensaje = " "

	# elimina cualquier registro de la session.
	session_id = request.session.session_key
	# Asigna is_staff para validacines
	is_staff = request.session['is_staff']

	"""cursor = connection.cursor()
	cursor.execute("DELETE FROM pedidos_pedidos_tmp where session_key= %s;",[session_id])	
	
	cursor.close()"""


	#for key,value in pr_dict.items():
	#	print key,value 
	
	 
	if request.method =='POST':
		
		form = ColocacionesForm(request.POST)
		
		if form.is_valid():
			
			
			

			mensaje = "ok" #+ articulo.codigoarticulo
			return render(request,'pedidos/colocaciones.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})
		else:	
			
			mensaje = "Error en la forma"
			return render(request,'pedidos/colocaciones.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})

	form = ColocacionesForm()
	mensaje = ""
	return render(request,'pedidos/colocaciones.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})	


#@ensure_csrf_cookie
def muestra_colocaciones(request):

	#pdb.set_trace()	
		
	#if request.method == 'GET':
	#if request.is_ajax() and request.method == 'GET':

	proveedor = request.GET['proveedor']
	try:
		almacen = request.GET['almacen']
	except:
		return HttpResponse("Requiere ingresar el almacen, la lista de almacenes se refresca al cambiar de proveedor !")
		
	tipo_consulta = request.GET['tipo_consulta']
	ordenado_por = request.GET['ordenado_por']
	
	fechainicial = request.GET['fechainicial']
	fechafinal = request.GET['fechafinal']
	

	# Convierte tipo_consulta a un formato legible por python, ya que entra como unicode
	tipo_consulta = tipo_consulta.encode('latin_1')
	tipo_consulta = int(tipo_consulta)

	# Convierte el tipo de ordenamiento a entero
	ordenado_por = ordenado_por.encode('latin_1')
	ordenado_por = int(ordenado_por)


	# Igualmente, las fechas se convierten a un formato adecuado para ser grabadas en la BD
	fechainicial = datetime.strptime(fechainicial, "%d/%m/%Y").date()
	fechafinal = datetime.strptime(fechafinal, "%d/%m/%Y").date()
	hay_cancelados = False
	cursor = connection.cursor()

	try:
		# Cuenta articulos encontrados ya en el almacen.
		#cursor.execute("SELECT COUNT(*) FROM pedidos_encontrados e INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) on (a.EmpresaNo=1 and e.ProductoNo=a.CodigoArticulo and e.Catalogo=a.Catalogo)  WHERE e.empresano=1 and e.encontrado='S' and  trim(e.observaciones)<>'Cancelado' and  e.id_cierre=0 and a.idproveedor=%s and e.BodegaEncontro=%s;",(proveedor,almacen))
		#cursor.execute("SELECT COUNT(*) FROM pedidos_encontrados e INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) on (a.EmpresaNo=1 and e.ProductoNo=a.CodigoArticulo and e.Catalogo=a.Catalogo)  WHERE e.empresano=1 and e.encontrado='S' and  trim(e.observaciones)<>'Cancelado' and  e.id_cierre=0 and a.idproveedor=%s and e.BodegaEncontro=%s;",(proveedor,almacen))
		
		cursor.execute("SELECT razonsocial from proveedor where proveedorno=%s;",(proveedor))
		prov_nombre=cursor.fetchone()

		cursor.execute("SELECT razonsocial from almacen where proveedorno=%s and almacen=%s;",(proveedor,almacen,))
		almacen_nombre=cursor.fetchone()

		cursor.execute("SELECT COUNT(*) FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo=1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (ind_emp_prov_cat_codpro) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo)  WHERE e.empresano=1 and a.idProveedor=%s  and e.BodegaEncontro=%s  and e.encontrado='S' and l.Status='Encontrado' and e.id_cierre=0 ORDER BY a.idestilo;",(proveedor,almacen))

		encontrados = cursor.fetchone()
		reg_encontrados = encontrados[0]
		
		# Detecta algun cancelado en el conjunto.
		
		cursor.execute("SELECT COUNT(*) FROM pedidos_encontrados e INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) on (a.EmpresaNo=1 and e.ProductoNo=a.CodigoArticulo and e.Catalogo=a.Catalogo) WHERE e.empresano=1 and e.observaciones ='Cancelado' and  e.id_cierre=0 and e.BodegaEncontro=%s and a.idProveedor=%s;",(almacen,proveedor))
		encontrados = cursor.fetchone()
		reg_cancelados = encontrados[0]
		#reg_cancelados = 1

		if tipo_consulta == 1: 
			# Ejecuta segun ordenamiento solicitado (1= estilo, 2=socio,3=fechapedido )
			if ordenado_por == 1:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal, l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidoslines l LEFT JOIN  pedidos_encontrados e on ( e.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo = 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo = 1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE l.empresano = 1 and a.idProveedor= %s and l.Status='Por Confirmar'  and (e.encontrado='' or e.encontrado='P' or e.encontrado IS NULL) ORDER BY a.idestilo;",(proveedor,))
			elif ordenado_por == 2:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal, l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidoslines l LEFT JOIN  pedidos_encontrados e on ( e.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo = 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo = 1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE l.empresano = 1 and a.idProveedor= %s and l.Status='Por Confirmar'  and (e.encontrado='' or e.encontrado='P' or e.encontrado IS NULL) ORDER BY p.asociadono;",(proveedor,))
			else:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal, l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidoslines l LEFT JOIN  pedidos_encontrados e on ( e.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo = 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo = 1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE l.empresano = 1 and a.idProveedor= %s and l.Status='Por Confirmar'  and (e.encontrado='' or e.encontrado='P' or e.encontrado IS NULL) ORDER BY p.FechaPedido;",(proveedor,))

		
		elif tipo_consulta == 2:

			# Ejecuta segun ordenamiento solicitado (1= estilo, 2=socio,3=fechapedido )

			if ordenado_por == 1:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo = 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano =1 and a.idProveedor=%s and e.encontrado='N'   and l.Status='Por Confirmar'  and p.FechaPedido>=%s and p.FechaPedido<=%s ORDER BY a.idestilo;",(proveedor,fechainicial,fechafinal))
			elif ordenado_por == 2:	
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo = 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano =1 and a.idProveedor=%s and e.encontrado='N'   and l.Status='Por Confirmar'  and p.FechaPedido>=%s and p.FechaPedido<=%s ORDER BY p.asociadono;",(proveedor,fechainicial,fechafinal))
			else:					
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo = 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano =1 and a.idProveedor=%s and e.encontrado='N'   and l.Status='Por Confirmar'  and p.FechaPedido>=%s and p.FechaPedido<=%s ORDER BY p.FechaPedido;",(proveedor,fechainicial,fechafinal))
	

		elif tipo_consulta == 3:

			# Ejecuta segun ordenamiento solicitado (1= estilo, 2=socio,3=fechapedido )

			if ordenado_por == 1:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo=1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (ind_emp_prov_cat_codpro) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano=1 and a.idProveedor=%s  and e.BodegaEncontro=%s  and e.encontrado='S' and l.Status='Encontrado' and e.id_cierre=0 ORDER BY a.idestilo;",(proveedor,almacen))
			elif ordenado_por == 2:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo=1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (ind_emp_prov_cat_codpro) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano=1 and a.idProveedor=%s  and e.BodegaEncontro=%s  and e.encontrado='S' and l.Status='Encontrado' and e.id_cierre=0 ORDER BY p.asociadono;",(proveedor,almacen))
			else:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo=1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (ind_emp_prov_cat_codpro) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano=1 and a.idProveedor=%s  and e.BodegaEncontro=%s  and e.encontrado='S' and l.Status='Encontrado' and e.id_cierre=0 ORDER BY p.FechaPedido;",(proveedor,almacen))

		elif tipo_consulta == 4:

			# Ejecuta segun ordenamiento solicitado (1= estilo, 2=socio,3=fechapedido )

			if ordenado_por == 1:			
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and  e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo= 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano =1 and a.idProveedor=%s and e.encontrado='X'   and ( (l.Status='Por Confirmar' ) )  and p.FechaPedido>=%s and p.FechaPedido<=%s and e.BodegaEncontro=%s ORDER BY a.idestilo;",(proveedor,fechainicial,fechafinal,almacen,))
			elif ordenado_por == 2:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and  e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo= 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano =1 and a.idProveedor=%s and e.encontrado='X'   and ( (l.Status='Por Confirmar' ) )  and p.FechaPedido>=%s and p.FechaPedido<=%s and e.BodegaEncontro=%s ORDER BY p.asociadono;",(proveedor,fechainicial,fechafinal,almacen,))
			else:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and  e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo= 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano =1 and a.idProveedor=%s and e.encontrado='X'   and ( (l.Status='Por Confirmar' ) )  and p.FechaPedido>=%s and p.FechaPedido<=%s and e.BodegaEncontro=%s ORDER BY p.FechaPedido;",(proveedor,fechainicial,fechafinal,almacen,))
	


		else:
			# Ejecuta segun ordenamiento solicitado (1= estilo, 2=socio,3=fechapedido )

			if ordenado_por == 1:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo= 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON  (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano=1 and a.idProveedor=%s and e.encontrado='D'    and p.FechaPedido>=%s and p.FechaPedido<=%s ORDER BY a.idestilo;",(proveedor,fechainicial,fechafinal))
			elif ordenado_por == 2:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo= 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON  (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano=1 and a.idProveedor=%s and e.encontrado='D'    and p.FechaPedido>=%s and p.FechaPedido<=%s ORDER BY p.asociadono;",(proveedor,fechainicial,fechafinal))
			else:
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones as encon_obser,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status,aso.nombre,aso.ApPaterno,aso.ApMaterno,n.observaciones as notas FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo= 1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (`ind_emp_prov_cat_codpro`) ON  (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN asociado as aso on (aso.asociadono=p.asociadono) left join pedidos_notas n on (e.empresano=n.empresano and e.pedido=n.pedido and e.productono=n.productono and e.catalogo=n.catalogo and e.nolinea=n.nolinea) WHERE e.empresano=1 and a.idProveedor=%s and e.encontrado='D'    and p.FechaPedido>=%s and p.FechaPedido<=%s ORDER BY p.FechaPedido;",(proveedor,fechainicial,fechafinal))


	except DatabaseError as e:

		print "Error en base de datos"
		print e
		mensaje ="Se  produjo un error al acceder a base de datos"

	if cursor.rowcount != 0:

		registros = dictfetchall(cursor)
		mensaje ="Lista de articulos  a colocar:"
	else:
		registros ={}
		mensaje = "Registros no encontrados para esta consulta !"
	cursor.close()
	return render(request,'pedidos/colocaciones_detalle.html',{'registros':registros,'mensaje':mensaje,'reg_encontrados':reg_encontrados,'almacen':almacen,'reg_cancelados':reg_cancelados,'tipo_consulta':tipo_consulta,'prov_nombre':prov_nombre[0],'almacen_nombre':almacen_nombre[0],})
	#return render(request,'pedidos/colocaciones_detalle.html',{'registros':registros,'mensaje':mensaje,'reg_encontrados':reg_encontrados,'almacen':almacen,'reg_cancelados':reg_cancelados,'tipo_consulta':tipo_consulta,})

	"""data = serializers.serialize('json', registros)
	return HttpResponse(data, mimetype='application/json')"""	

	#return HttpResponse(json.dumps(data),content_type='application/json')


	 	

'''
def muestra_colocaciones(request):

	pdb.set_trace()	
	if request.method == 'GET':
	#if request.is_ajax() and request.method == 'GET':
		proveedor = request.GET['proveedor']
		almacen = request.GET['almacen']
		tipo_consulta = request.GET['tipo_consulta']
		
		fechainicial = request.GET['fechainicial']
		fechafinal = request.GET['fechafinal']

		# Convierte tipo_consulta a un formato legible por python, ya que entra como unicode
		tipo_consulta = tipo_consulta.encode('latin_1')
		tipo_consulta = int(tipo_consulta)
		# Igualmente, las fechas se convierten a un formato adecuado para ser grabadas en la BD
		fechainicial = datetime.strptime(fechainicial, "%m/%d/%Y").date()
		fechafinal = datetime.strptime(fechafinal, "%m/%d/%Y").date()

		cursor = connection.cursor()

		try:
			if tipo_consulta == 1: 
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal, l.Observaciones FROM pedidoslines l LEFT JOIN  pedidos_encontrados e on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo)  INNER JOIN pedidos_status_fechas f on  ( e.EmpresaNo=f.EmpresaNo and e.Pedido=f.Pedido and e.ProductoNo=f.ProductoNo and e.Catalogo=f.catalogo and e.NoLinea=f.NoLinea) WHERE e.empresano = 1 and a.idProveedor= %s and  p.FechaPedido>=%s and p.FechaPedido<=%s   and l.Status='Por Confirmar'  and f.Status='Por Confirmar' and  (trim(e.encontrado)='' or  trim(e.encontrado)='P' or e.encontrado IS NULL);",(proveedor,fechainicial,fechafinal))
			else:
				if tipo_consulta == 2:
						cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.Nolinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN pedidos_status_fechas f on  ( e.EmpresaNo=f.EmpresaNo and e.Pedido=f.Pedido and e.ProductoNo=f.ProductoNo and e.Catalogo=f.catalogo and e.NoLinea=f.NoLinea) WHERE e.empresano =1 and a.idProveedor=%s and e.encontrado='N'   and (l.Status='Por Confirmar' and f.Status='Por Confirmar') and p.FechaPedido>=%s and p.FechaPedido<=%s;",(proveedor,fechainicial,fechafinal))
				else:
					if tipo_consulta == 3:
						cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN pedidos_status_fechas f on  ( e.EmpresaNo=f.EmpresaNo and e.Pedido=f.Pedido and e.ProductoNo=f.ProductoNo and e.Catalogo=f.catalogo and e.NoLinea=f.NoLinea and trim(f.Status='Encontrado')) WHERE (e.empresano=1 and a.idProveedor=%s and e.BodegaEncontro=%s and trim(l.Status)='Encontrado' and e.id_cierre=0) or (e.empresano=1 and a.idProveedor=%s and e.BodegaEncontro=%s and  trim(l.Status)='Cancelado' and e.encontrado='S' and trim(e.observaciones='Cancelado' )  and e.id_cierre=0 );",(proveedor,almacen,proveedor,almacen))
					else:
						if tipo_consulta == 4:
							cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.Nolinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN pedidos_status_fechas f on  ( e.EmpresaNo=f.EmpresaNo and e.Pedido=f.Pedido and e.ProductoNo=f.ProductoNo and e.Catalogo=f.catalogo and e.NoLinea=f.NoLinea) WHERE a.empresano =1 and a.idProveedor=%s and e.encontrado='X'   and ( (l.Status='Por Confirmar' and f.Status='Por Confirmar') or (l.Status='Cancelado' and f.status='Cancelado') )  and p.FechaPedido>=%s and p.FechaPedido<=%s and e.BodegaEncontro=%s;",(proveedor,fechainicial,fechafinal,almacen,))
						else:
							cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.Nolinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones FROM pedidos_encontrados e INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.Nolinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN pedidos_status_fechas f on  ( e.EmpresaNo=f.EmpresaNo and e.Pedido=f.Pedido and e.ProductoNo=f.ProductoNo and e.Catalogo=f.catalogo and e.NoLinea=f.NoLinea) WHERE a.empresano=1 and a.idProveedor=%s and e.encontrado='D'    and p.FechaPedido>=%s and p.FechaPedido<=%s;",(proveedor,fechainicial,fechafinal))
		except DatabaseError as e:

			print "Error en base de datos"
			print e

		if cursor:

			registros = dictfetchall(cursor)
		else:
			registros ={}
		cursor.close()
		return render(request,'pedidos/colocaciones_detalle.html',{'registros':registros,'mensaje':mensaje,})	

		"""data = serializers.serialize('json', registros)
		return HttpResponse(data, mimetype='application/json')"""	

		#return HttpResponse(json.dumps(data),content_type='application/json')
	return '''

# PROCESAMIENTO DE COLOCACIONES

#@ensure_csrf_cookie
def procesar_colocaciones(request):
	
	#pdb.set_trace()
	if request.is_ajax()  and request.method == 'POST':
		# Pasa a una variable la tabla  recibida en json string
		TableData = request.POST.get('TableData')
		
		# carga la tabla ( la prepara con el formato de lista adecuado para leerla)
		datos = json.loads(TableData)

		# Se define una lista para guardar los elementos con error.

		estilos_con_error = []


		try:

		
			capturista =  request.POST.get('usr_id') # toma el id  de confirmacion del empleado que captura 

			usr_id = request.POST.get('usr_id')

			fecha_probable = request.POST.get('fecha_probable')

			
		except:
			print "error en usr_id"
			pass
			#HttpResponse('div class="alert alert-warning" role="alert"><strong>Operacion fallida !</strong> Hubo un error de sesion al procesar, la transacción no pudo ser completada, cierre su navegador, ingrese nuevamente e intente otra vez !</div>')
		

		almacen = request.POST.get('almacen')
		almacen = almacen.encode('latin_1')

		cursor = connection.cursor()

		''' INICIALIZACION DE VARIABLES '''

		pedidos_cambiados = 0 # inicializa contador de pedidos que sufrieron cambios entre la lectura inicial y el commit.
		
		nuevo_status_pedido = '' # variable que servira para  guardar el status de pedido segun se vayan cumpliendo condiciones,
							# posteriomente se utilizara par actualizar el status del pedido en pedidoslines y pedidos_status_confirmacion.

		error = False # Si existe algun error de base de datos o de otro tipo se pondra en True

		''' FIN DE INCIALIZACION DE VARIABLES '''


		# Se convierte la fecha de hoy a formatos manejables para insertarlos en el registro.
		hoy = datetime.now()
		fecha_hoy = hoy.strftime("%Y-%m-%d")
		hora_hoy = hoy.strftime("%H:%M:%S") 




        # Recupera cada diccionario y extrae los valores de la llave a buscar.
		for j in datos:
			
			pedido = j.get("Pedido")

			productono = j.get('ProductoNo').strip()
			catalogo =j.get('Catalogo').strip()
			nolinea = j.get('Nolinea')
			encontrado = j.get('encontrado').strip()
			#version_original_pedidos_encontrados = j.get('ver_ant_encontrado').encode('latin_1').strip() # Traemos version anterior del registro pedidos_encontrados, para esto usamos el campo 'encontrado' con el que haremos una  futura comparacion con una nueva lectura al mismo para ver si cambio
			#version_original_pedidos_lines = j.get('status').encode('latin_1').strip() # Traemos version anterior del registro pedidoslines, para esto usamos el campo 'status' con el que hacemos una comparacion con una nueva lectura al mismo para ver si cambio
			version_original_pedidos_encontrados = j.get('ver_ant_encontrado').strip() # Traemos version anterior del registro pedidos_encontrados, para esto usamos el campo 'encontrado' con el que haremos una  futura comparacion con una nueva lectura al mismo para ver si cambio
			version_original_pedidos_lines = j.get('status').strip() # Traemos version anterior del registro pedidoslines, para esto usamos el campo 'status' con el que hacemos una comparacion con una nueva lectura al mismo para ver si cambio

			notas = j.get('notas').strip()
			notas = notas.encode('latin_1')

			if encontrado != '':

				# Comienza acceso a BD.

				
				try:
					
					# verifica version actual pedidos_encontrados y de una vez traemos id_cierre que se usara mas adelante
					cursor.execute("SELECT encontrado,id_cierre from pedidos_encontrados WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
					registro = cursor.fetchone()

					# Creea variable version_actual e id_cierre para pedidos_encontrados
					version_actual_pedidos_encontrados=registro[0].strip()
					id_cierre = registro[1]

					# verifica version actual pedidoslines y de una vez se trae el estatus actual para ser mostrado en caso de que la version actual difiera de la anterior
					cursor.execute("SELECT status from pedidoslines WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
					registro = cursor.fetchone()

					# Crea variables de  version actual asi como el actual_estatus para pedidoslines
					
					version_actual_pedidos_lines =  registro[0].strip()

					# Si las versiones no concuerdan crea contador de pedidos_cambiados y sus lista respectiva para ser mostrados al usuario.
					if (version_actual_pedidos_encontrados != version_original_pedidos_encontrados) or (version_actual_pedidos_lines != version_original_pedidos_lines):
						pedidos_cambiados += 1 # actualiza contador de pedidos cambiados durante el proceso
					
					else:

						if fecha_probable == u'':
							fecha_probable =u'19010101'
						fecha_probable = fecha_probable.encode('latin_1')


						# ACTUALIZA pedidoslines
						
						if encontrado == 'S':
								nuevo_status_pedido = 'Encontrado'
						else:
							
							fecha_probable = u'19010101'
							fecha_probable = fecha_probable.encode('latin_1')

						if version_actual_pedidos_lines != u'Cancelado':

							if (encontrado == '' or encontrado =='N' or encontrado == 'P' or encontrado=='X'):
								
								nuevo_status_pedido ='Por confirmar'	
							else:
								if encontrado =='D':

									nuevo_status_pedido = 'Descontinuado'

					

						# Abre transaccion
						cursor.execute("START TRANSACTION")
						
						# Actualiza pedidos_encontrados

						cursor.execute("UPDATE pedidos_encontrados SET encontrado=%s,BodegaEncontro=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,almacen,pedido,productono,catalogo,nolinea))
						
						# Marca articulo como descontinuado si encontrado ='D'
						if encontrado =='D':
								cursor.execute("UPDATE articulo SET descontinuado=1 WHERE EmpresaNo=1 and CodigoArticulo=%s and Catalogo=%s;",(productono,catalogo))


						if almacen == '2':
							cursor.execute("UPDATE pedidos_encontrados SET `2`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						elif almacen =='3':
							cursor.execute("UPDATE pedidos_encontrados SET `3`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						elif almacen == '4':
							cursor.execute("UPDATE pedidos_encontrados SET `4`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						elif almacen == '5':
							cursor.execute("UPDATE pedidos_encontrados SET `5`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						elif almacen == '6':
							cursor.execute("UPDATE pedidos_encontrados SET `6`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						elif almacen == '7':
							cursor.execute("UPDATE pedidos_encontrados SET `7`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						elif almacen == '8':
							cursor.execute("UPDATE pedidos_encontrados SET `8`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						elif almacen == '9':
							cursor.execute("UPDATE pedidos_encontrados SET `9`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))
						else:
							cursor.execute("UPDATE pedidos_encontrados SET `10`=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(encontrado,pedido,productono,catalogo,nolinea))

						# Actualiza pedidos

						cursor.execute("UPDATE pedidosheader SET FechaUltimaModificacion=%s,HoraModicacion=%s WHERE EmpresaNo=1 and pedidono=%s;",[fecha_hoy,hora_hoy,pedido,])							
						cursor.execute("UPDATE pedidoslines SET status=%s,FechaTentativaLLegada=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(nuevo_status_pedido,fecha_probable,pedido,productono,catalogo,nolinea))
						cursor.execute("UPDATE pedidos_notas set Observaciones=%s where EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(notas,pedido,productono,catalogo,nolinea))

						# Crea o bien actualiza pedidos_status_fechas

						if encontrado != 'X' and version_actual_pedidos_lines != 'Cancelado':

							# Verifica que no existe el registro, si existe actualiza, caso contrario crea.
							print pedido,productono,nuevo_status_pedido,catalogo,nolinea
							cursor.execute("SELECT Pedido FROM pedidos_status_fechas WHERE EmpresaNo=%s and Pedido=%s and ProductoNo=%s and Status=%s and catalogo=%s and NoLinea=%s;",(1,pedido,productono,nuevo_status_pedido,catalogo,nolinea))
							

							
							if (encontrado == 'S' or encontrado == 'D'):

								# Si no existe registro, crea
								if cursor.fetchone() is None:

									cursor.execute("INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,ProductoNo,Status,catalogo,NoLinea,FechaMvto,HoraMvto,Usuario) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",[1,pedido,productono,nuevo_status_pedido,catalogo,nolinea,fecha_hoy,hora_hoy,capturista])
								
								# De otra manera, actualiza
								else:	
									cursor.execute("UPDATE pedidos_status_fechas SET FechaMvto=%s,HoraMvto=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s and status='Por Confirmar';",(fecha_hoy,hora_hoy,pedido,productono,catalogo,nolinea))




						cursor.execute("COMMIT;")

				

				except DatabaseError as error_msg:
			
					cursor.execute("ROLLBACK;")
					data = {'status_operacion':'fail','error':error_msg,}
					print error_msg
					error = True
				except IntegrityError as error_msg:
					cursor.execute("ROLLBACK;")
					data = {'status_operacion':'fail','error':error_msg,}
					print error_msg
					error = True
				except OperationalError as error_msg:
					cursor.execute("ROLLBACK;")
					data = {'status_operacion':'fail','error':error_msg,}
					error = True
				except NotSupportedError as error_msg:
			
					cursor.execute("ROLLBACK;")
					data = {'status_operacion':'fail','error':error_msg,}
					error = True
					print error_msg

				except ProgrammingError as error_msg:

					cursor.execute("ROLLBACK;")
					data = {'status_operacion':'fail','error':error_msg,}
					error = True
					print error_msg

				except (RuntimeError, TypeError, NameError) as error_msg:
					#error_msg = 'Error no relativo a base de datos'
					data = {'status_operacion':'fail','error':error_msg,}
					error = True
					print error_msg
				except:
					error_msg = "Error desconocido"
					data = {'status_operacion':'fail','error':error_msg,}
					error = True

		cursor.close()

		# Si no hay error, nos devolvera la lista de pedidos cambiados
		# o bien un 'ok' y si hay error nos devolvera el mensaje de error.
		if not error:
			data={'status_operacion':'ok'}
			data['pedidos_no_procesados']=' '

			if pedidos_cambiados > 0:
				# Agrega una clave mas al dict indicando que algunos productos no se procesaron
				data['pedidos_no_procesados']='Algunos registros no fueron procesados, debido a que fueron modificados por otra transaccion mientras Ud los marcaba !'
			
		return HttpResponse(json.dumps(data),content_type='application/json',)

# PROCESAR CIERRE DE PEDIDOS

def procesar_cierre_pedido(request):
	
	#pdb.set_trace()
	if request.is_ajax()  and request.method == 'POST':
		# Pasa a una variable la tabla  recibida en json string
		TableData = request.POST.get('TableData')
		
		# carga la tabla ( la prepara con el formato de lista adecuado para leerla)
		datos = json.loads(TableData)

		if request.POST.get('usr_id') is not None:
			capturista = request.POST.get('usr_id')
		else:
			capturista = 99
		
		datos_cierre_invalidos = False
		errores_datos_cierre=[]
		

		''' TRAE VARIABLE CON POST '''

		almacen = request.POST.get('almacen')
		almacen = almacen.encode('latin_1')

		referencia = request.POST.get('referencia')
		referencia= referencia.encode('latin_1')

		if len(referencia)<10:
			#datos_cierre_invalidos = True
			#errores_datos_cierre.append('Referencia invalida !')
			pass
		total_articulos = request.POST.get('total_articulos')
		total_articulos = total_articulos.encode('latin_1')


		colocado_via = request.POST.get('colocado_via')
		colocado_via = colocado_via.encode('latin_1')


		tomado_por = request.POST.get('tomado_por')
		tomado_por = tomado_por.encode('latin_1')

		if (tomado_por)<3:
			datos_cierre_invalidos = True
			errores_datos_cierre.append('El campo "Tomado por" debe tener minimo 3 caracteres !')

		confirmado_por = request.POST.get('confirmado_por')
		confirmado_por = confirmado_por.encode('latin_1')

		if (confirmado_por)<3:
			datos_cierre_invalidos = True
			errores_datos_cierre.append('El campo "Confirmado por" debe tener minimo 3 caracteres !')

		'''fecha_cierre = request.POST.get('fecha_cierre')
		fecha_cierre = fecha_cierre.encode('latin_1')

		hora_cierre = request.POST.get('hora_cierre')
		hora_cierre = hora_cierre.encode('latin_1')

		fecha_cierre,hora_cierre = trae_fecha_hora_actual(fecha_cierre,hora_cierre)'''

		fecha_llegada = request.POST.get('fecha_llegada')
		fecha_llegada = fecha_llegada.encode('latin_1')

		if not fecha_llegada:
			datos_cierre_invalidos = True
			errores_datos_cierre.append('Fecha de llegada incorrecta !')



		pedido = request.POST.get('pedido')
		pedido = pedido.encode('latin_1')

		if pedido == 0:
			datos_cierre_invalidos = True
			errores_datos_cierre.append('El numero de pedido debe ser distinto de cero !')

		importe = request.POST.get('importe')
		importe = importe.encode('latin_1')

		if importe == 0:
			datos_cierre_invalidos = True
			errores_datos_cierre.append('El importe debe ser mayor a cero !')



		importe_nc = request.POST.get('importe_nc')
		importe_nc = importe_nc.encode('latin_1')

		monto_pagar = request.POST.get('monto_pagar')
		monto_pagar = monto_pagar.encode('latin_1')

		paqueteria = request.POST.get('paqueteria')
		paqueteria = paqueteria.encode('latin_1')

		if len(paqueteria)<3:
			datos_cierre_invalidos = True
			errores_datos_cierre.append('Paqueteria debe tener una logitud de al menos 3 caracteres !')

		no_de_guia = request.POST.get('no_de_guia')
		no_de_guia = no_de_guia.encode('latin_1')

		if len(no_de_guia)<3:
			#datos_cierre_invalidos = True
			#errores_datos_cierre.append('Numero de guia debe tener una longitud de al menos 3 caracteres !')
			pass
		proveedor = request.POST.get('proveedor')
		proveedor = proveedor.encode('latin_1')
        

		if datos_cierre_invalidos:
			error = errores_datos_cierre
			data = {'error':error,}
			return HttpResponse(json.dumps(data),content_type='application/json',)



		cursor = connection.cursor()

		''' INICIALIZACION DE VARIABLES '''

		nuevo_status_pedido ='Confirmado' # Para el cierre todos los pedidos toman este status
		error = False
		pedidos_cambiados = 0  

		''' FIN DE INCIALIZACION DE VARIABLES '''


		# Se convierte la fecha de hoy a formatos manejables para insertarlos en el registro.
		hoy = datetime.now()
		fecha_hoy = hoy.strftime("%Y-%m-%d")
		hora_hoy = hoy.strftime("%H:%M:%S") 


		try:

			cursor.execute("START TRANSACTION")
						
			cursor.execute("SELECT id FROM prov_ped_cierre ORDER BY id DESC LIMIT 1 FOR UPDATE;")

			registro = cursor.fetchone()
			id_nuevo_cierre = registro[0]+1



			# Crea nuevo cierre en tabla de cierres !

			
                                                                                                                                                                                                                                                                                                                                                                                               
			cursor.execute("INSERT INTO prov_ped_cierre (id,referencia,total_articulos,FechaColocacion,HoraColocacion,ColocadoVia,TomadoPor,ConfirmadoPor,CerradoPor,FechaCierre,HoraCierre,NumPedido,Importe,ImporteNC,MontoPagar,Paqueteria,NoGuia,prov_id,almacen,Totartrecibidos,Cerrado,Recepcionado) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",(id_nuevo_cierre,referencia,total_articulos,fecha_llegada,hora_hoy,colocado_via,tomado_por,confirmado_por,capturista,fecha_hoy,hora_hoy,pedido,importe,importe_nc,monto_pagar,paqueteria,no_de_guia,proveedor,almacen,total_articulos,True,False))



	        # Recupera cada diccionario y extrae los valores de la llave a buscar.
			for j in datos:
				
				if j is not None: # Procesa solo los registros con contenido
			
				
					print "elegido:", j.get('elegido')
					pedido = j.get("Pedido").encode('latin_1')

					productono = j.get('ProductoNo').strip()
					catalogo =j.get('Catalogo').strip()
					nolinea = j.get('Nolinea').encode('latin_1')
					elegido = j.get('elegido')
					version_original_pedidos_encontrados = j.get('ver_ant_encontrado').strip() # Traemos version anterior del registro pedidos_encontrados, para esto usamos el campo 'encontrado' con el que haremos una  futura comparacion con una nueva lectura al mismo para ver si cambio
					version_original_pedidos_lines = j.get('status').strip() # Traemos version anterior del registro pedidoslines, para esto usamos el campo 'status' con el que hacemos una comparacion con una nueva lectura al mismo para ver si cambio

					# Comienza acceso a BD.

					
					# verifica version actual pedidos_encontrados y de una vez traemos id_cierre que se usara mas adelante
					cursor.execute("SELECT encontrado,id_cierre from pedidos_encontrados WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
					registro = cursor.fetchone()

					# Creea variable version_actual e id_cierre para pedidos_encontrados
					version_actual_pedidos_encontrados=registro[0].strip()
					id_cierre = registro[1]

					# verifica version actual pedidoslines y de una vez se trae el estatus actual para ser mostrado en caso de que la version actual difiera de la anterior
					cursor.execute("SELECT status from pedidoslines WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
					registro = cursor.fetchone()

					# Crea variables de  version actual asi como el actual_estatus para pedidoslines
					
					version_actual_pedidos_lines =  registro[0].strip()

					# Si las versiones no concuerdan crea contador de pedidos_cambiados y sus lista respectiva para ser mostrados al usuario.
					if (version_actual_pedidos_encontrados != version_original_pedidos_encontrados) or (version_actual_pedidos_lines != version_original_pedidos_lines):
						pedidos_cambiados += 1 # actualiza contador de pedidos cambiados durante el proceso
						
					else:

						cursor.execute("UPDATE pedidos_encontrados SET id_cierre=%s,FechaProbable=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and Nolinea=%s;",(id_nuevo_cierre,fecha_llegada,pedido,productono,catalogo,nolinea))

						
						# Actualiza pedidos

						cursor.execute("UPDATE pedidosheader SET FechaUltimaModificacion=%s,HoraModicacion=%s WHERE EmpresaNo=1 and pedidono=%s;",[fecha_hoy,hora_hoy,pedido])							
						cursor.execute("UPDATE pedidoslines SET status=%s,FechaTentativaLLegada=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(nuevo_status_pedido,fecha_llegada,pedido,productono,catalogo,nolinea))


						# Crea o bien actualiza pedidos_status_fechas

						cursor.execute("INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,ProductoNo,Status,catalogo,NoLinea,FechaMvto,HoraMvto,Usuario) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",[1,pedido,productono,nuevo_status_pedido,catalogo,nolinea,fecha_hoy,hora_hoy,capturista])




			cursor.execute("COMMIT;")


		except DatabaseError as error_msg:
		
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':str(error_msg),}
			
			error = True
		except IntegrityError as error_msg:
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':str(error_msg),}
			error = True
		except OperationalError as error_msg:
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':str(error_msg),}
			error = True
		except NotSupportedError as error_msg:
	
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':str(error_msg),}
			error = True
		except ProgrammingError as error_msg:

			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':str(error_msg),}
			error = True
		except (RuntimeError, TypeError, NameError) as error_msg:
			#error_msg = 'Error no relativo a base de datos'
			data = {'status_operacion':'fail','error':str(error_msg),}
			error = True
		except:
			error_msg = "Error desconocido"
			data = {'status_operacion':'fail','error':error_msg,}
			error = True

		cursor.close()

		# Si no hay error, nos devolvera la lista de pedidos cambiados
		# o bien un 'ok' y si hay error nos devolvera el mensaje de error.
		if not error:
			if pedidos_cambiados != 0:
				data={'status_operacion':'ok','error':'Algunos registros no fueron procesados, debido a que fueron modificados por otra transaccion mientras Ud los marcaba !'}
			else:
				data={'status_operacion':'ok',}
		return HttpResponse(json.dumps(data),content_type='application/json',)



@login_required(login_url = "/pedidos/acceso/")
def elegir_almacen_a_cerrar(request):
	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..
	
	mensaje = " "
	reg_encontrados = 0

	# elimina cualquier registro de la session.
	session_id = request.session.session_key
	# Asigna is_staff para validacines
	is_staff = request.session['is_staff']

	hoy = date.today()
	hace_un_mes = hoy + timedelta(-120)





	"""cursor = connection.cursor()
	cursor.execute("DELETE FROM pedidos_pedidos_tmp where session_key= %s;",[session_id])	
	
	cursor.close()"""


	#for key,value in pr_dict.items():
	#	print key,value 
	
	 
	if request.method =='POST':
		
		form = ElegirAlmacenaCerrarForm(request.POST)
		print form.is_valid()
		print form.errors
		if form.is_valid():
		

		#proveedor = form.cleaned_data['proveedor']
		#almacen = form.cleaned_data['almacen']'''

			proveedor = request.POST.get('proveedor')
			almacen = request.POST.get('almacen')

			try:
				cursor =connection.cursor()
			 	#cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a a USE INDEX (`ind_emp_prov_cat_codpro`) ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) WHERE e.empresano=1 and a.idProveedor=%s and e.BodegaEncontro=%s and l.Status='Encontrado' and e.id_cierre=0;",(proveedor,almacen))
				#cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status FROM pedidos_encontrados e USE INDEX (ind_bodega_encontrado_cierre)  INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (p.EmpresaNo=1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (ind_emp_prov_cat_codpro) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) WHERE e.empresano=1 and a.idProveedor=%s  and e.BodegaEncontro=%s  and e.encontrado='S' and l.Status='Encontrado' and e.id_cierre=0 ORDER BY a.idestilo;",(proveedor,almacen))
				cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( l.EmpresaNo=1 and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p USE INDEX (ind_emp_fechapedido_numped) ON (p.EmpresaNo=1 and e.Pedido=p.PedidoNo) INNER JOIN articulo a USE INDEX (ind_emp_prov_cat_codpro) ON (a.EmpresaNo=1 and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo)  WHERE e.empresano=1 and a.idProveedor=%s and p.FechaPedido>=%s and p.FechaPedido<=%s and e.BodegaEncontro=%s  and e.encontrado='S' and l.Status='Encontrado' and e.id_cierre=0 ORDER BY a.idestilo;",(proveedor,hace_un_mes,hoy,almacen))
	
			except DatabaseError as e:
				mensaje = "Error de base de datos: "+str(e)


			if cursor:

				registros = dictfetchall(cursor)
				mensaje ="Lista de registros ya colocados en el almacen seleccionado que no han sido cerrados."

				for j in cursor:
					reg_encontrados +=1
				cursor.close()	
			else:
				registros ={}
				mensaje = "Registros no encontrados para esta consulta !"
				cursor.close()
				return render(request,'pedidos/elegir_almacen_a_cerrar.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})

			#return render(request,'pedidos/muestra_colocados_a_cerrar.html',{'registros':registros,'mensaje':mensaje,'reg_encontrados':reg_encontrados,'almacen':almacen,})	
			return render(request,'pedidos/muestra_colocados_a_cerrar.html',{'registros':registros,'mensaje':mensaje,'almacen':almacen,'reg_encontrados':reg_encontrados,'proveedor':proveedor,})	

			#return render(request,'pedidos/elegir_almacen_a_cerrar.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})

		else:	
			
			return render(request,'pedidos/elegir_almacen_a_cerrar.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})

	form = ElegirAlmacenaCerrarForm()
	return render(request,'pedidos/elegir_almacen_a_cerrar.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})	

"""def muestra_encontrados_almacen(request):
	#pdb.set_trace()	
	if request.method == 'GET':
	#if request.is_ajax() and request.method == 'GET':
		proveedor = request.GET['proveedor']
		almacen = request.GET['almacen']

		try:
			cursor =connection.cursor()
		 	cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,e.encontrado as ver_ant_encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,l.OpcionCompra,e.observaciones,p.idSucursal,l.Observaciones,e.`2`,e.`3`,e.`4`,e.`5`,e.`6`,e.`7`,e.`8`,e.`9`,e.`10`,l.status FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) WHERE e.empresano=1 and a.idProveedor=%s and e.BodegaEncontro=%s and l.Status='Encontrado' and e.id_cierre=0;",(proveedor,almacen))
		
		except DatabaseError as e:
			mensaje = e


		if cursor:

		registros = dictfetchall(cursor)
		mensaje ="ok"
		else:
			registros ={}
			mensaje = "Registros no encontrados para esta consulta !"
		cursor.close()
		return render(request,'pedidos/muestra_colocados_a_cerrar.html',{'registros':registros,'mensaje':mensaje,'reg_encontrados':reg_encontrados,'almacen':almacen,})	"""
def pruebaImprime(request):
		a = '<html><p class="imprime"><font size="6"> ES SHOES MULTIMARCAS </font></p>'
		b = '<p class="imprime"><font size="6"> prueba de impresion</font> </p><br>'
		c = '<p class="imprime"><font size="5"> ES SHOES MULTIMARCAS </font></p>'
		d = '<p class="imprime"><font size="5"> prueba de impresion</font> </p><br>'
		e = '<p class="imprime"><font size="4"> ES SHOES MULTIMARCAS </font></p>'
		f = '<p class="imprime"><font size="4"> prueba de impresion</font> </p><br>'
		g = '<p class="imprime"><font size="0.5"> prueba </font></p>'
		h = '<p class="imprime"><font size="1"> prueba de impresion</font> </p><br></html>'
		
		
		
		return HttpResponse(a+b+c+d+e+f+g+h)

@login_required(login_url = "/pedidos/acceso/")
def seleccion_cierre_rpte_cotejo(request):
	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..

	
	mensaje = " "
	reg_encontrados = 0

	# elimina cualquier registro de la session.
	session_id = request.session.session_key
	# Asigna is_staff para validacines
	is_staff = request.session['is_staff']


	
	 
	if request.method == 'POST':

		form = SeleccionCierreRpteCotejoForm(request.POST)

		if form.is_valid():
		
			

			proveedor = request.POST.get('proveedor_rpte_cotejo')
			cierre =  request.POST.get('cierre_rpte_cotejo')

			#proveedor = proveedor.encode('latin_1')
			#cierre = cierre.encode('latin_1')

			print cierre
			
			try:
				cursor =connection.cursor()
			 	#cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,e.BodegaEncontro,e.encontrado,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,a.idProveedor,l.FechaMaximaEntrega,p.idSucursal,l.Observaciones,suc.nombre as sucnom,concat(trim(soc.nombre),' ',trim(soc.appaterno),' ',trim(soc.apmaterno)) as socnom FROM pedidoslines l LEFT JOIN  pedidos_encontrados e on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo)  INNER JOIN pedidos_status_fechas f on  ( e.EmpresaNo=f.EmpresaNo and e.Pedido=f.Pedido and e.ProductoNo=f.ProductoNo and e.Catalogo=f.catalogo and e.NoLinea=f.NoLinea) inner join sucursal suc on (suc.empresano=1 and suc.SucursalNo=p.idsucursal) inner join asociado soc on (soc.EmpresaNo=1 and soc.AsociadoNo=p.AsociadoNo) WHERE a.idProveedor=%s and  l.Status='Confirmado'  and f.Status='Confirmado' and id_cierre=%s;",(proveedor,cierre))
			 	cursor.execute("SELECT e.id_cierre,suc.nombre as sucnom,e.Pedido,p.AsociadoNo,concat(trim(soc.nombre),'_',trim(soc.appaterno),'_',trim(soc.apmaterno)) as socnom,p.FechaPedido,e.Catalogo,a.idmarca,a.idestilo,a.idcolor,if (trim(a.talla)<>'NE',a.talla,l.observaciones) as talla ,l.precio,alm.razonsocial as bodega FROM pedidoslines l LEFT JOIN  pedidos_encontrados e on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo)  INNER JOIN pedidos_status_fechas f on  ( e.EmpresaNo=f.EmpresaNo and e.Pedido=f.Pedido and e.ProductoNo=f.ProductoNo and e.Catalogo=f.catalogo and e.NoLinea=f.NoLinea) inner join sucursal suc on (suc.empresano=1 and suc.SucursalNo=p.idsucursal) inner join asociado soc on (soc.EmpresaNo=1 and soc.AsociadoNo=p.AsociadoNo) inner join almacen alm on (alm.empresano=1 and alm.ProveedorNo=a.idProveedor and alm.Almacen=e.BodegaEncontro) WHERE a.idProveedor=%s and  l.Status='Confirmado'  and f.Status='Confirmado' and id_cierre=%s;",(proveedor,cierre))
			except DatabaseError as e:
				mensaje = e
				print "error de base de datos:",e

			registros = dictfetchall(cursor)
			
			if registros:
				response = HttpResponse(content_type='text/csv')
				response['Content-Disposition'] = 'attachment; filename="CIERRE.csv"'

				writer = csv.writer(response)
				writer.writerow(['ID_CIERRE', 'SUCURSAL', 'PEDIDO', 'NUM_SOCIO','NOMBRE_SOCIO','FECHA','CATALOGO','MARCA','ESTILO','COLOR','TALLA','PRECIO','BODEGA'])

			    
				for registro in registros:
					print registro
					'''if (registro[talla]).strip()=='NE':

						talla = registro[Observaciones]
					else:
						talla = registro[talla]'''

					# El registro contiene los elementos a exportar pero no en el orden que se necesita para eso se define la siguiente lista con las llaves en el orden que se desea se exporten	
					llaves_a_mostrar = ['id_cierre','sucnom','Pedido','AsociadoNo','socnom','FechaPedido','Catalogo','idmarca','idestilo','idcolor','talla','precio','bodega'] 
					# Con la siguiente linea se pasan los elementos del diccionario 'registro' a 'lista' de acuerdo al orden mostrado en 'llaves_a_mostrar'
					lista = [registro[x] for x in llaves_a_mostrar]
				
					writer.writerow(lista)
				cursor.close()
				return response			
				
			else:
				mensaje='No se encontraron registros con estos parametros !'
				cursor.close()
				return render(request,'pedidos/seleccion_cierre_rpte_cotejo.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})



		else:
			return render(request,'pedidos/seleccion_cierre_rpte_cotejo.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})
				

				


				

		
			#return render(request,'pedidos/elegir_almacen_a_cerrar.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})

		

	form = SeleccionCierreRpteCotejoForm()
	print form
	return render(request,'pedidos/seleccion_cierre_rpte_cotejo.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})	



def lista_cierres(id_prov):
	#pdb.set_trace()
	try:
		cursor=connection.cursor()
		# En la siguiente linea, la FechaColocaicion guarda en realidad la fecha tentativa de llegada.
		cursor.execute("SELECT c.id,c.NumPedido,c.referencia,c.FechaCierre,c.FechaColocacion,c.HoraCierre,c.total_articulos,c.importe, a.RazonSocial from prov_ped_cierre c inner join almacen a on (c.almacen=a.almacen and a.ProveedorNo=c.prov_id and a.empresano=1) where c.Cerrado and not (c.Recepcionado) and  c.prov_id=%s order by c.id desc;",[id_prov,])
	
	except DatabaseError as db_err:
	
		print "error en db:",db_err
	
	listaalm = dictfetchall(cursor)

	print listaalm
	
	
	return (listaalm)	



def combo_proveedor_rpte_cotejo(request,*args,**kwargs):
	#pdb.set_trace()

	if request.is_ajax() and request.method == 'GET':
		id_prov = request.GET['id_prov']
		
		
		# Trae la lista de catalogos con los parametros indicados:
		l = lista_cierres(id_prov)
		
		#data = serializers.serialize('json',r,fields=('clasearticulo',))
		
		# La siguiente instruccion genera una variable data con los datos en formato json.
		# En la linea anterior ( que esta comentada ), trataba de usar
		# serielizers para convertir a json pero no funciono.

		data = json.dumps(l,cls=DjangoJSONEncoder)
		return HttpResponse(data,content_type='application/json')
	else:
		raise Http404


# PROCESAMIENTO DE RECEPCIONES


def procesar_recepcion(request):
	
	#pdb.set_trace()
	# rutina para grabar header y lines 
	def graba_header_lines():

		cursor.execute("UPDATE pedidosheader SET FechaUltimaModificacion=%s,HoraModicacion=%s WHERE EmpresaNo=1 and pedidono=%s;",[fecha_hoy,hora_hoy,pedido])							
		cursor.execute("UPDATE pedidoslines SET status=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(nuevo_status_pedido,pedido,productono,catalogo,nolinea))
		return


	contador_productos_recibidos = 0



	if request.is_ajax()  and request.method == 'POST':
		# Pasa a una variable la tabla  recibida en json string
		TableData = request.POST.get('TableData')
		
		# carga la tabla ( la prepara con el formato de lista adecuado para leerla)
		datos = json.loads(TableData)

		capturista = request.session['socio_zapcat']
		

		almacen = request.POST.get('almacen')
		almacen = almacen.encode('latin_1')
		marcartodo_nollego = request.POST.get('marcartodo_nollego')
		cierre = request.POST.get('cierre').encode('latin_1')
		nueva_fecha_llegada = request.POST.get('nueva_fecha_llegada').encode('latin_1')
		
		if nueva_fecha_llegada == u'None': 

 			f_convertida = '1901/01/01'
 		else:
 			f_convertida = datetime.strptime(nueva_fecha_llegada, "%d/%m/%Y").strftime("%Y%m%d")
			#f_convertida = datetime.strptime(nueva_fecha_llegada, "%d/%m/%Y").date()

		cursor = connection.cursor()

		''' INICIALIZACION DE VARIABLES '''

		pedidos_cambiados = 0 # inicializa contador de pedidos que sufrieron cambios entre la lectura inicial y el commit.
		
		nuevo_status_pedido = '' # variable que servira para  guardar el status de pedido segun se vayan cumpliendo condiciones,
							# posteriomente se utilizara par actualizar el status del pedido en pedidoslines y pedidos_status_confirmacion.

		error = False

		''' FIN DE INCIALIZACION DE VARIABLES '''


		# Se convierte la fecha de hoy a formatos manejables para insertarlos en el registro.
		hoy = datetime.now()
		fecha_hoy = hoy.strftime("%Y-%m-%d")
		hora_hoy = hoy.strftime("%H:%M:%S") 

		cursor.execute("START TRANSACTION;")


        # Recupera cada diccionario y extrae los valores de la llave a buscar.
		
		try:
		
			for j in datos:
				
				pedido = j.get("Pedido").encode('latin_1')

				productono = j.get('ProductoNo').strip()
				catalogo =j.get('Catalogo').strip()
				nolinea = j.get('Nolinea').encode('latin_1')
				version_original_pedidos_lines = j.get('status').strip() # Traemos version anterior del registro pedidoslines, para esto usamos el campo 'status' con el que hacemos una comparacion con una nueva lectura al mismo para ver si cambio, no lo pasamos por encode (se queda en utf)
				incidencia = j.get('incidencia').encode('latin_1')
				# Comienza acceso a BD.

				
				# verifica version actual pedidos_encontrados y de una vez traemos id_cierre que se usara mas adelante
				cursor.execute("SELECT id_cierre from pedidos_encontrados WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
				registro = cursor.fetchone()

				# Creea variable version_actual e id_cierre para pedidos_encontrados
				id_cierre = registro[0]

				# verifica version actual pedidoslines y de una vez se trae el estatus actual para ser mostrado en caso de que la version actual difiera de la anterior
				cursor.execute("SELECT status from pedidoslines WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
				registro = cursor.fetchone()

				# Crea variables de  version actual asi como el actual_estatus para pedidoslines
				
				version_actual_pedidos_lines =  registro[0].strip()

				
				# Si las versiones no concuerdan crea contador de pedidos_cambiados y sus lista respectiva para ser mostrados al usuario.
				if (version_actual_pedidos_lines != version_original_pedidos_lines):
					pedidos_cambiados += 1 # actualiza contador de pedidos cambiados durante el proceso
				else:

					print marcartodo_nollego
					# Si el pedido es correcto y llego.
					if incidencia == '1':
						nuevo_status_pedido = 'Aqui'
					
						graba_header_lines()

						

						cursor.execute("""INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,
										ProductoNo,Status,
										catalogo,NoLinea,
										FechaMvto,HoraMvto,Usuario)
										VALUES (%s,%s,%s,%s,
											%s,%s,%s,%s,%s);""",
										[1,pedido,productono,nuevo_status_pedido,
										catalogo,nolinea,fecha_hoy,hora_hoy,capturista])




						contador_productos_recibidos += 1

					# Si el pedido No llego

					elif incidencia == '2' and marcartodo_nollego != 'on':
						
						nuevo_status_pedido='Por Confirmar'
						# Actualiza (pone en blancos registro de pedidos_encontrados)
						cursor.execute("UPDATE pedidos_encontrados SET id_cierre=0,FechaEncontrado='19010101',FechaProbable='19010101',BodegaEncontro=0,`2`='',`3`='',`4`='',`5`='',`6`='',`7`='',`8`='',`9`='',`10`='',encontrado='' WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
					
						# Actualiza header y lines con nuevo status
						graba_header_lines()
						
						# Elimina todos los status del articulo excepto el de 'Por Confirmar'
						cursor.execute("DELETE FROM pedidos_status_fechas WHERE empresano=1 and pedido=%s and productono=%s and catalogo=%s and nolinea=%s and not (status='Por Confirmar');",(pedido,productono,catalogo,nolinea))

					# Si el pedido completo no llego, se deja como esta y solo se cambia fecha tentativa de llegada
					
					elif incidencia == '2' and marcartodo_nollego == 'on':

						cursor.execute("UPDATE pedidosheader SET FechaUltimaModificacion=%s,HoraModicacion=%s WHERE EmpresaNo=1 and pedidono=%s;",[fecha_hoy,hora_hoy,pedido])							
						cursor.execute("UPDATE pedidoslines SET FechaTentativaLLegada=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(f_convertida,pedido,productono,catalogo,nolinea))
						cursor.execute("UPDATE prov_ped_cierre set TotArtRecibidos=%s, recepcionado=0,fechacolocacion=%s WHERE id=%s;",(contador_productos_recibidos,f_convertida,cierre))

					elif incidencia > '2':
						# Si el producto llego pero no pasa el control de calidad

						# GENERA UN NUEVO PRODUCTO CON STATUS DE 'Por Confirmar'
						# Y CAMBIA EL STATUS DEL ACTUAL A "Por Devolver"

						# Trae PedidoNuevo
						cursor.execute("SELECT pedidono  from pedidosheader WHERE empresano=1 order by pedidono desc limit 1 FOR UPDATE;")
						registro = cursor.fetchone()
						PedidoNuevo = registro[0]+1

						# Trae  datos de pedidosheader para replicarlos en un nuevov registro con el nuevo numero de pedido;
						cursor.execute("SELECT EmpresaNo,PedidoNo,FechaPedido,HoraPedido,Saldototal,VtaTotal,UsuarioCrea,FechaUltimaModificacion,FechaCreacion,HoraCreacion,HoraModicacion,UsuarioModifica,idSucursal,AsociadoNo,tiposervicio,viasolicitud  from pedidosheader WHERE empresano=1 and pedidono=%s;",[pedido])
						
						registroh = cursor.fetchone()
						
						reg_fecha_pedido = registroh[2]
						reg_Hora_pedido = registroh[3]
						reg_Saldototal= registroh[4]
						reg_VtaTotal = registroh[5]
						reg_UsuarioCrea = registroh[6]
						reg_FechaUltimaModificacion = registroh[7]
						reg_FechaCreacion = registroh[8]
						reg_HoraCreacion = registroh[9]
						reg_HoraModicacion = registroh[10]
						reg_UsuarioModifica = registroh[11]
						reg_idSucursal = registroh[12]
						reg_AsociadoNo = registroh[13]
						reg_tiposervicio = registroh[14]
						reg_viasolicitud = registroh[15]

						cursor.execute("SELECT EmpresaNo,\
							Pedido,ProductoNo,CantidadSolicitada,\
							precio,subtotal,PrecioOriginal,Status,\
							RemisionNo,NoNotaCreditoPorPedido,\
							NoNotaCreditoPorDevolucion,NoRequisicionAProveedor,\
							NoNotaCreditoPorDiferencia,catalogo,NoLinea,\
							plazoentrega,OpcionCompra,FechaMaximaEntrega,\
							FechaTentativaLLegada,FechaMaximaRecoger,Observaciones,\
							AplicarDcto FROM pedidoslines WHERE empresano=1 and pedido=%s\
							 and productono=%s and catalogo=%s and nolinea=%s;",\
							 (pedido,productono,catalogo,nolinea))
						
						registrol = cursor.fetchone()
						
						reg_ProductoNo = registrol[2]
						reg_CantidadSolicitada = registrol[3]
						reg_precio =registrol[4]
						reg_subtotal =  registrol[5]
						reg_PrecioOriginal =  registrol[6]
						reg_Status = registrol[7]
						reg_RemisionNo = registrol[8]
						reg_NoNotaCreditoPorPedido = registrol[9]
						reg_NoNotaCreditoPorDevolucion = registrol[10]
						reg_NoRequisicionAProveedor =  registrol[11]
						reg_NoNotaCreditoPorDiferencia = registrol[12]
						reg_catalogo = registrol[13]
						reg_NoLinea = registrol[14]
						reg_plazoentrega = registrol[15]
						reg_OpcionCompra = registrol[16]
						reg_FechaMaximaEntrega = registrol[17]
						reg_FechaTentativaLLegada = registrol[18]
						reg_FechaMaximaRecoger = registrol[19]
						reg_Observaciones = registrol[20]
						reg_AplicarDcto = registrol[21]


						cursor.execute("SELECT temporada from pedidoslinestemporada\
						 WHERE empresano=1 and pedido = %s and productono=%s\
						  and catalogo=%s and nolinea=%s;",\
						  (pedido,productono,catalogo,nolinea))
						
						registrot = cursor.fetchone()

						reg_temporada = registrot[0] 

						cursor.execute("""INSERT INTO pedidosheader (EmpresaNo,PedidoNo,
																FechaPedido,HoraPedido,
																Saldototal,VtaTotal,
																UsuarioCrea,FechaUltimaModificacion,
																FechaCreacion,HoraCreacion,
																HoraModicacion,UsuarioModifica,
																idSucursal,AsociadoNo,
																tiposervicio,viasolicitud)
																VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
																(1,PedidoNuevo,reg_fecha_pedido,reg_Hora_pedido,
																reg_Saldototal,reg_VtaTotal,
																reg_UsuarioCrea,reg_FechaUltimaModificacion,
																reg_FechaCreacion,reg_HoraCreacion,
																reg_HoraModicacion,reg_UsuarioModifica,
																reg_idSucursal,reg_AsociadoNo,
																reg_tiposervicio,reg_viasolicitud))

						cursor.execute("""INSERT INTO pedidoslines (EmpresaNo,Pedido,
																ProductoNo,CantidadSolicitada,
																precio,subtotal,PrecioOriginal,
																Status,RemisionNo,NoNotaCreditoPorPedido,
																NoNotaCreditoPorDevolucion,NoRequisicionAProveedor,
																NoNotaCreditoPorDiferencia,catalogo,
																NoLinea,plazoentrega,OpcionCompra,
																FechaMaximaEntrega,FechaTentativaLLegada,
																FechaMaximaRecoger,Observaciones,AplicarDcto)
																VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
																(1,PedidoNuevo,reg_ProductoNo,
																reg_CantidadSolicitada,
																reg_precio,
																reg_subtotal,
																reg_PrecioOriginal,
																'Por Confirmar',
																reg_RemisionNo,
																reg_NoNotaCreditoPorPedido,
																reg_NoNotaCreditoPorDevolucion,
																reg_NoRequisicionAProveedor,
																reg_NoNotaCreditoPorDiferencia,
																reg_catalogo,
																reg_NoLinea,
																reg_plazoentrega,
																reg_OpcionCompra,
																reg_FechaMaximaEntrega,
																reg_FechaTentativaLLegada,
																reg_FechaMaximaRecoger,
																reg_Observaciones,
																reg_AplicarDcto))



						cursor.execute("""INSERT INTO pedidoslinestemporada (EmpresaNo,Pedido,
																ProductoNo,catalogo,
																NoLinea,Temporada)
																VALUES(%s,%s,%s,%s,%s,%s);""",[1,PedidoNuevo,productono,
																catalogo,nolinea,reg_temporada])
															
						cursor.execute("""INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,
																ProductoNo,Status,
																catalogo,NoLinea,
																FechaMvto,HoraMvto,Usuario)
																VALUES (%s,%s,%s,%s,
																	%s,%s,%s,%s,%s);""",
																[1,PedidoNuevo,reg_ProductoNo,'Por Confirmar',
																catalogo,nolinea,reg_FechaCreacion,reg_HoraCreacion,reg_UsuarioCrea])
						
						cursor.execute("""INSERT INTO pedidos_notas (EmpresaNo,Pedido,
																ProductoNo,catalogo,
																NoLinea,observaciones)
																VALUES(%s,%s,%s,%s,%s,%s);""",[1,PedidoNuevo,productono,
																catalogo,nolinea,''])									






						cursor.execute("""INSERT INTO pedidos_encontrados(EmpresaNo,Pedido,
							ProductoNo,Catalogo,
							NoLinea,FechaEncontrado,
							BodegaEncontro,FechaProbable,
							`2`,`3`,`4`,`5`,`6`,`7`,`8`,
							`9`,`10`,encontrado,id_cierre,
							causadevprov,observaciones)
							VALUES (%s,%s,%s,%s,%s,%s,%s,%s,
								%s,%s,%s,%s,%s,%s,%s,%s,%s,
								%s,%s,%s,%s);""",
							[1,PedidoNuevo,reg_ProductoNo,catalogo,
							nolinea,'19010101',0,'19010101',
							'','','','','','','','','','',0,0,''])

						# CAMBIA STATUS AL PRODUCTO ACTUAL
						cursor.execute("UPDATE pedidoslines SET status='Por Devolver' WHERE empresano=1 and pedido=%s and productono=%s and catalogo=%s and nolinea=%s;",[pedido,productono,catalogo,nolinea])
						cursor.execute("UPDATE pedidosheader SET FechaUltimaModificacion=%s,HoraModicacion=%s WHERE EmpresaNo=1 and pedidono=%s;",[fecha_hoy,hora_hoy,pedido])							
						cursor.execute("""INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,
																ProductoNo,Status,
																catalogo,NoLinea,
																FechaMvto,HoraMvto,Usuario)
																VALUES (%s,%s,%s,%s,
																	%s,%s,%s,%s,%s);""",
																[1,pedido,reg_ProductoNo,'Por Devolver',
																catalogo,nolinea,fecha_hoy,hora_hoy,capturista])
					else:
						pass	
					

				# Marca como recepcionado todo el pedido a menos que se haya marcado todo el pedido como 'no llego'
				#if not ((incidencia == '2' and marcartodo_nollego=='on') or incidencia=='0'):

				#	cursor.execute("UPDATE prov_ped_cierre set TotArtRecibidos=%s, recepcionado=1 WHERE id=%s;",(contador_productos_recibidos,cierre))





			cursor.execute("COMMIT;")


		except DatabaseError as error:
			print error
		
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error en base de datos',}
			cursor.close()
			return HttpResponse(json.dumps(data),content_type='application/json',)
		except:
			data = {'status_operacion':'fail','error':'Error no relativo a db.'}
			cursor.close()
			return HttpResponse(json.dumps(data),content_type='application/json',)

		#pdb.set_trace()
		
		# Verifica que no existan registros del cierre con status de Confirmado, caso contrario es que faltan por cerrar
		cursor.execute("SELECT count(*) as reg_sin_recepcionar FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) WHERE e.empresano=1 and l.Status='Confirmado' and e.id_cierre=%s;",(cierre,))
		reg_sin_recepcionar = cursor.fetchone()
				
		try:

			"""Si no hay una nueva_fecha_de_llegada, es decir que (f_convertida sea igual a 1901/01/01) no se marca como
			recepcionado el cierre, de otra manera se marca como recepcionado """

			if f_convertida == '1901/01/01': 

				cursor.execute("START TRANSACTION;")
				# Si ya se recepcionaron todos, marca el cierre como recepcionado
				if reg_sin_recepcionar[0] == 0:

					cursor.execute("UPDATE prov_ped_cierre set recepcionado=1 WHERE id=%s;",(cierre,))
				else:
				# De otra manera solo incremeta el contador de recepcionados

					cursor.execute("UPDATE prov_ped_cierre set TotArtRecibidos=TotArtRecibidos+%s WHERE id=%s;",(contador_productos_recibidos,cierre))

				cursor.execute("COMMIT;")

		except DatabaseError as error_bd_actualizar_total_cierres:
			
			cursor.execute("ROLLBACK;")
			print error_bd_actualizar_total_cierres
			error = True

		cursor.close()

		# Si no hay error, nos devolvera la lista de pedidos cambiados
		# o bien un 'ok' y si hay error nos devolvera el mensaje de error.
		if not error:
			if pedidos_cambiados != 0:
				data={'status_operacion':'ok','error':'Algunos registros no fueron procesados, debido a que fueron modificados por otra transaccion mientras Ud los marcaba !'}
			else:
				data={'status_operacion':'ok',}
		return HttpResponse(json.dumps(data),content_type='application/json',)



# SELECCION DEL CIERRE PARA RECEPEPCION

@login_required(login_url = "/pedidos/acceso/")
def seleccion_cierre_recepcion(request):
	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..

	
	mensaje = " "
	reg_encontrados = 0

	# elimina cualquier registro de la session.
	session_id = request.session.session_key
	# Asigna is_staff para validacines
	is_staff = request.session['is_staff']


	
	 
	if request.method == 'POST':

		form = SeleccionCierreRecepcionForm(request.POST)

		if form.is_valid():

			proveedor = request.POST.get('proveedor_rpte_cotejo')
			cierre =  request.POST.get('cierre_rpte_cotejo')
			marcartodo_nollego = request.POST.get('marcartodo_nollego')
			nueva_fecha_llegada =request.POST.get('nueva_fecha_llegada')
			ordenado_por = request.POST.get('ordenado_por')

			cursor = connection.cursor()

			try:
				if ordenado_por == u'1':
					cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,l.status,e.BodegaEncontro,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,p.idSucursal,l.Observaciones,suc.nombre,concat(trim(aso.nombre),' ',trim(aso.appaterno),' ',trim(aso.apmaterno)) as nombre_socio FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN sucursal suc on (p.idSucursal=suc.SucursalNo) inner join asociado aso on (p.empresano=1 and aso.asociadono=p.asociadono) WHERE e.empresano=1 and a.idProveedor=%s and  l.Status='Confirmado' and e.id_cierre=%s order by a.idestilo;",(proveedor,cierre))
				elif ordenado_por == u'2':
					cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,l.status,e.BodegaEncontro,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,p.idSucursal,l.Observaciones,suc.nombre,concat(trim(aso.nombre),' ',trim(aso.appaterno),' ',trim(aso.apmaterno)) as nombre_socio FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN sucursal suc on (p.idSucursal=suc.SucursalNo) inner join asociado aso on (p.empresano=1 and aso.asociadono=p.asociadono) WHERE e.empresano=1 and a.idProveedor=%s and  l.Status='Confirmado' and e.id_cierre=%s order by p.asociadono,a.idestilo;",(proveedor,cierre))
				else:
					cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,l.status,e.BodegaEncontro,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,p.idSucursal,l.Observaciones,suc.nombre,concat(trim(aso.nombre),' ',trim(aso.appaterno),' ',trim(aso.apmaterno)) as nombre_socio FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN sucursal suc on (p.idSucursal=suc.SucursalNo) inner join asociado aso on (p.empresano=1 and aso.asociadono=p.asociadono) WHERE e.empresano=1 and a.idProveedor=%s and  l.Status='Confirmado' and e.id_cierre=%s order by p.idsucursal,p.asociadono,a.idestilo;",(proveedor,cierre))

			except DatabaseError as e:
				print "Error base de datos"

			
			if cursor:

				registros = dictfetchall(cursor)
				cursor.close()
				mensaje = "Recepcion de articulos del cierre " + str(cierre) +"  :"		
				return render(request,'pedidos/muestra_registros_recepcionar.html', {'registros':registros,'mensaje':mensaje,'is_staff':is_staff,'marcartodo_nollego':marcartodo_nollego,'nueva_fecha_llegada':nueva_fecha_llegada,'cierre':cierre})

				
			else:
				mensaje='No se encontraron registros con estos parametros !'
				cursor.close()
				
				return render(request,'pedidos/seleccion_cierre_recepcion.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})



		else:

			print form.non_field_errors
			#form = SeleccionCierreRecepcionForm()
			return render(request,'pedidos/seleccion_cierre_recepcion.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})
				
	form = SeleccionCierreRecepcionForm()
	print form
	return render(request,'pedidos/seleccion_cierre_recepcion.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})	


''' ***  DETALLE DEL DOCUMENTO O MODIFICACION DE DOCUMENTO *** '''



def detalle_documento(request,NoDocto):
	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..
	msg = ''
	if request.method == 'POST':
		form = DetalleDocumentoForm(request.POST)
		if form.is_valid():
			nodocto = request.POST.get('nodocto')
			tipodedocumento =request.POST.get('tipodedocumento')
			#vtadecatalogo = request.POST.get('vtadecatalogo').encode('latin_1')
			asociado = request.POST.get('asociado')
			concepto = request.POST.get('concepto')
			monto = request.POST.get('monto')
			bloquearnotacredito = request.POST.get('bloquearnotacredito')


			''' OJO, los siguientes if's sirven para verificar 
			los campos boleanos 'vtadecatalogo' y 'bloquearnotacredito' 
			dado que el templeate los regresa con valores 'None' y 'on'
			esto hay que investigar porque lo hace, mientras
			se actualizan con calores correctos dependiendo de lo que 
			traigan '''

			
			if bloquearnotacredito is None:
				bloquearnotacredito = False
			if bloquearnotacredito == 'on':
				bloquearnotacredito = True


			cursor =  connection.cursor()
			try:

				cursor.execute('START TRANSACTION')
				cursor.execute('UPDATE documentos SET asociado=%s,concepto=%s,monto=%s,BloquearNotaCredito=%s WHERE nodocto=%s;',(asociado,concepto,monto,bloquearnotacredito,NoDocto,))
				cursor.execute("COMMIT;")
				return HttpResponseRedirect(reverse('pedidos:documentos'))
				

			except DatabaseError as e:
				print e
				
				cursor.execute('ROLLBACK;')
				msg = 'Error en base de datos !'
				return HttpResponse('<h3>Ocurrio un error en la base de datos</h3><h2>{{e}}</h2>')

		else:
			nodocto = NoDocto

			return render(request,'pedidos/detalle_documento.html',{'form':form,'nodocto':nodocto,})
	else:	
				
		cursor =  connection.cursor()
		cursor.execute("SELECT d.NoDocto,\
			                   d.TipoDeDocumento,\
			                   d.VtaDeCatalogo,\
			                   d.Asociado,\
			                   d.Concepto,\
			                   d.Monto,\
			                   d.BloquearNotaCredito,\
			                   CONCAT(a.nombre,' ',a.appaterno,' ',a.apmaterno) as nombre_socio \
			                   FROM documentos d INNER JOIN asociado a ON (a.empresano=d.empresano and d.asociado=a.asociadono) \
			                   WHERE d.NoDocto=%s and d.empresano=1;",(NoDocto,))	
		datos_documento =  cursor.fetchone()
		
		nodocto = datos_documento[0]
		tipodedocumento = datos_documento[1] 
		
		if bool(datos_documento[2]) is True:
			ventadecatalogo = 'Si' 
		else:
			ventadecatalogo = 'No'
		asociado = datos_documento[3]
		concepto = datos_documento[4]
		monto = datos_documento[5]
		bloquearnotacredito = datos_documento[6]
		
		cursor.close()

		form =  DetalleDocumentoForm(initial= {'nodocto':nodocto,'tipodedocumento':tipodedocumento,'asociado':asociado,'concepto':concepto,'monto':monto,'bloquearnotacredito':bloquearnotacredito,})	
		return render(request,'pedidos/detalle_documento.html',{'form':form,'nodocto':nodocto,'tipodedocumento':tipodedocumento,'ventadecatalogo':ventadecatalogo,'msg':msg})



''' ***** CREACION DEL DOCUMETO **** '''

def crea_documento(request):
	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..
	msg = ''

	capturista = request.session['socio_zapcat']
	id_sucursal = request.session['sucursal_activa']

	if request.method == 'POST':
		form = CreaDocumentoForm(request.POST)
		if form.is_valid():
			tipodedocumento =request.POST.get('tipodedocumento')
			vtadecatalogo = request.POST.get('vtadecatalogo')
			proveedor = request.POST.get('proveedor')
			anio = request.POST.get('anio')
			temporada = request.POST.get('temporada')
			asociado = request.POST.get('asociado')
			concepto = request.POST.get('concepto')
			monto = request.POST.get('monto')

			fecha_hoy = ''
			hora_hoy =''
			
			# Para el caso de creditos antepone una 'C:' en el concepto.

			if tipodedocumento == 'Credito':
				concepto = "C: " + concepto

			fecha_hoy,hora_hoy = trae_fecha_hora_actual(fecha_hoy,hora_hoy)
			print fecha_hoy
			print hora_hoy

			

			''' OJO, los siguientes if's sirven para verificar 
			los campos boleanos 'vtadecatalogo' y 'bloquearnotacredito' 
			dado que el templeate los regresa con valores 'None' y 'on'
			esto hay que investigar porque lo hace, mientras
			se actualizan con calores correctos dependiendo de lo que 
			traigan '''

			
			if vtadecatalogo is None:
				vtadecatalogo = False
			if vtadecatalogo == 'on':
				vtadecatalogo = True


			cursor =  connection.cursor()
			try:

				cursor.execute('START TRANSACTION')

				cursor.execute('SELECT nodocto from documentos order by nodocto desc limit 1;')
				ultimodocto = cursor.fetchone()

				cursor.execute('SELECT consecutivo from documentos WHERE tipodedocumento=%s ORDER BY tipodedocumento,consecutivo desc limit 1;',(tipodedocumento,))
				ultimoconsec = cursor.fetchone()



				cursor.execute('''INSERT INTO documentos (
					  `EmpresaNo`,
					  `NoDocto`,
					  `Consecutivo`,
					  `TipoDeDocumento`,
					  `TipoDeVenta`,
					  `Asociado`,
					  `FechaCreacion`,
					  `HoraCreacion`,
					  `UsuarioQueCreoDcto.`,
					  `FechaUltimaModificacion`,
					  `HoraUltimaModificacion`,
					  `UsuarioModifico`,
					  `Concepto`,
					  `monto`,
					  `saldo`,
					  `DescuentoAplicado`,
					  `VtaDeCatalogo`,
					  `Cancelado`,
					  `comisiones`,
					  `PagoAplicadoARemisionNo`,
					  `Lo_Recibido`,
					  `venta`,
					  `idsucursal`,
					  `BloquearNotaCredito`)\
					  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
					  %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
					  %s,%s,%s,%s);''',[1,ultimodocto[0]+1,ultimoconsec[0]+1,tipodedocumento,'Contado',
					  	asociado,fecha_hoy,hora_hoy,capturista,\
					  	fecha_hoy,hora_hoy,capturista,\
					  	concepto,monto,monto,0,vtadecatalogo,0,0,0,0,0,id_sucursal,0])
				cursor.execute("COMMIT;")
				return HttpResponseRedirect(reverse('pedidos:documentos'))
				

			except DatabaseError as e:
				print e
				
				cursor.execute('ROLLBACK;')
				msg = 'Error en base de datos !'
				return HttpResponse('<h3>Ocurrio un error en la base de datos</h3><h2>{{e}}</h2>')

		
	else:	
		form =  CreaDocumentoForm()	
	return render(request,'pedidos/crea_documento.html',{'form':form,})


def calcula_descuento(p_socio,p_idproveedor):
	#pdb.set_trace() 

	factor_descuento = 0
	
	#if request.is_ajax()  and request.method == 'GET':
		# Pasa a una variable la tabla  recibida en json string
	socio = p_socio
	proveedor = p_idproveedor

	# Calcula la fecha inicial y la final final del mes inmediato anterior
	# para calcular el total de ventas del mes anterior

	fecha_inicial,fecha_final = traePrimerUltimoDiasMesAnterior()

	cursor = connection.cursor()

	# Se asegura que el socio realmente sea socio y no cliente:

	cursor.execute("SELECT EsSocio FROM asociado where AsociadoNo=%s;",(socio,))
	result = cursor.fetchone() # obtiene el resultado en forma de tupla 
	es_socio = result[0]


	# Determina el total de la venta del socio

	
	cursor.execute("SELECT SUM(p.precio) AS total\
	 FROM pedidos_status_fechas f  INNER JOIN pedidoslines p \
	  ON (p.EmpresaNo= f.EmpresaNo\
	   and p.Pedido=f.Pedido\
	    and p.ProductoNo=f.ProductoNo\
	     and f.Status=p.Status\
	      and p.catalogo=f.catalogo) INNER JOIN articulo a on \
	      (a.EmpresaNo=p.EmpresaNo\
	       and a.CodigoArticulo=p.ProductoNo\
	        and a.catalogo=p.catalogo) INNER JOIN pedidosheader h on\
	         (h.EmpresaNo= p.EmpresaNo and h.PedidoNo=p.pedido)\
	          WHERE f.FechaMvto>=%s and f.FechaMvto<=%s\
	           and p.Status='Facturado' and h.asociadono=%s\
	            and a.idProveedor=%s;",(fecha_inicial,fecha_final,socio,proveedor,))

	total_vta_xsocio_tupla = cursor.fetchone() # obtiene el resultado en forma de tupla 

	if total_vta_xsocio_tupla[0] is None:
		
		total_vta_xsocio_var = 0
	else:

		total_vta_xsocio_var = total_vta_xsocio_tupla[0]	



	# Determina el porcentaje de dscto que corresponde
	# segun el total de la venta 

	cursor.execute("SELECT porcentaje from prov_tarifas_desc\
	 where prove=%s and %s>=lim_inf and %s<=lim_sup;",\
	 (proveedor,total_vta_xsocio_var,total_vta_xsocio_var,))

	porc_desc_variable_tupla = cursor.fetchone()

	if porc_desc_variable_tupla is None:
		porc_desc_variable_var = 0
	else:
		porc_desc_variable_var = porc_desc_variable_tupla[0]


	# Trae el porcentaje porcentaje de desctuento fijo que tiene asignado al socio
	# para el proveedor en particular

	cursor.execute(" SELECT descuento_porc FROM socio_descuento\
	 WHERE idsocio=%s and idproveedor=%s;",(socio,proveedor,))	

	porc_desc_fijo_tupla = cursor.fetchone()

	if porc_desc_fijo_tupla is None:
		
		porc_desc_fijo_var = 0
	else:
		porc_desc_fijo_var =porc_desc_fijo_tupla[0]


	factor_descuento = 0

	# Calcula el factor de descuento siempre y cuando no sea cliente
	if es_socio:


		if porc_desc_fijo_var > porc_desc_variable_var:

			factor_descuento = porc_desc_fijo_var / 100
		else:
			factor_descuento = porc_desc_variable_var / 100

	cursor.close()

	return(factor_descuento)











def trae_inf_venta(request,num_socio):
	# funcion llamada desde la rutiona 'ingresa_socio'

	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..

	ejercicio_vigente =request.session['cnf_ejercicio_vigente']
	periodo_vigente = request.session['cnf_periodo_vigente']


	id_sucursal = request.session['sucursal_activa']
	cursor = connection.cursor()





	# trae pedidos que estan aqui
	cursor.execute("SELECT l.pedido,\
							l.productono,\
							l.catalogo,\
							l.nolinea,\
							h.fechacreacion,\
							l.fechatentativallegada,\
							a.idestilo,\
							a.idcolor,\
							a.idmarca,\
							a.talla,\
							l.status,\
							h.viasolicitud,\
							l.observaciones,\
							v.descripcion,\
							l.precio,a.idproveedor,ct.no_maneja_descuentos FROM pedidoslines l\
							inner join pedidosheader h\
							on l.empresano=h.empresano and\
							l.pedido=h.pedidono\
							inner join articulo a on l.empresano=a.empresano\
							and l.productono=a.codigoarticulo\
							and l.catalogo=a.catalogo\
							inner join viasolicitud v on (v.id=h.viasolicitud)\
							inner join catalogostemporada ct on (ct.proveedorno=a.idproveedor and ct.periodo=%s and ct.anio=%s and ct.clasearticulo=l.catalogo)\
							WHERE l.status='Aqui' and  h.asociadono=%s and h.idsucursal=%s;",(ejercicio_vigente, periodo_vigente, num_socio,id_sucursal,))
	ventas = dictfetchall(cursor)
	
	''' Como se va a modificar un registro de la lista de diccionarios,se crea
	esta lista temporal'''
	ventas_temp = [ ]

	for venta in ventas: # recorre la lista de diccionarios ()
		
		p_precio = venta['precio']
	
		p_idproveedor = venta['idproveedor']

		if venta['no_maneja_descuentos']=='\x01':

			venta['precio_dscto']=p_precio
		else:
			p_porcentaje_descuento = Decimal(calcula_descuento(num_socio,p_idproveedor),2)

			venta['precio_dscto']= p_precio - p_precio * p_porcentaje_descuento # agrega el precio de descuento al diccionario
			venta['precio_dscto']=round(venta['precio_dscto'],2)
			
			venta['porc_dscto'] = p_porcentaje_descuento*100
			venta['porc_dscto'] = round(venta['porc_dscto'],2)
		ventas_temp.append(venta) # Actualiza la lista temporal con el diccionario que ya incluye el precio de descuento
	
	ventas = ventas_temp # vuelve a apuntar a la lista ventas

	# trae informacion de pedidos con estatus de por confirmar, confirmados y encontrados

	#cursor.execute("SELECT p.pedido,p.productono,p.precio,p.status,p.catalogo,p.nolinea,a.pagina,a.idmarca,a.idestilo,a.idcolor,a.talla,h.idsucursal,aso.asociadoNo,aso.Nombre,aso.appaterno,aso.apmaterno, p.fechatentativallegada, f.fechamvto,p.Observaciones,h.fechapedido,if(trim(p.status)='Encontrado' or trim(p.status)='Confirmado',m.razonsocial,'') as razonsocial,n.observaciones as notas FROM pedidoslines p inner join pedidos_encontrados e on (p.empresano=e.empresano and p.pedido=e.pedido and p.productono=e.productono and p.catalogo=e.catalogo and p.nolinea=e.nolinea) inner join pedidosheader h on (p.EmpresaNo=h.EmpresaNo and p.pedido=h.pedidoNo) inner join articulo a on ( p.EmpresaNo=a.empresano and p.productono=a.codigoarticulo and p.catalogo=a.catalogo) inner join asociado aso on (h.asociadoNo=aso.asociadoNo)  inner join pedidos_status_fechas f on ( p.empresano=f.empresano and p.pedido=f.pedido and p.productono=f.productono and p.catalogo=f.catalogo and p.nolinea=f.nolinea and p.status=f.status) left join almacen m on (m.empresano=e.empresano and a.idproveedor=m.proveedorno and m.almacen=e.BodegaEncontro) inner join pedidos_notas n on (n.empresano=p.empresano and n.pedido=p.pedido and n.productono=p.productono and n.catalogo=p.catalogo and n.nolinea=p.nolinea) WHERE h.idsucursal=%s and (p.status='Encontrado' or p.status='Por Confirmar' or p.status='Confirmado' or p.status='Descontinuado') and h.asociadoNo=%s order by p.status;",(id_sucursal,num_socio,))

	cursor.execute("SELECT p.pedido,p.productono,p.precio,p.status,p.catalogo,p.nolinea,a.pagina,a.idmarca,a.idestilo,a.idcolor,a.talla,h.idsucursal,aso.asociadoNo,aso.Nombre,aso.appaterno,aso.apmaterno, p.fechatentativallegada, f.fechamvto,p.Observaciones,h.fechapedido,if(trim(p.status)='Encontrado' or trim(p.status)='Confirmado',m.razonsocial,'') as razonsocial,n.observaciones as notas FROM pedidoslines p inner join pedidos_encontrados e on (p.empresano=e.empresano and p.pedido=e.pedido and p.productono=e.productono and p.catalogo=e.catalogo and p.nolinea=e.nolinea) inner join pedidosheader h on (p.EmpresaNo=h.EmpresaNo and p.pedido=h.pedidoNo) inner join articulo a on ( p.EmpresaNo=a.empresano and p.productono=a.codigoarticulo and p.catalogo=a.catalogo) inner join asociado aso on (h.asociadoNo=aso.asociadoNo)  inner join pedidos_status_fechas f on ( p.empresano=f.empresano and p.pedido=f.pedido and p.productono=f.productono and p.catalogo=f.catalogo and p.nolinea=f.nolinea and p.status=f.status) left join almacen m on (m.empresano=e.empresano and a.idproveedor=m.proveedorno and m.almacen=e.BodegaEncontro) left join pedidos_notas n on (n.empresano=p.empresano and n.pedido=p.pedido and n.productono=p.productono and n.catalogo=p.catalogo and n.nolinea=p.nolinea) WHERE h.idsucursal=%s and (p.status='Encontrado' or p.status='Por Confirmar' or p.status='Confirmado' or p.status='Descontinuado') and h.asociadoNo=%s order by p.status;",(id_sucursal,num_socio,))

	porconfs_confs = dictfetchall(cursor) 


	# trae creditos

	cursor.execute("SELECT nodocto,fechacreacion,\
		concepto,monto FROM documentos WHERE\
		 empresano=1 and asociado=%s and tipodedocumento='Credito' and saldo<>0 and cancelado=0;",(num_socio,))

	creditos = dictfetchall(cursor)

	for credito in creditos:
		print credito

	# trae cargos

	cursor.execute("SELECT nodocto,fechacreacion,\
		concepto,monto FROM documentos WHERE\
		 empresano=1 and asociado=%s and tipodedocumento='Cargo' and saldo<>0 and cancelado=0;",(num_socio,))

	cargos = dictfetchall(cursor)

	cursor.close()

	return (ventas,creditos,cargos,porconfs_confs)




def nueva_venta(request):
	form = Ingresa_socioForm()
	tipo = 'V'
	existe_socio = True
	is_staff = request.session['is_staff']
	context={'existe_socio':existe_socio,'form':form,'is_staff':is_staff,'tipo':tipo,}	


	return render(request,'pedidos/ingresa_socio.html',context)
'''
def calcula_descuento(request,*args,**kwargs):
	#pdb.set_trace() 

	factor_descuento = 0
	
	if request.is_ajax()  and request.method == 'GET':
		# Pasa a una variable la tabla  recibida en json string
		socio = request.GET['id_socio']
		proveedor = request.GET['id_prov']

		# Calcula la fecha inicial y la final final del mes inmediato anterior
		# para calcular el total de ventas del mes anterior

		fecha_inicial,fecha_final = traePrimerUltimoDiasMesAnterior()

		cursor = connection.cursor()

		# Se asegura que el socio realmente sea socio y no cliente:

		cursor.execute("SELECT EsSocio FROM asociado where AsociadoNo=%s;",(socio,))
		result = cursor.fetchone() # obtiene el resultado en forma de tupla 
		es_socio = result[0]


		# Determina el total de la venta del socio

		
		cursor.execute("SELECT SUM(p.precio) AS total\
		 FROM pedidos_status_fechas f  INNER JOIN pedidoslines p \
		  ON (p.EmpresaNo= f.EmpresaNo\
		   and p.Pedido=f.Pedido\
		    and p.ProductoNo=f.ProductoNo\
		     and f.Status=p.Status\
		      and p.catalogo=f.catalogo) INNER JOIN articulo a on \
		      (a.EmpresaNo=p.EmpresaNo\
		       and a.CodigoArticulo=p.ProductoNo\
		        and a.catalogo=p.catalogo) INNER JOIN pedidosheader h on\
		         (h.EmpresaNo= p.EmpresaNo and h.PedidoNo=p.pedido)\
		          WHERE f.FechaMvto>=%s and f.FechaMvto<=%s\
		           and p.Status='Facturado' and h.asociadono=%s\
		            and a.idProveedor=%s;",(fecha_inicial,fecha_final,socio,proveedor,))

		total_vta_xsocio_tupla = cursor.fetchone() # obtiene el resultado en forma de tupla 

		if total_vta_xsocio_tupla[0] is None:
			
			total_vta_xsocio_var = 0
		else:

			total_vta_xsocio_var = total_vta_xsocio_tupla[0]	



		# Determina el porcentaje de dscto que corresponde
		# segun el total de la venta 

		cursor.execute("SELECT porcentaje from prov_tarifas_desc\
		 where prove=%s and %s>=lim_inf and %s<=lim_sup;",\
		 (proveedor,total_vta_xsocio_var,total_vta_xsocio_var,))

		porc_desc_variable_tupla = cursor.fetchone()

		if porc_desc_variable_tupla is None:
			porc_desc_variable_var = 0
		else:
			porc_desc_variable_var = porc_desc_variable_tupla[0]


		# Trae el porcentaje porcentaje de desctuento fijo que tiene asignado al socio
		# para el proveedor en particular

		cursor.execute(" SELECT descuento_porc FROM socio_descuento\
		 WHERE idsocio=%s and idproveedor=%s;",(socio,proveedor,))	

		porc_desc_fijo_tupla = cursor.fetchone()

		if porc_desc_fijo_tupla is None:
			
			porc_desc_fijo_var = 0
		else:
			porc_desc_fijo_var =porc_desc_fijo_tupla[0]


		factor_descuento = 0

		# Calcula el factor de descuento siempre y cuando no sea cliente
		if es_socio:
			if porc_desc_fijo_var >= porc_desc_variable_var:

				factor_descuento = porc_desc_fijo_var / 100
			else:
				factor_descuento = porc_desc_variable_var / 100

		cursor.close()
	try:	
		#data = json.dumps({'factor_descuento':factor_descuento,'otracosa':'otracosa',})

		data = json.dumps({'factor_descuento':factor_descuento,'otracosa':'otracosa',},cls=DjangoJSONEncoder)
		#simplejson.dumps(ql, cls=DjangoJSONEncoder)
	except TypeError as e:
		print e			
		# En el siguiente return utilizo content_type. Intente usar 'mimetype'
		# en lugar de 'content_type' y no funciono.

	return HttpResponse(data,content_type='application/json')	
'''


# ***************   PROCESAR VENTA *********************

def procesar_venta(request):
	
	#pdb.set_trace()

	# Inicializa variables

	CreditosPorAplicarSaldados = False
	CargosPorAplicarSaldados = False

	if request.is_ajax()  and request.method == 'POST':
		# Pasa a una variable las tablas  recibidas en json string
		TableData_ventas= request.POST.get('TableData_ventas')
		TableData_creditos= request.POST.get('TableData_creditos')
		TableData_cargos= request.POST.get('TableData_cargos')
		totalgral=request.POST.get('totalgral')
		id_socio = request.POST.get('id_socio')
		totalventas = request.POST.get('totalventas')
		totalcreditos =request.POST.get('totalcreditos')
		totalcargos = request.POST.get('totalcargos')
		totaldsctos = request.POST.get('totaldsctos')
		totalgral = request.POST.get('totalgral')
		recibido = request.POST.get('recibido')
		user_id = request.POST.get('usr_id')

		if float(totalcreditos) > 0:
		
			if float(totalventas) + float(totalcargos) > float(totalcreditos) :

				creditoaplicado = float(totalcreditos)
			else:
			
				creditoaplicado = float(totalventas) + float(totalcargos)
		else:
			creditoaplicado = 0


		
		# carga la tablas ( las prepara con el formato de lista adecuado para leerlas)
		datos_venta = json.loads(TableData_ventas)
		datos_credito =json.loads(TableData_creditos)
		datos_cargos = json.loads(TableData_cargos)

		#capturista = request.session['socio_zapcat']
		capturista = user_id
		sucursal_activa = request.session['sucursal_activa']

		if sucursal_activa == 0:
			HttpResponse("Al parecer, no selecciono una sucursal, por favor cierre su navegador, vuelva a abrir el navegador e ingrese nuevamente al sistema. !")


		datos_cierre_invalidos = False
		errores_datos_cierre=[]
		
		cursor = connection.cursor()

		''' INICIALIZACION DE VARIABLES '''

		nuevo_status_pedido ='Facturado' # Para el cierre todos los pedidos toman este status
		error = False
		pedidos_cambiados = 0  

		''' FIN DE INCIALIZACION DE VARIABLES '''


		# Se convierte la fecha de hoy a formatos manejables para insertarlos en el registro.
		hoy = datetime.now()
		fecha_hoy = hoy.strftime("%Y-%m-%d")
		hora_hoy = hoy.strftime("%H:%M:%S") 


		try:

			cursor.execute("START TRANSACTION")
						
			#cursor.execute("SELECT id FROM prov_ped_cierre ORDER BY id DESC LIMIT 1 FOR UPDATE;")

			#registro = cursor.fetchone()
			#id_nuevo_cierre = registro[0]+1



			# Crea nuevo cierre en tabla de cierres !
                                                                                                                                                                                                                                                                                                                                                                                               
			#cursor.execute("INSERT INTO prov_ped_cierre (id,referencia,total_articulos,FechaColocacion,HoraColocacion,ColocadoVia,TomadoPor,ConfirmadoPor,CerradoPor,FechaCierre,HoraCierre,NumPedido,Importe,ImporteNC,MontoPagar,Paqueteria,NoGuia,prov_id,almacen,Totartrecibidos,Cerrado,Recepcionado) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",(id_nuevo_cierre,referencia,total_articulos,fecha_hoy,hora_hoy,colocado_via,tomado_por,confirmado_por,capturista,fecha_hoy,hora_hoy,pedido,importe,importe_nc,monto_pagar,paqueteria,no_de_guia,proveedor,almacen,total_articulos,True,False))


			# Si no hay registros de venta seleccionados manda el mensaje adecuado.
			if not datos_venta:

				data={'status_operacion':'fail','error':'No hay ventas por procesar, seleccione ventas !'}
				return HttpResponse(json.dumps(data),content_type='application/json',)

	        # Recupera cada diccionario y extrae los valores de la llave a buscar.

			for j in datos_venta:

				if j is not None:    # Procesa solo los registros con contenido
					pedido = j.get("Pedido").encode('latin_1')

					productono = j.get('ProductoNo').encode('latin_1').strip()
					catalogo =j.get('Catalogo').strip() # es importante pasar por la funcion strip, de lo contrario no funcionan los queries
					nolinea = j.get('Nolinea').encode('latin_1')
					venta_elegida = j.get('venta_elegida')
					version_original_pedidos_lines = j.get('status').strip() # Traemos version anterior del registro pedidoslines, para esto usamos el campo 'status' con el que hacemos una comparacion con una nueva lectura al mismo para ver si cambio

					# Comienza acceso a BD.

					

					# verifica version actual pedidoslines y de una vez se trae el estatus actual para ser mostrado en caso de que la version actual difiera de la anterior
					cursor.execute("SELECT status from pedidoslines WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(pedido,productono,catalogo,nolinea))
					registro = cursor.fetchone()

					# Crea variables de  version actual asi como el actual_estatus para pedidoslines
					if registro is not None:
						version_actual_pedidos_lines =  registro[0].strip()
					else:	
						version_actual_pedidos_lines = 'Aqui'

					# Si las versiones no concuerdan crea contador de pedidos_cambiados y sus lista respectiva para ser mostrados al usuario.
					if (version_actual_pedidos_lines != version_original_pedidos_lines):
						pedidos_cambiados += 1 # actualiza contador de pedidos cambiados durante el proceso
						
					else:

					
						# Actualiza pedidos

						cursor.execute("UPDATE pedidosheader SET FechaUltimaModificacion=%s,HoraModicacion=%s WHERE EmpresaNo=1 and pedidono=%s;",[fecha_hoy,hora_hoy,pedido])							
						cursor.execute("UPDATE pedidoslines SET status=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(nuevo_status_pedido,pedido,productono,catalogo,nolinea))


						# Crea o bien actualiza pedidos_status_fechas

						print pedido
						print productono
						print nuevo_status_pedido
						print catalogo
						print nolinea

						cursor.execute("INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,ProductoNo,Status,catalogo,NoLinea,FechaMvto,HoraMvto,Usuario) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",[1,pedido,productono,nuevo_status_pedido,catalogo,nolinea,fecha_hoy,hora_hoy,capturista])

		 		

			# Trae el ultimo documento
			cursor.execute("SELECT nodocto from documentos WHERE empresano=1 ORDER BY nodocto DESC LIMIT 1 FOR UPDATE;")
			ultimo_docto = cursor.fetchone()
			nuevo_docto = ultimo_docto[0]+1
			nueva_remision = nuevo_docto # se usa nueva_remision para retornala via ajax en diccionario.

			# Trae el ultimo documento
			cursor.execute("SELECT consecutivo from documentos WHERE empresano=1 and tipodedocumento=%s  ORDER BY consecutivo DESC LIMIT 1 FOR UPDATE;",('Remision',))
			ultimo_consec = cursor.fetchone()
			Nuevo_consec = ultimo_consec[0]+1	

			# Genera el documento.
			# Ojo: observar que el campo `UsuarioQueCreoDcto.` se coloco entre apostrofes inversos y el nombre del campo tal y como esta definido en la tabla (casesensitive) dado que si
					# se pone sin apostrofes marca error!
			cursor.execute("INSERT INTO documentos (`EmpresaNo`,`NoDocto`,\
										`Consecutivo`,`TipoDeDocumento`,\
										`TipoDeVenta`,`Asociado`,\
										`FechaCreacion`,`HoraCreacion`,\
										`UsuarioQueCreoDcto.`,`FechaUltimaModificacion`,\
										`HoraUltimaModificacion`,`UsuarioModifico`,\
										`Concepto`,`monto`,`saldo`,\
										`DescuentoAplicado`,`VtaDeCatalogo`,\
										`Cancelado`,`comisiones`,\
										`PagoAplicadoARemisionNo`,`Lo_recibido`\
										,`venta`,`idsucursal`,\
										`BloquearNotaCredito`) VALUES(%s,%s,%s,%s,%s,%s\
										,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
										%s,%s,%s,%s,%s);",(1,nuevo_docto,Nuevo_consec,\
											'Remision','Contado',id_socio,\
											fecha_hoy,hora_hoy,capturista,\
											fecha_hoy,hora_hoy,capturista,\
											"Venta",float(totalgral),float(creditoaplicado),\
											float(totaldsctos),False,False,\
											float(totalcargos),0,float(recibido),\
											float(totalventas),sucursal_activa,False,))


			# Asocia cada registro al nuevo documento (remision) generado
			for j in datos_venta:

				if j is not None:   # Procesa solo los registros con contenido

					pedido = j.get("Pedido").encode('latin_1')

					productono = j.get('ProductoNo').encode('latin_1').strip()
					catalogo =j.get('Catalogo').strip() 
					nolinea = j.get('Nolinea').encode('latin_1')
					precio = j.get('precio').encode('latin_1')

					# Asigna la remision y el precio final ( que puede tener descuento)
					cursor.execute("UPDATE pedidoslines SET remisionno=%s,precio=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(nuevo_docto,precio,pedido,productono,catalogo,nolinea))
		


			'''
			# Genera el documento.
			# Ojo: observar que el campo `UsuarioQueCreoDcto.` se coloco entre apostrofes inversos y el nombre del campo tal y como esta definido en la tabla (casesensitive) dado que si
					# se pone sin apostrofes marca error!
			cursor.execute("INSERT INTO documentos (`EmpresaNo`,`NoDocto`,\
										`Consecutivo`,`TipoDeDocumento`,\
										`TipoDeVenta`,`Asociado`,\
										`FechaCreacion`,`HoraCreacion`,\
										`UsuarioQueCreoDcto.`,`FechaUltimaModificacion`,\
										`HoraUltimaModificacion`,`UsuarioModifico`,\
										`Concepto`,`monto`,`saldo`,\
										`DescuentoAplicado`,`VtaDeCatalogo`,\
										`Cancelado`,`comisiones`,\
										`PagoAplicadoARemisionNo`,`Lo_recibido`\
										,`venta`,`idsucursal`,\
										`BloquearNotaCredito`) VALUES(%s,%s,%s,%s,%s,%s\
										,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
										%s,%s,%s,%s,%s);",(1,nuevo_docto,Nuevo_consec,\
											'Remision','Contado',id_socio,\
											fecha_hoy,hora_hoy,capturista,\
											fecha_hoy,hora_hoy,capturista,\
											"Venta",float(totalgral),float(creditoaplicado),\
											float(totaldsctos),False,False,\
											float(totalcargos),0,0,\
											float(totalventas),sucursal_activa,False,))'''
			nueva_nota_credito = 0
			if float(totalgral) < 0:
				nueva_nota_credito = nuevo_docto + 1 # se usa nueva_nota_credito para pasarla via ajax en dict.

				montocredito = float(totalcreditos)-(float(totalventas)-float(totaldsctos)+float(totalcargos))

				# Genera NOTA DE CREDITO EN CASO DE QUE EL TOTAL SEA NEGATIVO.
				# Ojo: observar que el campo `UsuarioQueCreoDcto.` se coloco entre apostrofes inversos y el nombre del campo tal y como esta definido en la tabla (casesensitive) dado que si
						# se pone sin apostrofes marca error!
				cursor.execute("INSERT INTO documentos (`EmpresaNo`,`NoDocto`,\
											`Consecutivo`,`TipoDeDocumento`,\
											`TipoDeVenta`,`Asociado`,\
											`FechaCreacion`,`HoraCreacion`,\
											`UsuarioQueCreoDcto.`,`FechaUltimaModificacion`,\
											`HoraUltimaModificacion`,`UsuarioModifico`,\
											`Concepto`,`monto`,`saldo`,\
											`DescuentoAplicado`,`VtaDeCatalogo`,\
											`Cancelado`,`comisiones`,\
											`PagoAplicadoARemisionNo`,`Lo_recibido`\
											,`venta`,`idsucursal`,\
											`BloquearNotaCredito`) VALUES(%s,%s,%s,%s,%s,%s\
											,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
											%s,%s,%s,%s,%s);",(1,nuevo_docto+1,Nuevo_consec+1,\
												'Credito','Contado',id_socio,\
												fecha_hoy,hora_hoy,capturista,\
												fecha_hoy,hora_hoy,capturista,\
												"Crédito sobrante de Venta con remisión "+str(nuevo_docto),montocredito,montocredito,\
												0,False,False,\
												0,0,0,\
												0,sucursal_activa,False,))
				







			# PROCESA CREDITOS

			for k in datos_credito:
				
				if k is not None: # Procesa solo los registros con contenido
			
				
					no_docto_credito = k.get("no_docto_credito").encode('latin_1')

					monto_credito = k.get('monto_credito').encode('latin_1')


					# Verifica que el credito no haya sido aplicado en otra transaccion
					# mientras el registro estaba en memoria.

					cursor.execute("SELECT saldo from documentos where nodocto=%s",(no_docto_credito,))
					saldo_tmp = cursor.fetchone()
					
					if saldo_tmp[0] <= 0:

						CreditosPorAplicarSaldados  = True
					else:
						# Actualiza el saldo del credito y lo pone en cero para que no pueda volver
						# a aplicarse.
						cursor.execute("UPDATE documentos SET saldo=0,PagoAplicadoARemisionNo=%s where nodocto=%s;",(nuevo_docto,no_docto_credito,))



			# PROCESA CARGOS

			for l in datos_cargos:
				
				if l is not None: # Procesa solo los registros con contenido
			
				
					no_docto_cargo = l.get("no_docto_cargo").encode('latin_1')

					monto_cargo = l.get('monto_cargo').encode('latin_1')


					# Verifica que el cargo no haya sido aplicado en otra transaccion
					# mientras el registro estaba en memoria.

					cursor.execute("SELECT saldo from documentos where nodocto=%s",(no_docto_cargo,))
					saldo_tmp = cursor.fetchone()
					
					if saldo_tmp[0] <= 0:
					
						CargosPorAplicarSaldados = True
					else:
						# Actualiza el saldo del cargo y lo pone en cero para que no pueda volver
						# a aplicarse.
						cursor.execute("UPDATE documentos SET saldo=0 where nodocto=%s;",(no_docto_cargo,))


			# Hace un rollback si  hay pedidos cambiados, creditos o cargos ya aplicados, de otra
			# manera hace el commit a la base de datos.

		
			if pedidos_cambiados != 0 or CreditosPorAplicarSaldados or CargosPorAplicarSaldados:

				cursor.execute("ROLLBACK;")
			else:

				cursor.execute("COMMIT;")


		except DatabaseError as e:
		
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error de base de datos: '+str(e),}
			print e
			error = True
		except InternalError as e:

			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error interno: '+str(e),}
			print e
			error = True
		except TypeError as e:

			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error interno: '+str(e),}
			print e
			error = True
		except IntegrityError as e:
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error de integridad de BD: '+str(e),}
			error = True
		except OperationalError as e:
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error operacional: '+str(e),}
			error = True
		except NotSupportedError as e:
	
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error no soportado: '+str(e),}
			error = True
		except ProgrammingError as e:

			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':'Error de programacion: '+str(e),}
			error = True
		except:
			
			data = {'status_operacion':'fail','error':'Error no identificado.'}
			error = True

		cursor.close()

		# Si no hay error, nos devolvera la lista de pedidos cambiados
		# o bien un 'ok' y si hay error nos devolvera el mensaje de error.
		if not error:
			if pedidos_cambiados != 0 or CreditosPorAplicarSaldados or CargosPorAplicarSaldados:
				data={'status_operacion':'ok','error':'Venta no procesada ! algunos registros fueron ya modificados por otra transaccion !'}
			else:
				data={'status_operacion':'ok','nodocto':nueva_remision,'nueva_nota_credito':nueva_nota_credito,}
		return HttpResponse(json.dumps(data),content_type='application/json',)


def consultadsctos(request):
	''' Inicializa Variables '''

	Descuento  = 0.0
	Totaldscto = 0.0
	TotalRegistros = 0
	



	mensaje =''
	if request.method == 'POST':

		form = Consulta_ventasForm(request.POST)

		if form.is_valid():

			sucursal = form.cleaned_data['sucursal']
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']

			cursor=connection.cursor()

			if sucursal == '0':
				sucursalinicial =1
				sucursalfinal = 9999
				sucursal_nombre ='GENERAL'
			else:
				sucursalinicial =  sucursal
				sucursalfinal =  sucursal
				cursor.execute("SELECT nombre from sucursal WHERE EmpresaNo=1 and SucursalNo=%s;",(sucursal))
				sucursalencontrada = cursor.fetchone()
				sucursal_nombre = sucursalencontrada[0]


			

			
			"""cursor.execute("SELECT c.id,c.fechacolocacion,c.fechacierre,psf.fechatentativallegada,c.prov_id,c.almacen,c.total_articulos,c.numpedido,c.paqueteria,c.NoGuia FROM prov_ped_cierre c  left  join  pedidos_encontrados p on (c.id=p.id_cierre)  left join  pedidoslines psf on (p.empresano=psf.empresaNo and p.pedido=psf.pedido and p.productono=psf.productono and p.catalogo=psf.catalogo and p.nolinea=psf.nolinea) WHERE psf.fechatentativallegada>=%s and psf.fechatentativallegada<=%s and c.id<>0 group by c.id,psf.fechatentativallegada;",(fechainicial,fechafinal))"""

			
			cursor.execute("SELECT a.idproveedor,p.razonsocial,sum(if(l.preciooriginal>l.precio,l.preciooriginal-l.precio,0)) as dscto from pedidoslines l inner join pedidosheader h on (h.empresano=1 and h.pedidono=l.pedido) inner join pedidos_status_fechas f on (f.empresano=1 and f.pedido=l.pedido and f.productono=l.productono and f.status='Facturado' and f.catalogo=l.catalogo and f.nolinea=l.nolinea) inner join articulo a on (a.empresano=1 and a.codigoarticulo=l.productono and a.catalogo=l.catalogo) inner join proveedor p on (p.empresano=1 and p.proveedorno=a.idproveedor) where f.fechamvto>=%s and f.fechamvto<=%s and h.idsucursal>=%s and h.idsucursal<=%s group by a.idproveedor; ",(fechainicial,fechafinal,sucursalinicial,sucursalfinal))
			
			

			registros_venta = dictfetchall(cursor)

			elementos = len(registros_venta)

			


			"""cursor.execute("SELECT p.razonsocial,a.razonsocial from proveedor p inner join almacen a on (p.empresano=a.empresano and p.proveedorno=a.proveedorno) where p.proveedorno=%s;",(ped['prov_id'],))
			
			prov_alm = cursor.fetchone()"""

			if not registros_venta:
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_ventas.html',{'mensaje':mensaje,})

			else:

				
				for docto in registros_venta:
										
					
					Totaldscto = Totaldscto + float(docto['dscto'])
					
					if (float(docto['dscto']) != 0.0):
						TotalRegistros = TotalRegistros + 1
			
			mensaje ="Proveedores donde se otorgo descuentos == > "



			context = {'form':form,'mensaje':mensaje,'registros_venta':registros_venta,'TotalRegistros':TotalRegistros,'sucursal_nombre':sucursal_nombre,'Totaldscto':Totaldscto,'fechainicial':fechainicial,'fechafinal':fechafinal}	
		
			return render(request,'pedidos/lista_dsctos.html',context)

		
	else:

		form = Consulta_ventasForm()
	return render(request,'pedidos/consultadsctos.html',{'form':form,})

# RUTINA PARA GENERAR REPORTE DE DESGLOSE DE VENTA NETA  POR MARCAS

def consultavtasxproveedor(request):
	''' Inicializa Variables '''
	#pdb.set_trace()

	TotalRegVentas = 0
	TotalRegVtaDevMD = 0
	Totaldscto  = 0.0
	TotalVta = 0.0
	Totaldscto = 0.0
	TotalRegistros = 0
	TotalRegDev = 0
	TotalVtaDevMD = 0.0
	registros_devgral = 0.0
	registros_VtasDevMismodia = 0.0
	TotalDevGral = 0.0
	TotalCargos = 0.0
	TotalVtaCatalogos = 0.0

	



	mensaje =''
	if request.method == 'POST':

		form = Consulta_ventasForm(request.POST)

		if form.is_valid():

			sucursal = form.cleaned_data['sucursal']
			fechainicial = form.cleaned_data['fechainicial']
			fechafinal = form.cleaned_data['fechafinal']

			cursor=connection.cursor()


			# CREA TABLA TEMPORAL
			cursor.execute("DROP TEMPORARY TABLE IF EXISTS vtas_pro_tmp;")
			cursor.execute("CREATE TEMPORARY TABLE vtas_pro_tmp SELECT * FROM vtas_proveedor_imagenbase;")

			if sucursal == '0':
				sucursalinicial =1
				sucursalfinal = 9999
				sucursal_nombre ='GENERAL'
			else:
				sucursalinicial =  sucursal
				sucursalfinal =  sucursal
				cursor.execute("SELECT nombre from sucursal WHERE EmpresaNo=1 and SucursalNo=%s;",(sucursal))
				sucursalencontrada = cursor.fetchone()
				sucursal_nombre = sucursalencontrada[0]


			
			# TRAE VENTA Y DESCUENTOS

			#cursor.execute("SELECT d.EmpresaNo,d.Consecutivo,d.NoDocto,d.TipoDeDocumento,d.TipoDeVenta,d.Asociado,d.FechaCreacion,d.Concepto,d.Monto,d.Saldo,d.VtaDeCatalogo,d.Cancelado,d.comisiones,d.idsucursal,d.venta,d.descuentoaplicado,a.AsociadoNo,a.Nombre,a.ApPaterno,a.ApMaterno,s.SucursalNo,s.nombre as suc_nom, if(d.venta + d.comisiones-d.descuentoaplicado <= d.Saldo,0,d.venta+d.comisiones-d.Saldo-d.descuentoaplicado) as VtaComisionSaldo,if(d.venta + d.comisiones - d.descuentoaplicado <= d.Saldo,d.venta+d.comisiones-d.descuentoaplicado,d.Saldo) as cred_aplicado FROM documentos d INNER  JOIN  asociado a on ( d.EmpresaNo=a.EmpresaNo and d.Asociado=a.AsociadoNo) INNER JOIN  sucursal s ON (d.EmpresaNo= s.EmpresaNo and d.idsucursal=s.SucursalNo) WHERE d.EmpresaNo=1 and  d.TipoDeDocumento='Remision' and not(d.Cancelado) and d.TipoDeVenta='Contado' and d.FechaCreacion>=%s and d.FechaCreacion<=%s and d.idsucursal>=%s  and d.idsucursal<=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal))


			cursor.execute("SELECT a.idproveedor,\
				p.razonsocial,\
				sum(a.precio) as venta,\
				sum(if (a.precio>l.precio,a.precio-l.precio,0)) as dscto\
				from pedidoslines l inner join pedidosheader h\
				on (h.empresano=1 and h.pedidono=l.pedido)\
				inner join pedidos_status_fechas f\
				on (f.empresano=1 and f.pedido=l.pedido\
				and f.productono=l.productono\
				and f.status='Facturado'\
				and f.catalogo=l.catalogo and f.nolinea=l.nolinea)\
				inner join articulo a\
				on (a.empresano=1 and a.codigoarticulo=l.productono\
				and a.catalogo=l.catalogo)\
				inner join proveedor p\
				on (p.empresano=1 and p.proveedorno=a.idproveedor)\
				where f.fechamvto>=%s and f.fechamvto<=%s\
				and h.idsucursal>=%s and h.idsucursal<=%s\
				group by a.idproveedor ; ",\
				(fechainicial,fechafinal,sucursalinicial,sucursalfinal))

			
			registros_venta = dictfetchall(cursor)
			print "descuentos:",registros_venta[3]
			
			elementos = len(registros_venta)

			# TRAE DEVOLUCIONES EN GENERAL
			'''cursor.execute("SELECT a.idproveedor,'',\
				sum(l.precio) as devgral,\
				0 from pedidoslines l inner join pedidosheader h\
				on (h.empresano=1 and h.pedidono=l.pedido)\
				inner join pedidos_status_fechas f\
				on (f.empresano=1 and f.pedido=l.pedido\
				and f.productono=l.productono and f.status='Devuelto'\
				and f.catalogo=l.catalogo and f.nolinea =  l.nolinea) inner join articulo a\
				on (a.empresano=1 and a.codigoarticulo=l.productono\
				and a.catalogo=l.catalogo) inner join proveedor p\
				on (p.empresano=1 and p.proveedorno=a.idproveedor)\
				where f.fechamvto>=%s and f.fechamvto<=%s\
				and h.idsucursal>=%s and h.idsucursal<=%s\
				group by a.idproveedor; ",\
				(fechainicial,fechafinal,sucursalinicial,sucursalfinal))
			
			registros_devgral = dictfetchall(cursor)'''

			#TRAE DEVOLUCIONES GRAL
			cursor.execute("SELECT art.idproveedor,'',sum(l.precio) as devgral,0\
			 from (SELECT psf.pedido,\
			 psf.productono,\
			 psf.nolinea,\
			 psf.catalogo,\
			 psf.fechamvto from\
			 pedidos_status_fechas as psf \
			 INNER JOIN pedidosheader as h \
			 ON h.pedidono=psf.pedido WHERE psf.status='Devuelto' and psf.fechamvto>= %s and psf.fechamvto<= %s and h.idSucursal>=%s and h.idSucursal<=%s) as t2\
			 INNER JOIN pedidos_status_fechas as t3 on\
			 (t2.pedido=t3.pedido and t2.productono=t3.productono\
			 and t2.nolinea=t3.nolinea and t2.catalogo=t3.catalogo)\
	         INNER JOIN pedidoslines as l\
	         on (l.pedido=t3.pedido and l.productono=t3.productono\
	         and l.catalogo=t3.catalogo and l.nolinea=t3.nolinea)\
	         INNER JOIN articulo as art\
	         on (art.codigoarticulo=t3.productono and art.catalogo=t3.catalogo)\
	         WHERE t3.status='Facturado'\
	         GROUP BY art.idproveedor;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal,))

			registros_devgral = dictfetchall(cursor)




			if not registros_venta:

				pass
				
			else:

				cursor.execute("SELECT COUNT(*) as totrec FROM vtas_pro_tmp")
				totrectmp=dictfetchall(cursor)

				
				for registro in registros_venta:

					cursor.execute("UPDATE vtas_pro_tmp SET\
						ventas= %s,\
						venta_FD=0,\
						ventabruta=0,\
						descuento=%s,\
						devoluciones=0,\
						ventaneta=0,nombreprov=%s where idproveedor=%s;",\
					 	(Decimal(registro['venta']),Decimal(registro['dscto']),\
					 		registro['razonsocial'],registro['idproveedor']))					 
                        										
					TotalVta   = TotalVta + float(registro['venta'])
					Totaldscto = Totaldscto + float(registro['dscto'])
					
					if (float(registro['venta']) != 0.0):
						TotalRegVentas = TotalRegVentas + 1


			if not registros_devgral:
				
				pass

			else:				

				for registro in registros_devgral:

					cursor.execute("UPDATE vtas_pro_tmp\
						SET devoluciones=%s WHERE idproveedor=%s;",\
					 			(registro['devgral'],registro['idproveedor']))
										
					
					TotalDevGral = TotalDevGral + float(registro['devgral'])
					
					if (float(registro['devgral']) != 0.0):
						TotalRegDev = TotalRegDev + 1



			""" 			
			if not registros_VtasDevMismodia:
				
				mensaje = 'No se encontraron registros !'
				return render(request,'pedidos/lista_vtasxproveedor.html',{'mensaje':mensaje,})


			else:			

				for registro in registros_VtasDevMismodia:

					cursor.execute("UPDATE vtas_pro_tmp\
						SET venta_FD=%s WHERE idproveedor=%s;",\
					 			(registro['VtasDevMD'],registro['idproveedor']))
										

									
					
					TotalVtaDevMD = TotalVtaDevMD + float(registro['VtasDevMD'])
					
					if (float(registro['VtasDevMD']) != 0.0):
						TotalRegVtaDevMD = TotalRegVtaDevMD + 1 """

			cursor.execute("UPDATE vtas_pro_tmp as t INNER JOIN proveedor as p on t.idproveedor=p.proveedorno SET t.nombreprov=p.razonsocial;")
			cursor.execute("DELETE FROM vtas_pro_tmp WHERE  ventas = 0 and  descuento =0 and devoluciones = 0 and ventaneta = 0;")
			cursor.execute("UPDATE vtas_pro_tmp SET ventabruta = ventas + venta_FD;")
			cursor.execute("UPDATE vtas_pro_tmp SET ventaneta = ventabruta - descuento - devoluciones;")
			
			mensaje =" "

			cursor.execute("SELECT * FROM vtas_pro_tmp;")
			vtasresult =  dictfetchall(cursor)


			cursor.execute("SELECT SUM(ventas) as tot_vtas,SUM(venta_FD) as tot_ventaFD,SUM(ventabruta) as tot_ventabruta, SUM(descuento) as tot_descuento,SUM(devoluciones) as tot_devoluciones,SUM(ventaneta) as tot_ventaneta FROM vtas_pro_tmp;")	
			totales = dictfetchall(cursor)
			for tot in totales:
				tot_vtas = tot['tot_vtas']
				tot_ventaFD = tot['tot_ventaFD']
				tot_ventabruta = tot['tot_ventabruta']
				tot_descuento = tot['tot_descuento']
				tot_devoluciones = tot['tot_devoluciones']
				tot_ventaneta = tot['tot_ventaneta']


			cursor.execute("SELECT d.Monto,d.VtaDeCatalogo,d.Cancelado,d.comisiones,d.Concepto FROM documentos d  WHERE d.EmpresaNo=1 and  d.TipoDeDocumento='Remision' and not(d.Cancelado) and d.TipoDeVenta='Contado' and d.FechaCreacion>=%s and d.FechaCreacion<=%s and d.idsucursal>=%s and d.idsucursal<=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal,))
			
			

			registros_vtacomis_vtacatal = dictfetchall(cursor)


			for docto in registros_vtacomis_vtacatal:
										
					if (docto['Cancelado'] == '\x00'):  # pregunta si cancelado es '0' en hex o bien falso
						
						esvta =docto['Concepto'].strip()
						if esvta == 'Venta':
														
							TotalCargos = TotalCargos + float(docto['comisiones'])	
											
						if docto['VtaDeCatalogo'] == '\x01' :
							TotalVtaCatalogos = TotalVtaCatalogos + float(docto['Monto'])


			# SI TOTALES SON None, LES ASIGNA UN CERO YA QUE EN EL CONTEXT
			# HABRIA PROBLEMAS CON LA FUNCION FLOAT(), DADO QUE NO ACEPTA UN None COMO PARAMETRO.
			if tot_vtas is None:
				tot_vtas = 0
			if tot_ventabruta is None:
				tot_ventabruta = 0
			if tot_ventaFD is None:
				tot_ventaFD = 0
			if tot_ventaneta is None:
				tot_ventaneta = 0
			if tot_descuento is None:
				tot_descuento = 0
			if tot_devoluciones is None:
				tot_devoluciones =0
			

			

			context = {'form':form,'mensaje':mensaje,'vtasresult':vtasresult,'TotalRegistros':TotalRegistros,'tot_vtas':float(tot_vtas),'tot_ventaFD':float(tot_ventaFD),'tot_ventabruta':float(tot_ventabruta),'tot_descuento':float(tot_descuento),'tot_devoluciones':float(tot_devoluciones),'tot_ventaneta':float(tot_ventaneta),'TotalCargos':TotalCargos,'TotalVtaCatalogos':TotalVtaCatalogos,'fechainicial':fechainicial,'fechafinal':fechafinal,'sucursal_nombre':sucursal_nombre,'sucursalinicial':sucursalinicial,'sucursalfinal':sucursalfinal,}	
		
			return render(request,'pedidos/lista_vtasxproveedor.html',context)

		
	else:

		form = Consulta_ventasForm()
	return render(request,'pedidos/consultavtasxproveedor.html',{'form':form,})


# DETALLE DE LA VTA X PROVEEDOR.

def detallevtaxproveedor(request,idproveedor,fechainicial,fechafinal,sucursalinicial,sucursalfinal):

	#pdb.set_trace()
	cursor=connection.cursor()

	totalvta = 0

	cursor.execute("SELECT razonsocial from proveedor WHERE proveedorno=%s;",(idproveedor,))
	proveedor_nombre = dictfetchall(cursor)
	for j in proveedor_nombre:
		proveedor = j['razonsocial']

	try:
		
		cursor.execute("SELECT h.pedidono,l.remisionno as remision_num,h.asociadono,h.fechapedido,h.horapedido,a.idmarca, a.idestilo,idcolor,a.talla,l.preciooriginal,l.observaciones from pedidoslines l inner join pedidosheader h on (h.empresano=1 and h.pedidono=l.pedido) inner join pedidos_status_fechas f on (f.empresano=1 and f.pedido=l.pedido and f.productono=l.productono and f.status='Facturado' and f.catalogo=l.catalogo and f.nolinea=l.nolinea) inner join articulo a on (a.empresano=1 and a.codigoarticulo=l.productono and a.catalogo=l.catalogo) inner join proveedor p on (p.empresano=1 and p.proveedorno=a.idproveedor) where f.fechamvto>=%s and f.fechamvto<=%s and h.idsucursal>=%s and h.idsucursal<=%s and a.idproveedor=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal,idproveedor,))
		"""cursor.execute("SELECT h.pedidono,\
			l.remisionno as remision_num,\
			h.asociadono,\
			h.fechapedido,\
			h.horapedido,\
			a.idmarca,\
			a.idestilo,\
			a.idcolor,\
			a.talla,\
			l.preciooriginal,\
			from pedidoslines l inner join pedidosheader h\
			on (h.empresano=1 and h.pedidono=l.pedido)\
			inner join pedidos_status_fechas f\
			on (f.empresano=1 and f.pedido=l.pedido\
			and f.productono=l.productono and f.status='Facturado'\
			and f.catalogo=l.catalogo)\
			inner join articulo a on (a.empresano=1 and a.codigoarticulo=l.productono\
			and a.catalogo=l.catalogo)\
			inner join proveedor p on (p.empresano=1 and p.proveedorno=a.idproveedor)\
			where f.fechamvto>=%s and f.fechamvto<=%s\
			and h.idsucursal>=%s and h.idsucursal<=%s and a.idproveedor=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal,idproveedor,))"""
			
		vtasresult = dictfetchall(cursor)

		# DETERMINA EL TOTAL DE LA VENTA
		cursor.execute("SELECT l.preciooriginal from pedidoslines l inner join pedidosheader h on (h.empresano=1 and h.pedidono=l.pedido) inner join pedidos_status_fechas f on (f.empresano=1 and f.pedido=l.pedido and f.productono=l.productono and f.status='Facturado' and f.catalogo=l.catalogo and f.nolinea=l.nolinea) inner join articulo a on (a.empresano=1 and a.codigoarticulo=l.productono and a.catalogo=l.catalogo) inner join proveedor p on (p.empresano=1 and p.proveedorno=a.idproveedor) where f.fechamvto>=%s and f.fechamvto<=%s and h.idsucursal>=%s and h.idsucursal<=%s and a.idproveedor=%s;",(fechainicial,fechafinal,sucursalinicial,sucursalfinal,idproveedor,))

		total_registros = dictfetchall(cursor)
		
		for reg in total_registros:
			totalvta = totalvta + float(reg['preciooriginal'])



	except DatabaseError as e:
		print (e)


	context = {'vtasresult':vtasresult,'totalvta':totalvta,'proveedor':proveedor,'fechainicial':fechainicial,'fechafinal':fechafinal,}	


	return render(request,'pedidos/detalle_vtasxproveedor.html',context)









# VERICA LA EXISTENCIA DEL USUARIO EN 
# LA TABLA DE USUARIOS

def verifica_existencia_usr(usr_id):
	#pdb.set_trace()

	cursor=connection.cursor()
	cursor.execute('SELECT usuariono FROM usuarios where usuariono=%s;',(usr_id,))
	num = cursor.fetchone()

	cursor.close()

	if num is None:
		
		return(0) # Si no existe retorna un 0
	else:
		return(1) # Si existe retorna un 1

# VERIFICA QUE EL USUARIO TENGA DERECHOS


def verifica_derechos_usr(num_usr_valido,usr_derecho):
	#pdb.set_trace()

	cursor=connection.cursor()
	cursor.execute('SELECT derechono FROM usuario_derechos where usuariono=%s and derechono=%s;',(num_usr_valido,usr_derecho))
	derechono = cursor.fetchone()


	cursor.close()
	if derechono is None:
		derecho = 0
	else:
		derecho = 1
	return(derecho)




def valida_usr(request):
	#pdb.set_trace()
	socio_zapcat = request.session['socio_zapcat']	
	tiene_derecho = 0 # asume que no tiene derecho
	usr_id = request.GET.get('usr_id')
	usr_derecho = request.GET.get('usr_derecho')


	num_usr_valido = verifica_existencia_usr(usr_id) # verifica si existe

	if num_usr_valido != 0:
		tiene_derecho = verifica_derechos_usr(num_usr_valido,usr_derecho) # Si existe verifica que tenga el derecho solicitado


	data = {'num_usr_valido':num_usr_valido,'tiene_derecho':tiene_derecho,}
	return HttpResponse(json.dumps(data),content_type='application/json',)




'''def modifica_cierre(request,id):
	#pdb.set_trace()

	id_cierre = id

	cursor=connection.cursor()

	cursor.execute("SELECT id,referencia,total_articulos,ColocadoVia,NumPedido,Paqueteria,NoGuia,TotArtRecibidos FROM prov_ped_cierre where id=%s;",(id,) )
	

	form = CierresForm(request.POST)
		
	if form.is_valid():

				# Agregue los siguientes dos if's por si entrega registros en cero, deben ir ???
		if cursor.fetchone():
			print "DATOS CIERRE:"

			datos_cierre = cursor.fetchone()
			for j  in range(0,len(datos_cierre)):
				
				form.id

				print datos_cierre[j]
		else:
			datos_cierre = ()
		
			data = json.dumps(l,cls=DjangoJSONEncoder)
			return HttpResponse(data,content_type='application/json')
		else:
			raise Http404'''

def modifica_cierre(request,id):
	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..
	msg = ''
	form = CierresForm(request.POST)
	if request.method == 'POST':
		
		if form.is_valid():
			#vtadecatalogo = request.POST.get('vtadecatalogo').encode('latin_1')
			id = request.POST.get('id')
			referencia = request.POST.get('referencia')
			pedidonum = request.POST.get('pedidonum')
			total_articulos = request.POST.get('total_articulos')
			total_art_recibidos = request.POST.get('total_art_recibidos')
			paqueteria = request.POST.get('paqueteria')
			noguia = request.POST.get('noguia')
			colocado_via = request.POST.get('colocado_via')
	
			
			cursor =  connection.cursor()
			try:

				cursor.execute('START TRANSACTION')
				cursor.execute('UPDATE prov_ped_cierre SET referencia=%s,NumPedido=%s,total_articulos=%s,TotArtRecibidos=%s,Paqueteria=%s,NoGuia=%s,ColocadoVia=%s WHERE id=%s;',(referencia,pedidonum,total_articulos,total_art_recibidos,paqueteria,noguia,colocado_via,id,))
				cursor.execute("COMMIT;")
				return HttpResponseRedirect(reverse('pedidos:seleccion_cierre_rpte_cotejo'))
			except ValueError as e:
				print e

			except DatabaseError as e:
				print e
				
				cursor.execute('ROLLBACK;')
				msg = 'Error en base de datos !'
				return HttpResponse('<h3>Ocurrio un error en la base de datos</h3><h2>{{e}}</h2>')

		
	print form.errors
				
	cursor =  connection.cursor()
	cursor.execute("SELECT id,referencia,NumPedido,total_articulos,ColocadoVia,Paqueteria,NoGuia,TotArtRecibidos FROM prov_ped_cierre where id=%s;",(id,) )

	datos_cierre =  cursor.fetchone()
	
		
	referencia = datos_cierre[1]
	pedidonum = datos_cierre[2]
	total_articulos = datos_cierre[3]
	total_art_recibidos = datos_cierre[7]
	paqueteria = datos_cierre[5]
	noguia = datos_cierre[6]
	colocado_via = datos_cierre[4]
	msg = "Existen campos vacios, por favor llene todo el formulario !"
	cursor.close()

	form =  CierresForm(initial= {'id':id,'referencia':referencia,'total_articulos':total_articulos,'colocado_via':colocado_via,'pedidonum':pedidonum,'paqueteria':paqueteria,'noguia':noguia,'total_art_recibidos':total_art_recibidos,})	
	return render(request,'pedidos/modifica_cierre.html',{'id':id,'form':form,'referencia':referencia,'total_articulos':total_articulos,'colocado_via':colocado_via,'pedidonum':pedidonum,'paqueteria':paqueteria,'noguia':noguia,'total_art_recibidos':total_art_recibidos,'msg':msg})




def imprime_venta(request):
	#pdb.set_trace()
	
	is_staff = request.session['is_staff']

	if request.method =='GET':
		p_num_venta = request.GET.get('p_num_venta') 
		p_num_credito = request.GET.get('p_num_credito')# p_num_pedido realmente almacena el numero  de documento (remision), solo que se dejo asi para no mover el codigo.
	else:
		p_num_venta = request.POST.get('p_num_venta')
		p_num_credito = request.GET.get('p_num_credito')

	# se encodifica como 'latin_1' ya que viene como unicode.

	#p_num_venta = p_num_venta.encode('latin_1')
	
	
	response = HttpResponse(content_type='application/pdf')
	response['Content-Disposition'] = 'inline; filename="mypdf.pdf"'

	#Trae informacion del pedido.
	cursor =  connection.cursor()
	#pdb.set_trace()

	datos_documento,pedido_detalle,usuario,NotaCredito = None,None,None,0

	try:
		cursor.execute("SELECT asociado,venta,comisiones,saldo,descuentoaplicado,Lo_Recibido,idsucursal,UsuarioModifico,FechaCreacion,HoraCreacion,monto FROM documentos where nodocto=%s;",(p_num_venta,))
		datos_documento = cursor.fetchone()	

		cursor.execute("SELECT appaterno,apmaterno,nombre FROM asociado where asociadono=%s;",(datos_documento[0],))
		datos_socio =  cursor.fetchone()

		cursor.execute("SELECT l.precio,l.NoNotaCreditoPorPedido,l.Observaciones,l.Status,a.pagina,a.idmarca,a.idestilo,a.idcolor,a.talla,a.catalogo,so.nombre,so.appaterno,so.apmaterno,suc.nombre FROM pedidoslines l INNER JOIN articulo a ON (l.empresano = a.empresano and l.productono = a.codigoarticulo and l.catalogo = a.catalogo) INNER JOIN asociado so ON (so.empresano=1 and so.asociadono = %s) INNER JOIN sucursal suc ON (suc.empresano=1 and suc.sucursalno = %s) WHERE l.RemisionNo = %s;",(datos_documento[0],datos_documento[6],p_num_venta))
		pedido_detalle = dictfetchall(cursor)

		cursor.execute("SELECT NoDocto,FechaCreacion,HoraCreacion,monto FROM documentos where PagoAplicadoARemisionNo=%s;",(p_num_venta,))
		creditos_aplicados = cursor.fetchall()	


		# la siguiente variable  se asigna para ser pasada a la rutina que 
		# imprimira la nota de credito ( en caso de que exista )
		if pedido_detalle is not(None):

			for elem in  pedido_detalle:
				NotaCredito = elem['NoNotaCreditoPorPedido']
				if elem['talla'] != 'NE':
					talla = elem['talla']
				else:
					talla = elem['Observaciones']
		
		cursor.execute("SELECT usuario from usuarios where usuariono=%s;",[datos_documento[7]])
		
		usuario = cursor.fetchone()

		mensaje=""
		
		if usuario is None:
			usuario=['ninguno']
		if (not datos_documento or not pedido_detalle):
			mensaje = "No se encontro informacion del pedido !"

	except DatabaseError as e:
		print "Ocurrio de base datos"
		print e
		
		mensaje = "Ocurrio un error de acceso a la bd. Inf. tecnica: "
	except Exception as e:
		mensaje = "Ocurrio un error desconocido. Inf. tecnica: "
		print "error desconocido: "
		print e
		
	cursor.close()

	linea = 800
	
	
    # Create a file-like buffer to receive PDF data.
	buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
	p = canvas.Canvas(buffer)
	#p.setPageSize("inch")

	#p.setFont("Helvetica",10)
	#p.drawString(1,linea,inicializa_imp)
	

    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
	#p.drawString(20,810,mensaje)

	if (datos_documento and pedido_detalle and usuario):
		p.drawString(45,linea, request.session['cnf_razon_social'])
		linea -=20
		p.drawString(45,linea," SUC. "+request.session['sucursal_nombre'])
		linea -=20
		p.setFont("Helvetica",12)
		p.drawString(20,linea, "*** VENTA NUM."+p_num_venta+" ***")
		linea -=20
		p.setFont("Helvetica",8)
		p.drawString(20,linea,request.session['sucursal_direccion'])
		linea -= 10
		p.drawString(20,linea,"COL. "+request.session['sucursal_colonia'])
		linea -= 10
		p.drawString(20,linea,request.session['sucursal_ciudad']+", "+request.session['sucursal_estado'])
		linea -= 10
		p.drawString(20,linea,datos_documento[8].strftime("%d-%m-%Y"))
		p.drawString(100,linea,datos_documento[9].strftime("%H:%M:%S"))
		linea -= 10
		p.drawString(20,linea,"CREADO POR: ")
		#p.drawString(100,linea,request.user.username)
		p.drawString(100,linea,usuario[0])
		linea -= 10
		p.drawString(20,linea,"SOCIO NUM: ")
		type(datos_documento[0])
		p.drawString(100,linea,str(datos_documento[0]))
		linea -= 10
		var_nombre = datos_socio[0]+' '+datos_socio[1]+' '+datos_socio[2]
		p.drawString(20,linea,var_nombre[0:26])
		linea -= 10
		p.drawString(20,linea,"--------------------------------------------------")
		
		linea -= 10
		p.drawString(20,linea,"Descrpcion")
		p.drawString(130,linea,"Precio")
		linea -= 10
		p.drawString(20,linea,"--------------------------------------------------")
		linea -= 10
		#p.setFont("Helvetica",8)
		i,paso=1,linea-10
		for elemento in pedido_detalle:

			if elemento['talla'] != 'NE':
				talla = elemento['talla']
			else:
				talla = elemento['Observaciones']
			
			p.drawString(20,paso,elemento['pagina']+' '+elemento['idmarca']+' '+elemento['idestilo']) 
			p.drawString(20,paso-10,elemento['idcolor'][0:7]+' '+talla)
			p.drawString(130,paso-10,'$ '+str(elemento['precio']))
			paso -= 20
		p.drawString(20,paso-10,"+ Venta ==>")
		p.drawString(130,paso-10,'$ '+str(datos_documento[1]))
		p.drawString(20,paso-20,"+ Cargo ==>")
		p.drawString(130,paso-20,'$ '+str(datos_documento[2]))
		p.drawString(20,paso-30,"-  Credito ==>")
		p.drawString(130,paso-30,'$ '+str(datos_documento[3]))
		p.drawString(20,paso-40,"-  Descuento ==>")
		p.drawString(130,paso-40,'$ '+str(datos_documento[4]))
		p.drawString(20,paso-50,"   TOTAL ==>")
		p.drawString(130,paso-50,'$ '+str(0 if datos_documento[10]<0 else datos_documento[10]))
		
		p.drawString(20,paso-70,"Gracias por su compra !!!")
		

		if creditos_aplicados:
			p.drawString(20,paso-90,"Notas de credito aplicadas:")
			p.drawString(20,paso-100,"--------------------------------------------------")
			linea -= 10
			p.drawString(20,paso-110,"Num. Nota")
			p.drawString(130,paso-110,"Monto")
			linea -= 10
			p.drawString(20,paso-120,"--------------------------------------------------")
			linea = paso-130	

			for elemento in creditos_aplicados:
				p.drawString(20,linea,str(elemento[0]))
				p.drawString(130,linea,'$ '+str(elemento[3]))
				linea -= 10 

			linea -= 20
		linea -= 110

	#pdb.set_trace()	
	if p_num_credito != u'0':
		imprime_documento(p_num_credito,'Credito',False,request.session['cnf_razon_social'],request.session['cnf_direccion'],request.session['cnf_colonia'],request.session['cnf_ciudad'],request.session['cnf_estado'],p,buffer,response,True,linea,request)
	else:

	# Close the PDF object cleanly, and we're done.
		p.showPage()
		p.save()


		pdf = buffer.getvalue()
		buffer.close()

		response.write(pdf)

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    #return FileResponse(buffer, as_attachment=True,filename='hello.pdf')
	#return response
	return response



# SELECCION DEL CRITERIOS PARA DEVOLUCIONES QUE HACE CLIENTE
@login_required(login_url = "/pedidos/acceso/")
def devolucion_socio(request):
	#pdb.set_trace() # DEBUG...QUITAR AL TERMINAR DE PROBAR..

	
	mensaje = " "
	reg_encontrados = 0

	# elimina cualquier registro de la session.
	session_id = request.session.session_key
	# Asigna is_staff para validacines
	is_staff = request.session['is_staff']


	
	 
	if request.method == 'POST':

		form = Crea_devolucionForm(request.POST)

		if form.is_valid():

			socio = request.POST.get('Socio')
			tipoconsulta =  request.POST.get('tipoconsulta')
			fechainicial = request.POST.get('fechainicial')
			finicial =datetime.strptime(fechainicial, "%d/%m/%Y").date()
			fechafinal =request.POST.get('fechafinal')
			ffinal = datetime.strptime(fechafinal, "%d/%m/%Y").date()
			
			if tipoconsulta ==  u'1':
				tc = 'Facturado'
			else:
				tc = 'Aqui'
			
			cursor = connection.cursor()

			try:

				cursor.execute("SELECT appaterno,apmaterno,nombre FROM asociado WHERE asociadono=%s;",(socio,))
				nombre_socio =  cursor.fetchone()

				
				if nombre_socio is None:
					
					form = Crea_devolucionForm()
					print form
					return render(request,'pedidos/DevolucionSocio.html',{'form':form,'mensaje':"Socio Inexistente !",'is_staff':is_staff,})	

				else:

					cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,l.status,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,p.idSucursal,l.Observaciones,suc.nombre,psf.fechamvto FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) LEFT JOIN pedidos_status_fechas psf on (psf.empresano=l.empresano and psf.pedido=l.pedido and psf.productono=l.productono and psf.nolinea=l.nolinea and psf.status='Aqui') INNER JOIN pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN sucursal suc on (p.idSucursal=suc.SucursalNo) WHERE e.empresano=1 and p.asociadono=%s and p.fechacreacion>=%s and p.fechacreacion<=%s and  l.Status=%s order by a.idestilo;",(socio,finicial,ffinal,tc))
					#cursor.execute("SELECT e.Pedido,e.ProductoNo,e.Catalogo,e.NoLinea,l.status,p.FechaPedido,p.AsociadoNo,a.idmarca,a.idestilo,a.idcolor,a.talla,l.precio,p.idSucursal,l.Observaciones,suc.nombre FROM pedidos_encontrados e  INNER JOIN  pedidoslines l on ( e.EmpresaNo=l.EmpresaNo and e.Pedido=l.Pedido and e.ProductoNo=l.ProductoNo and e.Catalogo=l.catalogo and e.NoLinea=l.nolinea ) INNER JOIN  pedidosheader p ON (e.EmpresaNo= p.EmpresaNo and e.Pedido=p.PedidoNo) INNER JOIN articulo a ON (e.EmpresaNo=a.EmpresaNo and e.ProductoNo=a.codigoarticulo and e.Catalogo=a.catalogo) INNER JOIN sucursal suc on (p.idSucursal=suc.SucursalNo) WHERE e.empresano=1 and p.asociadono=%s and p.fechacreacion>=%s and p.fechacreacion<=%s and  l.Status=%s order by a.idestilo;",(socio,finicial,ffinal,tc))

			except DatabaseError as e:
				print "Error base de datos "+str(e)


			if cursor:

				registros = dictfetchall(cursor)
				cursor.close()
				mensaje = "Devolucion de articulos con status de " + tc		
				return render(request,'pedidos/muestra_registros_devolver.html', {'registros':registros,'mensaje':mensaje,'is_staff':is_staff,'socio':socio, 'nombre_socio':nombre_socio[0]+' '+nombre_socio[1]+' '+nombre_socio[2],'tipoconsulta':tipoconsulta})

				
			else:
				mensaje='No se encontraron registros con estos parametros !'
				cursor.close()
				
				return render(request,'pedidos/DevolucionSocio.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})



		else:

			print form.non_field_errors
			#form = SeleccionCierreRecepcionForm()
			return render(request,'pedidos/DevolucionSocio.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})
				
	form = Crea_devolucionForm()
	print form
	return render(request,'pedidos/DevolucionSocio.html',{'form':form,'mensaje':mensaje,'is_staff':is_staff,})	


# PROCESAR DEVOLUCIO DE SOCIO


def procesar_devolucion_socio(request):

	#pdb.set_trace()
	# rutina para grabar header y lines 
	def graba_header_lines():

		cursor.execute("UPDATE pedidosheader SET FechaUltimaModificacion=%s,HoraModicacion=%s WHERE EmpresaNo=1 and pedidono=%s;",[fecha_hoy,hora_hoy,pedido])							
		cursor.execute("UPDATE pedidoslines SET status=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(nuevo_status_pedido,pedido,productono,catalogo,nolinea))
		return


	contador_productos_recibidos = 0



	if request.is_ajax()  and request.method == 'POST':
		# Pasa a una variable la tabla  recibida en json string
		TableData = request.POST.get('TableData')
		
		# carga la tabla ( la prepara con el formato de lista adecuado para leerla)
		datos = json.loads(TableData)

		capturista = request.session['socio_zapcat']
		
		socio = request.POST.get('socio')

		usr_id = request.POST.get('usr_id')
		#almacen = request.POST.get('almacen')
		#almacen = almacen.encode('latin_1')
		tipoconsulta = request.POST.get('tipoconsulta')
		

		#marcartodo_nollego = request.POST.get('marcartodo_nollego')
		#cierre = request.POST.get('cierre').encode('latin_1')
		#nueva_fecha_llegada = request.POST.get('nueva_fecha_llegada').encode('latin_1')
		'''
		if nueva_fecha_llegada == u'None': 

 			f_convertida = '1901/01/01'
 		else:
 			f_convertida = datetime.strptime(nueva_fecha_llegada, "%d/%m/%Y").strftime("%Y%m%d")
			#f_convertida = datetime.strptime(nueva_fecha_llegada, "%d/%m/%Y").date()
		'''
		cursor = connection.cursor()

		''' INICIALIZACION DE VARIABLES '''

		pedidos_cambiados = 0 # inicializa contador de pedidos que sufrieron cambios entre la lectura inicial y el commit.
		
		nuevo_status_pedido = '' # variable que servira para  guardar el status de pedido segun se vayan cumpliendo condiciones,
							# posteriomente se utilizara par actualizar el status del pedido en pedidoslines y pedidos_status_confirmacion.

		error = False

		''' FIN DE INCIALIZACION DE VARIABLES '''


		# Se convierte la fecha de hoy a formatos manejables para insertarlos en el registro.
		hoy = datetime.now()
		fecha_hoy = hoy.strftime("%Y-%m-%d")
		hora_hoy = hoy.strftime("%H:%M:%S") 

		cursor.execute("START TRANSACTION;")



		cursor.execute("SELECT sucursalno from asociado WHERE EmpresaNo=1 and asociadono=%s;",(socio,) )
		registro = cursor.fetchone()
		sucursal = registro[0]


		# Se trae datos para revisar si procede el cobro de comision por no recoger calazado en tiempo.
		if tipoconsulta == u'2':		
			cursor.execute("SELECT maxdiasextemp,ComisionPorCalzadoNoRecogido from configuracion WHERE EmpresaNo=1 limit 1;")
			datos_extemporaniedad = cursor.fetchone()
			maxdiasextemp = datos_extemporaniedad[0]
			cuotadiasextemp = datos_extemporaniedad[1]
			total_comisiones_extemporaneas = Decimal(0.0)


        # Recupera cada diccionario y extrae los valores de la llave a buscar.
		
		try:
			total_devuelto_dinero = Decimal(0.0) # Inicializa acumulador de dinero a devolver
			
			for j in datos:
							
				pedido = j.get("Pedido").encode('latin_1')

				productono = j.get('ProductoNo').strip()
				catalogo =j.get('Catalogo').strip()
				nolinea = j.get('Nolinea').encode('latin_1')
				version_original_pedidos_lines = j.get('status').strip() # Traemos version anterior del registro pedidoslines, para esto usamos el campo 'status' con el que hacemos una comparacion con una nueva lectura al mismo para ver si cambio, no lo pasamos por encode (se queda en utf)
				incidencia = j.get('incidencia').encode('latin_1')
				
				# Comienza acceso a BD.

				# Se trae la fecha en que se recibio el pedido para utlizarla para
				# calcular si se aplica la cuota por extemporaneidad
				cursor.execute("SELECT fechamvto from pedidos_status_fechas WHERE EmpresaNo=1 and Pedido=%s and  ProductoNo=%s and Catalogo=%s and NoLinea=%s and status='Aqui';",(pedido,productono,catalogo,nolinea))
				registro = cursor.fetchone()
				f_fechamvto = registro[0]

		
				# verifica version actual pedidoslines y de una vez se trae el estatus actual para ser mostrado en caso de que la version actual difiera de la anterior
				cursor.execute("SELECT l.status,l.precio,a.idestilo,a.idcolor,a.talla from pedidoslines l inner join articulo a on (l.empresano=a.empresano and l.catalogo = a.catalogo and l.productono=a.CodigoArticulo) WHERE l.EmpresaNo=1 and l.Pedido=%s and  l.ProductoNo=%s and l.Catalogo=%s and l.NoLinea=%s;",(pedido,productono,catalogo,nolinea))
				registro = cursor.fetchone()

				# Crea variables de  version actual asi como el actual_estatus para pedidoslines
				
				version_actual_pedidos_lines =  registro[0].strip()
				
				# Si las versiones no concuerdan crea contador de pedidos_cambiados y sus lista respectiva para ser mostrados al usuario.
				if (version_actual_pedidos_lines != version_original_pedidos_lines):
					pedidos_cambiados += 1 # actualiza contador de pedidos cambiados durante el proceso
				else:

					# Si el pedido es correcto y llego.
					if incidencia != 'Seleccionar':
						nuevo_status_pedido = 'Devuelto'
						
						if tipoconsulta == u'1':
							total_devuelto_dinero += registro[1]
						else:

							# Para el caso de pedidos con status de Aqui.
							total_devuelto_dinero += 0

							# calcula cuota por extemporaneidad si es que le 
							# corresponde

							

							total_comisiones_extemporaneas += Decimal(cuotadiasextemp)
							nuevo_credito = 0
							nuevo_cargo = genera_documento(cursor,
							'Cargo',
							'Contado',
							socio,
							fecha_hoy,
							hora_hoy,
							usr_id,
							fecha_hoy,
							hora_hoy,
							usr_id,
							'Com. prod. no recogido '+registro[2]+' '+registro[3]+' '+registro[4],
							Decimal(cuotadiasextemp),
							Decimal(cuotadiasextemp),
							0,
							0,
							0,
							0,
							0,
							0,
							0,
							sucursal,
							0)






						graba_header_lines()

			

						cursor.execute("""INSERT INTO pedidos_status_fechas (EmpresaNo,Pedido,
										ProductoNo,Status,
										catalogo,NoLinea,
										FechaMvto,HoraMvto,Usuario)
										VALUES (%s,%s,%s,%s,
											%s,%s,%s,%s,%s);""",
										[1,pedido,productono,nuevo_status_pedido,
										catalogo,nolinea,fecha_hoy,hora_hoy,usr_id])




						contador_productos_recibidos += 1

					else:
						pass	


			if tipoconsulta == u'1':		
				nuevo_credito = genera_documento(cursor,
				'Credito',
				'Contado',
				socio,
				fecha_hoy,
				hora_hoy,
				usr_id,
				fecha_hoy,
				hora_hoy,
				usr_id,
				'Credito generado por concepto de devolucion sobre venta',
				total_devuelto_dinero,
				total_devuelto_dinero,
				0,
				0,
				0,
				0,
				0,
				0,
				0,
				sucursal,
				0)

				''' Una vez generado el documento, asigna este a cada producto seleccionado
				para ser devuelto '''

				for j in datos:
								
					pedido = j.get("Pedido").encode('latin_1')

					productono = j.get('ProductoNo').strip()
					catalogo =j.get('Catalogo').strip()
					nolinea = j.get('Nolinea').encode('latin_1')
					incidencia = j.get('incidencia').encode('latin_1')

					if incidencia != 'Seleccionar':
						cursor.execute("UPDATE pedidoslines SET NoNotaCreditoPorDevolucion=%s WHERE EmpresaNo=1 and Pedido=%s and ProductoNo=%s and Catalogo=%s and NoLinea=%s;",(nuevo_credito,pedido,productono,catalogo,nolinea))

			cursor.execute("COMMIT;")

			data = {'status_operacion':'ok','error':"",'nuevo_credito':nuevo_credito,}

						
		except DatabaseError as error:
			
			cursor.execute("ROLLBACK;")
			data = {'status_operacion':'fail','error':str(error),}
			cursor.close()
		except:
			data = {'status_operacion':'fail','error':'Error no relativo a db.'}
			cursor.close()
		return HttpResponse(json.dumps(data),content_type='application/json',)


def imprime_credito(request):
	#pdb.set_trace()
	
	is_staff = request.session['is_staff']

	p_num_credito = request.GET.get('p_num_credito')# p_num_credito realmente almacena el numero  de documento (credito), solo que se dejo asi para no mover el codigo.


	# se encodifica como 'latin_1' ya que viene como unicode.

	#p_num_venta = p_num_venta.encode('latin_1')
	
	
	response = HttpResponse(content_type='application/pdf')
	response['Content-Disposition'] = 'inline; filename="mypdf.pdf"'

	linea = 800
	
	
    # Create a file-like buffer to receive PDF data.
	buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
	p = canvas.Canvas(buffer)
	#p.setPageSize("inch")
	imprime_documento(p_num_credito,'Credito',True,request.session['cnf_razon_social'],request.session['cnf_direccion'],request.session['cnf_colonia'],request.session['cnf_ciudad'],request.session['cnf_estado'],p,buffer,response,True,linea,request)
		
	return response