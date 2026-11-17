-- crear la base de datos
create database cantina_bd 
character set utf8mb4
collate utf8mb4_unicode_ci;

-- hacer uso de la base de datos
use cantina_bd;

/*
crear las tablas necesarias para la gestion del sistema
*/
-- tablas para gestion de usuarios

-- roles
create table roles(
	id_rol int auto_increment primary key,
    nombre varchar(50) not null unique,
    descripcion varchar(100)
);

-- usuarios
create table usuarios(
	id_usuario int auto_increment primary key,
    id_rol int not null,
    nombre varchar(100) not null,
    correo varchar(120) not null,
    username varchar(50) not null unique,
    password varchar(15) not null,
    estado enum('Activo','Inactivo') default 'Activo',
    fecha_registro datetime default current_timestamp,
    
    constraint fk_usuarios_roles  -- esta conectada con la tabla de usuarios para determinar que rol se le va a asignar el rol a cada usuario
    foreign key (id_rol) references roles(id_rol)
);

-- tablas para catalogo e inventario de insumos

-- categorias de los insumos
create table categorias_insumos(
	id_categoria int auto_increment primary key,
    nombre varchar(80) not null unique,
    descripcion varchar(200)
);

-- unidades de medida
create table unidades_medida(
	id_unidad int auto_increment primary key,
    nombre varchar(50) not null unique,
    abreviatura varchar(10) not null unique
);

-- insumos
create table insumos(
	id_insumo int auto_increment primary key,
    codigo varchar(20) not null unique,
    id_categoria int not null,
    id_unidad int not null,
    nombre varchar(150) not null,
    descripcion varchar(200),
    costo_unitario decimal(12,3) not null default 0,
    stock_actual decimal(12,3) not null default 0,
    stock_minimo decimal(12,3) not null default 5,
    estado enum('Activo','Inactivo') default 'Activo',
    
    -- llaves foraneas conectadas a categorias y unidades
    constraint fk_insumos_categoria
    foreign key (id_categoria) references categorias_insumos(id_categoria),
    
    constraint fk_insumos_unidad
    foreign key (id_unidad) references unidades_medida(id_unidad)
);

-- proovedores
create table proveedores(
	id_proveedor int auto_increment primary key,
    nombre varchar(120) not null,
    telefono varchar(20),
    correo varchar(120),
    direccion varchar(200),
    estado enum('Activo', 'Inactivo') default 'Activo'
);

-- compras (realizadas a los proveedores)
create table compras(
	id_compra int auto_increment primary key,
    id_proveedor int not null,
    id_usuario int not null,
    fecha_compra datetime default current_timestamp,
    total decimal(12,2) not null default 0,
    estado enum('Registrada','Cancelada','Pendiente') default 'Pendiente',
    
    -- llaves foraneas conectadas a proveedores y usuarios
    constraint fk_compras_proveedor
    foreign key (id_proveedor)
    references proveedores(id_proveedor),
    
    constraint fk_compras_usuario
    foreign key (id_usuario)
    references usuarios(id_usuario)
);

-- detalle de las compras
create table detalle_compras(
	id_detalle_compra int auto_increment primary key,
    id_compra  int not null,
    id_insumo int not null,
    cantidad decimal(12,3) not null,
    costo_unitario decimal(12,2) not null,
    
    -- llaves foraneas que conectan con las tablas compras e insumos
    constraint fk_detalle_compras_compra
    foreign key (id_compra)
    references compras(id_compra),
    
    constraint fk_detalle_compras_insumo
    foreign key (id_insumo)
    references insumos(id_insumo)
);

-- movimientos en el inventario
create table movimientos_inventario(
	id_movimiento int auto_increment primary key,
    id_insumo int not null,
    id_usuario int not null,
    tipo_movimiento enum('Entrada','Salida','Ajuste') not null,
    cantidad decimal(12,3) not null,
    motivo varchar(200),
    fecha_movimiento datetime default current_timestamp,
    
    -- llaves foraneas que conectan con las tablas insumos e usuarios
    constraint fk_movientos_insumo
    foreign key (id_insumo)
    references insumos(id_insumo),
    
    constraint fk_movimientos_usuario
    foreign key (id_usuario)
    references usuarios(id_usuario)
);

