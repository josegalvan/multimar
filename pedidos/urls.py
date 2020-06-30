from django.conf.urls import url
from pedidos import views
#from pedidos.subvi import imprime_documento
from django.contrib.auth.views import password_reset,password_reset_done,password_reset_confirm,password_reset_complete
urlpatterns = [
	url(r'^index/$',views.index,name='index'),
	url(r'^acceso/$',views.acceso,name='acceso'),
	url(r'^asociados/$',views.lista_asociados,name='asociados'),
	url(r'^edita_asociado/(?P<asociadono>[0-9]{1,8})/$',views.edita_asociado,name='edita_asociado'),
	url(r'^crea_asociado/$',views.crea_asociado,name='crea_asociado'),
	url(r'^asociado_proveedor/(?P<asociadono>[0-9]{1,8})/$',views.asociado_proveedor,name='asociado_proveedor'),
	url(r'^asociado_edita_descuento/(?P<proveedorno>[0-9]{1,8})/(?P<asociadono>[0-9]{1,8})/$',views.asociado_edita_descuento,name='asociado_edita_descuento'),
	url(r'^asociado_nuevo_descuento/(?P<asociadono>[0-9]{1,8})/$',views.asociado_nuevo_descuento,name='asociado_nuevo_descuento'),
	url(r'^busca_pedidos/$',views.busca_pedidos,name='busca_pedidos'),
	url(r'^lista_pedidos/$',views.lista_pedidos,name='lista_pedidos'),
	url(r'^crea_pedidos/$',views.crea_pedidos,name='crea_pedidos'),
	url(r'^combo_temporadas/$',views.combo_temporadas,name='combo_temporadas'),
	url(r'^combo_catalogos/$',views.combo_catalogos,name='combo_catalogos'),
	url(r'^combo_estilos/$',views.combo_estilos,name='combo_estilos'),
	url(r'^combo_marcas/$',views.combo_marcas,name='combo_marcas'),
	url(r'^combo_colores/$',views.combo_colores,name='combo_colores'),
	url(r'^combo_tallas/$',views.combo_tallas,name='combo_tallas'),
	url(r'^grabar_pedidos/$',views.grabar_pedidos,name='grabar_pedidos'),
	url(r'^eli_reg_tmp/$',views.eli_reg_tmp,name='eli_reg_tmp'),
	url(r'^procesar_pedido/$',views.procesar_pedido,name='procesar_pedido'),
	url(r'^busca_socio/$',views.busca_socio,name='busca_socio'),
	url(r'^registro_socio/$',views.registro_socio,name='registro_socio'),
	url(r'^llena_combo_sucursal/$',views.llena_combo_sucursal,name='llena_combo_sucursal'),
	url(r'^logout_view/$',views.logout_view,name='logout_view'),
	url(r'^cambiar_password/$',views.cambiar_password,name='cambiar_password'),
	url(r'^reset/password_reset/$',password_reset,
		{'template_name':'pedidos/password_reset_form.html',
		'email_template_name':'pedidos/password_reset_email.html',
		'current_app':'pedidos','post_reset_redirect':'pedidos:password_reset_done'},
		name ='password_reset'),
	url(r'^reset/password_done/$',password_reset_done,
		{'template_name':'pedidos/password_reset_done.html','current_app':'pedidos'},
		name ='password_reset_done'),
	url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
		password_reset_confirm,
		{'template_name':'pedidos/password_reset_confirm.html',
		'current_app':'pedidos','post_reset_redirect' : 'pedidos:password_reset_complete'},
		name ='password_reset_confirm'),
	url(r'^reset/password_complete/$',password_reset_complete,
		{'template_name':'pedidos/password_reset_complete.html','current_app':'pedidos'},
		name ='password_reset_complete'),
	url(r'^empleados/$',views.empleados,name='empleados'),
	url(r'^entrada_sistema/$',views.entrada_sistema,name='entrada_sistema'),
	url(r'^consulta_menu/$',views.consulta_menu,name='consulta_menu'),
	url(r'^calzadollego_gral/$',views.calzadollego_gral,name='calzadollego_gral'),
	url(r'^con_pedidos_por_socio_status/$',views.con_pedidos_por_socio_status,name='con_pedidos_por_socio_status'),
	url(r'^con_confirmaciones/$',views.con_confirmaciones,name='con_confirmaciones'),
	url(r'^existe_socio/$',views.existe_socio,name='existe_socio'),
	url(r'^picklist_socio/$',views.picklist_socio,name='picklist_socio'),
	url(r'^calzadoquellego_detalle/$',views.calzadoquellego_detalle,name='calzadoquellego_detalle'),
	url(r'^consultacolocaciones/$',views.consultacolocaciones,name='consultacolocaciones'),
	url(r'^consultaventas/$',views.consultaventas,name='consultaventas'),
	url(r'^consultacomisiones/$',views.consultacomisiones,name='consultacomisiones'),
	url(r'^buscapedidosposfecha/$',views.buscapedidosposfecha,name='buscapedidosposfecha'),
	url(r'^pedidosgeneral/$',views.pedidosgeneral,name='pedidosgeneral'),
	# url(r'^pedidosgeneraldetalle/(?P<pedido>[0-9]{1,8})/(?P<productono>[\w\-]+)/(?P<catalogo>[\w\-]+)/(?P<nolinea>[0-9]{1,8})/$',views.pedidosgeneraldetalle,name='pedidosgeneraldetalle'),
	url(r'^pedidosgeneraldetalle/(?P<pedido>[0-9]{1,8})/(?P<productono>.*)/(?P<catalogo>.*)/(?P<nolinea>[0-9]{1,8})/$',views.pedidosgeneraldetalle,name='pedidosgeneraldetalle'),
	#url(r'^cancelarpedidoadvertencia/(?P<pedido>[0-9]{1,8})/(?P<productono>[\w\-]+)/(?P<catalogo>[\w \-]+)/(?P<nolinea>[0-9]{1,8})/$',views.cancelarpedidoadvertencia,name='cancelarpedidoadvertencia'),
	url(r'^cancelarpedidoadvertencia/(?P<pedido>[0-9]{1,8})/(?P<productono>.*)/(?P<catalogo>.*)/(?P<nolinea>[0-9]{1,8})/$',views.cancelarpedidoadvertencia,name='cancelarpedidoadvertencia'),
	#url(r'^ingresa_socio/$',views.ingresa_socio,name='ingresa_socio'),
	url(r'^ingresa_socio/(?P<tipo>[D,P,V]{1})/$',views.ingresa_socio,name='ingresa_socio'),

	url(r'^imprime_ticket/$',views.imprime_ticket,name='imprime_ticket'),
	#url(r'^i_d/$',imprime_documento.i_d,name='i_d'),
	url(r'^colocaciones/$',views.colocaciones,name='colocaciones'),
	url(r'^combo_almacenes/$',views.combo_almacenes,name='combo_almacenes'),
	url(r'^muestra_colocaciones/$',views.muestra_colocaciones,name='muestra_colocaciones'),
	url(r'^procesar_colocaciones/$',views.procesar_colocaciones,name='procesar_colocaciones'),
	url(r'^elegir_almacen_a_cerrar/$',views.elegir_almacen_a_cerrar,name='elegir_almacen_a_cerrar'),
	url(r'^procesar_cierre_pedido/$',views.procesar_cierre_pedido,name='procesar_cierre_pedido'),
	url(r'^pruebaImprime/$',views.pruebaImprime,name='pruebaImprime'),
	url(r'^seleccion_cierre_rpte_cotejo/$',views.seleccion_cierre_rpte_cotejo,name='seleccion_cierre_rpte_cotejo'),
	url(r'^combo_proveedor_rpte_cotejo/$',views.combo_proveedor_rpte_cotejo,name='combo_proveedor_rpte_cotejo'),
	url(r'^seleccion_cierre_recepcion/$',views.seleccion_cierre_recepcion,name='seleccion_cierre_recepcion'),
	url(r'^procesar_recepcion/$',views.procesar_recepcion,name='procesar_recepcion'),
	url(r'^documentos/$',views.documentos,name='documentos'),
	url(r'^muestra_documentos/$',views.muestra_documentos,name='muestra_documentos'),
	url(r'^detalle_documento/(?P<NoDocto>[0-9]{1,8})/$',views.detalle_documento,name='detalle_documento'),
	url(r'^crea_documento/$',views.crea_documento,name='crea_documento'),
	url(r'^consulta_menu/$',views.consulta_menu,name='consulta_menu'),
	url(r'^nueva_venta/$',views.nueva_venta,name='nueva_venta'),
	url(r'^calcula_descuento/$',views.calcula_descuento,name='calcula_descuento'),
	url(r'^procesar_venta/$',views.procesar_venta,name='procesar_venta'),
	url(r'^picklist_estilopagina/$',views.picklist_estilopagina,name='picklist_estilopagina'),
	url(r'^consultadsctos/$',views.consultadsctos,name='consultadsctos'),
	url(r'^consultavtasxproveedor/$',views.consultavtasxproveedor,name='consultavtasxproveedor'),
	url(r'^valida_usr/$',views.valida_usr,name='valida_usr'),
	url(r'^detallevtaxproveedor/(?P<idproveedor>[0-9]{1,8})/(?P<fechainicial>[\w\-]+)/(?P<fechafinal>[\w\-]+)/(?P<sucursalinicial>[0-9]{1,8})/(?P<sucursalfinal>[0-9]{1,8})/$',views.detallevtaxproveedor,name='detallevtaxproveedor'),
	url(r'^trae_nombre_socio/$',views.trae_nombre_socio,name='trae_nombre_socio'),
	url(r'^modifica_cierre/(?P<id>[0-9]{1,8})/$',views.modifica_cierre,name='modifica_cierre'),
	url(r'^imprime_venta/$',views.imprime_venta,name='imprime_venta'),
	url(r'^imprime_documento/$',views.imprime_documento,name='imprime_documento'),
	url(r'^cancelar_pedido/$',views.cancelar_pedido,name='cancelar_pedido'),
	url(r'^devolucion_socio/$',views.devolucion_socio,name='devolucion_socio'),
	url(r'^procesar_devolucion_socio/$',views.procesar_devolucion_socio,name='procesar_devolucion_socio'),
	url(r'^imprime_credito/$',views.imprime_credito,name='imprime_credito'),
	url(r'^calcula_bono/$',views.calcula_bono,name='calcula_bono'),
	url(r'^detallebonosocio/(?P<idsocio>[0-9]{1,8})/(?P<fechainicial>[\w\-]+)/(?P<fechafinal>[\w\-]+)/$',views.detallebonosocio,name='detallebonosocio'),
	url(r'^vtaneta_socio/$',views.vtaneta_socio,name='vtaneta_socio'),
	url(r'^cancelardocumentoadvertencia/(?P<NoDocto>[0-9]{1,8})/$',views.cancelardocumentoadvertencia,name='cancelardocumentoadvertencia'),	
	url(r'^rptedecreditos/$',views.rptedecreditos,name='rptedecreditos'),
	url(r'^recepcion_dev_prov/$',views.recepcion_dev_prov,name='recepcion_dev_prov'),
	url(r'^procesar_recepcion_devolucion_proveedor/$',views.procesar_recepcion_devolucion_proveedor,name='procesar_recepcion_devolucion_proveedor'),
	url(r'^devolucion_a_proveedor/$',views.devolucion_a_proveedor,name='devolucion_a_proveedor'),
	url(r'^procesar_devolucion_proveedor/$',views.procesar_devolucion_proveedor,name='procesar_devolucion_proveedor'),
	url(r'^filtro_dev_prov/$',views.filtro_dev_prov,name='filtro_dev_prov'),
	url(r'^imprime_hoja_devolucion/$',views.imprime_hoja_devolucion,name='imprime_hoja_devolucion'),
	url(r'^edita_devprov/(?P<id_prov>[0-9]{1,8})/$',views.edita_devprov,name='edita_devprov'),
	url(r'^proveedores/$',views.proveedores,name='proveedores'),
	url(r'^edita_proveedor/(?P<proveedorno>[0-9]{1,8})/$',views.edita_proveedor,name='edita_proveedor'),
	url(r'^crea_proveedor/$',views.crea_proveedor,name='crea_proveedor'),
	url(r'^lista_catalogos_proveedor/(?P<proveedorno>[0-9]{1,8})/$',views.lista_catalogos_proveedor,name='lista_catalogos_proveedor'),
	url(r'^edita_catalogo/(?P<p_ProveedorNo>[0-9]{1,8})/(?P<p_Anio>[0-9]{1,8})/(?P<p_Periodo>[0-9]{1,8})/(?P<p_ClaseArticulo>.*)/$',views.edita_catalogo,name='edita_catalogo'),
	url(r'^crea_catalogo/(?P<id_proveedor>[0-9]{1,8})/$',views.crea_catalogo,name='crea_catalogo'),
	url(r'^lista_devoluciones_recepcionadas/$',views.lista_devoluciones_recepcionadas,name='lista_devoluciones_recepcionadas'),
	url(r'^rpte_ventas/$',views.rpte_ventas,name='rpte_ventas'),
	url(r'^rpteStatusPedidosPorSocio/$',views.rpteStatusPedidosPorSocio,name='rpteStatusPedidosPorSocio'),
	url(r'^vtasporusuario/$',views.vtasporusuario,name='vtasporusuario'),
	url(r'^busca_estilo/$',views.busca_estilo,name='busca_estilo'),
	url(r'^piezas_no_solicitadas/$',views.piezas_no_solicitadas,name='piezas_no_solicitadas'),
	url(r'^rpte_piezas_no_solicitadas/$',views.rpte_piezas_no_solicitadas,name='rpte_piezas_no_solicitadas'),
	url(r'^filtrocatalogosasociado/(?P<asociadono>[0-9]{1,8})/$',views.filtrocatalogosasociado,name='filtrocatalogosasociado'),
	url(r'^filtroproveedor_almacen/$',views.filtroproveedor_almacen,name='filtroproveedor_almacen'),
	url(r'^crea_almacen/(?P<proveedorno>[0-9]{1,8})/$',views.crea_almacen,name='crea_almacen'),
	url(r'^edita_almacen/(?P<proveedorno>[0-9]{1,8})/(?P<almacenno>[0-9]{1,8})/$',views.edita_almacen,name='edita_almacen'),
	url(r'^rpte_remisiones_especiales/$',views.rpte_remisiones_especiales,name='rpte_remisiones_especiales'),

	]