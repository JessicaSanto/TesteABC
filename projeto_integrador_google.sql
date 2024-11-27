CREATE DATABASE bd_medidor;

USE bd_medidor;

CREATE TABLE tb_registro(
	id INT NOT NULL AUTO_INCREMENT, 
	temperatura DECIMAL(10,2),
	pressao DECIMAL(10,2), 
	altitude DECIMAL(10,2),
	umidade DECIMAL(10,2),
	co2 DECIMAL(10,2),
	poeira DECIMAL(10,2),
	tempo_registro DATETIME,
    PRIMARY KEY (id)
    )