-- categorias de los productos
create table categorias_productos(
	id_categoria int auto_increment primary key,
    nombre varchar(80) not null unique,
    descripcion varchar(200)
);

-- productos (bebidas que se le ofrecen al publico)
create table productos(
	id_producto int auto_increment primary key,
    codigo varchar(20) not null unique,
    id_categoria int not null,
    nombre varchar(100) not null,
    descripcion varchar(200),
    costo_preparacion decimal(12,2) not null default 0,
    porcentaje_utilidad decimal(5,2) not null default 60,
    precio_venta decimal(12,2) not null default 0,
    estado enum('Activo', 'Inactivo') default 'Activo',
    
    -- llaves foraneas conectada a las tabla categoria
    constraint fk_productos_categoria
    foreign key (id_categoria)
    references categorias_productos(id_categoria)
);

-- tabla de recetas
create table recetas(
	id_receta int auto_increment primary key,
    id_producto int not null unique,
    nombre varchar(100) not null,
    porciones decimal(10,3) not null default 1,
    instrucciones text,
    costo_total decimal(12,2) not null default 0,
    
    -- llave foranea que conecta con la tabla productos
    constraint fk_recetas_producto
    foreign key (id_producto)
    references productos(id_producto)
);

-- detalles de la receta
create table detalle_recetas (
	id_detalle_receta int auto_increment primary key,
    id_receta int not null,
    id_insumo int not null,
    cantidad decimal(12,3) not null,
    costo_unitario decimal(12,4) not null default 0,
    subtotal decimal(12,2) not null default 0,
    
    -- llaves foraneas conectadas a las tablas recetas e insumos
    constraint fk_detalles_recetas_receta
    foreign key (id_receta)
    references recetas(id_receta),
    
    constraint fk_detalles_recetas_insumo
    foreign key (id_insumo)
    references insumos(id_insumo)
);

-- configuracion de las utilidades
create table configuracion_utilidades(
	id_configuracion int auto_increment primary key,
    porcentaje_utilidad decimal(5,2) not null default 60,
    fecha_actualizacion datetime default current_timestamp,
    id_usuario int not null,
    
    -- llave foranea conectada a tabla usuarios
    constraint fk_configuracion_usuario
    foreign key (id_usuario)
    references usuarios(id_usuario)
);

-- ventas (Bebidas que se le venden a los clientes en la cantina)
create table ventas(
	id_venta int auto_increment primary key,
    id_usuario int not null,
    fecha_venta datetime default current_timestamp,
    subtotal decimal(12,2) not null default 0,
    total decimal(12,2) not null default 0,
    metodo_pago varchar(40) not null,
    estado enum('Completada','Cancelada') default 'Completada',
    
    -- llave foranea que conecta con la tabla usuario
    constraint fk_ventas_usuario
    foreign key (id_usuario)
    references usuarios(id_usuario)
);

-- detalles de las ventas
create table detalle_ventas(
	id_detalle_venta int auto_increment primary key,
    id_venta int not null,
    id_producto int not null,
    cantidad int not null,
    precio_unitario decimal(12,2) not null,
    costo_unitario decimal(12,2) not null,
    subtotal decimal(12,2) not null,
    
    -- llaves foraneas conectadas con la tabla ventas y productos 
    constraint fk_detalle_ventas_venta
    foreign key (id_venta)
    references ventas(id_venta),
    
    constraint fk_detalle_ventas_producto
    foreign key (id_producto)
    references productos(id_producto)
);

-- alertas del inventario
create table alertas_inventario(
	id_alerta int auto_increment primary key,
    id_insumo int not null,
    tipo_alerta enum('Stock bajo', 'Stock nulo') not null,
    mensaje varchar(200) not null,
    fecha_alerta datetime default current_timestamp,
    estado enum('Pendiente', 'Atendida') default 'Pendiente',
    
    -- llave foranea que conecta con la tabla insumos
    constraint fk_alertas_insumo
    foreign key (id_insumo)
    references insumos(id_insumo)
);