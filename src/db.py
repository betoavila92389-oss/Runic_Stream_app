import sqlite3
import os
from pathlib import Path
from datetime import datetime

class DatabaseManager:
    """
    Gestor de la base de datos de la aplicación.
    Proporciona métodos para interactuar con SQLite y gestionar el historial y la biblioteca de medios.
    """
    def __init__(self, db_path="runic_stream.db"):
        """
        Inicializa el gestor de la base de datos.
        
        Args:
            db_path (str): Ruta del archivo de la base de datos de SQLite.
        """
        self.db_path = db_path
        # Inicializamos la base de datos y sus tablas al instanciar
        self._init_db()

    def _get_connection(self):
        """
        Crea y devuelve una conexión a la base de datos SQLite.
        
        Returns:
            sqlite3.Connection: Objeto de conexión a la base de datos.
        """
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """
        Inicializa el esquema de la base de datos si este no existe.
        Crea la tabla principal 'media_library' y asegura que tenga las columnas necesarias.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Creamos la tabla de la biblioteca multimedia si no existe
            # con restricciones para el tipo de archivo y marcas de tiempo
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('video', 'audio')),
                    file_path TEXT NOT NULL,
                    url TEXT,
                    quality TEXT,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Comprobamos si la columna 'quality' existe para compatibilidad con bases de datos antiguas
            cursor.execute("PRAGMA table_info(media_library)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'quality' not in columns:
                # Si no existe la columna de calidad, la añadimos mediante ALTER TABLE
                cursor.execute("ALTER TABLE media_library ADD COLUMN quality TEXT")
            conn.commit()

    def add_media(self, title: str, media_type: str, file_path: str, url: str = None, quality: str = None) -> int:
        """
        Añade un nuevo registro de medio a la biblioteca.
        
        Args:
            title (str): Título del contenido multimedia.
            media_type (str): Tipo de contenido ('video' o 'audio').
            file_path (str): Ruta local del archivo descargado.
            url (str, opcional): Enlace original desde donde se descargó.
            quality (str, opcional): Calidad del medio.
            
        Returns:
            int: El ID del último registro insertado.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Insertamos los valores parametrizados para evitar inyección SQL
            cursor.execute(
                "INSERT INTO media_library (title, type, file_path, url, quality) VALUES (?, ?, ?, ?, ?)",
                (title, media_type, file_path, url, quality)
            )
            conn.commit()
            return cursor.lastrowid

    def get_media_by_url(self, url: str):
        """
        Recupera registros de la biblioteca que coincidan con una URL específica.
        
        Args:
            url (str): La URL a buscar.
            
        Returns:
            list: Lista de diccionarios que representan los registros encontrados.
        """
        with self._get_connection() as conn:
            # Configuramos la conexión para devolver filas como diccionarios
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_library WHERE url = ?", (url,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_media(self, media_type: str = None):
        """
        Recupera todos los medios de la biblioteca, opcionalmente filtrados por tipo.
        
        Args:
            media_type (str, opcional): Tipo de medio ('video' o 'audio') para filtrar los resultados.
            
        Returns:
            list: Lista de diccionarios ordenados descendentemente por fecha de añadido.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if media_type:
                # Si se especifica un tipo, filtramos por él
                cursor.execute("SELECT * FROM media_library WHERE type = ? ORDER BY date_added DESC", (media_type,))
            else:
                # Si no, devolvemos todo el contenido
                cursor.execute("SELECT * FROM media_library ORDER BY date_added DESC")
                
            return [dict(row) for row in cursor.fetchall()]

    def sync_library(self):
        """
        Elimina registros de la base de datos si el archivo físico ya no existe en el sistema de archivos.
        Útil para mantener la base de datos sincronizada si el usuario borra archivos manualmente.
        
        Returns:
            int: Cantidad de registros eliminados.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Seleccionamos ID y ruta de todos los registros
            cursor.execute("SELECT id, file_path FROM media_library")
            records = cursor.fetchall()
            
            to_delete = []
            for record_id, file_path in records:
                # Comprobamos si el archivo de la ruta ya no existe localmente
                if not file_path or not os.path.exists(file_path):
                    to_delete.append(record_id)
            
            if to_delete:
                # Eliminamos todos los registros perdidos usando executemany para mayor eficiencia
                cursor.executemany("DELETE FROM media_library WHERE id = ?", [(rid,) for rid in to_delete])
                conn.commit()
            return len(to_delete)

    def delete_media(self, media_id: int):
        """
        Elimina un registro de medio por su ID y también borra el archivo físico correspondiente.
        
        Args:
            media_id (int): El identificador único del medio a eliminar.
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Primero, obtenemos la ruta del archivo del registro
            cursor.execute("SELECT file_path FROM media_library WHERE id = ?", (media_id,))
            result = cursor.fetchone()
            
            if result:
                file_path = result[0]
                # Eliminamos el registro de la base de datos
                cursor.execute("DELETE FROM media_library WHERE id = ?", (media_id,))
                conn.commit()
                
                # Eliminamos el archivo físico si aún existe
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        return True
                    except OSError as e:
                        # Imprimimos error si no se pudo eliminar (ej. archivo en uso)
                        print(f"Error deleting file {file_path}: {e}")
                        return False
            return False

# Instancia singleton (global) para facilitar la importación y el acceso a la base de datos
db = DatabaseManager()
